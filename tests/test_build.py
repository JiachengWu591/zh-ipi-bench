import json

from zhipi import build, carriers
from zhipi.schemas import CARRIERS


def _samples():  # type: ignore[no-untyped-def]
    return build.build_samples(build.load_intents(), build.load_hard_negatives())


def test_expected_counts() -> None:
    samples = _samples()
    intents = len(build.load_intents())
    injected = [s for s in samples if s.label == "injected"]
    zh = [s for s in injected if s.language == "zh"]
    en = [s for s in injected if s.language == "en"]
    assert len(zh) == intents * len(CARRIERS) * len(build.ZH_TRANSFORM_SETS)
    assert len(en) == intents * len(CARRIERS)
    assert any(s.stratum == "discusses_injection" for s in samples)


def test_ids_unique() -> None:
    ids = [s.sample_id for s in _samples()]
    assert len(ids) == len(set(ids))


def test_build_is_deterministic(tmp_path) -> None:  # type: ignore[no-untyped-def]
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    build.write_jsonl(_samples(), a)
    build.write_jsonl(_samples(), b)
    assert a.read_bytes() == b.read_bytes()
    first = json.loads(a.read_text(encoding="utf-8").splitlines()[0])
    assert first["label"] == "injected"


def test_every_injected_sample_declares_a_plaintext_intent() -> None:
    for s in _samples():
        if s.label == "injected":
            assert s.plaintext_intent.strip(), s.sample_id


def test_tool_output_carrier_stays_valid_json_for_every_payload() -> None:
    for s in _samples():
        if s.carrier == "tool_output" and s.label == "injected":
            parsed = json.loads(s.text)
            assert parsed["results"][0]["snippet"], s.sample_id


def test_benign_host_is_the_injected_host_minus_the_payload() -> None:
    for carrier, lang in carriers.all_pairs():
        injected = carriers.wrap("PAYLOAD", carrier, lang)
        assert "PAYLOAD" in injected
        assert "PAYLOAD" not in carriers.benign(carrier, lang)
