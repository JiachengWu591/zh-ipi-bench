"""Build the dataset: intents x carriers x transforms, plus benign controls.

    python -m zhipi.build                    # v1 -> data/generated/v1.jsonl
    python -m zhipi.build --version v2       # v1 plus the ported attacks
    python -m zhipi.build --version v0       # the original 226-sample set
    python -m zhipi.build --out some/path.jsonl

Three versions, each a superset of the last, all deterministic (same seed files,
byte-identical output):

- v0: the six explicit intents, the bare benign hosts and the first six hard
  negatives. Kept reproducible because Phase 1's results were measured on it.
- v1: adds the implicit / spoofed / judge-targeted intents, a "buried in a long
  document" placement, more hard negatives, and long benign controls. Built because
  v0 turned out to be saturated for a strong LLM judge. Frozen: Phase 2 and the first
  end-to-end run were measured on it, and a test pins its fingerprint.
- v2: adds twelve attacks ported from injection-blast-radius's corpus (the techniques
  its undefended baseline leaks on) in Chinese with English originals, and benign
  issues containing HTML comments. Built because the baseline agent barely leaked on
  v1, which left the structural layer nothing to prevent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import carriers, transforms
from .schemas import CARRIERS, Intent, MalformedSample, Sample

ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "data" / "seed"
VERSIONS = ("v0", "v1", "v2")

# Transform sets applied to Chinese payloads. English payloads are the
# cross-lingual control and only appear untransformed.
ZH_TRANSFORM_SETS: tuple[tuple[str, ...], ...] = (
    (),
    ("fullwidth",),
    ("zero_width",),
    ("space_split",),
    ("code_mix",),
    ("code_mix", "zero_width"),
)


def default_out(version: str) -> Path:
    return ROOT / "data" / "generated" / f"{version}.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise MalformedSample(f"{path.name}:{number}: {exc}") from exc
    return rows


def load_intents(
    path: Path = SEED_DIR / "intents.jsonl", version: str = "v1"
) -> list[Intent]:
    intents = [Intent.from_dict(row) for row in _read_jsonl(path)]  # type: ignore[arg-type]
    if version == "v0":
        return [i for i in intents if i.tier == "explicit"]
    if version == "v1":
        return [i for i in intents if i.tier != "ibr_corpus"]
    return intents


def load_hard_negatives(
    path: Path = SEED_DIR / "benign.jsonl", version: str = "v1"
) -> list[Sample]:
    keep = {"v0": {"v0"}, "v1": {"v0", "v1"}, "v2": {"v0", "v1", "v2"}}[version]
    samples = []
    for row in _read_jsonl(path):
        if row.get("added_in", "v0") not in keep:
            continue
        row = {k: v for k, v in row.items() if k != "added_in"}
        samples.append(Sample.from_dict({**row, "label": "benign"}))  # type: ignore[arg-type]
    return samples


def _sample_id(
    carrier: str, intent_id: str, tfs: tuple[str, ...], lang: str, placement: str = "default"
) -> str:
    suffix = "" if placement == "default" else f"-{placement}"
    return f"{carrier}-{intent_id}-{'_'.join(tfs) or 'plain'}-{lang}{suffix}"


def _injected(
    intent: Intent,
    carrier: str,
    lang: str,
    tfs: tuple[str, ...],
    placement: str = "default",
) -> Sample:
    plain = intent.plain(lang)
    payload = transforms.apply(tfs, intent.text_zh if lang == "zh" else intent.text_en)
    return Sample(
        sample_id=_sample_id(carrier, intent.intent_id, tfs, lang, placement),
        label="injected",
        carrier=carrier,
        language=lang,
        transforms=tfs,
        text=carriers.wrap(payload, carrier, lang, placement),
        intent_id=intent.intent_id,
        plaintext_intent=plain,
        tier=intent.tier,
        placement=placement,
    )


def build_samples(
    intents: list[Intent], hard_negatives: list[Sample], version: str = "v1"
) -> list[Sample]:
    if version not in VERSIONS:
        raise ValueError(f"unknown version {version!r} (have: {VERSIONS})")
    samples: list[Sample] = []

    for intent in intents:
        for carrier in CARRIERS:
            for tfs in ZH_TRANSFORM_SETS:
                # A transform that changes nothing (fullwidth on a payload with no
                # ASCII, say) would yield a sample that is a byte-for-byte duplicate
                # of the plain one but labelled as transformed. Skip it.
                if tfs and transforms.apply(tfs, intent.text_zh) == intent.text_zh:
                    continue
                samples.append(_injected(intent, carrier, "zh", tfs))
            samples.append(_injected(intent, carrier, "en", ()))

    if version in ("v1", "v2"):
        for intent in intents:
            for carrier in CARRIERS:
                samples.append(_injected(intent, carrier, "zh", (), "buried"))

    for carrier, lang in carriers.all_pairs():
        samples.append(
            Sample(
                sample_id=f"benign-host-{carrier}-{lang}",
                label="benign",
                carrier=carrier,
                language=lang,
                transforms=(),
                text=carriers.benign(carrier, lang),
                stratum="plain",
            )
        )
    samples.extend(hard_negatives)

    if version in ("v1", "v2"):
        for carrier, lang in carriers.all_pairs():
            samples.append(
                Sample(
                    sample_id=f"benign-buried-{carrier}-{lang}",
                    label="benign",
                    carrier=carrier,
                    language=lang,
                    transforms=(),
                    text=carriers.benign(carrier, lang, "buried"),
                    stratum="long_benign",
                    placement="buried",
                )
            )

    ids = [s.sample_id for s in samples]
    if len(ids) != len(set(ids)):
        raise MalformedSample("duplicate sample_id in built dataset")
    return samples


def build_version(version: str) -> list[Sample]:
    return build_samples(load_intents(version=version), load_hard_negatives(version=version), version)


def write_jsonl(samples: list[Sample], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=VERSIONS, default="v1")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or default_out(args.version)
    samples = build_version(args.version)
    write_jsonl(samples, out)
    injected = sum(1 for s in samples if s.label == "injected")
    print(f"wrote {len(samples)} samples ({injected} injected) -> {out}")


if __name__ == "__main__":
    main()
