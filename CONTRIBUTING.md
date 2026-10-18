# Contributing

Thanks for looking. This is an early-stage research project (see `docs/ROADMAP.md`),
so the most useful contributions are the ones that make the benchmark harder to
dismiss.

## Good first contributions

- **A new Chinese-specific transform** (pinyin, traditional/simplified mixing,
  homophones, character decomposition, classical Chinese). Add it to
  `src/zhipi/transforms.py` with tests; keep it pure and deterministic.
- **A new detector adapter** implementing the `Defense` protocol in
  `src/zhipi/defenses.py`.
- **Hard negatives**: benign Chinese text that a naive detector would flag.
- **Annotation review**: check that `plaintext_intent` and the English parallel
  text are accurate.

## Ground rules

- Payloads may target only this project's sandbox path and the fixed fake
  placeholder secret — never a real product, service, credential, or person.
- Every injected sample must declare `plaintext_intent`.
- No real secrets in any file, including tests.
- Failures fail closed: an errored or timed-out check is never counted as a
  detection (`Verdict.completed`).
- Every reported rate carries a 95% Wilson interval.
- Don't claim novelty ("first", "new") without updating `docs/RELATED_WORK.md`.

## Development

```bash
uv venv
uv pip install -e ".[dev]"
python -m pytest
```

Open a pull request against `main`. Keep one logical change per PR and include tests.
By contributing you agree your code is released under the MIT License and your data
under CC BY 4.0 (see `LICENSE` and `DATA_LICENSE.md`).
