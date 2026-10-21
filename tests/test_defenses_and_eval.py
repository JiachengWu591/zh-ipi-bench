"""Harness tests. These use the naive keyword baselines to check the plumbing;
nothing here is a finding about real detectors."""

import pytest

from zhipi import build
from zhipi.defenses import EN_KEYWORDS, ZH_KEYWORDS, Verdict, safe_detect
from zhipi.evaluate import by_transform, evaluate, summarize
from zhipi.stats import wilson_interval


def _samples():  # type: ignore[no-untyped-def]
    return build.build_version("v0")


def test_wilson_zero_successes_matches_hand_computation() -> None:
    low, high = wilson_interval(0, 10)
    assert low == 0.0
    assert high == pytest.approx(0.2775, abs=1e-3)


def test_mcnemar_matches_hand_computation() -> None:
    from zhipi.stats import mcnemar_exact

    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0  # perfectly balanced: no evidence of an effect
    # 0 lost vs 8 gained: 2 * (1/2^8) = 2/256
    assert mcnemar_exact(0, 8) == pytest.approx(2 / 256)
    assert mcnemar_exact(8, 0) == pytest.approx(2 / 256)  # symmetric
    assert mcnemar_exact(1, 9) == pytest.approx(2 * (1 + 10) / 1024)


def test_auroc_basic_cases_and_bootstrap_is_reproducible() -> None:
    from zhipi.stats import auroc, auroc_bootstrap_ci

    assert auroc([0.9, 0.8], [0.1, 0.2]) == 1.0
    assert auroc([0.1, 0.2], [0.9, 0.8]) == 0.0
    assert auroc([0.5], [0.5]) == 0.5  # ties count half
    assert auroc([0.9, 0.2], [0.5]) == 0.5
    pos, neg = [0.9, 0.8, 0.7, 0.3], [0.6, 0.2, 0.1, 0.4]
    assert auroc_bootstrap_ci(pos, neg) == auroc_bootstrap_ci(pos, neg)  # fixed seed
    low, high = auroc_bootstrap_ci(pos, neg)
    assert 0.0 <= low <= auroc(pos, neg) <= high <= 1.0
    with pytest.raises(ValueError):
        auroc([], [0.1])


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
