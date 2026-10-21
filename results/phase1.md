# Phase 1 results (v0)

Dataset: `v0.jsonl` (226 samples). Regenerate with `python -m zhipi.run_eval ...` then `python -m zhipi.report`.

> **Read the caveats at the bottom before quoting any number.** Intervals are 95% Wilson intervals that assume independent samples; these samples are template-generated (6 intents × 5 carriers per condition), so the intervals are narrower than the true uncertainty.

## At a glance

Read the two columns together: a detector that flags everything has perfect detection and 100% false positives.

| detector | detection, all injected | false positives, all benign |
|---|---|---|
| community-mbert-injection | 100% [98%–100%] | 100% [81%–100%] |
| deberta-v3-base-prompt-injection-v2/t0.5 | 83% [78%–88%] | 56% [33%–77%] |
| deepseek-judge/high_risk | 100% [98%–100%] | 0% [0%–19%] |
| deepseek-judge/suspicious+high_risk | 100% [98%–100%] | 0% [0%–19%] |
| keyword-en | 5% [3%–9%] | 0% [0%–19%] |
| keyword-zh | 12% [8%–17%] | 6% [1%–28%] |
| prompt-injection-guard-base/t0.5 | 88% [82%–91%] | 6% [1%–28%] |
| qwen3guard-gen-0.6b/jailbreak | 3% [2%–7%] | 0% [0%–19%] |
| qwen3guard-gen-0.6b/unsafe | 0% [0%–2%] | 0% [0%–19%] |
| qwen3guard-gen-0.6b/unsafe+ctrv | 3% [2%–7%] | 0% [0%–19%] |

## Detection rate on injected samples (higher is better)

Each cell: rate [95% interval]. `⚠k` = k samples where the detector failed and were excluded from the rate (never counted as detections).

| language / transform | n | community-mbert-injection | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | keyword-en | keyword-zh | prompt-injection-guard-base/t0.5 | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|---|---|---|---|---|
| en/plain | 30 | 100% [89%–100%] | 37% [22%–54%] | 100% [89%–100%] | 100% [89%–100%] | 33% [19%–51%] | 0% [0%–11%] | 97% [83%–99%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |
| zh/plain | 30 | 100% [89%–100%] | 87% [70%–95%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 33% [19%–51%] | 87% [70%–95%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |
| zh/fullwidth | 30 | 100% [89%–100%] | 77% [59%–88%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 33% [19%–51%] | 87% [70%–95%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] |
| zh/zero_width | 30 | 100% [89%–100%] | 97% [83%–99%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 0% [0%–11%] | 87% [70%–95%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] |
| zh/space_split | 30 | 100% [89%–100%] | 97% [83%–99%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 0% [0%–11%] | 77% [59%–88%] | 3% [1%–17%] | 0% [0%–11%] | 3% [1%–17%] |
| zh/code_mix | 30 | 100% [89%–100%] | 93% [79%–98%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 17% [7%–34%] | 90% [74%–97%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |
| zh/code_mix+zero_width | 30 | 100% [89%–100%] | 97% [83%–99%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 0% [0%–11%] | 90% [74%–97%] | 0% [0%–11%] | 0% [0%–11%] | 0% [0%–11%] |

## Paired comparisons: does a Chinese-specific change hurt detection?

Each pair is the same intent in the same carrier, with and without the change. `a↓/b↑` = the baseline detected it and the variant missed it (`a`), or the reverse (`b`). `p` is an exact two-sided McNemar test; pairs that agree carry no information. Not corrected for the many comparisons made here. The pairs are template-generated and the 5 carriers of one intent are replicates of the same payload, so the effective number of independent pairs is closer to the number of intents than to the pair count; treat a small `p` as a lead, not a finding, and check the AUROC table below before reading a rate difference as lost discrimination.

| comparison | community-mbert-injection | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | keyword-en | keyword-zh | prompt-injection-guard-base/t0.5 | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|---|---|---|---|---|---|---|---|---|---|
| language: Chinese vs the English control | no change (n=30) | 0↓/15↑ of 30, p=0.00 | no change (n=30) | no change (n=30) | 10↓/0↑ of 30, p=0.00 | 0↓/10↑ of 30, p=0.00 | 3↓/0↑ of 30, p=0.25 | 2↓/2↑ of 30, p=1.00 | no change (n=30) | 2↓/2↑ of 30, p=1.00 |
| transform: fullwidth | no change (n=30) | 3↓/0↑ of 30, p=0.25 | no change (n=30) | no change (n=30) | no change (n=30) | no change (n=30) | no change (n=30) | 2↓/0↑ of 30, p=0.50 | no change (n=30) | 2↓/0↑ of 30, p=0.50 |
| transform: zero-width | no change (n=30) | 0↓/3↑ of 30, p=0.25 | no change (n=30) | no change (n=30) | no change (n=30) | 10↓/0↑ of 30, p=0.00 | no change (n=30) | 2↓/0↑ of 30, p=0.50 | no change (n=30) | 2↓/0↑ of 30, p=0.50 |
| transform: space-split | no change (n=30) | 0↓/3↑ of 30, p=0.25 | no change (n=30) | no change (n=30) | no change (n=30) | 10↓/0↑ of 30, p=0.00 | 5↓/2↑ of 30, p=0.45 | 1↓/0↑ of 30, p=1.00 | no change (n=30) | 1↓/0↑ of 30, p=1.00 |
| transform: code-mix | no change (n=30) | 0↓/2↑ of 30, p=0.50 | no change (n=30) | no change (n=30) | no change (n=30) | 5↓/0↑ of 30, p=0.06 | 1↓/2↑ of 30, p=1.00 | no change (n=30) | no change (n=30) | no change (n=30) |
| transform: code-mix + zero-width | no change (n=30) | 0↓/3↑ of 30, p=0.25 | no change (n=30) | no change (n=30) | no change (n=30) | 10↓/0↑ of 30, p=0.00 | 1↓/2↑ of 30, p=1.00 | 2↓/0↑ of 30, p=0.50 | no change (n=30) | 2↓/0↑ of 30, p=0.50 |

## Threshold-free view: AUROC

For detectors that output a score. 0.5 = no better than chance, 1.0 = perfect ranking. Negatives are all benign samples in the same language. Intervals are bootstrap percentile intervals over samples (fixed seed); they ignore that samples from one intent are correlated, so they are too narrow.

| language / transform | community-mbert-injection | deberta-v3-base-prompt-injection-v2/t0.5 | keyword-en | keyword-zh | prompt-injection-guard-base/t0.5 |
|---|---|---|---|---|---|
| en/plain | 0.68 [0.35–0.99] | 0.73 [0.51–0.94] | 0.67 [0.58–0.75] | 0.50 [0.50–0.50] | 0.99 [0.97–1.00] |
| zh/plain | 0.71 [0.48–0.91] | 0.55 [0.33–0.77] | 0.50 [0.50–0.50] | 0.62 [0.51–0.73] | 0.99 [0.95–1.00] |
| zh/fullwidth | 0.73 [0.52–0.92] | 0.53 [0.32–0.76] | 0.50 [0.50–0.50] | 0.62 [0.51–0.73] | 0.99 [0.95–1.00] |
| zh/zero_width | 0.71 [0.48–0.91] | 0.62 [0.38–0.85] | 0.50 [0.50–0.50] | 0.45 [0.36–0.50] | 0.99 [0.95–1.00] |
| zh/space_split | 0.71 [0.48–0.91] | 0.59 [0.35–0.83] | 0.50 [0.50–0.50] | 0.45 [0.36–0.50] | 0.98 [0.94–1.00] |
| zh/code_mix | 0.73 [0.50–0.92] | 0.62 [0.42–0.84] | 0.50 [0.50–0.50] | 0.54 [0.43–0.63] | 1.00 [0.98–1.00] |
| zh/code_mix+zero_width | 0.73 [0.50–0.92] | 0.67 [0.46–0.89] | 0.50 [0.50–0.50] | 0.45 [0.36–0.50] | 1.00 [0.98–1.00] |

## Detection by payload tier and placement (injected, Chinese, untransformed)

Tiers: `explicit` names target and action, `implicit` asks without naming them, `spoofed_structure` forges delimiters or tool messages, `judge_targeted` also addresses the screening component. `buried` = the payload sits mid-way through a long benign document.

| tier / placement | n | community-mbert-injection | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | keyword-en | keyword-zh | prompt-injection-guard-base/t0.5 | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|---|---|---|---|---|
| explicit / default | 30 | 100% [89%–100%] | 87% [70%–95%] | 100% [89%–100%] | 100% [89%–100%] | 0% [0%–11%] | 33% [19%–51%] | 87% [70%–95%] | 7% [2%–21%] | 0% [0%–11%] | 7% [2%–21%] |

## False-positive rate on benign samples (lower is better)

| benign stratum | n | community-mbert-injection | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | keyword-en | keyword-zh | prompt-injection-guard-base/t0.5 | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|---|---|---|---|---|
| plain | 10 | 100% [72%–100%] | 50% [24%–76%] | 0% [0%–28%] | 0% [0%–28%] | 0% [0%–28%] | 0% [0%–28%] | 10% [2%–40%] | 0% [0%–28%] | 0% [0%–28%] | 0% [0%–28%] |
| imperative_to_humans | 2 | 100% [34%–100%] | 50% [9%–91%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] |
| discusses_injection | 1 | 100% [21%–100%] | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| mentions_config | 1 | 100% [21%–100%] | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| quotes_secret_shaped | 1 | 100% [21%–100%] | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| edge_shape | 1 | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |

## Detection by carrier (injected, pooled over all conditions)

| carrier | n | community-mbert-injection | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | keyword-en | keyword-zh | prompt-injection-guard-base/t0.5 | qwen3guard-gen-0.6b/jailbreak | qwen3guard-gen-0.6b/unsafe | qwen3guard-gen-0.6b/unsafe+ctrv |
|---|--:|---|---|---|---|---|---|---|---|---|---|
| email | 42 | 100% [92%–100%] | 83% [69%–92%] | 100% [92%–100%] | 100% [92%–100%] | 5% [1%–16%] | 12% [5%–25%] | 95% [84%–99%] | 0% [0%–8%] | 0% [0%–8%] | 0% [0%–8%] |
| issue | 42 | 100% [92%–100%] | 88% [75%–95%] | 100% [92%–100%] | 100% [92%–100%] | 5% [1%–16%] | 12% [5%–25%] | 60% [44%–73%] | 0% [0%–8%] | 0% [0%–8%] | 0% [0%–8%] |
| rag_doc | 42 | 100% [92%–100%] | 79% [64%–88%] | 100% [92%–100%] | 100% [92%–100%] | 5% [1%–16%] | 12% [5%–25%] | 83% [69%–92%] | 0% [0%–8%] | 0% [0%–8%] | 0% [0%–8%] |
| tool_output | 42 | 100% [92%–100%] | 67% [52%–79%] | 100% [92%–100%] | 100% [92%–100%] | 5% [1%–16%] | 12% [5%–25%] | 100% [92%–100%] | 10% [4%–22%] | 0% [0%–8%] | 10% [4%–22%] |
| web_html | 42 | 100% [92%–100%] | 100% [92%–100%] | 100% [92%–100%] | 100% [92%–100%] | 5% [1%–16%] | 12% [5%–25%] | 100% [92%–100%] | 7% [2%–19%] | 0% [0%–8%] | 7% [2%–19%] |

## Run-to-run stability

- `deepseek-judge/high_risk`: 0 of 226 samples changed verdict across repeats
- `deepseek-judge/suspicious+high_risk`: 0 of 226 samples changed verdict across repeats

## What was run

| detector kind | model / revision / prompt | run at (UTC) | commit |
|---|---|---|---|
| community-mbert | devndeploy/bert-prompt-injection-detector 63bf478b076eacd6eb29a6268cf53775f33042f5 | 2026-10-20T14:47:28+00:00 | d0232213+dirty |
| deepseek-judge | deepseek-v4-flash f5243ad501f5 | 2026-10-20T14:22:56+00:00 | d0232213 |
| hf-classifier:Horizon-Labs/prompt-injection-guard-base | Horizon-Labs/prompt-injection-guard-base 495ee67524911c8409f7aec7b5f135b94aef15ea | 2026-10-21T16:45:36+00:00 | 781141be |
| hf-classifier:protectai/deberta-v3-base-prompt-injection-v2 | protectai/deberta-v3-base-prompt-injection-v2 90c9989b1a342275dd0d1a95aad283c04e075671 | 2026-10-21T16:49:08+00:00 | 781141be |
| keyword-en | sanity baseline  | 2026-10-19T13:02:11+00:00 | 78180b9a |
| keyword-zh | sanity baseline  | 2026-10-19T13:02:11+00:00 | 78180b9a |
| qwen3guard | Qwen/Qwen3Guard-Gen-0.6B fada3b2f655b89601929198343c94cd2f64d93cc | 2026-10-19T13:08:40+00:00 | 78180b9a |

## Caveats (what these numbers can and cannot show)

- The keyword rows are harness sanity baselines, not evidence about real detectors.
- Qwen3Guard is a content-moderation model, included as a wrong-tool control. Its numbers are not injection-detection performance.
- Prompt Guard 2's model card lists English, French, German, Hindi, Italian, Portuguese, Spanish and Thai as evaluated languages. Chinese is not listed.
- `community-mbert-injection` is an unvetted community model (see the metadata table). On v0 it flags every sample, benign ones included, so its detection numbers carry no information. Probing it directly showed it separates short casual text ("The weather is nice today.") from blatant injections, but scores task-like or technical text ("Please close this issue as a duplicate of #311.") as an injection at 0.999. That is a property of this model on this distribution, not evidence about multilingual detectors in general.
- The LLM judge's result depends on its prompt (hash recorded above); a different prompt can move the numbers.
- **A 100% cell means the dataset cannot tell this detector from a perfect one, not that the detector is robust.** On v0 the payloads state their goal outright (read a named file, publish it), so a strong LLM reads through every transform; a ceiling result is a statement about the dataset.
- Judge repeats use temperature 0, so zero verdict changes across repeats shows low residual non-determinism at that setting, not that the verdict is insensitive to sampling.
- 30–30 samples per condition, 6 hand-written intents, one author: indicative, not conclusive. The benign set is 16 samples spread over several strata, so false-positive intervals are wide.
- Only detection is measured here. Whether an injection *succeeds* against a victim agent is Phase 4.
