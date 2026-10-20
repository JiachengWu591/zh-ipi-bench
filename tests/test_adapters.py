"""Offline tests for the detector adapters. No model, network, or key is used:
heavy parts are replaced by fakes, so these test parsing, caching, and
fail-closed behaviour, not detector quality."""

import json
from types import SimpleNamespace

import pytest

from zhipi.adapters import deepseek_judge as dj
from zhipi.adapters import prompt_guard as pg
from zhipi.adapters import qwen3guard as qg
from zhipi.cache import ResponseCache, make_key
from zhipi.defenses import safe_detect

# --- revision pinning -----------------------------------------------------


def test_resolved_revision_reads_the_hub_cache_ref(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from zhipi.adapters._hf import resolved_revision

    refs = tmp_path / "models--org--name" / "refs"
    refs.mkdir(parents=True)
    (refs / "main").write_text("a" * 40 + "\n", encoding="utf-8")
    assert resolved_revision("org/name", None, tmp_path) == "a" * 40
    assert resolved_revision("org/name", "b" * 40, tmp_path) == "b" * 40  # full hash passes through
    assert resolved_revision("org/other", None, tmp_path) is None


# --- Prompt Guard 2 -------------------------------------------------------


def test_malicious_index_finds_the_single_malicious_label() -> None:
    assert pg.malicious_index({0: "BENIGN", 1: "MALICIOUS"}) == 1
    assert pg.malicious_index({0: "malicious", 1: "benign"}) == 0


@pytest.mark.parametrize("labels", [{0: "A", 1: "B"}, {0: "MALICIOUS", 1: "malicious"}])
def test_malicious_index_refuses_to_guess(labels: dict[int, str]) -> None:
    with pytest.raises(ValueError):
        pg.malicious_index(labels)


def test_window_aggregation_is_max_so_one_bad_window_flags_the_text() -> None:
    assert pg.aggregate([0.01, 0.97, 0.2]) == 0.97
    with pytest.raises(ValueError):
        pg.aggregate([])


def test_pg2_defense_applies_threshold_to_the_runner_score() -> None:
    runner = SimpleNamespace(score=lambda text: 0.7)
    assert pg.PromptGuard2Defense(runner, threshold=0.5).detect("x").flagged  # type: ignore[arg-type]
    assert not pg.PromptGuard2Defense(runner, threshold=0.9).detect("x").flagged  # type: ignore[arg-type]


# --- Qwen3Guard -----------------------------------------------------------


def test_qwen_parse_matches_the_documented_output_format() -> None:
    label, cats = qg.parse_output("Safety: Unsafe\nCategories: Jailbreak\n")
    assert (label, cats) == ("Unsafe", ("Jailbreak",))
    assert qg.parse_output("Safety: Safe\nCategories: None") == ("Safe", ("None",))


def test_qwen_parse_returns_none_label_for_garbage() -> None:
    assert qg.parse_output("I cannot help with that.")[0] is None


def test_qwen_rules_derive_from_one_raw_label() -> None:
    assert qg.flag("unsafe", "Unsafe", ())
    assert not qg.flag("unsafe", "Controversial", ())
    assert qg.flag("unsafe+ctrv", "Controversial", ())
    assert qg.flag("jailbreak", "Safe", ("Jailbreak",))
    with pytest.raises(ValueError):
        qg.flag("nope", "Safe", ())


def test_qwen_unparseable_output_is_incomplete_not_a_detection() -> None:
    runner = SimpleNamespace(classify=lambda text: (None, ()))
    verdict = qg.Qwen3GuardDefense(runner, "unsafe").detect("x")  # type: ignore[arg-type]
    assert verdict.completed is False and verdict.flagged is True


# --- cache and DeepSeek judge ---------------------------------------------


def _fake_client(arguments: str, calls: list[dict[str, object]]) -> SimpleNamespace:
    def create(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        fn = SimpleNamespace(arguments=arguments)
        message = SimpleNamespace(tool_calls=[SimpleNamespace(function=fn)])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_cache_round_trips_through_disk(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "c.jsonl"
    key = make_key("m", 1, "text")
    first = ResponseCache(path)
    assert first.get(key) is None
    first.put(key, "v")
    assert ResponseCache(path).get(key) == "v"


def test_judge_forces_the_tool_call_and_caches_the_response() -> None:
    calls: list[dict[str, object]] = []
    args = json.dumps({"risk_level": "high_risk", "reason": "r"})
    judge = dj.DeepSeekJudge(model="m", client=_fake_client(args, calls))
    assert judge.detect("hello").flagged is True
    assert judge.detect("hello").flagged is True
    assert len(calls) == 1  # second call served from cache
    assert calls[0]["tool_choice"] == {
        "type": "function",
        "function": {"name": dj.TOOL_NAME},
    }


def test_judge_flag_rule_is_a_view_over_the_same_cached_answer() -> None:
    calls: list[dict[str, object]] = []
    args = json.dumps({"risk_level": "suspicious", "reason": "r"})
    cache = ResponseCache(None)
    client = _fake_client(args, calls)
    strict = dj.DeepSeekJudge(model="m", client=client, cache=cache, flag_on=("high_risk",))
    loose = dj.DeepSeekJudge(
        model="m", client=client, cache=cache, flag_on=("suspicious", "high_risk")
    )
    assert strict.detect("t").flagged is False
    assert loose.detect("t").flagged is True
    assert len(calls) == 1


def test_judge_repeat_index_is_part_of_the_cache_key() -> None:
    calls: list[dict[str, object]] = []
    args = json.dumps({"risk_level": "safe", "reason": "r"})
    cache = ResponseCache(None)
    client = _fake_client(args, calls)
    for repeat in (0, 1):
        dj.DeepSeekJudge(model="m", repeat=repeat, client=client, cache=cache).detect("t")
    assert len(calls) == 2


def test_judge_invalid_answer_fails_closed_and_is_not_cached() -> None:
    calls: list[dict[str, object]] = []
    bad = json.dumps({"risk_level": "catastrophic", "reason": "r"})
    cache = ResponseCache(None)
    judge = dj.DeepSeekJudge(model="m", client=_fake_client(bad, calls), cache=cache)
    verdict = safe_detect(judge, "t")
    assert verdict.flagged is True and verdict.completed is False
    assert verdict.detail == "error:ValueError"  # type only, never the message
    assert len(cache) == 0


def test_judge_disables_thinking_so_the_forced_tool_choice_is_accepted() -> None:
    calls: list[dict[str, object]] = []
    args = json.dumps({"reason": "r", "risk_level": "safe"})
    dj.DeepSeekJudge(model="m", client=_fake_client(args, calls)).detect("t")
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}


def test_judge_without_a_key_fails_closed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    verdict = safe_detect(dj.DeepSeekJudge(model="m"), "t")
    assert verdict.completed is False


def test_prompt_hash_tracks_the_prompt() -> None:
    assert len(dj.PROMPT_HASH) == 12
