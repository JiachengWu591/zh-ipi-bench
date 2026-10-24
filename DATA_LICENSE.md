# Data license

The dataset content in this repository — everything under `data/` (the hand-written
intents in `data/seed/` and any files generated from them) — is licensed under the
**Creative Commons Attribution 4.0 International (CC BY 4.0)** license.

- Summary: <https://creativecommons.org/licenses/by/4.0/>
- Full legal code: <https://creativecommons.org/licenses/by/4.0/legalcode>

You may share and adapt the data for any purpose, including commercially, provided
you give appropriate credit (see `CITATION.cff`), link to the license, and indicate
if changes were made.

The source code (`src/`, `tests/`, tooling) is licensed separately under the MIT
License; see `LICENSE`.

The full CC BY 4.0 legal text, downloaded unmodified from the Creative Commons URL
above (plain-text version, SHA-256 `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411`
before line endings were normalised to LF), is in
[`release/CC-BY-4.0.txt`](release/CC-BY-4.0.txt) and is copied into the dataset upload
folder by `python -m zhipi.release dist`. If it ever disagrees with the link, the link
is authoritative.

## Intended use

The data contains prompt-injection *wording* aimed at a fictional sandbox and a fixed
fake placeholder secret. It is released to evaluate and harden defenses. See
`SECURITY.md` for the responsible-use statement.
