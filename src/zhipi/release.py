"""Package the result rows and the dataset for release.

    python -m zhipi.release pack     # raw run output -> results/rows/ (committed)
    python -m zhipi.release dist     # dataset release folder -> dist/zh-ipi-bench/

`pack` copies the per-sample result rows (detector verdicts and end-to-end outcomes)
out of the git-ignored scratch directories into `results/rows/<dataset>/`, leaving out
response caches and trial runs. Those rows are the evidence behind every table in
`results/*.md`; with them `python -m zhipi.verify` regenerates the tables with no model,
no key and no network. They contain model outputs but no credentials: the only "secret"
anywhere is the fixed fake placeholder.

`dist` builds the folder that is uploaded as the dataset: the data files, the seed files,
a checksum manifest, and the dataset card.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from . import build
from .run_eval import ROOT

ROWS_DIR = ROOT / "results" / "rows"
MANIFEST = ROOT / "release" / "MANIFEST.json"
CARD_TEMPLATE = ROOT / "release" / "DATASET_CARD.md"
VERSIONS = build.VERSIONS

# dataset version -> scratch directory holding its run output
SCRATCH = {"v0": ROOT / "results" / "raw", "v1": ROOT / "results" / "raw_v1", "v2": ROOT / "results" / "raw_v2"}
# Trial runs and response caches are scratch, not evidence.
EXCLUDE_NAMES = ("weak-spike",)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(samples: list) -> str:  # type: ignore[type-arg]
    """sha256 over (sample_id, text) pairs: the identity of a dataset's content."""
    payload = json.dumps([[s.sample_id, s.text] for s in samples], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def pack_rows(scratch: dict[str, Path] = SCRATCH, rows_dir: Path = ROWS_DIR) -> list[Path]:
    """Copy result rows and run metadata, skipping caches and trial runs."""
    copied: list[Path] = []
    for version, src in scratch.items():
        if not src.exists():
            continue
        dest = rows_dir / version
        dest.mkdir(parents=True, exist_ok=True)
        for path in sorted(src.iterdir()):
            if not path.is_file() or any(tag in path.name for tag in EXCLUDE_NAMES):
                continue
            if path.suffix not in (".jsonl", ".json"):
                continue
            shutil.copyfile(path, dest / path.name)
            copied.append(dest / path.name)
    return copied


def dataset_entries(directory: Path) -> dict[str, dict[str, object]]:
    """Counts, content fingerprint and file checksum for every dataset version."""
    entries: dict[str, dict[str, object]] = {}
    for version in VERSIONS:
        samples = build.build_version(version)
        path = directory / f"{version}.jsonl"
        build.write_jsonl(samples, path)
        injected = sum(1 for s in samples if s.label == "injected")
        entries[version] = {
            "samples": len(samples),
            "injected": injected,
            "benign": len(samples) - injected,
            "fingerprint": fingerprint(samples),
            "file_sha256": sha256_file(path),
            "file_bytes": path.stat().st_size,
        }
    return entries


def write_manifest(path: Path = MANIFEST) -> dict[str, object]:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        entries = dataset_entries(Path(tmp))
    manifest = {
        "note": "Content identity of each dataset version. `fingerprint` hashes "
        "(sample_id, text) pairs; `file_sha256` hashes the JSONL bytes as written by "
        "`python -m zhipi.build`. v0 and v1 are frozen.",
        "datasets": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def render_card(entries: dict[str, dict[str, object]]) -> str:
    card = CARD_TEMPLATE.read_text(encoding="utf-8")
    for version, info in entries.items():
        for key in ("samples", "injected", "benign"):
            card = card.replace("{" + f"{version}_{key}" + "}", f"{info[key]:,}")
    return card


def build_dist(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    data_dir = out / "data"
    data_dir.mkdir(parents=True)
    entries = dataset_entries(data_dir)
    seed = out / "seed"
    seed.mkdir()
    for name in ("intents.jsonl", "benign.jsonl"):
        shutil.copyfile(build.SEED_DIR / name, seed / name)
    (out / "README.md").write_text(render_card(entries), encoding="utf-8", newline="\n")
    (out / "MANIFEST.json").write_text(
        json.dumps({"datasets": entries}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    licence = ROOT / "DATA_LICENSE.md"
    if licence.exists():
        shutil.copyfile(licence, out / "LICENSE.md")
    legal = ROOT / "release" / "CC-BY-4.0.txt"
    if legal.exists():
        shutil.copyfile(legal, out / "CC-BY-4.0.txt")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pack")
    sub.add_parser("manifest")
    dist = sub.add_parser("dist")
    dist.add_argument("--out", type=Path, default=ROOT / "dist" / "zh-ipi-bench")
    args = parser.parse_args()
    if args.command == "pack":
        files = pack_rows()
        print(f"copied {len(files)} files into {ROWS_DIR}")
    elif args.command == "manifest":
        manifest = write_manifest()
        print(f"wrote {MANIFEST} ({', '.join(manifest['datasets'])})")  # type: ignore[arg-type]
    else:
        print(f"wrote {build_dist(args.out)}")


if __name__ == "__main__":
    main()
