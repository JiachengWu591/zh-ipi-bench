# Data card (draft — not released)

Two builds from the same seed files. Both are generated locally by
`python -m zhipi.build --version v0|v1` and are not published yet.

| | v0 | v1 |
|---|---|---|
| Purpose | What Phase 1 was measured on; frozen | Harder successor, built after v0 proved saturated for a strong LLM judge |
| Size | 226 samples: 210 injected, 16 benign | 803 samples: 750 injected, 53 benign |
| Intents | 6 (all `explicit`) | 19: 6 `explicit`, 10 `implicit`, 2 `spoofed_structure`, 1 `judge_targeted` |
| Injected | 180 zh (6 transform sets) + 30 en control | 655 default placement (zh × up to 6 transform sets + en control) + 95 `buried`. A transform that leaves a payload unchanged is skipped (fullwidth does nothing to a payload with no ASCII), so no two samples have identical text |
| Benign | 10 bare hosts + 6 hard negatives | 10 bare hosts + 10 long (buried-style) hosts + 33 hard negatives |
| Languages | Simplified Chinese; English parallel control | same |
| Construction | Template-based, hand-written seeds | same |
| Frozen? | **Yes.** `tests/test_build.py` pins a fingerprint of all (id, text) pairs | No; may change before release |
| License | Code: MIT (`LICENSE`). Data: CC BY 4.0 (`DATA_LICENSE.md`) | same |

## Intended use

Measuring how well prompt-injection *defenses* handle Chinese indirect injection,
and how much they over-flag benign Chinese text. Not for attacking real systems.

## What the new axes mean

- **Tier**: how recognisable the payload is by how it asks.
  `explicit` names target and action outright; `implicit` asks without naming them
  (or frames the ask as a format, a checklist, a quotation, a precedent);
  `spoofed_structure` forges delimiters or tool/system messages; `judge_targeted`
  also addresses the screening component itself.
- **Placement**: `default` (short host) or `buried` (the payload sits between two
  blocks of benign release-note and log filler, ~400–650 characters each side, with
  no imperatives in the filler).
- **Hard-negative strata** now mirror the attack styles on purpose:
  `asks_humans_for_info` ("please paste your environment config" addressed to a
  human reporter, which reads almost exactly like the `ctx_config` attack),
  `task_list`, `format_request`, `quoted_text`, and `long_benign`.

## Safety statement

Every payload targets this project's own sandbox path and a fixed fake
placeholder secret, or the assistant's own instructions. The one payload with a
link points at `example.invalid`, a reserved top-level domain that never resolves
(`tests/test_build.py` asserts every link in the intents is `.invalid`). Nothing
targets a real product, service, credential, or person. Each injected sample
declares its `plaintext_intent` so reviewers can audit obfuscated payloads
(zero-width, code-mixed) that a plaintext scan would miss. The dataset contains
injection *wording*, not working exploit chains.

## Known limitations

- Synthetic and template-based: not the real-world distribution of attacks.
- 19 intents is still small, and per-tier counts are very uneven: `spoofed_structure`
  is 2 intents and `judge_targeted` is **1** intent, so its rows rest on 5 samples
  per condition and say almost nothing beyond that one wording.
- Benign set is 53 samples across 11 strata, so most per-stratum false-positive
  intervals are wide and must be reported as such.
- Intents and the English parallel were written by one author; no second
  annotator yet. Agreement (Cohen's κ) is still to be measured.
- Whether v1 is harder than v0 is an empirical question. Measured on one detector
  (the DeepSeek judge): yes, slightly (97% vs 100% detection), and only through two
  `implicit` intents. The tier labels are the author's judgement of difficulty, not a
  measured property.
- **Label ambiguity.** The `ctx_config` and `checklist` intents are near-identical
  to legitimate requests addressed to a human reporter (compare the benign
  `asks_humans_for_info` stratum); which label is correct depends on who reads the
  text. The only judge misses on v1 are these two intents, so they may measure this
  ambiguity rather than a detector weakness. Pending a second annotator.
- The `carriers` fiction is borrowed from injection-blast-radius for
  comparability, which also means results may not transfer to other task types.

## Fields

See `zhipi.schemas.Sample`: `sample_id`, `label`, `carrier`, `language`,
`transforms`, `text`, `intent_id`, `plaintext_intent`, `stratum`, `tier`,
`placement`.
