# Phase 1 results

Dataset: `v0.jsonl` (226 samples). Regenerate with `python -m zhipi.run_eval ...` then `python -m zhipi.report`.

> **Read the caveats at the bottom before quoting any number.** Intervals are 95% Wilson intervals that assume independent samples; these samples are template-generated (6 intents × 5 carriers per condition), so the intervals are narrower than the true uncertainty.

## Detection rate on injected samples (higher is better)

Each cell: rate [95% interval]. `⚠k` = k samples where the detector failed and were excluded from the rate (never counted as detections).

| language / transform | n | keyword-en | keyword-zh | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|
| en/plain | 30 | 33% [19%–51%] | 0% [0%–11%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |
| zh/plain | 30 | 0% [0%–11%] | 33% [19%–51%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |
| zh/fullwidth | 30 | 0% [0%–11%] | 33% [19%–51%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] |
| zh/zero_width | 30 | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] |
| zh/space_split | 30 | 0% [0%–11%] | 0% [0%–11%] | 3% [1%–17%] | 0% [0%–11%] | 3% [1%–17%] |
| zh/code_mix | 30 | 0% [0%–11%] | 17% [7%–34%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |
| zh/code_mix+zero_width | 30 | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] |

## False-positive rate on benign samples (lower is better)

| benign stratum | n | keyword-en | keyword-zh | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|
| plain | 10 | 0% [0%–28%] | 0% [0%–28%] | 0% [0%–28%] | 0% [0%–28%] | 0% [0%–28%] |
| imperative_to_humans | 2 | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] |
| discusses_injection | 1 | 0% [0%–79%] | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| mentions_config | 1 | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| quotes_secret_shaped | 1 | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| edge_shape | 1 | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |

## Detection by carrier (injected, pooled over all conditions)

| carrier | n | keyword-en | keyword-zh | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|
| email | 42 | 5% [1%–16%] | 12% [5%–25%] | 0% [0%–8%] | 0% [0%–8%] | 0% [0%–8%] |
| issue | 42 | 5% [1%–16%] | 12% [5%–25%] | 0% [0%–8%] | 0% [0%–8%] | 0% [0%–8%] |
| rag_doc | 42 | 5% [1%–16%] | 12% [5%–25%] | 0% [0%–8%] | 0% [0%–8%] | 0% [0%–8%] |
| tool_output | 42 | 5% [1%–16%] | 12% [5%–25%] | 10% [4%–22%] | 0% [0%–8%] | 10% [4%–22%] |
| web_html | 42 | 5% [1%–16%] | 12% [5%–25%] | 7% [2%–19%] | 0% [0%–8%] | 7% [2%–19%] |

## What was run

| detector kind | model / revision / prompt | run at (UTC) | commit |
|---|---|---|---|
| keyword-en | sanity baseline  | 2026-10-19T13:02:11+00:00 | 78180b9a |
| keyword-zh | sanity baseline  | 2026-10-19T13:02:11+00:00 | 78180b9a |
| qwen3guard | Qwen/Qwen3Guard-Gen-0.6B fada3b2f655b89601929198343c94cd2f64d93cc | 2026-10-19T13:08:40+00:00 | 78180b9a |

## Caveats (what these numbers can and cannot show)

- The keyword rows are harness sanity baselines, not evidence about real detectors.
- Qwen3Guard is a content-moderation model, included as a wrong-tool control. Its numbers are not injection-detection performance.
- Prompt Guard 2's model card lists English, French, German, Hindi, Italian, Portuguese, Spanish and Thai as evaluated languages. Chinese is not listed.
- The LLM judge's result depends on its prompt (hash recorded above); a different prompt can move the numbers.
- 30 samples per condition, 6 hand-written intents, one author: indicative, not conclusive. Benign set is 16 samples, so false-positive intervals are wide.
- Only detection is measured here. Whether an injection *succeeds* against a victim agent is Phase 4.
