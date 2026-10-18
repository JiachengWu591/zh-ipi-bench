"""Build the dataset: intents x carriers x transforms, plus benign controls.

    python -m zhipi.build                      # writes data/generated/v0.jsonl
    python -m zhipi.build --out some/path.jsonl

Deterministic: the same seed files always produce byte-identical output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import carriers, transforms
from .schemas import CARRIERS, Intent, MalformedSample, Sample

ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "data" / "seed"
DEFAULT_OUT = ROOT / "data" / "generated" / "v0.jsonl"

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


def load_intents(path: Path = SEED_DIR / "intents.jsonl") -> list[Intent]:
    return [Intent.from_dict(row) for row in _read_jsonl(path)]  # type: ignore[arg-type]


def load_hard_negatives(path: Path = SEED_DIR / "benign.jsonl") -> list[Sample]:
    samples = []
    for row in _read_jsonl(path):
        samples.append(Sample.from_dict({**row, "label": "benign"}))  # type: ignore[arg-type]
    return samples


def _sample_id(carrier: str, intent_id: str, tfs: tuple[str, ...], lang: str) -> str:
    return f"{carrier}-{intent_id}-{'_'.join(tfs) or 'plain'}-{lang}"


def build_samples(intents: list[Intent], hard_negatives: list[Sample]) -> list[Sample]:
    samples: list[Sample] = []

    for intent in intents:
        for carrier in CARRIERS:
            for tfs in ZH_TRANSFORM_SETS:
                payload = transforms.apply(tfs, intent.text_zh)
                samples.append(
                    Sample(
                        sample_id=_sample_id(carrier, intent.intent_id, tfs, "zh"),
                        label="injected",
                        carrier=carrier,
                        language="zh",
                        transforms=tfs,
                        text=carriers.wrap(payload, carrier, "zh"),
                        intent_id=intent.intent_id,
                        plaintext_intent=intent.text_zh,
                    )
                )
            samples.append(
                Sample(
                    sample_id=_sample_id(carrier, intent.intent_id, (), "en"),
                    label="injected",
                    carrier=carrier,
                    language="en",
                    transforms=(),
                    text=carriers.wrap(intent.text_en, carrier, "en"),
                    intent_id=intent.intent_id,
                    plaintext_intent=intent.text_en,
                )
            )

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

    ids = [s.sample_id for s in samples]
    if len(ids) != len(set(ids)):
        raise MalformedSample("duplicate sample_id in built dataset")
    return samples


def write_jsonl(samples: list[Sample], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    samples = build_samples(load_intents(), load_hard_negatives())
    write_jsonl(samples, args.out)
    injected = sum(1 for s in samples if s.label == "injected")
    print(f"wrote {len(samples)} samples ({injected} injected) -> {args.out}")


if __name__ == "__main__":
    main()
