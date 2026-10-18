# Related work and novelty check

**Checked 2026-10-18.** Method: web search plus reading arXiv abstract pages. That
is abstract-level only: no paper below was read in full, and search was not
exhaustive. Re-run this before making any "first" claim in public, and read the
full text of the three closest entries marked ⚠.

## The gap this project targets

No benchmark found that is **both** (a) about *indirect* prompt injection (the
instruction arrives in a document, web page, email, or tool output, not in the
user's own message) **and** (b) Chinese-native, i.e. built around how
Chinese text is actually written and obfuscated rather than translated from
English.

## What exists (and how this project differs)

| Work | What it covers | Why it does not close the gap |
|---|---|---|
| [BIPIA, arXiv 2312.14197](https://arxiv.org/abs/2312.14197) | The original indirect-injection benchmark | English |
| [InjecAgent, arXiv 2403.02691](https://arxiv.org/abs/2403.02691) | 1,054 cases, tool-integrated agents | English (a Chinese *translation* of the paper exists on CSDN; not a Chinese-native dataset) |
| [Agent Security Bench, arXiv 2410.02644](https://arxiv.org/pdf/2410.02644) | Attacks and defenses for LLM agents | English |
| [OpenRAG-Soc, arXiv 2601.10923](https://arxiv.org/pdf/2601.10923) | Web-facing RAG, retrieval poisoning, Unicode normalization as a mitigation | English-oriented; ⚠ check whether any non-English subset exists |
| [RAG-PIBench, arXiv 2610.08571](https://arxiv.org/html/2610.08571v1) | Injection *detection* in RAG context, leakage-aware | ⚠ language coverage not verified |
| [IssueTrojanBench, arXiv 2607.20759](https://arxiv.org/abs/2607.20759) | Malicious GitHub issues vs Cursor / Claude Code / Codex (66.5% got past all guardrails) | Abstract does not state payload languages ⚠ — the closest to our `issue` carrier |
| [INFUSE, arXiv 2610.20776](https://arxiv.org/abs/2610.20776) | 56 attack scenarios, 19 LLMs incl. Qwen, ~41.8k trajectories | Abstract does not mention language coverage ⚠ |
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
- **Qwen3Guard** ([arXiv 2510.14276](https://arxiv.org/abs/2510.14276); Gen-0.6B
  etc. on Hugging Face, Apache-2.0). Evaluated on Chinese and supports 119
  languages, but its documented scope is harmful-content moderation, **not**
  prompt-injection detection. Including it is a deliberate "wrong tool" control,
  and must be labelled as such.
- **LLM-as-judge audit** via DeepSeek (API), and the
  [injection-blast-radius](https://github.com/JiachengWu591/injection-blast-radius)
  audit (see `src/zhipi/adapters/ibr_adapter.py`).

## What this means for the claim

Safe to say, after the ⚠ items are read: *"We did not find a Chinese-native
indirect prompt-injection benchmark."* Not safe to say: *"the first."* The
scoping that survives a close neighbour appearing is the specific combination
of Chinese-specific transforms, hard-negative false-positive measurement, and an
architectural-isolation comparison against the probabilistic layer.
