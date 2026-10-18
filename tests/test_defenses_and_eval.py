"""Harness tests. These use the naive keyword baselines to check the plumbing;
nothing here is a finding about real detectors."""

import pytest

from zhipi import build
from zhipi.defenses import EN_KEYWORDS, ZH_KEYWORDS, Verdict, safe_detect
from zhipi.evaluate import by_transform, evaluate, summarize
from zhipi.stats import wilson_interval


def _samples():  # type: ignore[no-untyped-def]
    return build.build_samples(build.load_intents(), build.load_hard_negatives())


def test_wilson_zero_successes_matches_hand_computation() -> None:
    low, high = wilson_interval(0, 10)
    assert low == 0.0
    assert high == pytest.approx(0.2775, abs=1e-3)


def test_wilson_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        wilson_interval(1, 0)
    with pytest.raises(ValueError):
        wilson_interval(5, 4)


def test_failing_defense_fails_closed_and_is_not_a_detection() -> None:
    class Broken:
        name = "broken"

        def detect(self, text: str) -> Verdict:
            raise TimeoutError

    verdict = safe_detect(Broken(), "anything")
    assert verdict.flagged is True
    assert verdict.completed is False


def test_incomplete_verdicts_are_excluded_from_the_rate() -> None:
    class Flaky:
        name = "flaky"

        def detect(self, text: str) -> Verdict:
            raise TimeoutError

    rows = evaluate(Flaky(), _samples())
    cells = summarize(rows, label="injected", key=by_transform)
    assert all(c.rate is None and c.incomplete > 0 for c in cells)


def test_zero_width_evades_the_chinese_keyword_baseline() -> None:
    rows = evaluate(ZH_KEYWORDS, _samples())
    rates = {
        c.group: c.rate
        for c in summarize(rows, label="injected", key=by_transform)
    }
    assert rates["plain"] is not None and rates["plain"] > 0
    assert rates["zero_width"] == 0.0


def test_english_baseline_is_blind_to_chinese_payloads() -> None:
    zh_plain = [s for s in _samples() if s.language == "zh" and not s.transforms]
    assert not any(r.flagged for r in evaluate(EN_KEYWORDS, zh_plain))


def test_hard_negative_that_discusses_injection_is_a_false_positive() -> None:
    rows = evaluate(ZH_KEYWORDS, _samples())
    fp = {
        c.group: c.flagged
        for c in summarize(rows, label="benign", key=lambda s: s.stratum)
    }
    assert fp["discusses_injection"] >= 1
    assert fp["plain"] == 0
