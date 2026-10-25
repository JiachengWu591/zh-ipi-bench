"""Reproduce the released results from the committed rows. No model, key or network.

    python -m zhipi.verify            # check; exit code 1 if anything differs
    python -m zhipi.verify --update   # rewrite results/*.md from the rows (after a code change)

Four checks:

1. every dataset version rebuilds from the seed files to the checksum in
   `release/MANIFEST.json` (so v0 and v1 really are frozen);
2. every table in `results/*.md` is regenerated from `results/rows/` and compared
   byte for byte with the committed file;
3. the README figure `assets/results.svg` and the second-annotator report
   `results/annotation.md` (from the committed answers) are regenerated the same way;
4. nothing here calls a model, so a pass means the numbers in the report are a pure
   function of the committed rows and the committed code.

What a pass does NOT show: that the rows themselves are right (they came from model
runs, recorded with commit, model revision and dataset hash in `run_meta.json`), or that
rerunning a model today would reproduce them (hosted models drift).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import annotate, figure
from .e2e import collapse, load_rows
from .release import MANIFEST, ROWS_DIR, dataset_entries
from .report import build_report, load_raw
from .report_e2e import build_e2e_report
from .run_eval import ROOT, load_samples

RESULTS = ROOT / "results"
FIGURE = figure.OUT


@dataclass(frozen=True)
class Job:
    report: str  # file under results/
    kind: str  # "detectors" | "e2e"
    version: str
    tag: str = ""


JOBS = (
    Job("phase1.md", "detectors", "v0"),
    Job("v1.md", "detectors", "v1"),
    Job("v3_study.md", "detectors", "v3_study"),
    Job("v1_e2e.md", "e2e", "v1"),
    Job("v2_e2e.md", "e2e", "v2"),
    Job("v2_e2e_qwen25-7b.md", "e2e", "v2", "qwen25-7b"),
)


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def render(job: Job, data_dir: Path, rows_dir: Path = ROWS_DIR) -> str:
    data_path = data_dir / f"{job.version}.jsonl"
    samples = load_samples(data_path)
    raw = rows_dir / job.version
    if job.kind == "detectors":
        return build_report(load_raw(raw), samples, _json(raw / "run_meta.json"), data_path)
    suffix = f"_{job.tag}" if job.tag else ""
    rows = collapse(load_rows(raw / f"e2e{suffix}.jsonl"))
    return build_e2e_report(rows, samples, _json(raw / f"e2e{suffix}_meta.json"), data_path)


def check_datasets(data_dir: Path) -> list[tuple[str, bool, str]]:
    expected = _json(MANIFEST).get("datasets", {})
    got = dataset_entries(data_dir)
    out = []
    for version, info in got.items():
        want = expected.get(version) if isinstance(expected, dict) else None
        ok = isinstance(want, dict) and all(
            want.get(k) == info[k] for k in ("samples", "fingerprint", "file_sha256")
        )
        out.append((f"dataset {version}", ok, f"{info['samples']} samples, {str(info['file_sha256'])[:10]}"))
    return out


def run(update: bool = False) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        results += check_datasets(data_dir)
        for job in JOBS:
            target = RESULTS / job.report
            try:
                text = render(job, data_dir)
            except Exception as exc:  # noqa: BLE001 - reported, not hidden
                results.append((f"report {job.report}", False, f"could not regenerate: {type(exc).__name__}: {exc}"))
                continue
            if update:
                target.write_text(text, encoding="utf-8", newline="\n")
                results.append((f"report {job.report}", True, "rewritten"))
                continue
            current = target.read_text(encoding="utf-8") if target.exists() else None
            if current == text:
                results.append((f"report {job.report}", True, f"{len(text):,} chars identical"))
            else:
                results.append((f"report {job.report}", False, "differs from the committed file"))
    results.append(_check_figure(update))
    results.append(_check_annotation(update))
    return results


def _check_annotation(update: bool) -> tuple[str, bool, str]:
    name = f"report {annotate.COMMITTED_REPORT.name}"
    try:
        text = annotate.render_committed_report()
    except Exception as exc:  # noqa: BLE001 - reported, not hidden
        return (name, False, f"could not regenerate: {type(exc).__name__}: {exc}")
    if update:
        annotate.COMMITTED_REPORT.write_text(text, encoding="utf-8", newline="\n")
        return (name, True, "rewritten")
    current = (
        annotate.COMMITTED_REPORT.read_text(encoding="utf-8")
        if annotate.COMMITTED_REPORT.exists() else None
    )
    if current == text:
        return (name, True, f"{len(text):,} chars identical")
    return (name, False, "differs from the committed file")


def _check_figure(update: bool) -> tuple[str, bool, str]:
    name = f"figure {FIGURE.relative_to(ROOT).as_posix()}"
    try:
        text = figure.render()
    except Exception as exc:  # noqa: BLE001 - reported, not hidden
        return (name, False, f"could not regenerate: {type(exc).__name__}: {exc}")
    if update:
        FIGURE.parent.mkdir(parents=True, exist_ok=True)
        FIGURE.write_text(text, encoding="utf-8", newline="\n")
        return (name, True, "rewritten")
    current = FIGURE.read_text(encoding="utf-8") if FIGURE.exists() else None
    if current == text:
        return (name, True, f"{len(text):,} chars identical")
    return (name, False, "differs from the committed file")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="rewrite the committed reports")
    args = parser.parse_args()
    results = run(update=args.update)
    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {detail}")
    bad = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
