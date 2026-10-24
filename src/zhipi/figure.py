"""The README results figure, generated from the committed rows (stdlib only).

    python -m zhipi.figure          # writes assets/results.svg

Two panels, both computed from `results/rows/` and the rebuilt datasets, so the picture
is held to the same standard as the tables: `python -m zhipi.verify` regenerates it and
fails if the committed file differs.

Left: each detector's detection rate against its false-positive rate on v1 (top-left is
good; top-right flags everything). Right: attack success of the undefended agent against
the isolated pipeline with its audit bypassed, in the three end-to-end settings. Bars are
rates, whiskers are 95% Wilson intervals. Runs of one sample are not independent, so the
intervals are narrower than the true uncertainty; the figure says so.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

from . import build
from .e2e import collapse, load_rows
from .release import ROWS_DIR
from .run_eval import ROOT
from .schemas import Sample
from .stats import wilson_interval

OUT = ROOT / "assets" / "results.svg"

# (label, rows file under results/rows/v1, kind). `kind` only picks the colour.
DETECTORS = (
    ("DeepSeek judge", "deepseek-judge__high_risk.jsonl", "works"),
    ("Horizon classifier", "prompt-injection-guard-base__t0.5.jsonl", "works"),
    ("protectai (English-only)", "deberta-v3-base-prompt-injection-v2__t0.5.jsonl", "over"),
    ("community mBERT", "community-mbert-injection.jsonl", "over"),
    ("keyword regex (zh)", "keyword-zh.jsonl", "blind"),
    ("Qwen3Guard (wrong tool)", "qwen3guard-gen-0.6b__unsafe_ctrv.jsonl", "blind"),
)
# (label, dataset version, e2e rows file)
E2E_SETTINGS = (
    ("DeepSeek v4-flash, v1 data", "v1", "e2e.jsonl"),
    ("DeepSeek v4-flash, v2 data", "v2", "e2e.jsonl"),
    ("Qwen2.5-7B (local), v2 data", "v2", "e2e_qwen25-7b.jsonl"),
)
COLORS = {"works": "#1b7f5c", "over": "#c0392b", "blind": "#6b7280"}
INK, MUTED, GRID = "#111827", "#6b7280", "#e5e7eb"
BASELINE_COLOR, ISOLATED_COLOR = "#c0392b", "#1b7f5c"

# Label offsets (dx, dy, anchor) per detector so labels do not collide.
LABEL_AT = {
    "DeepSeek judge": (12, -8, "start"),
    "Horizon classifier": (4, 22, "start"),
    "protectai (English-only)": (0, -14, "middle"),
    "community mBERT": (-12, 18, "end"),
    "keyword regex (zh)": (12, -7, "start"),
    "Qwen3Guard (wrong tool)": (12, 13, "start"),
}


@dataclass(frozen=True)
class DetectorPoint:
    label: str
    kind: str
    det_k: int
    det_n: int
    fp_k: int
    fp_n: int


@dataclass(frozen=True)
class E2EPoint:
    label: str
    base_k: int
    base_n: int
    iso_k: int
    iso_n: int


def detector_points(rows_dir: Path, samples: dict[str, Sample]) -> list[DetectorPoint]:
    points = []
    for label, filename, kind in DETECTORS:
        det_k = det_n = fp_k = fp_n = 0
        for line in (rows_dir / "v1" / filename).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if not row["completed"]:
                continue
            if samples[row["sample_id"]].label == "injected":
                det_n += 1
                det_k += bool(row["flagged"])
            else:
                fp_n += 1
                fp_k += bool(row["flagged"])
        points.append(DetectorPoint(label, kind, det_k, det_n, fp_k, fp_n))
    return points


def e2e_points(rows_dir: Path, datasets: dict[str, dict[str, Sample]]) -> list[E2EPoint]:
    points = []
    for label, version, filename in E2E_SETTINGS:
        rows = collapse(load_rows(rows_dir / version / filename))
        counts = {"baseline": [0, 0], "isolated": [0, 0]}
        for r in rows:
            if r.completed and datasets[version][r.sample_id].label == "injected":
                counts[r.architecture][1] += 1
                counts[r.architecture][0] += int(r.leaked)
        points.append(E2EPoint(label, *counts["baseline"], *counts["isolated"]))
    return points


def _f(x: float) -> str:
    return f"{x:.1f}"


def _pct(k: int, n: int) -> str:
    if k == 0:
        return "0%"
    value = 100 * k / n
    return f"{value:.1f}%" if value < 10 else f"{value:.0f}%"


def _text(x: float, y: float, content: str, *, size: int = 12, anchor: str = "start",
          fill: str = INK, weight: str = "normal") -> str:
    return (
        f'<text x="{_f(x)}" y="{_f(y)}" font-size="{size}" text-anchor="{anchor}" '
        f'fill="{fill}" font-weight="{weight}">{escape(content)}</text>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, stroke: str, width: float = 1.0,
          opacity: float = 1.0) -> str:
    return (
        f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-opacity="{opacity}"/>'
    )


def _left_panel(points: list[DetectorPoint]) -> list[str]:
    x0, x1, y0, y1 = 80.0, 450.0, 78.0, 352.0
    pad = 0.03

    def X(p: float) -> float:
        return x0 + (p + pad) / (1 + 2 * pad) * (x1 - x0)

    def Y(p: float) -> float:
        return y1 - (p + pad) / (1 + 2 * pad) * (y1 - y0)

    out = [_text(x0 - 40, 50, "Detectors: catch injections without flagging benign text", size=14, weight="bold")]
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        out.append(_line(x0, Y(tick), x1, Y(tick), GRID))
        out.append(_line(X(tick), y0, X(tick), y1, GRID))
        out.append(_text(x0 - 8, Y(tick) + 4, f"{int(tick * 100)}%", size=11, anchor="end", fill=MUTED))
        out.append(_text(X(tick), y1 + 16, f"{int(tick * 100)}%", size=11, anchor="middle", fill=MUTED))
    out.append(_text((x0 + x1) / 2, y1 + 36, "false positives on benign text (lower is better)", size=12, anchor="middle", fill=MUTED))
    out.append(_text(22, (y0 + y1) / 2, "detection of injections (higher is better)", size=12, anchor="middle", fill=MUTED)
               .replace("<text ", f'<text transform="rotate(-90 22 {_f((y0 + y1) / 2)})" ', 1))
    for p in points:
        det, fp = p.det_k / p.det_n, p.fp_k / p.fp_n
        det_lo, det_hi = wilson_interval(p.det_k, p.det_n)
        fp_lo, fp_hi = wilson_interval(p.fp_k, p.fp_n)
        color = COLORS[p.kind]
        out.append(_line(X(fp_lo), Y(det), X(fp_hi), Y(det), color, 1.6, 0.55))
        out.append(_line(X(fp), Y(det_hi), X(fp), Y(det_lo), color, 1.6, 0.55))
        out.append(f'<circle cx="{_f(X(fp))}" cy="{_f(Y(det))}" r="5.5" fill="{color}"/>')
        dx, dy, anchor = LABEL_AT[p.label]
        out.append(_text(X(fp) + dx, Y(det) + dy, f"{p.label}  {det:.0%} / {fp:.0%}", size=11.5, anchor=anchor, fill=color))
    legend_y = y1 + 62
    for i, (kind, name) in enumerate((("works", "works"), ("over", "flags benign text too"), ("blind", "blind or wrong tool"))):
        lx = x0 + [0, 70, 232][i]
        out.append(f'<circle cx="{_f(lx)}" cy="{_f(legend_y - 4)}" r="4.5" fill="{COLORS[kind]}"/>')
        out.append(_text(lx + 10, legend_y, name, size=11, fill=MUTED))
    return out


def _right_panel(points: list[E2EPoint]) -> list[str]:
    x0, x1 = 592.0, 890.0
    top = 78.0
    scale_max = 0.20

    def X(p: float) -> float:
        return x0 + min(p, scale_max) / scale_max * (x1 - x0)

    out = [_text(500, 50, "End to end: does the fake secret reach the output?", size=14, weight="bold")]
    block, bar_h, gap = 84.0, 20.0, 6.0
    bottom = top + block * len(points) - 12
    for tick in (0.0, 0.05, 0.10, 0.15, 0.20):
        out.append(_line(X(tick), top - 4, X(tick), bottom, GRID))
        out.append(_text(X(tick), bottom + 16, f"{int(round(tick * 100))}%", size=11, anchor="middle", fill=MUTED))
    out.append(_text((x0 + x1) / 2, bottom + 36, "attack success (share of injected runs that leaked; lower is better)", size=12, anchor="middle", fill=MUTED))
    for i, p in enumerate(points):
        y = top + i * block
        out.append(_text(500, y + 8, p.label, size=12, weight="bold"))
        for j, (name, k, n, color) in enumerate((("undefended agent", p.base_k, p.base_n, BASELINE_COLOR),
                                                  ("isolated pipeline, audit bypassed", p.iso_k, p.iso_n, ISOLATED_COLOR))):
            by = y + 18 + j * (bar_h + gap)
            rate = k / n
            lo, hi = wilson_interval(k, n)
            width = max(X(rate) - x0, 2.0)
            out.append(f'<rect x="{_f(x0)}" y="{_f(by)}" width="{_f(width)}" height="{_f(bar_h)}" fill="{color}" fill-opacity="0.85"/>')
            cy = by + bar_h / 2
            out.append(_line(X(lo), cy, X(hi), cy, INK, 1.4))
            out.append(_line(X(lo), cy - 4, X(lo), cy + 4, INK, 1.4))
            out.append(_line(X(hi), cy - 4, X(hi), cy + 4, INK, 1.4))
            out.append(_text(max(X(rate), X(hi)) + 8, cy + 4, f"{k}/{n} ({_pct(k, n)})", size=11.5, fill=INK))
            out.append(_text(x0 - 8, cy + 4, "undefended" if j == 0 else "isolated", size=10.5, anchor="end", fill=color))
    return out


def render(rows_dir: Path = ROWS_DIR) -> str:
    datasets = {v: {s.sample_id: s for s in build.build_version(v)} for v in ("v1", "v2")}
    det = detector_points(rows_dir, datasets["v1"])
    e2e = e2e_points(rows_dir, datasets)
    width, height = 960, 470
    desc = (
        "Left: detection rate against false-positive rate for six detectors on the v1 data. "
        "Right: attack success of an undefended agent versus the isolated pipeline in three "
        "end-to-end settings; the isolated pipeline leaked in none of the runs."
    )
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'font-family="Segoe UI, DejaVu Sans, Arial, sans-serif" role="img" aria-labelledby="t d">',
        "<title id=\"t\">zh-ipi-bench results</title>",
        f'<desc id="d">{escape(desc)}</desc>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="#ffffff" stroke="{GRID}"/>',
        *_left_panel(det),
        _line(478, 36, 478, height - 44, GRID),
        *_right_panel(e2e),
        _text(width / 2, height - 14,
              "95% Wilson intervals. Samples and runs are treated as independent, so the intervals are narrower than the true "
              "uncertainty. Details: paper/REPORT.md",
              size=10.5, anchor="middle", fill=MUTED),
        "</svg>",
    ]
    return "\n".join(body) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
