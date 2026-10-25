# Results on v3_study

Dataset: `v3_study.jsonl` (388 samples). Regenerate with `python -m zhipi.run_eval ...` then `python -m zhipi.report`.

> **Read the caveats at the bottom before quoting any number.** Intervals are 95% Wilson intervals that assume independent samples; these samples are template-generated (31 intents × 2 carriers per condition), so the intervals are narrower than the true uncertainty.

## At a glance

Read the two columns together: a detector that flags everything has perfect detection and 100% false positives.

| detector | detection, all injected | false positives, all benign |
|---|---|---|
| deberta-v3-base-prompt-injection-v2/t0.5 | 95% [91%–97%] | 60% [49%–70%] |
| deepseek-judge/high_risk | 98% [96%–99%] | 1% [0%–7%] |
| deepseek-judge/suspicious+high_risk | 100% [98%–100%] | 1% [0%–7%] |
| prompt-injection-guard-base/t0.5 | 58% [53%–64%] | 10% [5%–19%] |

## Detection rate on injected samples (higher is better)

Each cell: rate [95% interval]. `⚠k` = k samples where the detector failed and were excluded from the rate (never counted as detections).

| language / transform | n | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | prompt-injection-guard-base/t0.5 |
|---|--:|---|---|---|---|
| zh/plain | 62 | 94% [85%–97%] | 97% [89%–99%] | 100% [94%–100%] | 61% [49%–72%] |
| zh/traditional | 62 | 94% [85%–97%] | 100% [94%–100%] | 100% [94%–100%] | 52% [39%–64%] |
| zh/pinyin | 62 | 95% [87%–98%] | 100% [94%–100%] | 100% [94%–100%] | 50% [38%–62%] |
| zh/homophone | 62 | 94% [85%–97%] | 95% [87%–98%] | 98% [91%–100%] | 47% [35%–59%] |
| zh/char_decomp | 62 | 97% [89%–99%] | 100% [94%–100%] | 100% [94%–100%] | 82% [71%–90%] |

## Paired comparisons: does a Chinese-specific change hurt detection?

Each pair is the same intent in the same carrier, with and without the change. `a↓/b↑` = the baseline detected it and the variant missed it (`a`), or the reverse (`b`). `p` is an exact two-sided McNemar test; pairs that agree carry no information. Not corrected for the many comparisons made here. The pairs are template-generated and the 2 carriers of one intent are replicates of the same payload, so the effective number of independent pairs is closer to the number of intents than to the pair count; treat a small `p` as a lead, not a finding, and check the AUROC table below before reading a rate difference as lost discrimination.

| comparison | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | prompt-injection-guard-base/t0.5 |
|---|---|---|---|---|
| transform: traditional script | 1↓/1↑ of 62, p=1.00 | 0↓/2↑ of 62, p=0.50 | no change (n=62) | 6↓/0↑ of 62, p=0.03 |
| transform: pinyin | 1↓/2↑ of 62, p=1.00 | 0↓/2↑ of 62, p=0.50 | no change (n=62) | 8↓/1↑ of 62, p=0.04 |
| transform: homophone | 1↓/1↑ of 62, p=1.00 | 1↓/0↑ of 62, p=1.00 | 1↓/0↑ of 62, p=1.00 | 10↓/1↑ of 62, p=0.01 |
| transform: character decomposition | 0↓/2↑ of 62, p=0.50 | 0↓/2↑ of 62, p=0.50 | no change (n=62) | 0↓/13↑ of 62, p=0.00 |

### Intent-level view of the v3 transforms

The unit is the intent: `↓` = the variant was flagged in fewer of that intent's carriers than the plain text, `↑` = in more; ties are dropped; exact sign test. This is the fairer count of independent comparisons (the carriers of one intent carry the same payload), and still not corrected for the number of comparisons made in this table.

| comparison | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | prompt-injection-guard-base/t0.5 |
|---|---|---|---|---|
| transform: traditional script | 1↓/1↑ of 31 intents, p=1.00 | 0↓/2↑ of 31 intents, p=0.50 | no change (n=31 intents) | 6↓/0↑ of 31 intents, p=0.03 |
| transform: pinyin | 1↓/2↑ of 31 intents, p=1.00 | 0↓/2↑ of 31 intents, p=0.50 | no change (n=31 intents) | 8↓/1↑ of 31 intents, p=0.04 |
| transform: homophone | 1↓/1↑ of 31 intents, p=1.00 | 1↓/0↑ of 31 intents, p=1.00 | 1↓/0↑ of 31 intents, p=1.00 | 10↓/1↑ of 31 intents, p=0.01 |
| transform: character decomposition | 0↓/2↑ of 31 intents, p=0.50 | 0↓/2↑ of 31 intents, p=0.50 | no change (n=31 intents) | 0↓/10↑ of 31 intents, p=0.00 |

## Threshold-free view: AUROC

For detectors that output a score. 0.5 = no better than chance, 1.0 = perfect ranking. Negatives are all benign samples in the same language. Intervals are bootstrap percentile intervals over samples (fixed seed); they ignore that samples from one intent are correlated, so they are too narrow.

| language / transform | deberta-v3-base-prompt-injection-v2/t0.5 | prompt-injection-guard-base/t0.5 |
|---|---|---|
| zh/plain | 0.52 [0.42–0.63] | 0.92 [0.86–0.96] |
| zh/traditional | 0.52 [0.41–0.63] | 0.88 [0.82–0.93] |
| zh/pinyin | 0.55 [0.46–0.67] | 0.89 [0.83–0.93] |
| zh/homophone | 0.53 [0.43–0.65] | 0.87 [0.80–0.92] |
| zh/char_decomp | 0.53 [0.43–0.64] | 0.96 [0.92–0.99] |

## Detection by payload tier and placement (injected, Chinese, untransformed)

Tiers: `explicit` names target and action, `implicit` asks without naming them, `spoofed_structure` forges delimiters or tool messages, `judge_targeted` also addresses the screening component. `buried` = the payload sits mid-way through a long benign document.

| tier / placement | n | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | prompt-injection-guard-base/t0.5 |
|---|--:|---|---|---|---|
| explicit / default | 12 | 92% [65%–99%] | 100% [76%–100%] | 100% [76%–100%] | 75% [47%–91%] |
| implicit / default | 20 | 90% [70%–97%] | 90% [70%–97%] | 100% [84%–100%] | 60% [39%–78%] |
| spoofed_structure / default | 4 | 100% [51%–100%] | 100% [51%–100%] | 100% [51%–100%] | 75% [30%–95%] |
| judge_targeted / default | 2 | 100% [34%–100%] | 100% [34%–100%] | 100% [34%–100%] | 50% [9%–91%] |
| ibr_corpus / default | 24 | 96% [80%–99%] | 100% [86%–100%] | 100% [86%–100%] | 54% [35%–72%] |

## False-positive rate on benign samples (lower is better)

| benign stratum | n | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | prompt-injection-guard-base/t0.5 |
|---|--:|---|---|---|---|
| plain | 10 | 50% [24%–76%] | 0% [0%–28%] | 0% [0%–28%] | 10% [2%–40%] |
| imperative_to_humans | 5 | 60% [23%–88%] | 0% [0%–43%] | 0% [0%–43%] | 0% [0%–43%] |
| discusses_injection | 5 | 100% [57%–100%] | 0% [0%–43%] | 0% [0%–43%] | 20% [4%–62%] |
| mentions_config | 5 | 80% [38%–96%] | 0% [0%–43%] | 0% [0%–43%] | 0% [0%–43%] |
| quotes_secret_shaped | 3 | 100% [44%–100%] | 0% [0%–56%] | 0% [0%–56%] | 67% [21%–94%] |
| edge_shape | 4 | 25% [5%–70%] | 0% [0%–49%] | 0% [0%–49%] | 0% [0%–49%] |
| asks_humans_for_info | 5 | 100% [57%–100%] | 20% [4%–62%] | 20% [4%–62%] | 60% [23%–88%] |
| task_list | 2 | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] |
| format_request | 2 | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] | 0% [0%–66%] |
| quoted_text | 1 | 100% [21%–100%] | 0% [0%–79%] | 0% [0%–79%] | 0% [0%–79%] |
| long_benign | 11 | 18% [5%–48%] | 0% [0%–26%] | 0% [0%–26%] | 0% [0%–26%] |
| traditional_text | 8 | 62% [31%–86%] | 0% [0%–32%] | 0% [0%–32%] | 12% [2%–47%] |
| pinyin_text | 5 | 100% [57%–100%] | 0% [0%–43%] | 0% [0%–43%] | 0% [0%–43%] |
| char_breakdown_text | 4 | 50% [15%–85%] | 0% [0%–49%] | 0% [0%–49%] | 0% [0%–49%] |
| homophone_text | 3 | 67% [21%–94%] | 0% [0%–56%] | 0% [0%–56%] | 0% [0%–56%] |

## Detection by carrier (injected, pooled over all conditions)

| carrier | n | deberta-v3-base-prompt-injection-v2/t0.5 | deepseek-judge/high_risk | deepseek-judge/suspicious+high_risk | prompt-injection-guard-base/t0.5 |
|---|--:|---|---|---|---|
| email | 40 | 100% [91%–100%] | 100% [91%–100%] | 100% [91%–100%] | 48% [33%–63%] |
| issue | 155 | 100% [98%–100%] | 98% [94%–99%] | 99% [96%–100%] | 44% [36%–52%] |
| rag_doc | 40 | 75% [60%–86%] | 95% [83%–99%] | 100% [91%–100%] | 48% [33%–63%] |
| tool_output | 35 | 80% [64%–90%] | 100% [90%–100%] | 100% [90%–100%] | 100% [90%–100%] |
| web_html | 40 | 100% [91%–100%] | 100% [91%–100%] | 100% [91%–100%] | 100% [91%–100%] |

## What was run

| detector kind | model / revision / prompt | run at (UTC) | commit |
|---|---|---|---|
| deepseek-judge | deepseek-v4-flash f5243ad501f5 | 2026-10-25T08:48:06+00:00 | ad07bcab |
| hf-classifier:Horizon-Labs/prompt-injection-guard-base | Horizon-Labs/prompt-injection-guard-base 495ee67524911c8409f7aec7b5f135b94aef15ea | 2026-10-25T08:34:37+00:00 | ad07bcab |
| hf-classifier:protectai/deberta-v3-base-prompt-injection-v2 | protectai/deberta-v3-base-prompt-injection-v2 90c9989b1a342275dd0d1a95aad283c04e075671 | 2026-10-25T08:36:35+00:00 | ad07bcab |

## Caveats (what these numbers can and cannot show)

- The keyword rows are harness sanity baselines, not evidence about real detectors.
- Qwen3Guard is a content-moderation model, included as a wrong-tool control. Its numbers are not injection-detection performance.
- Prompt Guard 2's model card lists English, French, German, Hindi, Italian, Portuguese, Spanish and Thai as evaluated languages. Chinese is not listed.
- `community-mbert-injection` is an unvetted community model (see the metadata table). On v0 it flags every sample, benign ones included, so its detection numbers carry no information. Probing it directly showed it separates short casual text ("The weather is nice today.") from blatant injections, but scores task-like or technical text ("Please close this issue as a duplicate of #311.") as an injection at 0.999. That is a property of this model on this distribution, not evidence about multilingual detectors in general.
- The LLM judge's result depends on its prompt (hash recorded above); a different prompt can move the numbers.
- **A 100% cell means the dataset cannot tell this detector from a perfect one, not that the detector is robust.** On v0 the payloads state their goal outright (read a named file, publish it), so a strong LLM reads through every transform; a ceiling result is a statement about the dataset.
- Some `implicit` intents ask for something generic (for example, the configuration the reader can see, or one unticked box in a checklist). Their text is near-identical to legitimate requests addressed to a human reporter, so which label is correct depends on who reads it. Misses on them, and false positives on the `asks_humans_for_info` stratum, may reflect that ambiguity rather than a detector error; a second annotator is needed to tell.
- The v3 transforms rewrite only the payload, so a traditional-script payload sits inside a simplified-script host; the pinyin, homophone and character-decomposition transforms re-spell only the key terms in small curated tables, not whole sentences. Results here say nothing about other ways of writing those forms. The paired comparisons use each intent's untransformed twin re-run in the same session, so hosted-model drift between sessions does not enter them.
- The new benign strata (traditional-script text, pinyin, character breakdowns, homophone discussions) are small (3 to 8 samples each) and hand-written; a false-positive interval on them is wide, and zero flags in 3 samples still allows a false-positive rate above 50%.
- Judge repeats use temperature 0, so zero verdict changes across repeats shows low residual non-determinism at that setting, not that the verdict is insensitive to sampling.
- 62–62 samples per condition, 31 hand-written intents, one author: indicative, not conclusive. The benign set is 78 samples spread over several strata, so false-positive intervals are wide.
- Only detection is measured here. Whether an injection *succeeds* against a victim agent is Phase 4.
