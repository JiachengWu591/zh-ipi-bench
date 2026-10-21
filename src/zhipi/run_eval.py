"""Run detectors over the dataset; write raw rows and run metadata.

    python -m zhipi.run_eval --defense keyword-en --defense keyword-zh
    python -m zhipi.run_eval --defense qwen3guard
    python -m zhipi.run_eval --defense prompt-guard-2
    python -m zhipi.run_eval --defense deepseek-judge --repeats 3
    python -m zhipi.run_eval --defense deepseek-judge --dry-run

Raw rows go to results/raw/ (git-ignored: they echo prompts and can be large);
`python -m zhipi.report` turns them into results/phase1.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

from . import build
from .cache import ResponseCache
from .defenses import EN_KEYWORDS, ZH_KEYWORDS, Defense
from .evaluate import Row, evaluate
from .schemas import Sample

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "generated" / "v1.jsonl"
RAW_DIR = ROOT / "results" / "raw"


def raw_dir_for(data_path: Path) -> Path:
    """Where raw rows for a dataset live. v0 keeps its original location."""
    return RAW_DIR if data_path.stem == "v0" else RAW_DIR.parent / f"raw_{data_path.stem}"


def report_path_for(data_path: Path) -> Path:
    name = "phase1.md" if data_path.stem == "v0" else f"{data_path.stem}.md"
    return ROOT / "results" / name

KINDS = (
    "keyword-en",
    "keyword-zh",
    "hf-classifier",
    "prompt-guard-2",
    "community-mbert",
    "qwen3guard",
    "deepseek-judge",
    "ibr-audit",
)
STOCHASTIC = {"deepseek-judge", "ibr-audit"}  # repeated calls can disagree
# The model id below is the one injection-blast-radius's CLAUDE.md names. It is
# not verified here; override with --judge-model if the provider says otherwise.
DEFAULT_JUDGE_MODEL = "deepseek-v4-flash"
COMMUNITY_MODEL = "devndeploy/bert-prompt-injection-detector"


def load_dotenv(path: Path = ROOT / ".env") -> list[str]:
    """Load KEY=VALUE lines from a git-ignored `.env` into the environment.

    Returns the *names* that were set (never the values). Already-set variables win,
    so a real environment variable overrides the file, and empty values are skipped.
    """
    if not path.exists():
        return []
    loaded: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip("\"'")
        if name and value and name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded


def load_samples(path: Path) -> list[Sample]:
    if not path.exists():
        print(f"{path} not found; building it from the seed files")
        version = path.stem if path.stem in build.VERSIONS else "v1"
        build.write_jsonl(build.build_version(version), path)
    return [
        Sample.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def slug(name: str) -> str:
    return name.replace("/", "__").replace("+", "_")


def make_defenses(
    kind: str, args: argparse.Namespace, repeat: int, cache: ResponseCache
) -> tuple[list[Defense], dict[str, object]]:
    """Build the defenses for one kind. Heavy imports stay inside the branches."""
    if kind == "keyword-en":
        return [EN_KEYWORDS], {"role": "sanity baseline"}
    if kind == "keyword-zh":
        return [ZH_KEYWORDS], {"role": "sanity baseline"}
    if kind == "prompt-guard-2":
        from .adapters.prompt_guard import (
            PromptGuard2Defense,
            PromptGuard2Runner,
        )

        runner = PromptGuard2Runner(revision=args.pg2_revision)
        return [PromptGuard2Defense(runner, threshold=0.5)], runner.metadata()
    if kind == "hf-classifier":
        # Any binary injection classifier on the Hub: pass --hf-model and the label
        # that means injection. The metadata records the resolved commit.
        from .adapters.prompt_guard import (
            PromptGuard2Defense,
            PromptGuard2Runner,
        )

        if not args.hf_model:
            raise ValueError("hf-classifier needs --hf-model")
        hrunner = PromptGuard2Runner(
            model_id=args.hf_model,
            revision=args.hf_revision,
            positive_labels=tuple(p.strip() for p in args.hf_positive.split(",") if p.strip()),
            role=args.hf_role,
            max_tokens=args.hf_max_tokens,
            stride=args.hf_stride,
        )
        name = args.hf_model.split("/")[-1] + "/" + args.hf_threshold_name
        return [
            PromptGuard2Defense(hrunner, threshold=args.hf_threshold, name=name)
        ], {**hrunner.metadata(), "threshold": args.hf_threshold}
    if kind == "community-mbert":
        # Stand-in for the gated Prompt Guard 2: a community multilingual-BERT
        # injection classifier whose card lists Chinese among its training
        # languages. Unvetted: unknown author, metrics with no stated test set.
        from .adapters.prompt_guard import (
            PromptGuard2Defense,
            PromptGuard2Runner,
        )

        crunner = PromptGuard2Runner(
            model_id=COMMUNITY_MODEL,
            revision=args.community_revision,
            positive_labels=("injection",),
            role="community model, unvetted (stand-in for gated Prompt Guard 2)",
        )
        return [
            PromptGuard2Defense(crunner, threshold=0.5, name="community-mbert-injection")
        ], crunner.metadata()
    if kind == "qwen3guard":
        from .adapters.qwen3guard import (
            RULES,
            Qwen3GuardDefense,
            Qwen3GuardRunner,
        )

        qrunner = Qwen3GuardRunner(revision=args.qwen_revision)
        return [Qwen3GuardDefense(qrunner, r) for r in RULES], qrunner.metadata()
    if kind == "deepseek-judge":
        from .adapters.deepseek_judge import DeepSeekJudge

        model = args.judge_model or os.environ.get("ZHIPI_JUDGE_MODEL") or DEFAULT_JUDGE_MODEL
        judges = [
            DeepSeekJudge(model=model, repeat=repeat, cache=cache, flag_on=flag_on)
            for flag_on in (("high_risk",), ("suspicious", "high_risk"))
        ]
        return list(judges), judges[0].metadata()
    if kind == "ibr-audit":
        from .adapters.ibr_adapter import IbrAuditDefense

        return [IbrAuditDefense()], {"role": "injection-blast-radius audit_only"}
    raise ValueError(f"unknown defense {kind!r} (have: {KINDS})")


def write_rows(defense_name: str, rows: list[Row], out_dir: Path, append: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug(defense_name)}.jsonl"
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {
                        "defense": defense_name,
                        "repeat": row.repeat,
                        "sample_id": row.sample.sample_id,
                        "flagged": row.flagged,
                        "completed": row.completed,
                        "score": row.score,
                        "detail": row.detail,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return path


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _git_state() -> dict[str, object]:
    def run(*cmd: str) -> str:
        return subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {"commit": run("git", "rev-parse", "HEAD"), "dirty": bool(run("git", "status", "--porcelain"))}


def write_meta(
    kind: str, defense_meta: dict[str, object], data_path: Path, out_dir: Path
) -> None:
    meta_path = out_dir / "run_meta.json"
    existing: dict[str, object] = (
        json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    )
    existing[kind] = {
        **defense_meta,
        "run_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {p: _version(p) for p in ("torch", "transformers", "openai")},
        "git": _git_state(),
    }
    meta_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--defense", action="append", required=True, choices=KINDS)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="default: results/raw for v0, results/raw_<name> otherwise")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="smoke test: every k-th sample")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--judge-model", default="")
    parser.add_argument("--pg2-revision", default=None)
    parser.add_argument("--qwen-revision", default=None)
    parser.add_argument("--community-revision", default=None)
    hf = parser.add_argument_group("hf-classifier (any Hub injection classifier)")
    hf.add_argument("--hf-model", default="", help="e.g. Horizon-Labs/prompt-injection-guard-base")
    hf.add_argument("--hf-positive", default="injection", help="label name(s) meaning injection, comma-separated")
    hf.add_argument("--hf-revision", default=None)
    hf.add_argument("--hf-role", default="", help="how to label this detector in the report")
    hf.add_argument("--hf-max-tokens", type=int, default=512)
    hf.add_argument("--hf-stride", type=int, default=64)
    hf.add_argument("--hf-threshold", type=float, default=0.5)
    hf.add_argument("--hf-threshold-name", default="t0.5", help="suffix that distinguishes operating points")
    args = parser.parse_args()
    if args.out_dir is None:
        args.out_dir = raw_dir_for(args.data)

    loaded = load_dotenv()
    if loaded:
        print(f"loaded from .env: {', '.join(loaded)}")  # names only, never values
    samples = load_samples(args.data)
    if args.limit:
        samples = samples[:: max(1, len(samples) // args.limit)]
    print(f"{len(samples)} samples from {args.data}")

    for kind in args.defense:
        repeats = args.repeats if kind in STOCHASTIC else 1
        if args.dry_run:
            billed = kind in {"deepseek-judge", "ibr-audit"}
            print(f"[dry-run] {kind}: {len(samples) * repeats} calls"
                  f"{' (billed API calls)' if billed else ' (local)'}")
            continue
        cache = ResponseCache(args.out_dir / "cache" / f"{kind}.jsonl")
        meta: dict[str, object] = {}
        for repeat in range(repeats):
            defenses, meta = make_defenses(kind, args, repeat, cache)
            for defense in defenses:
                rows = evaluate(defense, samples, repeat=repeat)
                path = write_rows(defense.name, rows, args.out_dir, append=repeat > 0)
                done = sum(r.completed for r in rows)
                flagged = sum(r.flagged and r.completed for r in rows)
                print(f"{defense.name} repeat {repeat}: {done}/{len(rows)} completed, "
                      f"{flagged} flagged -> {path}")
        write_meta(kind, meta, args.data, args.out_dir)


if __name__ == "__main__":
    main()
