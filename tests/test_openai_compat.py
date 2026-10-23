"""Offline tests for the OpenAI-compatibility shim."""

import pytest

from zhipi.adapters.openai_compat import CompatClient, adapt_kwargs

NAMED = {"type": "function", "function": {"name": "report_risk"}}


def _kwargs() -> dict[str, object]:
    return {
        "model": "m",
        "messages": [{"role": "user", "content": "hello 你好"}],
        "tools": [
            {"type": "function", "function": {"name": "report_risk", "strict": True,
                                              "parameters": {"type": "object"}}},
        ],
        "tool_choice": NAMED,
        "extra_body": {"thinking": {"type": "disabled"}},
        "max_tokens": 64,
    }


def test_provider_specific_parts_are_removed_and_the_input_is_not_mutated() -> None:
    original = _kwargs()
    adapted = adapt_kwargs(original)
    assert "extra_body" not in adapted
    assert "strict" not in adapted["tools"][0]["function"]  # type: ignore[index]
    assert original["extra_body"] and original["tools"][0]["function"]["strict"] is True  # type: ignore[index]


def test_messages_are_never_touched() -> None:
    for mode in ("named", "required", "auto"):
        assert adapt_kwargs(_kwargs(), tool_choice_mode=mode)["messages"] == _kwargs()["messages"]


@pytest.mark.parametrize(
    ("mode", "expected"), [("named", NAMED), ("required", "required"), ("auto", "auto")]
)
def test_named_tool_choice_is_rewritten_only_when_asked(mode: str, expected: object) -> None:
    assert adapt_kwargs(_kwargs(), tool_choice_mode=mode)["tool_choice"] == expected


def test_string_tool_choice_is_left_alone() -> None:
    kwargs = _kwargs()
    kwargs["tool_choice"] = "auto"
    assert adapt_kwargs(kwargs, tool_choice_mode="required")["tool_choice"] == "auto"


def test_unknown_mode_is_an_error() -> None:
    with pytest.raises(ValueError):
        adapt_kwargs(_kwargs(), tool_choice_mode="forced")


def test_client_forwards_the_adapted_call_and_logs_the_choice() -> None:
    seen: dict[str, object] = {}

    class Completions:
        def create(self, **kw: object) -> str:
            seen.update(kw)
            return "response"

    class Inner:
        chat = type("C", (), {"completions": Completions()})()

    log: list[dict[str, object]] = []
    client = CompatClient(Inner(), tool_choice_mode="required", log=log)
    assert client.chat.completions.create(**_kwargs()) == "response"
    assert seen["tool_choice"] == "required" and "extra_body" not in seen
    assert log == [{"tool_choice": "required", "model": "m"}]
