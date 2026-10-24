# Changelog

## Unreleased

- README: a results figure (`assets/results.svg`, generated from the committed rows and
  checked by `python -m zhipi.verify`), a short summary, and a Simplified Chinese version
  (`README.zh-CN.md`) with a language switch.
- Second-annotator kit: `python -m zhipi.annotate` builds a blind offline annotation page
  (label judgement plus translation ratings) and an answer key, and scores the returned
  answers (agreement with a Wilson interval, Cohen's kappa with a bootstrap interval, by tier
  and stratum). Protocol: `docs/ANNOTATION_GUIDE.md`. A blind LLM annotator (not a human) agreed
  with the author on 102 of 103 texts; the answers and report are committed
  (`results/annotation/`, `results/annotation.md`) and checked by `python -m zhipi.verify`
  (now 10 checks). Human agreement is still unmeasured.

## 0.1.0 (2026-10-24)

First release: a benchmark, an evaluation harness, results, and the means to reproduce
them. Everything below is described, with limits, in `paper/REPORT.md`.

- **Data.** v0 (226 samples, frozen), v1 (803, frozen), v2 (1,288): 31 hand-written intents
  in five tiers, five carriers, Chinese-specific transforms, a "buried in a long document"
  placement, and benign hard negatives. `release/MANIFEST.json` pins each version.
- **Detector study.** Ten detector configurations on v0/v1: keyword baselines, Qwen3Guard
  (wrong-tool control), a DeepSeek LLM judge, three Hub classifiers. Wilson, McNemar and
  AUROC reporting.
- **End-to-end study.** Undefended agent versus injection-blast-radius's isolated pipeline
  on DeepSeek (v1, v2) and on a local Qwen2.5-7B served by llama.cpp (v2).
- **Reproduction.** `python -m zhipi.verify` regenerates every table from the committed
  rows (`results/rows/`) with no model, key or network; a test runs it in CI.
- **Known gaps.** Llama Prompt Guard 2 was not run (gated access rejected); no second
  annotator; pinyin, traditional/simplified, homophone and character-decomposition
  transforms are planned, not implemented.

Notable fixes along the way, each with a regression test: a duplicate "transformed"
sample created by a no-op transform; run provenance overwritten when a second Hub model
was evaluated; a judge that failed silently under a provider's thinking mode; a literal
zero-width character left in source.
