# zh-ipi-bench

[![tests](https://github.com/JiachengWu591/zh-ipi-bench/actions/workflows/tests.yml/badge.svg)](https://github.com/JiachengWu591/zh-ipi-bench/actions/workflows/tests.yml)
[![code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](DATA_LICENSE.md)

*A Chinese-native benchmark for indirect prompt injection: instructions hidden in the documents, web pages, emails, and tool outputs an LLM application reads as data.*

> **Status: Phase 0 (scaffold). No results yet.** The dataset generator, harness, and tests run; no real detector has been evaluated. Numbers will appear here only when they come with intervals and a command that reproduces them.

## Why this exists

Public indirect-injection benchmarks are overwhelmingly English. The few
multilingual or Chinese resources I found cover direct jailbreaks or content
safety, not injections planted in an application's context
(see [docs/RELATED_WORK.md](docs/RELATED_WORK.md), which also lists what I could
not verify). Chinese text offers evasion routes English does not — fullwidth
forms, zero-width characters between characters, 中英夹杂, pinyin, traditional /
simplified mixing — and a defense tuned on English may handle them differently,
or not. This project measures that instead of assuming it.

It is the companion to
[injection-blast-radius](https://github.com/JiachengWu591/injection-blast-radius),
which argues that architectural isolation, not prompt-level filtering, is the
defense layer that does not degrade as attacks get smarter. Here the question is
whether the *probabilistic* layer degrades on Chinese input, and whether the
*structural* layer still holds.

## Research questions

1. How does a defense's detection rate change between an English payload and the same intent in Chinese, and which transforms drive it?
2. What does it do to benign Chinese text (text that discusses injection, addresses humans imperatively, mentions config)?
3. When the probabilistic layer is bypassed, does schema-constrained isolation still contain Chinese injections?

Details: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## What's here

```
src/zhipi/
  schemas.py      frozen dataclasses: Intent, Sample (validated, fail-closed)
  transforms.py   fullwidth · zero_width · space_split · code_mix   (more planned)
  carriers.py     5 benign hosts: issue · rag_doc · email · web_html · tool_output
  build.py        intents × carriers × transforms (+ benign controls) -> JSONL
  defenses.py     Defense protocol, fail-closed wrapper, keyword sanity baselines
  evaluate.py     run a defense, summarize per group with 95% Wilson intervals
  adapters/       prompt_guard · qwen3guard · deepseek_judge · ibr_adapter (each a Defense)
  cache.py        append-only response cache (failures are never cached)
  run_eval.py     run detectors over the dataset -> raw rows + run metadata
  report.py       raw rows -> results/phase1.md (never calls a model)
data/seed/        hand-written intents and hard-negative benign text
docs/             threat model, related work, roadmap, data card
tests/            offline tests (no model, network, or key needed)
```

v0 data: 226 samples (210 injected, 16 benign). Draft [data card](docs/DATA_CARD.md).

## Quickstart

```bash
uv venv
uv pip install -e ".[dev]"
python -m pytest
python -m zhipi.build        # writes data/generated/v0.jsonl
```

Running real detectors (Phase 1; needs the `eval` extra, plus a Hugging Face token
for the gated Prompt Guard 2 and `DEEPSEEK_API_KEY` for the judge, which makes
billed API calls):

```bash
uv pip install -e ".[eval]"
python -m zhipi.run_eval --defense qwen3guard --defense prompt-guard-2
python -m zhipi.run_eval --defense deepseek-judge --repeats 3 --dry-run   # count calls first
python -m zhipi.report       # writes results/phase1.md
```

## Sanity baselines are not results

`keyword-en` and `keyword-zh` exist to test the harness. They are deliberately
naive, and the tests assert only things that are true by construction (e.g.
inserting zero-width characters defeats a contiguous-substring regex). Do not
read them as evidence about real detectors; Phase 1 adds those.

## Safety

All payloads target this repo's own sandbox path and a fixed fake placeholder
secret. Nothing targets a real product, service, credential, or person, and
every injected sample declares its plaintext intent for review. Intended use:
evaluating and hardening defenses.

## Roadmap

[docs/ROADMAP.md](docs/ROADMAP.md): real detectors → more data and transforms →
analysis → structural-layer experiment → release.

## License, citation, contributing

Code is MIT ([LICENSE](LICENSE)); data is CC BY 4.0 ([DATA_LICENSE.md](DATA_LICENSE.md)).
To cite, see [CITATION.cff](CITATION.cff) (GitHub shows a "Cite this repository"
button). Contributions are welcome: [CONTRIBUTING.md](CONTRIBUTING.md). Responsible
use and how to report a problem: [SECURITY.md](SECURITY.md).

## Honest limitations (so far)

Synthetic template data; six intents; a 16-sample benign set; single annotator;
novelty checked at abstract level only. Each is tracked in the data card and
roadmap.
