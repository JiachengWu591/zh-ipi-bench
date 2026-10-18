# CLAUDE.md

## Project
A Chinese-native indirect prompt-injection benchmark. Read `docs/THREAT_MODEL.md`
(questions, axes, metrics) and `docs/ROADMAP.md` (phases) before starting work.

## Environment
- Python 3.12; package manager uv (`uv pip install -e ".[dev]"`); keep the core
  stdlib-only, put heavy deps in the `eval` extra.
- Models: DeepSeek via the `openai` package with `base_url="https://api.deepseek.com"`.
  The key lives in `DEEPSEEK_API_KEY`; code references the name only. Never write,
  print, or log its value.
- Local GPU: RTX 4060 Laptop, 8 GB. Check VRAM fit before assuming a model runs.

## Conventions
- Strict type hints; data contracts are `@dataclass(frozen=True)`, never bare dicts.
- Everything fails closed: an errored, timed-out, or malformed check is never a
  pass, and is never counted as a detection (`Verdict.completed`).
- Every reported rate carries a Wilson interval.
- Source, comments, and docs in English (public repo); talk to the owner in Chinese.
- File I/O with explicit `encoding="utf-8"`.
- One phase = one commit, message `Phase N: ...`.

## Safety rails (hard)
- Payloads target only the project's own sandbox and the fixed fake placeholder
  secret. Never a real product, service, credential, or person.
- Every injected sample must declare `plaintext_intent`; obfuscated payloads are
  reviewed through it.
- No real secrets in any file, including tests.

## Before pushing
- `python -m pytest` must pass.
- When reporting a check, say what it can and cannot detect. "The keyword
  baseline missed it" is not "the transform is strong".

## Always
- After each phase, show the result and wait for confirmation before the next.
- Do not make "first" / "novel" claims without re-running `docs/RELATED_WORK.md`.
