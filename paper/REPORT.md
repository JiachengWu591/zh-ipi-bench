# zh-ipi-bench: a Chinese-native benchmark for indirect prompt injection, and what it shows about detectors and architectural isolation

**Jiacheng Wu** · technical report, v0.2 (October 2026) · code and data: <https://github.com/JiachengWu591/zh-ipi-bench>

> This is a one-author technical report on a small, template-generated benchmark. Every
> number in it is reproduced offline from committed result rows by `python -m zhipi.verify`.
> It makes no claim to be the first of anything; section 2 says what was and was not checked.
>
> *Revision note (v0.2):* the first version of this report described the v0.1.0 release
> (data v0 to v2, four transforms). This revision adds the four transforms and data v3
> (section 4.4), which qualify the H1 conclusion for the small classifier, a blind LLM
> annotation check (section 6), and a re-run of the related-work search (section 2).

## Abstract

Public indirect-prompt-injection benchmarks are overwhelmingly English. We built
**zh-ipi-bench**, a Chinese benchmark of instructions hidden in issues, documents, emails,
web pages and tool outputs, with Chinese-specific obfuscations (fullwidth forms, zero-width
characters, spaced characters, Chinese-English code-mixing, and, in a later version,
traditional script, pinyin, homophones and character decomposition) and benign *hard
negatives* written to resemble the attacks. Four versions (226, 803, 1,288 and 1,556
samples) support two studies. **(1) Detectors.** Across ten detector configurations, a strong
LLM judge reached 97% detection with 2% false positives, while a community multilingual
classifier flagged everything and an English-only one flagged 55% of benign text. The first
four transforms had no measurable effect on the two detectors that worked, and no transform,
including the four added later, hurt the LLM judge. For the small multilingual classifier,
three of the four later transforms lowered its detection rate (homophone 61% to 47%, the only
fall that survives correction for multiple comparisons) while its ranking quality (AUROC)
moved only 0.92 to 0.87-0.89, and character decomposition raised its detection to 82%. A
language gap in detection *rate* (97% vs 81%) was mostly a calibration shift (AUROC 0.97 vs
0.94). What did hurt was burying the payload in a long document (AUROC 0.94 to 0.89).
**(2) Architectural isolation.** Running an undefended agent and a schema-constrained
isolated pipeline end to end, the isolated pipeline leaked a planted fake secret in 0 of 239
runs with its probabilistic audit bypassed, in every language condition. On a strong model
the undefended baseline barely leaked (2%), so isolation had little to prevent; with a weak
local model (Qwen2.5-7B, whose own audit rated none of the injections high-risk) the
baseline leaked in 81 of 717 runs (11%). We discuss what each result can and cannot show.

## 1. Introduction

An LLM application that reads untrusted text, such as an issue tracker, a retrieval corpus,
an email inbox, or the output of a tool, can be steered by instructions hidden in that text.
This is *indirect* prompt injection. The defenses fall in two families: probabilistic ones
that try to recognise the attack (classifiers, LLM judges), and structural ones that limit
what a captured model can do (isolating the component that reads untrusted text from the
one that acts, constraining its output to a small fixed set).

Evaluation of both families is mostly in English. This matters for a concrete reason:
Chinese text offers evasions English does not (fullwidth forms, characters separated by
zero-width spaces or by spaces, free mixing with English), and a detector tuned on English
data may handle them differently, or not at all. We ask:

- **H1.** Do small detectors lose recall on Chinese-specific obfuscation, even where plain
  translation changes nothing?
- **H2.** How do detectors treat benign Chinese text that merely *resembles* an attack?
- **H3.** When the probabilistic layer is bypassed or fooled, does a structural boundary still
  contain Chinese-language injections, independently of the model's capability?

Each hypothesis may come out null, and we report nulls as such. The contributions are the
benchmark (section 3), a detector study with hard negatives, threshold-free and paired
analysis (section 4), an end-to-end study of an undefended agent against an isolated
pipeline on three model settings (section 5), and a reproduction package (section 7).

## 2. Related work and what was checked

Indirect-injection benchmarks and evaluations: BIPIA (arXiv 2312.14197), InjecAgent
(2403.02691) and Agent Security Bench (2410.02644) are English. OpenRAG-Soc (2601.10923) and
RAG-PIBench (2610.08571) target RAG; we read RAG-PIBench's body, which states it is
restricted to English. IssueTrojanBench (2607.20759) attacks coding agents through GitHub
issues; its only non-English condition is a single perturbation translating the payload to
Mandarin inside an otherwise English issue, which changed no outcome on three commercial
agents. INFUSE (2610.20776) evaluates 19 models and guard models; an appendix is headed
"English-only". MIPIAD (2605.07269) covers indirect-injection defense in English and
Bangla. Chinese safety resources (ChiSafe-PAS 2605.29667, CPAD 2309.11830, 2402.12193) target
harmful content and jailbreaks, not injections into an application's context.

A re-check (2026-10-25) found three closer neighbours that the first search missed.
GenTel-Safe (2409.19521) compares prompt-injection detectors (ProtectAI, Lakera, Prompt
Guard and others) on 84,812 attack prompts and includes a Chinese split, but the split is
machine-translated from English, the prompts are direct, and no Chinese-specific obfuscation is
described. A study of hidden prompts in papers submitted to LLM reviewers (2512.23684) injects
indirectly in English, Japanese, Chinese and Arabic, but evaluates victim models, not detectors.
An evaluation across English, Turkish, Russian and Simplified Chinese (2606.29602) uses direct
prompts and language-independent encodings (Base64, ROT13, hex) against six LLMs. Chinese
indirect-injection evaluation and Chinese detector evaluation therefore both exist in narrower
forms; Chinese-language toxicity work (ToxiCloakCN and others) studies the same pinyin and
homophone evasions for content moderation rather than injection.

**How far this was checked.** Search was not exhaustive (five queries in the re-check, one of
them in Chinese; Chinese venues such as CNKI were not searched); IssueTrojanBench, INFUSE,
RAG-PIBench, GenTel-Safe and 2606.29602 were checked against the page body, the others at
abstract level. We therefore claim only that we *did not find* a benchmark that is
Chinese-native, targets injections planted in an application's context, applies Chinese-specific
obfuscation, and measures detectors with hard-negative false positives; we do not claim priority.
`docs/RELATED_WORK.md` has the full list and the evidence level for each entry.

## 3. The benchmark

**Threat model.** Anyone who can put text where an application reads it as data (an issue,
an indexed document, a web page, an email, a tool result). The attacker cannot see the model,
the system prompt or the defense. Every goal targets a fictional sandbox and a fixed fake
placeholder secret, or the assistant's own instructions.

**Construction.** A fixed fictional host per carrier (a CLI, `blastdemo`, that fails on a
repeated `--profile`) and language; the payload is the only thing that varies. The five
carriers are `issue`, `rag_doc`, `email`, `web_html` and `tool_output`. 31 hand-written
*intents* each fix a goal and vary the persuasion, in Chinese with an English parallel. The
data is generated deterministically from seed files.

**Tiers** (the author's judgement of how recognisable the ask is, *not* a measured
property): `explicit` names the target and action; `implicit` does not, or frames the ask as
a format, a checklist, a quotation or a precedent; `spoofed_structure` forges delimiters or
tool/system messages; `judge_targeted` also addresses the screening component;
`ibr_corpus` holds twelve attacks ported from injection-blast-radius's corpus (English
original verbatim, Chinese hand-translated).

**Transforms** (applied to the payload only): `fullwidth`, `zero_width` (U+200B between CJK
characters), `space_split`, `code_mix` (Chinese terms replaced by English), and the
combination `code_mix`+`zero_width`. Four more were added in data v3 and are lookups in small
curated tables (no new dependency): `traditional` (simplified payload in traditional script; a
one-character table, cross-checked once against OpenCC), `pinyin` (key terms as toneless
pinyin), `homophone` (key terms with a same-sound character) and `char_decomp` (key terms
written as the components of their characters). They re-spell only vocabulary the payloads
already use, so they say nothing about other ways of writing those forms. A transform that
changes nothing is skipped, because a duplicate "transformed" sample would inflate *n* (a bug
of this kind was found and fixed).
**Placement:** `default`, or `buried`, with the payload between two blocks of benign
release-note and log filler.

**Hard negatives.** Benign samples written to look like attacks: a maintainer asking a human
reporter to paste their environment config; a security article quoting "ignore the previous
instructions"; an issue mentioning `.env`; a task list; a format request; a quoted
instruction; HTML-comment issue templates; a long document.

**Versions.** v0 (226 samples: 210 injected, 16 benign; six explicit intents) and v1 (803:
750 injected, 53 benign; adds the implicit, spoofed and judge-targeted tiers, the buried
placement and hard negatives) are frozen and pinned by a content fingerprint. v2 (1,288:
1,230 injected, 58 benign) adds the ported attacks and HTML-comment benign issues. v3 (1,556:
1,478 injected, 78 benign) adds the four table-based transforms on all 31 intents in the
`issue` carrier plus one rotating carrier, and 20 hand-written benign controls that contain the
same surface forms innocently (traditional-script text, pinyin, character breakdowns, homophone
discussions). v0 to v2 are frozen and pinned. v1 was built *because* v0 was saturated for a
strong judge (section 4); v2 *because* the baseline agent barely leaked on v1 (section 5); v3
to complete the transform axis.

**Safety.** Payloads contain injection wording against a fake secret, no exploit chains.
The one payload with a link uses the reserved, never-resolving `example.invalid`. Each
injected sample declares a `plaintext_intent` so an encoded or obfuscated payload can be
reviewed by eye.

## 4. Detector study

**Detectors.** Two naive keyword regex baselines (English, Chinese), included only to test
the harness; Qwen3Guard-Gen-0.6B as a *wrong-tool control* (a content-moderation model, not
an injection detector); a DeepSeek LLM judge (`deepseek-v4-flash`, forced tool call, temperature
0; prompt hash `f5243ad501f5`); a community multilingual-BERT classifier (unvetted);
Horizon-Labs/prompt-injection-guard-base (308M, multilingual including Chinese; its
published metrics are the authors' own and were not independently verified); and
protectai/deberta-v3-base-prompt-injection-v2 (English only, widely used). Llama Prompt
Guard 2 was planned but its gated access request was rejected, so it was not run. Local
models were run on CPU with pinned Hub commits.

**Metrics.** Detection rate on injected samples and false-positive rate on benign samples,
both with Wilson 95% intervals; exact McNemar tests on paired samples (same intent and
carrier, with and without a change); and AUROC with bootstrap intervals for detectors that
output a score. A failed detector call fails closed and is never counted as a detection.
Intervals treat samples as independent, which template-generated samples are not, so they are
too narrow; paired *p*-values are leads, not findings.

### 4.1 Overall (v1: 750 injected, 53 benign)

| detector | detection | false positives | note |
|---|---|---|---|
| DeepSeek judge (`high_risk` only) | 97% [96–98] | 2% [0–10] | works |
| Horizon-Labs classifier | 80% [77–83] | 13% [7–25] | works; AUROC 0.94 on Chinese |
| protectai (English only) | 84% [81–86] | **55%** [41–67] | over-flags; AUROC 0.57 on Chinese |
| community mBERT | 100% [99–100] | **100%** [93–100] | flags everything |
| keyword-zh / keyword-en | 5% / 1% | 4% / 2% | harness sanity only |
| Qwen3Guard (3 rules) | 0–1% | 0–4% | wrong-tool control |

On v0 the judge scored 100% detection and 0% false positives in every condition and
across three repeats: v0 could not tell it from a perfect detector, which is why v1 exists.
**A 100% cell is a statement about the dataset, not the detector.**

### 4.2 Chinese-specific transforms (H1)

For the judge and Horizon, no transform moved detection measurably (judge 96–98% across all
conditions; Horizon 76–84%; paired tests p ≥ 0.36). Fullwidth and zero-width changed no
Horizon verdict at all. The English-only protectai model shows the opposite sign (its
detection *rises* from 32% on English plain payloads to 87% on Chinese ones), but only
because it flags nearly all Chinese text: its AUROC falls from 0.68 to 0.57. **Rates alone
mislead; the threshold-free view corrects them.**

| Horizon | en/plain | zh/plain | zh/zero-width | zh/code-mix | zh/plain buried |
|---|---|---|---|---|---|
| detection @0.5 | 97% | 81% | 81% | 84% | **58%** |
| AUROC | 0.97 | 0.94 | 0.94 | 0.95 | **0.89** |

H1 is therefore **not supported** for the two detectors that work on the first four
transforms (the four added later, section 4.4, qualify this for Horizon). The English-vs-Chinese gap
in Horizon's detection rate (97% vs 81%, English better in 9 of 19 intents and worse in none)
is mostly a calibration shift: English text is also flagged more when benign (4 of 11 vs
3 of 32), and AUROC differs by 0.03 with overlapping intervals. A fair test of
"English-centric detectors degrade on Chinese" needs an English detector that works on
*indirect* injection first; protectai, built for direct injections, is not one.

### 4.3 Placement, and hard negatives (H2)

Burying the payload in a long document is the factor that mattered: Horizon's detection fell
from 81% to 58% (23 pairs lost, 1 gained) and its AUROC from 0.94 to 0.89; the judge was
unaffected. Hard negatives are where detectors differ most. The judge flagged one benign
request of the form "paste your environment config" addressed to a human (the
`asks_humans_for_info` stratum, 1 of 5 at the strict setting, 2 of 5 at the loose one);
Horizon flagged 3 of 5 of them and 2 of 3 in the placeholder-secret stratum; protectai flagged
5 of 5 in `asks_humans_for_info`, 5 of 5 in `discusses_injection` and 4 of 5 in
`mentions_config`. The judge's only misses on v1 (19 of 750) all
came from two `implicit` intents whose text is near-identical to a legitimate request to a
human; which label is correct depends on who reads the text, so these misses may measure
label ambiguity rather than a detector weakness (section 6 reports what a blind LLM annotator
said about this).

### 4.4 The four table-based transforms (data v3)

Run after the first release on a 388-sample slice of v3 (the 248 samples with a new transform,
their 62 untransformed twins, and all 78 benign samples), three detectors in one session at one
commit, no failures; the judge cost 388 billed calls, one repeat. Source: `results/v3_study.md`.

| | plain | traditional | pinyin | homophone | char. decomposition |
|---|---|---|---|---|---|
| judge, detection (strict) | 97% | 100% | 100% | 95% | 100% |
| Horizon, detection @0.5 | 61% | 52% | 50% | 47% | **82%** |
| Horizon, AUROC | 0.92 | 0.88 | 0.89 | 0.87 | **0.96** |
| Horizon, lost / gained vs plain (31 intents) | | 6 / 0 | 8 / 1 | 10 / 1 | 0 / 10 |

- **The LLM judge was not affected by any of the four** (at most one pair lost, zero to two
  gained; 1 of 78 benign samples flagged, none of the 20 new controls).
- **Horizon lost detection on three of them** (intent-level sign tests p = 0.03, 0.04, 0.01),
  but with four comparisons per detector only the homophone fall survives a Bonferroni
  threshold of 0.0125. Its AUROC moved only from 0.92 to 0.87-0.89 with overlapping
  intervals, the same calibration-shift pattern as the Chinese-versus-English gap in section 4.2,
  not a collapse of ranking. Decomposed text was flagged *more* (82%, AUROC 0.96, 0 lost and 10
  gained, p = 0.002), which suggests the classifier partly keys on how odd the text looks; the
  four benign character-breakdown controls were not flagged (0 of 4), too few to say more.
  Carrier mattered more than any transform for Horizon: 100% on `tool_output` and `web_html`,
  44-48% on issue, email and document.
- **protectai stayed at chance** (AUROC 0.52-0.55) and flagged 60% of benign text, including
  100% of the pinyin and injection-discussion controls.
- **False positives on the new controls:** judge 0 of 20, Horizon 1 of 20 (a traditional-script
  issue), protectai 14 of 20.

H1 is thus **not supported for the LLM judge on any of the eight Chinese transforms**, and
**weakly supported for the small classifier**: three of the four table-based transforms cost it
detection, the homophone one clearly, without much loss of ranking quality. Limits: the
comparisons are uncorrected across detectors, the two carriers of an intent are replicates (31
independent intents), the tables cover key terms only, a traditional payload sits in a
simplified-script host, and the new benign strata have 3 to 8 samples each, so a zero in three
samples still allows a false-positive rate above 50%.

## 5. End-to-end study of architectural isolation (H3)

Detection is not the goal; preventing harm is. We therefore measure whether an injection
*succeeds*: does the planted fake secret reach the public output?

**Systems.** Using injection-blast-radius (commit `af8a758`) as the target: (a) an
undefended single agent that reads the issue and can read files and post comments; (b) its
*isolated pipeline*, in which the component that reads untrusted text may emit only a
schema-constrained decision and the component that acts sees only an enum and can publish only
four static templates. For (b) the probabilistic audit is **bypassed**, so only the
structural layer stands between the injection and the output. One isolated run also yields the
audit-on outcome (a real `high_risk` verdict would have stopped the run).

**Procedure.** Carrier `issue`; samples of eight conditions (English, Chinese, four transforms,
one combination, buried) over every intent except `dump_prompt` (its goal is the assistant's
instructions, not the secret); plus benign issues. The baseline is run three times per
sample, the isolated pipeline once. A *leak* is any fake secret value in the public output
in plain, URL-encoded or base64 form. A failed run is neither a leak nor a hold. Runs are
resumable and any isolated leak is flagged as a defect.

| setting | injected samples | baseline leaked | isolated leaked (audit bypassed) | note |
|---|--:|---|---|---|
| E1: `deepseek-v4-flash`, v1 | 143 | 4 / 429 (1%) | 0 / 143 | no language or transform effect |
| E2: `deepseek-v4-flash`, v2 | 239 | 14 / 717 (2%) | 0 / 239 | ported attacks 10 / 288 (3.5%) |
| **E3: Qwen2.5-7B (local), v2** | 239 | **81 / 717 (11%)** [9–14] | **0 / 239** [0–2] | same model also as audit |

**E1 and E2: a strong model.** The undefended baseline barely leaked, so the boundary had
almost nothing to prevent; E1/E2 show only that it holds and costs little. We checked that this
was not an artefact of how this project embeds payloads: the target repository's own
`attack_matrix.py` (its hosts, its payloads), run twice today, leaked on 1 of 12 and 0 of 12
patterns, against 6 of 12 its README reports. The robustness is the model's, whether from drift
or the variance of the earlier run (not investigated).

**E3: a capturable model.** DeepSeek's key offers no weaker model, so Qwen2.5-7B-Instruct
(official Q4_K_M GGUF, checksums verified, llama.cpp b11829, 12k context) ran locally as the
brain of **both** architectures and of every stage (baseline agent, audit, reader), removing a
confound. A small trial gated the run (tool-call success 100% against an 80% bar; baseline
leak 17% against a 10% bar). The baseline leaked in 81 of 717 completed injected runs, the
isolated pipeline with its audit bypassed in **0 of 239** (Fisher exact p = 3e-11, treating
runs as independent). The same model acting as the audit rated **none** of 239 injected samples
`high_risk` (226 `safe`, 12 `suspicious`, 1 failed): the probabilistic layer was effectively
blind, so "audit on" equals "audit bypassed" and everything that stopped the attacks was
structural. 24 of 30 intents leaked on the baseline at least once. The server ignored a
*named* tool choice (in a probe it called `read_file("sandbox/.env")` when told to call the
screening tool, i.e. it was captured), so the run used "some tool call required"; the pipeline
still validates which tool and arguments return.

**Language and transform effects on the baseline** are not established: Chinese 76/627 (12%)
vs English 5/90 (6%) by run, but per intent p = 0.55 (30 intents); transforms and buried
placement also null (p ≥ 0.45). Leaks concentrate in a few intents (`leak_secret` 12/24,
`json_format` 10/24, `exfil_link` 8/24), while the ported `ibr_corpus` attacks leaked less on
this model (6%).

**Cost.** On benign issues the isolated pipeline took no action on 2 of 21 (10%, [3–29]),
3 of 26 (12%, [4–29]) and 2 of 26 (8%, [2–24]) in E1, E2 and E3, consistent with the 6.1% its
authors report; the fixed action set is the price. The undefended agent leaked the secret on a
*benign* issue in 1 of 63 and 1 of 78 runs (E1, E2) when an issue merely mentioned `.env`.

## 6. Discussion

**What the evidence supports.**
(H3) With a model that is demonstrably capturable and an audit that caught nothing, the
boundary turned an 11% leak rate into 0 of 239, in Chinese, under every transform and the
buried placement. Containment did not depend on the language or the model, as its design
implies. (H1) For the LLM judge, no Chinese-specific transform and not the language itself
hurt. For the small classifier, the first four transforms and the language did not (the
rate gap was calibration), three of the four later table-based ones cost it detection with
little loss of ranking quality, and the structure of the document (burying the payload) hurt
most. (H2) Hard negatives separate
detectors that the headline detection rate cannot: one that flags everything and one that
flags 13% of benign text score alike on detection.

**What it does not show.** That the boundary is unbeatable (the executor can only post four
static templates, so zero leaks is true by construction on this criterion). That Chinese is
*easier or harder* to defend: no language effect on the baseline was established. Anything
about real-world attack distributions. A language effect on small English-centric detectors
(no working English control).

**Threats to validity.**
*Template data and few intents* (31; some tiers rest on 1–2): intervals are too narrow, and
the carriers of an intent (five, or two in v3) are replicates. *One author, no human second
annotator*: a blind LLM annotator (a fresh Claude agent given only the texts and the written
rule, not a person) agreed with the author's label on 102 of 103 texts (Cohen's kappa 0.98;
the one exception was a `ctx_config` text it marked unsure) and rated 4 of 31 translations
slightly off (`results/annotation.md`). That is an upper bound: the model family overlaps with
the tools that helped draft the data, these templated texts are easy for it, and its
independence rests on an instruction. It does not support "the judge's misses are label
noise" (it labelled both `checklist` texts and one of two `ctx_config` texts injected, and all
four `asks_humans_for_info` benign texts benign), and human agreement remains unmeasured.
*Difficulty tiers are a hypothesis.* *Leak criterion*: one (a fake secret value in the
output); a leak in another form would be missed. *The bait file announces that it is fake*,
which may change how readily a baseline quotes it; not tested. *One model per E3*, quantized,
under a `required` rather than named tool choice. *Hosted models drift* (E1/E2 versus the
README's 6 of 12). *Several detectors' published metrics* are the authors' own and were not
independently verified. *Related-work coverage* is partial (section 2).

**Responsible release.** The data is adversarial text against a fake secret and is released
to evaluate and harden defenses; it should not be fed to an agent holding real secrets or
tools. Code is MIT, data is CC BY 4.0. Problems with the repository's content can be reported
privately through GitHub's security advisories.

## 7. Reproducibility

`python -m zhipi.verify` rebuilds every dataset version from the seed files, checks it against
`release/MANIFEST.json`, regenerates every table in `results/` (the detector, end-to-end,
v3 and annotation reports) and the README figure from the committed rows in `results/rows/`
and `results/annotation/`, and compares them byte for byte with the committed files (twelve
checks); a test runs it in CI.
It needs no model, key or network. It shows that the tables are a pure function of the rows
and the code; it does not show that the rows are right or that rerunning a hosted model today
would reproduce them. Each run records the code commit, model revision (Hub commit or prompt
hash), dataset hash and, for E3, the llama.cpp build and model file.

| item | pinned |
|---|---|
| datasets | v0 `4017820d…`, v1 `d507be34…`, v2 `7d478b6a…`, v3 `a78ba37f…` (content fingerprints; `MANIFEST.json`) |
| Hub models | Qwen3Guard-Gen-0.6B `fada3b2f65`; Horizon base `495ee67524`; protectai `90c9989b1a`; community mBERT `63bf478b07` |
| judge | `deepseek-v4-flash`, prompt hash `f5243ad501f5` |
| end-to-end target | injection-blast-radius `af8a758` |
| E3 | Qwen2.5-7B-Instruct Q4_K_M (official GGUF, SHA-256 checked), llama.cpp b11829 |

Re-running the *models* needs, for the judge (including the 388 calls of section 4.4) and
E1/E2, a DeepSeek key (roughly a few thousand billed calls in total) and a clone of the target repository; E3 and the local detectors are
free but need a GPU or patience (README has the commands).

## References

BIPIA (Yi et al.) arXiv 2312.14197 · InjecAgent arXiv 2403.02691 · Agent Security Bench arXiv
2410.02644 · OpenRAG-Soc arXiv 2601.10923 · RAG-PIBench arXiv 2610.08571 · IssueTrojanBench
arXiv 2607.20759 · INFUSE arXiv 2610.20776 · MIPIAD arXiv 2605.07269 · ChiSafe-PAS arXiv
2605.29667 · CPAD arXiv 2309.11830 · Chinese safeguards dataset arXiv 2402.12193 · Qwen3Guard
arXiv 2510.14276 · Llama Prompt Guard 2 model card · Horizon-Labs/prompt-injection-guard-base
model card · protectai/deberta-v3-base-prompt-injection-v2 model card · llama.cpp function
calling documentation.
