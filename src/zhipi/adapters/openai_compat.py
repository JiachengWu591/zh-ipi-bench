"""Make an OpenAI-compatible server look like what injection-blast-radius expects.

That project talks to DeepSeek and passes a few provider-specific things: a
`thinking: disabled` body field, `strict: true` inside tool schemas, and a *named*
`tool_choice` to force exactly one tool. A local or third-party server may reject or
ignore any of these. This shim sits between the pipeline and the client and rewrites
only those, so the target repository does not need to change.

`tool_choice_mode` says what to do with a named tool choice:
- `named`: pass it through (the server must honour it);
- `required`: ask for "some tool call" instead (the pipeline then validates *which*
  tool and its arguments, as it always does);
- `auto`: let the model decide (weakest; a model may answer in prose, which the
  pipeline treats as a failed structured call and refuses to act on).

The shim never touches message content, so it cannot change what a model reads.
"""

from __future__ import annotations

import copy
from typing import Any

MODES = ("named", "required", "auto")


def adapt_kwargs(kwargs: dict[str, Any], *, tool_choice_mode: str = "named") -> dict[str, Any]:
    """Return a copy of `kwargs` without the provider-specific parts."""
    if tool_choice_mode not in MODES:
        raise ValueError(f"unknown tool_choice_mode {tool_choice_mode!r} (have {MODES})")
    out = copy.deepcopy(kwargs)
    out.pop("extra_body", None)
    for tool in out.get("tools") or []:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(fn, dict):
            fn.pop("strict", None)
    choice = out.get("tool_choice")
    if isinstance(choice, dict) and tool_choice_mode != "named":
        out["tool_choice"] = tool_choice_mode
    return out


class _Completions:
    def __init__(self, client: Any, mode: str, log: list[dict[str, Any]] | None) -> None:
        self._client = client
        self._mode = mode
        self._log = log

    def create(self, **kwargs: Any) -> Any:
        adapted = adapt_kwargs(kwargs, tool_choice_mode=self._mode)
        if self._log is not None:
            self._log.append({"tool_choice": adapted.get("tool_choice"), "model": adapted.get("model")})
        return self._client.chat.completions.create(**adapted)


class _Chat:
    def __init__(self, completions: _Completions) -> None:
        self.completions = completions


class CompatClient:
    """Drop-in for `openai.OpenAI` as far as the pipeline uses it (chat.completions.create)."""

    def __init__(
        self,
        client: Any,
        *,
        tool_choice_mode: str = "named",
        log: list[dict[str, Any]] | None = None,
    ) -> None:
        self.chat = _Chat(_Completions(client, tool_choice_mode, log))
        self.tool_choice_mode = tool_choice_mode


def build_local_client(base_url: str, api_key: str = "sk-local", timeout: float = 600.0) -> Any:
    import openai  # noqa: PLC0415 - optional (the `eval` extra)

    return openai.OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
