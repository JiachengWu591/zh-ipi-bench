# Data card (draft — v0, not released)

| | |
|---|---|
| Name | zh-ipi-bench v0 |
| Status | Generated locally by `python -m zhipi.build`; not published |
| Size | 226 samples: 210 injected (180 zh + 30 en control), 16 benign (10 plain hosts + 6 hard negatives) |
| Languages | Simplified Chinese; English parallel control |
| Construction | Template-based: 6 hand-written intents × 5 carriers × 6 transform sets, plus hand-written benign controls |
| License | Code: MIT (`LICENSE`). Data: CC BY 4.0 (`DATA_LICENSE.md`) |

## Intended use

Measuring how well prompt-injection *defenses* handle Chinese indirect injection,
and how much they over-flag benign Chinese text. Not for attacking real systems.

## Safety statement

Every payload targets this project's own sandbox path and a fixed fake
placeholder secret. Nothing targets a real product, service, credential, or
person. Each injected sample declares its `plaintext_intent` so reviewers can
audit obfuscated payloads (zero-width, code-mixed) that a plaintext scan would
miss. The dataset contains injection *wording*, not working exploit chains.

## Known limitations

- Synthetic and template-based: not the real-world distribution of attacks.
- Six intents is small; the report must not generalize beyond them.
- Benign set is tiny (16). False-positive rates computed on it have wide
  intervals and must be reported as such.
- Intents and the English parallel were written by one author; no second
  annotator yet (Phase 2).
- The `carriers` fiction is borrowed from injection-blast-radius for
  comparability, which also means results may not transfer to other task types.

## Fields

See `zhipi.schemas.Sample`: `sample_id`, `label`, `carrier`, `language`,
`transforms`, `text`, `intent_id`, `plaintext_intent`, `stratum`.
