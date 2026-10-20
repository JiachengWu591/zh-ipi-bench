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
DEFAULT_DATA = ROOT / "data" / "generated" / "v0.jsonl"
RAW_DIR = ROOT / "results" / "raw"

KINDS = (
    "keyword-en",
    "keyword-zh",
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
        build.write_jsonl(
            build.build_samples(build.load_intents(), build.load_hard_negatives()),
            path,
        )
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
    parser.add_argument("--out-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="smoke test: every k-th sample")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--judge-model", default="")
    parser.add_argument("--pg2-revision", default=None)
    parser.add_argument("--qwen-revision", default=None)
    parser.add_argument("--community-revision", default=None)
    args = parser.parse_args()

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
