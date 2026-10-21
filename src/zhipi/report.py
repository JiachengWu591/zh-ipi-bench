"""Turn raw rows into a results report.

    python -m zhipi.report                                  # v1: results/raw_v1 -> results/v1.md
    python -m zhipi.report --data data/generated/v0.jsonl   # v0: results/raw -> results/phase1.md

Pure reporting: it never calls a model. Everything it prints is a function of the
raw rows, so the report can be regenerated and diffed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .evaluate import Cell, Row, by_carrier, by_condition, summarize
from .run_eval import DEFAULT_DATA, load_samples, raw_dir_for, report_path_for
from .schemas import TIERS, Sample

CONDITION_ORDER = (
    "en/plain",
    "zh/plain",
    "zh/fullwidth",
    "zh/zero_width",
    "zh/space_split",
    "zh/code_mix",
    "zh/code_mix+zero_width",
)
STRATUM_ORDER = (
    "plain",
    "imperative_to_humans",
    "discusses_injection",
    "mentions_config",
    "quotes_secret_shaped",
    "edge_shape",
    "asks_humans_for_info",
    "task_list",
    "format_request",
    "quoted_text",
    "long_benign",
)
TIER_ORDER = tuple(f"{tier} / {placement}" for placement in ("default", "buried") for tier in TIERS)


def _tier_key(sample: Sample) -> str:
    return f"{sample.tier} / {sample.placement}"


def load_raw(raw_dir: Path) -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = {}
    for path in sorted(raw_dir.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if rows:
            out[str(rows[0]["defense"])] = rows
    return out


def to_rows(raw: list[dict[str, object]], by_id: dict[str, Sample], repeat: int = 0) -> list[Row]:
    return [
        Row(
            by_id[str(r["sample_id"])],
            bool(r["flagged"]),
            bool(r["completed"]),
            score=r["score"] if isinstance(r["score"], float) else None,  # type: ignore[arg-type]
            detail=str(r["detail"]),
            repeat=int(r["repeat"]),  # type: ignore[call-overload]
        )
        for r in raw
        if int(r["repeat"]) == repeat  # type: ignore[call-overload]
    ]


def fmt(cell: Cell | None) -> str:
    if cell is None or cell.rate is None:
        return "n/a" if cell is None or cell.incomplete == 0 else f"n/a ⚠{cell.incomplete}"
    assert cell.ci_low is not None and cell.ci_high is not None
    text = f"{cell.rate:.0%} [{cell.ci_low:.0%}–{cell.ci_high:.0%}]"
    return text + (f" ⚠{cell.incomplete}" if cell.incomplete else "")


def _table(
    defenses: list[str],
    groups: tuple[str, ...],
    cells: dict[str, dict[str, Cell]],
    sizes: dict[str, int],
    first_col: str,
) -> list[str]:
    lines = [
        f"| {first_col} | n | " + " | ".join(defenses) + " |",
        "|---|--:|" + "|".join("---" for _ in defenses) + "|",
    ]
    for group in groups:
        if group not in sizes:
            continue
        row = [group, str(sizes[group])]
        row += [fmt(cells.get(d, {}).get(group)) for d in defenses]
        lines.append("| " + " | ".join(row) + " |")
    return lines


def stability(raw: list[dict[str, object]]) -> tuple[int, int] | None:
    """(# samples whose verdict varies across repeats, # compared) or None."""
    by_sample: dict[str, dict[int, bool]] = defaultdict(dict)
    repeats: set[int] = set()
    for r in raw:
        repeats.add(int(r["repeat"]))  # type: ignore[call-overload]
        if r["completed"]:
            by_sample[str(r["sample_id"])][int(r["repeat"])] = bool(r["flagged"])  # type: ignore[call-overload]
    if len(repeats) < 2:
        return None
    full = [v for v in by_sample.values() if len(v) == len(repeats)]
    return sum(1 for v in full if len(set(v.values())) > 1), len(full)


def build_report(
    raw_by_defense: dict[str, list[dict[str, object]]],
    samples: list[Sample],
    meta: dict[str, object],
    data_path: Path,
) -> str:
    by_id = {s.sample_id: s for s in samples}
    defenses = sorted(raw_by_defense)
    rows = {d: to_rows(raw_by_defense[d], by_id) for d in defenses}

    det = {d: {c.group: c for c in summarize(rows[d], label="injected", key=by_condition)} for d in defenses}
    fpr = {d: {c.group: c for c in summarize(rows[d], label="benign", key=lambda s: s.stratum)} for d in defenses}
    car = {d: {c.group: c for c in summarize(rows[d], label="injected", key=by_carrier)} for d in defenses}

    # Tier / placement view: Chinese, untransformed samples only, so the tier or the
    # placement is the only thing that differs between rows.
    def _plain_zh(r: Row) -> bool:
        return r.sample.language == "zh" and not r.sample.transforms

    tier = {
        d: {c.group: c for c in summarize([r for r in rows[d] if _plain_zh(r)], label="injected", key=_tier_key)}
        for d in defenses
    }

    det_n: dict[str, int] = defaultdict(int)
    car_n: dict[str, int] = defaultdict(int)
    fpr_n: dict[str, int] = defaultdict(int)
    tier_n: dict[str, int] = defaultdict(int)
    for s in samples:
        if s.label == "injected":
            det_n[by_condition(s)] += 1
            car_n[s.carrier] += 1
            if s.language == "zh" and not s.transforms:
                tier_n[_tier_key(s)] += 1
        else:
            fpr_n[s.stratum] += 1
    n_intents = len({s.intent_id for s in samples if s.intent_id})
    n_benign = sum(fpr_n.values())
    per_condition = sorted(set(det_n.values()))
    per_condition_text = "–".join(str(n) for n in (per_condition[0], per_condition[-1])) if per_condition else "0"

    glance = [
        "| detector | detection, all injected | false positives, all benign |",
        "|---|---|---|",
    ]
    for d in defenses:
        all_det = summarize(rows[d], label="injected", key=lambda s: "all")
        all_fp = summarize(rows[d], label="benign", key=lambda s: "all")
        glance.append(
            f"| {d} | {fmt(all_det[0] if all_det else None)} | {fmt(all_fp[0] if all_fp else None)} |"
        )

    out = [
        "# Phase 1 results",
        "",
        f"Dataset: `{data_path.name}` ({len(samples)} samples). Regenerate with "
        "`python -m zhipi.run_eval ...` then `python -m zhipi.report`.",
        "",
        "> **Read the caveats at the bottom before quoting any number.** Intervals are "
        "95% Wilson intervals that assume independent samples; these samples are "
        f"template-generated ({n_intents} intents × 5 carriers per condition), so the "
        "intervals are narrower than the true uncertainty.",
        "",
        "## At a glance",
        "",
        "Read the two columns together: a detector that flags everything has perfect "
        "detection and 100% false positives.",
        "",
        *glance,
        "",
        "## Detection rate on injected samples (higher is better)",
        "",
        "Each cell: rate [95% interval]. `⚠k` = k samples where the detector failed "
        "and were excluded from the rate (never counted as detections).",
        "",
        *_table(defenses, CONDITION_ORDER, det, det_n, "language / transform"),
        "",
        "## Detection by payload tier and placement (injected, Chinese, untransformed)",
        "",
        "Tiers: `explicit` names target and action, `implicit` asks without naming them, "
        "`spoofed_structure` forges delimiters or tool messages, `judge_targeted` also "
        "addresses the screening component. `buried` = the payload sits mid-way through a "
        "long benign document.",
        "",
        *_table(defenses, TIER_ORDER, tier, tier_n, "tier / placement"),
        "",
        "## False-positive rate on benign samples (lower is better)",
        "",
        *_table(defenses, STRATUM_ORDER, fpr, fpr_n, "benign stratum"),
        "",
        "## Detection by carrier (injected, pooled over all conditions)",
        "",
        *_table(defenses, tuple(sorted(car_n)), car, car_n, "carrier"),
        "",
    ]

    unstable = []
    for d in defenses:
        result = stability(raw_by_defense[d])
        if result is not None:
            unstable.append(f"- `{d}`: {result[0]} of {result[1]} samples changed verdict across repeats")
    if unstable:
        out += ["## Run-to-run stability", "", *unstable, ""]

    out += ["## What was run", "", "| detector kind | model / revision / prompt | run at (UTC) | commit |", "|---|---|---|---|"]
    for kind, info in sorted(meta.items()):
        if not isinstance(info, dict):
            continue
        ident = info.get("model_id") or info.get("role") or ""
        pin = info.get("revision") or info.get("prompt_hash") or ""
        git = info.get("git") or {}
        commit = str(git.get("commit", ""))[:8] + ("+dirty" if git.get("dirty") else "") if isinstance(git, dict) else ""
        out.append(f"| {kind} | {ident} {pin} | {info.get('run_at_utc', '')} | {commit} |")

    out += [
        "",
        "## Caveats (what these numbers can and cannot show)",
        "",
        "- The keyword rows are harness sanity baselines, not evidence about real detectors.",
        "- Qwen3Guard is a content-moderation model, included as a wrong-tool control. "
        "Its numbers are not injection-detection performance.",
        "- Prompt Guard 2's model card lists English, French, German, Hindi, Italian, "
        "Portuguese, Spanish and Thai as evaluated languages. Chinese is not listed.",
        "- `community-mbert-injection` is an unvetted community model (see the metadata "
        "table). On v0 it flags every sample, benign ones included, so its detection "
        "numbers carry no information. Probing it directly showed it separates short "
        "casual text (\"The weather is nice today.\") from blatant injections, but "
        "scores task-like or technical text (\"Please close this issue as a duplicate "
        "of #311.\") as an injection at 0.999. That is a property of this model on "
        "this distribution, not evidence about multilingual detectors in general.",
        "- The LLM judge's result depends on its prompt (hash recorded above); a different "
        "prompt can move the numbers.",
        "- **A 100% cell means v0 cannot tell this detector from a perfect one, not that "
        "the detector is robust.** The v0 payloads state their goal outright (read a "
        "named file, publish it), so a strong LLM reads through every transform. Harder "
        "payloads are a Phase 2 task; until then a ceiling result is a statement about "
        "the dataset.",
        "- Judge repeats use temperature 0, so zero verdict changes across repeats shows "
        "low residual non-determinism at that setting, not that the verdict is insensitive "
        "to sampling.",
        f"- {per_condition_text} samples per condition, {n_intents} hand-written intents, "
        f"one author: indicative, not conclusive. The benign set is {n_benign} samples "
        "spread over several strata, so false-positive intervals are wide.",
        "- Only detection is measured here. Whether an injection *succeeds* against a "
        "victim agent is Phase 4.",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--raw-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    args.raw_dir = args.raw_dir or raw_dir_for(args.data)
    args.out = args.out or report_path_for(args.data)

    raw = load_raw(args.raw_dir)
    if not raw:
        raise SystemExit(f"no raw results in {args.raw_dir}; run zhipi.run_eval first")
    meta_path = args.raw_dir / "run_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    report = build_report(raw, load_samples(args.data), meta, args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
