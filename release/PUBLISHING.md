# Publishing v0.2.0

Everything here is outward-facing and happens under the owner's name, so each step is the
owner's call. The repository is public already; v0.1.0 (tag, GitHub release and the
Hugging Face dataset with configs `v0`, `v1`, `v2`) is out. These steps add v0.2.0: a tag, a
GitHub release, and the `v3` config on the existing Hugging Face dataset.

## Before publishing

1. `python -m zhipi.verify` should print `12/12 checks passed`, `python -m pytest` should
   pass, and CI on `main` should be green.
2. Skim `results/v3_study.md` and the v0.2.0 entry in `CHANGELOG.md`; they are published under
   your name. Anything you do not stand behind should be changed first.
3. `paper/REPORT.md` still describes v0.1.0 (it carries a note pointing at the newer results).
   Folding the v3 results into the report is optional and is not required for this release.

## 1. Tag and GitHub release

```bash
git switch main && git pull
git tag -a v0.2.0 -m "zh-ipi-bench v0.2.0"
git push origin v0.2.0
```

Then on GitHub: Releases -> Draft a new release -> choose tag `v0.2.0` -> paste the notes
below. (Creating a release object needs the website or a token; the tag alone is a plain
git push.)

### Release notes (paste)

> **zh-ipi-bench v0.2.0**: a research artifact, not a leaderboard.
>
> Adds four Chinese-specific transforms (traditional script, pinyin, homophone, character
> decomposition), data version **v3** (1,556 samples; v0, v1 and v2 are byte-identical to
> 0.1.0), detector results on them, and a blind annotation check.
>
> - **Data.** `v3` = v2 plus the four transforms on all 31 intents in two carriers, and 20
>   hand-written benign controls that contain the same surface forms innocently. Checksums
>   in `release/MANIFEST.json`.
> - **Findings** (`results/v3_study.md`, 388 samples; intervals and caveats in the report):
>   no new transform hurt the strong LLM judge (1% false positives). The small multilingual
>   classifier lost detection on three of them (homophone 61% to 47%, the clearest) while its
>   AUROC moved only 0.92 to 0.87-0.89, and flagged *more* of the character-decomposed text.
>   An English-only classifier stayed at chance (AUROC about 0.5). Comparisons are uncorrected,
>   intent replicates are correlated, and the new benign strata have 3-8 samples each.
> - **Annotation.** A blind LLM annotator (not a person) agreed with the author's label on 102
>   of 103 texts: an upper bound; human agreement is still unmeasured.
> - Reproduce every table and the figure with no model, key or network:
>   `python -m zhipi.verify`.
>
> Code is MIT, data is CC BY 4.0.

## 2. Hugging Face dataset (add `v3`)

The upload folder is built locally and is not committed:

```bash
python -m zhipi.release dist        # -> dist/zh-ipi-bench/
```

It contains `README.md` (the dataset card with its YAML header, now listing the `v3`
config), `data/v0|v1|v2|v3.jsonl`, `seed/`, `MANIFEST.json`, `LICENSE.md` and the CC BY 4.0
text. Only four files differ from what is already on Hugging Face: `README.md`,
`MANIFEST.json`, `seed/benign.jsonl` and the new `data/v3.jsonl`; `data/v0|v1|v2.jsonl` are
byte-identical (compare their SHA-256 with `MANIFEST.json`).

**Without sharing a token (simplest):** open the dataset page -> "Files and versions" ->
"Add file" -> "Upload files", and drag in the *contents* of `dist/zh-ipi-bench/` (keep the
`data/` and `seed/` folders; uploading the unchanged files again is harmless). The page then
renders the updated card and a `v3` config appears in the viewer.

**With the CLI** (needs a write token that you set yourself, never in a file or a chat):

```bash
hf auth login
hf upload <your-username>/zh-ipi-bench dist/zh-ipi-bench . --repo-type dataset
```

Check afterwards that the viewer shows four configs (`v0` to `v3`) and that the card's counts
match `MANIFEST.json`.

## After publishing

- If the report goes to arXiv it needs converting to LaTeX/PDF first (and, if you want the
  v3 results in it, folding them in).
