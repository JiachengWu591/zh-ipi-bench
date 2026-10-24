# Publishing v0.1.0

Everything here is outward-facing and happens under the owner's name, so each step is the
owner's call. The repository itself is already public; these steps add a tag, a GitHub
release and a Hugging Face dataset.

## Before publishing

1. Read `paper/REPORT.md` end to end; it is published under your name. Anything you do not
   stand behind should be changed first.
2. `python -m zhipi.verify` should print `9/9 checks passed`, and CI on `main` should be green.

## 1. Tag and GitHub release

```bash
git switch main && git pull
git tag -a v0.1.0 -m "zh-ipi-bench v0.1.0"
git push origin v0.1.0
```

Then on GitHub: Releases -> Draft a new release -> choose tag `v0.1.0` -> paste the notes
below. (Creating a release object needs the website or a token; the tag alone is a plain
git push.)

### Release notes (paste)

> **zh-ipi-bench v0.1.0**: a research artifact, not a leaderboard.
>
> A Chinese-native benchmark for indirect prompt injection, a detector-evaluation harness,
> and an end-to-end test of architectural isolation. One author, template-generated data, no
> second annotator yet; limits are in the report.
>
> - Data: v0 (226 samples) and v1 (803) are frozen; v2 (1,288) adds attacks ported from
>   injection-blast-radius. Checksums in `release/MANIFEST.json`.
> - Findings (with intervals and caveats in `paper/REPORT.md`): a strong LLM judge reached
>   97% detection / 2% false positives; Chinese-specific transforms had no measurable effect
>   on the detectors that worked; the isolated pipeline leaked a planted fake secret in 0 of
>   239 runs while an undefended agent on a weak local model leaked in 81 of 717.
> - Reproduce every table with no model, key or network: `python -m zhipi.verify`.
>
> Code is MIT, data is CC BY 4.0.

## 2. Hugging Face dataset

The upload folder is built locally and is not committed:

```bash
python -m zhipi.release dist        # -> dist/zh-ipi-bench/
```

It contains `README.md` (the dataset card with its YAML header), `data/v0|v1|v2.jsonl`,
`seed/`, `MANIFEST.json`, `LICENSE.md` and the CC BY 4.0 text.

**Without sharing a token (simplest):** create a new *public Dataset* on huggingface.co
named `zh-ipi-bench` under your account, open "Files and versions" -> "Add file" -> "Upload
files", and drag in the *contents* of `dist/zh-ipi-bench/` (keep the `data/` and `seed/`
folders). The page then renders the card, and the `v0`/`v1`/`v2` configs appear in the
viewer.

**With the CLI** (needs a write token that you set yourself, never in a file or a chat):

```bash
hf auth login
hf upload <your-username>/zh-ipi-bench dist/zh-ipi-bench . --repo-type dataset
```

Check afterwards that the viewer shows three configs and that the card's counts match
`MANIFEST.json`.

## After publishing

- Add the dataset link to `README.md` and `CITATION.cff` (`url:`/`identifiers:`), and the
  tag date to `CITATION.cff` (`date-released`).
- If the report goes to arXiv it needs converting to LaTeX/PDF first.
