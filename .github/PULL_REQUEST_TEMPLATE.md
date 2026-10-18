## What and why

## Checklist

- [ ] `python -m pytest` passes
- [ ] New injected samples declare `plaintext_intent`
- [ ] Payloads target only the sandbox and the fake placeholder secret
- [ ] No real secrets or personal data
- [ ] Any new rate reported carries a 95% interval
- [ ] No unsupported "first" / "novel" claim (see `docs/RELATED_WORK.md`)
