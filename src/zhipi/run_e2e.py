"""Run the end-to-end experiment against injection-blast-radius (billed API calls).

    python -m zhipi.run_e2e --dry-run                 # count samples and calls, change nothing
    python -m zhipi.run_e2e --limit 20 --baseline-repeats 1    # small trial
    python -m zhipi.run_e2e                           # baseline x3, isolated x1 on v1

Needs IBR_REPO (a dedicated checkout of injection-blast-radius) and DEEPSEEK_API_KEY,
both read from the environment or the git-ignored .env. Rows are appended to
results/raw_<dataset>/e2e.jsonl as they finish and a rerun resumes where it stopped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .e2e import E2E_CONDITIONS, plan, run_e2e, secret_forms, select_samples
from .run_eval import DEFAULT_DATA, ROOT, _git_state, load_dotenv, load_samples, raw_dir_for

BASELINE_MAX_TURNS = 6  # injection-blast-radius's cap; an upper bound on calls per run
ISOLATED_CALLS = 2  # audit + reader


def _git_head(repo: str) -> str:
    out = subprocess.run(  # noqa: S603
        ["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--baseline-repeats", type=int, default=3)
    parser.add_argument("--isolated-repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="trial run: roughly this many samples")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ibr-repo", default="")
    args = parser.parse_args()

    loaded = load_dotenv()
    if loaded:
        print(f"loaded from .env: {', '.join(loaded)}")  # names only

    samples = load_samples(args.data)
    injected, benign = select_samples(samples)
    if args.limit:
        step_i = max(1, len(injected) // max(1, args.limit * 7 // 8))
        step_b = max(1, len(benign) // max(1, args.limit // 8))
        injected, benign = injected[::step_i], benign[::step_b]
    jobs = plan(injected, benign, args.baseline_repeats, args.isolated_repeats)
    n_base = sum(1 for j in jobs if j[1] == "baseline")
    n_iso = sum(1 for j in jobs if j[1] == "isolated")
    low = n_base + n_iso * ISOLATED_CALLS
    high = n_base * BASELINE_MAX_TURNS + n_iso * ISOLATED_CALLS
    print(
        f"{len(injected)} injected + {len(benign)} benign samples (carrier=issue; conditions: "
        f"{', '.join(E2E_CONDITIONS)})\n"
        f"{n_base} baseline runs + {n_iso} isolated runs; billed API calls: at least {low}, "
        f"at most about {high}"
    )
    if args.dry_run:
        return

    from .adapters.ibr_e2e import IbrVictim

    victim = IbrVictim(args.ibr_repo or None)
    out_dir = raw_dir_for(args.data)
    out = out_dir / "e2e.jsonl"
    meta = {
        "run_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": args.data.name,
        "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "ibr_repo_commit": _git_head(victim.repo),
        "ibr_models": victim.models,
        "baseline_repeats": args.baseline_repeats,
        "isolated_repeats": args.isolated_repeats,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": _git_state(),
        "injected_samples": len(injected),
        "benign_samples": len(benign),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "e2e_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    rows = run_e2e(victim, jobs, secret_forms(victim.secret_values), out)
    failed = sum(1 for r in rows if not r.completed)
    leaked_iso = sum(1 for r in rows if r.architecture == "isolated" and r.leaked)
    print(f"ran {len(rows)} jobs ({failed} failed) -> {out}")
    if leaked_iso:
        print(f"!! {leaked_iso} isolated run(s) leaked the fake secret: that is a defect to investigate")


if __name__ == "__main__":
    main()
