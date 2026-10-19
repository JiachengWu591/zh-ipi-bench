# Related work and novelty check

**Checked 2026-10-18.** Method: web search, plus fetching the arXiv page text. Three
entries (IssueTrojanBench, INFUSE, RAG-PIBench) were checked against the paper body
(marked ✔); the rest are abstract-level only, and the search was not exhaustive.
"Body" here means the text returned by a page-fetch tool that summarizes with a small
model, not a manual read of the PDF, so quotes were cross-checked with a second fetch
where they carry weight. Re-run this before making any "first" claim in public.

## The gap this project targets

No benchmark found that is **both** (a) about *indirect* prompt injection (the
instruction arrives in a document, web page, email, or tool output, not in the
user's own message) **and** (b) Chinese-native, i.e. built around how
Chinese text is actually written and obfuscated rather than translated from
English.

**Closest neighbour, which changes how to phrase this:** IssueTrojanBench ✔ includes
exactly one Chinese condition, a "cross-lingual" perturbation where the payload is
translated to Mandarin inside an otherwise English issue. So "no benchmark has any
Chinese indirect-injection condition" is **false**. What was not found is a benchmark
that is Chinese throughout (context and payload), uses Chinese-specific obfuscation,
or evaluates injection *detectors* (not victim agents) on Chinese text.

**A result that constrains our hypotheses:** the same paper reports that the
translation perturbation, like position, capitalization and font size, "produced
identical outcomes" across all 4,176 runs on three commercial coding agents. Together
with arXiv 2607.10080 (below), the prior evidence is that translating a payload does
*not* by itself raise attack success against frontier victims. Our research questions
therefore must not assume a language effect on victims; they ask about *detectors* and
about *Chinese-specific obfuscation*, and a null result is a legitimate outcome.

## What exists (and how this project differs)

| Work | What it covers | Why it does not close the gap |
|---|---|---|
| [BIPIA, arXiv 2312.14197](https://arxiv.org/abs/2312.14197) | The original indirect-injection benchmark | English |
| [InjecAgent, arXiv 2403.02691](https://arxiv.org/abs/2403.02691) | 1,054 cases, tool-integrated agents | English (a Chinese *translation* of the paper exists on CSDN; not a Chinese-native dataset) |
| [Agent Security Bench, arXiv 2410.02644](https://arxiv.org/pdf/2410.02644) | Attacks and defenses for LLM agents | English |
| [OpenRAG-Soc, arXiv 2601.10923](https://arxiv.org/pdf/2601.10923) | Web-facing RAG, retrieval poisoning, Unicode normalization as a mitigation | English-oriented; ⚠ check whether any non-English subset exists |
| [RAG-PIBench, arXiv 2610.08571](https://arxiv.org/html/2610.08571v1) ✔ | Injection *detection* in RAG context; 4,876 examples (balanced benign/malicious), hosts from CNN/DailyMail, SQuAD, WikiText-2; DistilBERT best at F1 0.896 | English only: the paper states "restricted to English textual inputs" (§3.1) and lists multilingual attacks as future work |
| [IssueTrojanBench, arXiv 2607.20759](https://arxiv.org/abs/2607.20759) ✔ | Malicious GitHub issues vs Cursor / Claude Code / Codex: 6 seed issues → 696 artifacts → 4,176 runs; 66.5% got past all guardrails | One Chinese condition only (payload translated to Mandarin, context English); no effect observed; ≈ our `issue` carrier. Evaluates victim agents and one Spotlighting-style prompt defense, not injection detectors |
| [INFUSE, arXiv 2610.20776](https://arxiv.org/abs/2610.20776) ✔ | 40 tasks, 56 attack scenarios, 19 LLMs (incl. Qwen), ~41.8k trajectories; Qwen Guard and Llama Guard as external classifiers | English-only (Appendix H heading "English-only"; its body text was truncated in the fetch, so the details are unread) |
| [MIPIAD, arXiv 2605.07269](https://arxiv.org/pdf/2605.07269) | Multilingual indirect-injection *defense*, built on BIPIA templates | English + Bangla only; synthetic; no Chinese |
| [Turkish prompt-injection benchmark (MDPI)](https://www.mdpi.com/2076-3417/16/13/6740) | 790 Turkish prompts, 55 LLMs, EN comparison | Turkish; direct prompts |
| [arXiv 2607.10080](https://arxiv.org/pdf/2607.10080) | Multilingual/keyword adversarial injection vs LLM relevance judgment | Reports multilinguality did not reduce attack effectiveness — motivates *not* assuming a language gap, and measuring it |
| [ChiSafe-PAS, arXiv 2605.29667](https://arxiv.org/pdf/2605.29667) | 1,897 Chinese adversarial prompts with pinyin / character-decomposition evasion | Content *safety*, not injection into an application's context. Useful source of evasion ideas |
| [CPAD, arXiv 2309.11830](https://arxiv.org/abs/2309.11830v1) | Chinese prompt-attack dataset | Jailbreak-style, direct |
| [Chinese safeguards dataset, arXiv 2402.12193](https://arxiv.org/pdf/2402.12193) | Chinese harmful-content / over-refusal evaluation | Content safety |

## Detectors worth evaluating

- **Llama Prompt Guard 2 (86M / 22M).** Meta's page says the 86M model is trained
  on English and non-English attacks and the 22M model is English-only. The exact
  language list and whether Chinese is covered were **not verified**; read the
  model card, and treat Chinese performance as an open question this benchmark
  can answer.
  *Update (model card read 2026-10-19):* the card says the model was **evaluated** on
  English, French, German, Hindi, Italian, Portuguese, Spanish and Thai. Chinese is
  not in that list, so a Chinese result is a measurement outside the stated
  evaluation, not a regression from a claimed capability. The repo is gated (Llama 4
  Community License plus an access form), the context window is 512 tokens, and the
  card advises splitting longer inputs into segments (`adapters/prompt_guard.py` does
  this and takes the max).
- **Qwen3Guard** ([arXiv 2510.14276](https://arxiv.org/abs/2510.14276); Gen-0.6B
  etc. on Hugging Face, Apache-2.0). Evaluated on Chinese and supports 119
  languages, but its documented scope is harmful-content moderation, **not**
  prompt-injection detection. Including it is a deliberate "wrong tool" control,
  and must be labelled as such.
- **LLM-as-judge audit** via DeepSeek (API), and the
  [injection-blast-radius](https://github.com/JiachengWu591/injection-blast-radius)
  audit (see `src/zhipi/adapters/ibr_adapter.py`).

## What this means for the claim

Safe to say: *"We did not find a benchmark that is Chinese throughout and evaluates
injection defenses on Chinese-specific obfuscation; the closest, IssueTrojanBench,
tests a single translation condition on victim agents."* Not safe to say: *"the
first"*, or *"no Chinese indirect-injection evaluation exists."*

The scoping that survives is the specific combination of Chinese-specific
transforms, detector evaluation with hard-negative false-positive measurement, and an
architectural-isolation comparison against the probabilistic layer. Still unread in
full: OpenRAG-Soc, MIPIAD, Agent Security Bench, and the second half of INFUSE's
appendix.
