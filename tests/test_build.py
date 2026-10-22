import hashlib
import json
from collections import Counter

import pytest

from zhipi import build, carriers, transforms
from zhipi.schemas import CARRIERS, PLACEMENTS, TIERS

# Phase 1's results were measured on v0, so v0 must never change silently. This is a
# fingerprint of (sample_id, text) for all 226 samples; update it only on purpose,
# and say so in the commit.
V0_FINGERPRINT = "4017820dc9dbb8748d8aa23f00b3520db11d03a411cd75a95ee62f485bd4ae00"
# v1 is frozen too: every Phase 2 result and the first end-to-end run were measured on it.
V1_FINGERPRINT = "d507be34462b75a4328b4defbf244d713011f431715e1c8e92dfd270f0faeaf0"


def _fingerprint(samples) -> str:  # type: ignore[no-untyped-def]
    return hashlib.sha256(
        json.dumps([[s.sample_id, s.text] for s in samples], ensure_ascii=False).encode("utf-8")
    ).hexdigest()


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


def test_v1_is_unchanged_by_the_v2_additions() -> None:
    samples = _v1()
    assert len(samples) == 803
    assert _fingerprint(samples) == V1_FINGERPRINT
    assert "ibr_corpus" not in {s.tier for s in samples}


def test_v2_adds_the_ported_attacks_and_keeps_all_of_v1() -> None:
    v2 = {s.sample_id: s for s in build.build_version("v2")}
    for s in _v1():
        assert v2[s.sample_id].text == s.text
    ported = [s for s in v2.values() if s.tier == "ibr_corpus"]
    assert {s.intent_id for s in ported} == {
        i.intent_id for i in build.load_intents(version="v2") if i.tier == "ibr_corpus"
    }
    assert len({s.intent_id for s in ported}) == 12
    assert any(s.stratum == "html_comment_note" for s in v2.values())


def test_encoded_ports_declare_what_they_decode_to() -> None:
    import base64
    import re

    by_id = {i.intent_id: i for i in build.load_intents(version="v2")}
    intent = by_id["ibr_base64_encoded"]
    for text, gloss in ((intent.text_zh, intent.gloss_zh), (intent.text_en, intent.gloss_en)):
        blob = re.search(r"^[A-Za-z0-9+/=]{20,}$", text, re.M)
        assert blob is not None
        assert base64.b64decode(blob.group(0)).decode("utf-8") == gloss
    # and the sample's declared plaintext is the decoded request, not the blob
    sample = next(s for s in build.build_version("v2") if s.intent_id == "ibr_base64_encoded")
    assert sample.plaintext_intent in (intent.gloss_zh, intent.gloss_en)


def test_ported_intents_say_where_they_came_from() -> None:
    for intent in build.load_intents(version="v2"):
        if intent.tier == "ibr_corpus":
            assert "injection-blast-radius" in intent.rationale, intent.intent_id


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
    assert set(Counter(s.tier for s in injected)) == set(TIERS) - {"ibr_corpus"}
    assert {s.placement for s in samples} == set(PLACEMENTS)
    # Per intent and carrier: each transform that actually changes the text, the plain
    # Chinese one, the English control, and the buried one.
    expected = 0
    for intent in build.load_intents(version="v1"):
        effective = [
            tfs
            for tfs in build.ZH_TRANSFORM_SETS
            if not tfs or transforms.apply(tfs, intent.text_zh) != intent.text_zh
        ]
        expected += len(CARRIERS) * (len(effective) + 2)
    assert len(injected) == expected


@pytest.mark.parametrize("version", build.VERSIONS)
def test_no_two_samples_share_the_same_text(version: str) -> None:
    # Regression: fullwidth was a no-op on payloads with no ASCII, which produced
    # byte-identical "transformed" duplicates that inflated n and were counted as
    # independent samples.
    texts = [s.text for s in build.build_version(version)]
    assert len(texts) == len(set(texts))


def test_every_transformed_sample_differs_from_its_plain_twin() -> None:
    by_id = {s.sample_id: s for s in _v1()}
    for s in by_id.values():
        if s.label == "injected" and s.language == "zh" and s.transforms and s.placement == "default":
            plain_id = f"{s.carrier}-{s.intent_id}-plain-zh"
            assert s.text != by_id[plain_id].text, s.sample_id


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
    for intent in build.load_intents(version="v2"):
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
