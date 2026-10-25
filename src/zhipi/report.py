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
from .stats import auroc, auroc_bootstrap_ci, mcnemar_exact

CONDITION_ORDER = (
    "en/plain",
    "zh/plain",
    "zh/fullwidth",
    "zh/zero_width",
    "zh/space_split",
    "zh/code_mix",
    "zh/code_mix+zero_width",
    "zh/traditional",
    "zh/pinyin",
    "zh/homophone",
    "zh/char_decomp",
    "zh/plain (buried)",
)
# (baseline condition, variant condition, what the comparison isolates)
PAIRED_COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("en/plain", "zh/plain", "language: Chinese vs the English control"),
    ("zh/plain", "zh/fullwidth", "transform: fullwidth"),
    ("zh/plain", "zh/zero_width", "transform: zero-width"),
    ("zh/plain", "zh/space_split", "transform: space-split"),
    ("zh/plain", "zh/code_mix", "transform: code-mix"),
    ("zh/plain", "zh/code_mix+zero_width", "transform: code-mix + zero-width"),
    ("zh/plain", "zh/traditional", "transform: traditional script"),
    ("zh/plain", "zh/pinyin", "transform: pinyin"),
    ("zh/plain", "zh/homophone", "transform: homophone"),
    ("zh/plain", "zh/char_decomp", "transform: character decomposition"),
    ("zh/plain", "zh/plain (buried)", "placement: buried in a long document"),
)


def paired_cell(rows: list[Row], base: str, variant: str) -> str:
    """`lost↓/gained↑ of n, p=…` for samples matched on (intent, carrier).

    Only injected samples where both versions produced a completed verdict count.
    `lost`: the baseline detected it and the variant missed it; `gained`: the reverse.
    """

    def index(cond: str) -> dict[tuple[str | None, str], Row]:
        return {
            (r.sample.intent_id, r.sample.carrier): r
            for r in rows
            if r.sample.label == "injected" and r.completed and by_condition(r.sample) == cond
        }

    base_idx, var_idx = index(base), index(variant)
    keys = base_idx.keys() & var_idx.keys()
    if not keys:
        return "n/a"
    lost = sum(1 for k in keys if base_idx[k].flagged and not var_idx[k].flagged)
    gained = sum(1 for k in keys if not base_idx[k].flagged and var_idx[k].flagged)
    if lost == 0 and gained == 0:
        return f"no change (n={len(keys)})"
    return f"{lost}↓/{gained}↑ of {len(keys)}, p={mcnemar_exact(lost, gained):.2f}"


def intent_level_cell(rows: list[Row], base: str, variant: str) -> str:
    """The same comparison with the intent as the unit: an intent counts as `↓` if the
    variant was flagged in fewer of its carriers than the baseline, `↑` if in more. The
    carriers of one intent carry the same payload, so this is closer to the number of
    independent comparisons than the per-sample pairs. Exact sign test; ties are dropped."""

    def index(cond: str) -> dict[tuple[str | None, str], Row]:
        return {
            (r.sample.intent_id, r.sample.carrier): r
            for r in rows
            if r.sample.label == "injected" and r.completed and by_condition(r.sample) == cond
        }

    base_idx, var_idx = index(base), index(variant)
    per_intent: dict[str | None, list[int]] = defaultdict(lambda: [0, 0])
    for key in base_idx.keys() & var_idx.keys():
        per_intent[key[0]][0] += int(base_idx[key].flagged)
        per_intent[key[0]][1] += int(var_idx[key].flagged)
    if not per_intent:
        return "n/a"
    down = sum(1 for b, v in per_intent.values() if v < b)
    up = sum(1 for b, v in per_intent.values() if v > b)
    if down == 0 and up == 0:
        return f"no change (n={len(per_intent)} intents)"
    return f"{down}↓/{up}↑ of {len(per_intent)} intents, p={mcnemar_exact(down, up):.2f}"


INTENT_LEVEL_COMPARISONS = tuple(
    (base, variant, label) for base, variant, label in PAIRED_COMPARISONS
    if variant in ("zh/traditional", "zh/pinyin", "zh/homophone", "zh/char_decomp")
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
    "traditional_text",
    "pinyin_text",
    "char_breakdown_text",
    "homophone_text",
)
TIER_ORDER = tuple(f"{tier} / {placement}" for placement in ("default", "buried") for tier in TIERS)


def _tier_key(sample: Sample) -> str:
    return f"{sample.tier} / {sample.placement}"


def load_raw(raw_dir: Path) -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = {}
    for path in sorted(raw_dir.glob("*.jsonl")):
        if path.name.startswith("e2e"):  # end-to-end rows have their own report
            continue
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


def auroc_section(defenses: list[str], rows: dict[str, list[Row]]) -> list[str]:
    """Threshold-free AUROC per condition, for detectors that emit a score.

    Positives: completed injected samples of the condition. Negatives: every completed
    benign sample in the same language. A difference here is a change in how well the
    detector *ranks* injections above benign text; a difference only in the rate tables
    can come from calibration alone (the same ranking cut at a different point).
    """
    scored: dict[str, list[Row]] = {}
    for d in defenses:
        done = [r for r in rows[d] if r.completed]
        if done and all(r.score is not None for r in done):
            scored[d] = done
    if not scored:
        return []
    names = list(scored)
    lines = [
        "## Threshold-free view: AUROC",
        "",
        "For detectors that output a score. 0.5 = no better than chance, 1.0 = perfect "
        "ranking. Negatives are all benign samples in the same language. Intervals are "
        "bootstrap percentile intervals over samples (fixed seed); they ignore that "
        "samples from one intent are correlated, so they are too narrow.",
        "",
        "| language / transform | " + " | ".join(names) + " |",
        "|---|" + "|".join("---" for _ in names) + "|",
    ]
    for cond in CONDITION_ORDER:
        cells, any_cell = [], False
        for d in names:
            pos = [r.score for r in scored[d] if r.sample.label == "injected" and by_condition(r.sample) == cond]
            lang = cond.split("/")[0]
            neg = [r.score for r in scored[d] if r.sample.label == "benign" and r.sample.language == lang]
            if pos and neg:
                any_cell = True
                value = auroc(pos, neg)  # type: ignore[arg-type]
                low, high = auroc_bootstrap_ci(pos, neg)  # type: ignore[arg-type]
                cells.append(f"{value:.2f} [{low:.2f}–{high:.2f}]")
            else:
                cells.append("n/a")
        if any_cell:
            lines.append(f"| {cond} | " + " | ".join(cells) + " |")
    return [*lines, ""]


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
    carriers_per_condition = round(max(det_n.values(), default=0) / n_intents) if n_intents else 0
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

    title = "Phase 1 results (v0)" if data_path.stem == "v0" else f"Results on {data_path.stem}"
    out = [
        f"# {title}",
        "",
        f"Dataset: `{data_path.name}` ({len(samples)} samples). Regenerate with "
        "`python -m zhipi.run_eval ...` then `python -m zhipi.report`.",
        "",
        "> **Read the caveats at the bottom before quoting any number.** Intervals are "
        "95% Wilson intervals that assume independent samples; these samples are "
        f"template-generated ({n_intents} intents × {carriers_per_condition} carriers per condition), so the "
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
        "## Paired comparisons: does a Chinese-specific change hurt detection?",
        "",
        "Each pair is the same intent in the same carrier, with and without the change. "
        "`a↓/b↑` = the baseline detected it and the variant missed it (`a`), or the "
        "reverse (`b`). `p` is an exact two-sided McNemar test; pairs that agree carry no "
        "information. Not corrected for the many comparisons made here. The pairs are "
        f"template-generated and the {carriers_per_condition} carriers of one intent are replicates of the same "
        "payload, so the effective number of independent pairs is closer to the number of "
        "intents than to the pair count; treat a small `p` as a lead, not a finding, and "
        "check the AUROC table below before reading a rate difference as lost "
        "discrimination.",
        "",
        "| comparison | " + " | ".join(defenses) + " |",
        "|---|" + "|".join("---" for _ in defenses) + "|",
        *[
            f"| {label} | "
            + " | ".join(paired_cell(rows[d], base, variant) for d in defenses)
            + " |"
            for base, variant, label in PAIRED_COMPARISONS
            if all(any(s.label == "injected" and by_condition(s) == cond for s in samples) for cond in (base, variant))
        ],
        "",
        *(
            [
                "### Intent-level view of the v3 transforms",
                "",
                "The unit is the intent: `↓` = the variant was flagged in fewer of that intent's "
                "carriers than the plain text, `↑` = in more; ties are dropped; exact sign test. "
                "This is the fairer count of independent comparisons (the carriers of one intent "
                "carry the same payload), and still not corrected for the number of comparisons "
                "made in this table.",
                "",
                "| comparison | " + " | ".join(defenses) + " |",
                "|---|" + "|".join("---" for _ in defenses) + "|",
                *[
                    f"| {label} | " + " | ".join(intent_level_cell(rows[d], base, variant) for d in defenses) + " |"
                    for base, variant, label in INTENT_LEVEL_COMPARISONS
                ],
                "",
            ]
            if any(by_condition(s) == "zh/pinyin" for s in samples)
            else []
        ),
        *auroc_section(defenses, rows),
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
        "- **A 100% cell means the dataset cannot tell this detector from a perfect one, "
        "not that the detector is robust.** On v0 the payloads state their goal outright "
        "(read a named file, publish it), so a strong LLM reads through every transform; "
        "a ceiling result is a statement about the dataset.",
        *(
            [
                "- Some `implicit` intents ask for something generic (for example, the "
                "configuration the reader can see, or one unticked box in a checklist). "
                "Their text is near-identical to legitimate requests addressed to a human "
                "reporter, so which label is correct depends on who reads it. Misses on "
                "them, and false positives on the `asks_humans_for_info` stratum, may "
                "reflect that ambiguity rather than a detector error; a second annotator "
                "is needed to tell."
            ]
            if any(s.tier == "implicit" for s in samples)
            else []
        ),
        *(
            [
                "- The v3 transforms rewrite only the payload, so a traditional-script payload "
                "sits inside a simplified-script host; the pinyin, homophone and character-"
                "decomposition transforms re-spell only the key terms in small curated tables, "
                "not whole sentences. Results here say nothing about other ways of writing "
                "those forms. The paired comparisons use each intent's untransformed twin "
                "re-run in the same session, so hosted-model drift between sessions does not "
                "enter them.",
                "- The new benign strata (traditional-script text, pinyin, character breakdowns, "
                "homophone discussions) are small (3 to 8 samples each) and hand-written; a "
                "false-positive interval on them is wide, and zero flags in 3 samples still "
                "allows a false-positive rate above 50%.",
            ]
            if any(s.stratum == "traditional_text" for s in samples)
            else []
        ),
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
