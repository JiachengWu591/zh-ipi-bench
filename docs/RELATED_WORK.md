# Related work and novelty check

**Checked 2026-10-18; re-checked 2026-10-25.** Method: web search, plus fetching the arXiv
page text. Three entries (IssueTrojanBench, INFUSE, RAG-PIBench) were checked against the
paper body in the first pass, and in the re-check GenTel-Safe and arXiv 2606.29602 were read
from their HTML bodies (all marked ✔); the rest are abstract-level only, and the searches
were not exhaustive. "Body" here means the text returned by a page-fetch tool that
summarizes with a small model, not a manual read of the PDF (PDF fetches returned
compressed binary and were not usable), so quotes were cross-checked with a second fetch
where they carry weight. The re-check ran four English and one Chinese-language search
(Chinese indirect-injection benchmarks; pinyin/homophone/decomposition obfuscation;
multilingual detector benchmarks; Chinese agent-injection benchmarks) and found the
additions marked "re-check" below. Re-run this before making any "first" claim in public.

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
| [ChiSafe-PAS, arXiv 2605.29667](https://arxiv.org/abs/2605.29667) | "Beyond English and Evasion", Chinese Safety Pilot Annotation Set: 1,897 Chinese adversarial prompts (1,544 fully annotated) in four high-stakes domains, with pinyin romanization and character decomposition among its evasion techniques (re-check: the abstract page confirms the name and these two) | Content *safety*, not injection into an application's context. Useful source of evasion ideas |
| [GenTel-Safe, arXiv 2409.19521](https://arxiv.org/abs/2409.19521) ✔ (re-check) | 84,812 attack prompts (jailbreak, goal hijacking, prompt leaking), 1:1 with benign data; compares GenTel-Shield with ProtectAI, Hyperion, Lakera, Deepset, Fmops, WhyLabs LangKit and Prompt Guard. The English benchmark was machine-translated (Google Translate) into Chinese, Japanese, French, Spanish and German for a multilingual test | **The closest prior work on detectors in Chinese**, so "no Chinese detector evaluation exists" is false. But: direct prompts, not injections inside documents or tool outputs; Chinese is machine-translated from English, not native; no Chinese-specific obfuscation; Chinese sample count not stated in what was fetched |
| [Multilingual hidden prompt injection on LLM reviewing, arXiv 2512.23684](https://arxiv.org/abs/2512.23684) (re-check, abstract only) | Hidden prompts in academic papers, in English, Japanese, Chinese and Arabic; English, Japanese and Chinese injections shifted review scores, Arabic hardly did | **An indirect, Chinese-inclusive study**, so Chinese indirect injection has been measured. It evaluates victim LLMs, not detectors, and one carrier (a paper); no Chinese-specific obfuscation was mentioned |
| [arXiv 2606.29602](https://arxiv.org/html/2606.29602v1) ✔ (re-check) | Multilingual and obfuscated prompt injection against six LLMs (DeepSeek-V3.2, Gemini 2.5 Flash, GPT-5 Mini, Grok-4-1-Fast, Llama 4 Scout, Qwen 3 235B) in English, Turkish, Russian and Simplified Chinese; Base64, ROT13 and Hex encodings | Direct prompts; victims, not detectors; the obfuscations are language-independent encodings, none Chinese-specific (no pinyin, homophone, fullwidth, zero-width or traditional script) |
| [WAInjectBench, arXiv 2510.01354](https://arxiv.org/abs/2510.01354) (re-check, abstract only) | Benchmark of prompt-injection *detection* for web agents, text and image | Languages not stated on the abstract page; Chinese not mentioned |
| [IPI Arena, arXiv 2603.15714](https://arxiv.org/abs/2603.15714) (re-check, abstract only) | Public red-teaming competition on indirect injection: about 272,000 attempts, 13 frontier models, 41 scenarios; 95 successful attacks against Qwen released | No language breakdown on the abstract page; no detectors |
| [PIGuard / NotInject, ACL 2025](https://aclanthology.org/2025.acl-long.1468/) (re-check, abstract only) | 339 benign samples with injection trigger words, to measure *over-defense* of prompt guards | Same idea as our hard-negative strata, in a different setting. A search snippet said it includes Chinese; the fetched page did not confirm languages, so unverified |
| ToxiCloakCN ([2406.12223](https://arxiv.org/pdf/2406.12223)), Lost in Pronunciation ([2507.07640](https://arxiv.org/pdf/2507.07640)), Breaking the Cloak ([2505.22184](https://arxiv.org/pdf/2505.22184)) (re-check, search snippets only) | Chinese offensive-language detection against pinyin, homophone and other cloaking | Toxicity, not injection; they show the same evasion families are studied for Chinese content moderation. Useful as taxonomy |
| [Promptfoo, "Chinese Pattern Safety Evasion"](https://www.promptfoo.dev/lm-security-db/vuln/chinese-pattern-safety-evasion-680120ac/) (re-check, search snippet only) | Jailbreak obfuscation with pinyin mix, homophones, symbol mix and zero-width insertion against lightweight Chinese LLMs | Direct jailbreaks against models, not indirect injection or detectors |
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
  this and takes the max). *Update:* the Hugging Face access request was rejected,
  so it has not been run; the Horizon-Labs model below took its place.
- **Horizon-Labs/prompt-injection-guard-base** (Apache-2.0, ungated, 308M, mmBERT
  backbone; card read 2026-10-21). States synthetic training data in 30 languages
  (Chinese listed) and documents with planted injections in 45 types, built from
  permissively licensed sources only. Its numbers (for example 94.4% on NotInject,
  F1 0.99 on its own held-out synthetic sets) are computed by the authors and have
  **not** been independently verified here; held-out synthetic data from the same
  generator is the easiest setting for any detector. The card lists its own weak
  spot: bare out-of-place tasks in documents are often missed. Evaluated here via
  the generic `hf-classifier` kind with the 2048-token window the card recommends.
- **protectai/deberta-v3-base-prompt-injection-v2** (Apache-2.0, 704 MB, DeBERTa-v3
  base; card: "highly accurate in identifying prompt injections in English", English
  only). Run as an English-centric control. On v1 it over-flags (55% false positives,
  worst on Chinese text) and ranks injections poorly (AUROC 0.68 English, 0.57
  Chinese), so it is a weak control for *indirect* injection; see `docs/ROADMAP.md`.
- Other ungated candidates seen but not run: `patronus-studio/wolf-defender-*`
  (multilingual, Chinese not confirmed), `NeuralTrust/prompt-guard-oss-small`
  (nine languages, Chinese not seen in the list).
- **Qwen3Guard** ([arXiv 2510.14276](https://arxiv.org/abs/2510.14276); Gen-0.6B
  etc. on Hugging Face, Apache-2.0). Evaluated on Chinese and supports 119
  languages, but its documented scope is harmful-content moderation, **not**
  prompt-injection detection. Including it is a deliberate "wrong tool" control,
  and must be labelled as such.
- **LLM-as-judge audit** via DeepSeek (API), and the
  [injection-blast-radius](https://github.com/JiachengWu591/injection-blast-radius)
  audit (see `src/zhipi/adapters/ibr_adapter.py`).

## What this means for the claim

Safe to say (after the 2026-10-25 re-check): *"We did not find a benchmark that is
Chinese-native, targets injections planted in documents, emails, web pages and tool
outputs, applies Chinese-specific obfuscation (traditional script, pinyin, homophones,
character decomposition, fullwidth, zero-width, code-mixing), and measures detectors with
hard-negative false positives. The nearest are GenTel-Safe (detectors, machine-translated
direct prompts, no Chinese-specific obfuscation), arXiv 2512.23684 (indirect Chinese
injection, victim models only) and IssueTrojanBench (one translation condition, victim
agents)."* Not safe to say: *"the first"*, *"no Chinese detector evaluation exists"*, or
*"no Chinese indirect-injection evaluation exists"*; both exist in narrower forms.

The scoping that survives is the specific combination of Chinese-specific
transforms, detector evaluation with hard-negative false-positive measurement, and an
architectural-isolation comparison against the probabilistic layer. Still unread in
full: OpenRAG-Soc, MIPIAD, Agent Security Bench, the second half of INFUSE's appendix, and
(from the re-check) 2512.23684, WAInjectBench, IPI Arena and NotInject beyond their abstract
pages. The Chinese-language search returned mostly popular-science articles and no Chinese
benchmark, but it is a single query, not a survey of Chinese-language venues (CNKI,
Chinese conferences, WeChat or Zhihu posts were not searched).
