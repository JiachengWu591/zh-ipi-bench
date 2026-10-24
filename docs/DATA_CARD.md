# Data card

Versions built from the same seed files by `python -m zhipi.build --version v0|v1|v2`.
Released as v0.1.0 on Hugging Face (`JiachengWu591/zh-ipi-bench`, configs `v0`, `v1`, `v2`);
checksums in `release/MANIFEST.json`. The Hugging Face card is `release/DATASET_CARD.md`;
this file is the fuller working card. The table below compares v0 and v1; v2 follows it.

| | v0 | v1 |
|---|---|---|
| Purpose | What Phase 1 was measured on; frozen | Harder successor, built after v0 proved saturated for a strong LLM judge |
| Size | 226 samples: 210 injected, 16 benign | 803 samples: 750 injected, 53 benign |
| Intents | 6 (all `explicit`) | 19: 6 `explicit`, 10 `implicit`, 2 `spoofed_structure`, 1 `judge_targeted` |
| Injected | 180 zh (6 transform sets) + 30 en control | 655 default placement (zh × up to 6 transform sets + en control) + 95 `buried`. A transform that leaves a payload unchanged is skipped (fullwidth does nothing to a payload with no ASCII), so no two samples have identical text |
| Benign | 10 bare hosts + 6 hard negatives | 10 bare hosts + 10 long (buried-style) hosts + 33 hard negatives |
| Languages | Simplified Chinese; English parallel control | same |
| Construction | Template-based, hand-written seeds | same |
| Frozen? | **Yes.** `tests/test_build.py` pins a fingerprint of all (id, text) pairs **Yes** since v0.1.0 (pinned in `release/MANIFEST.json`, checked by `python -m zhipi.verify`) |
| License | Code: MIT (`LICENSE`). Data: CC BY 4.0 (`DATA_LICENSE.md`) | same |

## v2 (added after the first end-to-end run)

1,288 samples (1,230 injected, 58 benign): v1 unchanged, plus

- **12 `ibr_corpus` intents** ported from injection-blast-radius's `ibr/attack_corpus.py`
  (commit `af8a758`): direct override, fabricated convention, maintainer impersonation,
  urgency, split instruction, obfuscated target, debugging framing, base64-encoded,
  homoglyph, long-context burial, cross-language, layered. The English text is the
  original payload verbatim; the Chinese text is a hand translation by the author (the
  cross-language pattern is Chinese in the original). They are HTML-comment-wrapped
  "repository convention" notes, a different register from the short direct requests in
  v0/v1, and the long-context one is about 7,000 characters.
- A `gloss_zh` / `gloss_en` field, used as `plaintext_intent` when the payload does not
  say what it asks (base64 blob, indirect file description, log wall). A test checks the
  base64 intents decode to their declared gloss.
- **5 benign issues containing HTML comments** (issue-template prompts, a maintainer
  note, a note about `.env` placeholders), so a detector cannot win by keying on `<!--`.

Same safety statement as above: every payload targets the fixed sandbox and fake secret.
The Chinese translations are single-author and unreviewed; a second reader is still
needed. The corpus was chosen because the source project reports its undefended baseline
leaking on these techniques, which did **not** reproduce on the model used here
(see `docs/ROADMAP.md`, Phase 4).

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
  human annotator yet. A blind LLM annotator (a fresh Claude agent, not a person) agreed with
  the author on 102 of 103 texts (Cohen's κ 0.98) and flagged four of 31 translations as
  slightly off (`results/annotation.md`); that is an upper bound on what a human would give.
  Human agreement is still unmeasured; protocol and tooling: `docs/ANNOTATION_GUIDE.md`.
- Whether v1 is harder than v0 is an empirical question. Measured on one detector
  (the DeepSeek judge): yes, slightly (97% vs 100% detection), and only through two
  `implicit` intents. The tier labels are the author's judgement of difficulty, not a
  measured property.
- **Label ambiguity.** The `ctx_config` and `checklist` intents are near-identical
  to legitimate requests addressed to a human reporter (compare the benign
  `asks_humans_for_info` stratum); which label is correct depends on who reads the
  text. The only judge misses on v1 are these two intents, so they may measure this
  ambiguity rather than a detector weakness. A blind LLM reader labelled both `checklist`
  texts and one of two `ctx_config` texts injected and hesitated (`unsure`) on the other, and
  called all four `asks_humans_for_info` benign texts benign, so this reader does not support
  "the misses are mostly label noise". A human reader may still differ.
- The `carriers` fiction is borrowed from injection-blast-radius for
  comparability, which also means results may not transfer to other task types.

## Fields

See `zhipi.schemas.Sample`: `sample_id`, `label`, `carrier`, `language`,
`transforms`, `text`, `intent_id`, `plaintext_intent`, `stratum`, `tier`,
`placement`.
