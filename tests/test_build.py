import hashlib
import json
from collections import Counter

import pytest

from zhipi import build, carriers
from zhipi.schemas import CARRIERS, PLACEMENTS, TIERS

# Phase 1's results were measured on v0, so v0 must never change silently. This is a
# fingerprint of (sample_id, text) for all 226 samples; update it only on purpose,
# and say so in the commit.
V0_FINGERPRINT = "4017820dc9dbb8748d8aa23f00b3520db11d03a411cd75a95ee62f485bd4ae00"


def _v0():  # type: ignore[no-untyped-def]
    return build.build_version("v0")


def _v1():  # type: ignore[no-untyped-def]
    return build.build_version("v1")


def test_v0_is_unchanged() -> None:
    samples = _v0()
    digest = hashlib.sha256(
        json.dumps([[s.sample_id, s.text] for s in samples], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert len(samples) == 226
    assert digest == V0_FINGERPRINT


def test_v0_counts_and_tiers() -> None:
    samples = _v0()
    injected = [s for s in samples if s.label == "injected"]
    intents = len(build.load_intents(version="v0"))
    assert len(injected) == intents * len(CARRIERS) * (len(build.ZH_TRANSFORM_SETS) + 1)
    assert {s.tier for s in injected} == {"explicit"}
    assert {s.placement for s in samples} == {"default"}


def test_v1_adds_every_tier_and_the_buried_placement() -> None:
    samples = _v1()
    injected = [s for s in samples if s.label == "injected"]
    assert set(Counter(s.tier for s in injected)) == set(TIERS)
    assert {s.placement for s in samples} == set(PLACEMENTS)
    intents = len(build.load_intents(version="v1"))
    assert len(injected) == intents * len(CARRIERS) * (len(build.ZH_TRANSFORM_SETS) + 2)


def test_v1_contains_all_of_v0() -> None:
    v1 = {s.sample_id: s.text for s in _v1()}
    for s in _v0():
        assert v1[s.sample_id] == s.text


@pytest.mark.parametrize("version", build.VERSIONS)
def test_ids_unique_and_every_injected_sample_declares_its_intent(version: str) -> None:
    samples = build.build_version(version)
    ids = [s.sample_id for s in samples]
    assert len(ids) == len(set(ids))
    for s in samples:
        if s.label == "injected":
            assert s.plaintext_intent.strip(), s.sample_id
            assert s.tier in TIERS, s.sample_id


@pytest.mark.parametrize("version", build.VERSIONS)
def test_build_is_deterministic(version: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    build.write_jsonl(build.build_version(version), a)
    build.write_jsonl(build.build_version(version), b)
    assert a.read_bytes() == b.read_bytes()


def test_v1_has_hard_negative_strata_that_mirror_the_attacks() -> None:
    strata = Counter(s.stratum for s in _v1() if s.label == "benign")
    for stratum in ("asks_humans_for_info", "task_list", "format_request", "quoted_text", "long_benign"):
        assert strata[stratum] >= 1, stratum


def test_intents_are_safe_by_construction() -> None:
    for intent in build.load_intents():
        for text in (intent.text_zh, intent.text_en):
            lowered = text.lower()
            # Every exfiltration target must be the reserved, never-resolving .invalid TLD.
            if "http" in lowered:
                assert ".invalid/" in lowered, intent.intent_id
            assert "sk-" not in lowered, intent.intent_id


def test_tool_output_carrier_stays_valid_json_for_every_payload() -> None:
    for s in _v1():
        if s.carrier == "tool_output" and s.label == "injected":
            parsed = json.loads(s.text)
            assert parsed["results"][0]["snippet"], s.sample_id


def test_benign_host_is_the_injected_host_minus_the_payload() -> None:
    for carrier, lang in carriers.all_pairs():
        injected = carriers.wrap("PAYLOAD", carrier, lang)
        assert "PAYLOAD" in injected
        assert "PAYLOAD" not in carriers.benign(carrier, lang)


def test_buried_payload_appears_once_with_filler_on_both_sides() -> None:
    for carrier, lang in carriers.all_pairs():
        text = carriers.wrap("PAYLOAD", carrier, lang, "buried")
        if carrier == "tool_output":
            text = json.loads(text)["results"][0]["snippet"]
        assert text.count("PAYLOAD") == 1
        before, after = text.split("PAYLOAD")
        assert len(before) > 300 and len(after) > 300
        assert "PAYLOAD" not in carriers.benign(carrier, lang, "buried")


def test_unknown_placement_is_an_error() -> None:
    with pytest.raises(ValueError):
        carriers.wrap("x", "issue", "zh", "middle")
