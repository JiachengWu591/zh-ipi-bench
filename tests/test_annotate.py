from __future__ import annotations

import json
from dataclasses import replace

import pytest

from zhipi import annotate, build
from zhipi.annotate import Annotations, Answer, MalformedAnnotation, Rating
from zhipi.schemas import Sample
from zhipi.stats import cohen_kappa, kappa_bootstrap_ci


@pytest.fixture(scope="module")
def samples() -> list[Sample]:
    return build.build_version("v2")


@pytest.fixture(scope="module")
def packet(samples: list[Sample]) -> annotate.Packet:
    return annotate.build_packet(samples, build.load_intents(version="v2"), seed=7)


def _perfect(key: annotate.Key) -> Annotations:
    answers = tuple(Answer(r.item_id, r.label) for r in key.rows)
    ratings = tuple(Rating(t.item_id, 3, 3) for t in key.translations)
    return Annotations(key.packet_id, "t", answers, ratings)


def test_kappa_known_values() -> None:
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]) == pytest.approx(0.5)
    assert cohen_kappa(["a", "b"], ["a", "b"]) == 1.0
    assert cohen_kappa(["a", "b"], ["b", "a"]) == -1.0
    assert cohen_kappa([], []) is None
    assert cohen_kappa(["a", "a"], ["a", "a"]) is None  # chance agreement is already 1
    with pytest.raises(ValueError):
        cohen_kappa(["a"], ["a", "b"])


def test_kappa_interval_is_reproducible_and_contains_the_estimate() -> None:
    first = ["injected"] * 30 + ["benign"] * 20
    second = first[:25] + ["benign"] * 5 + first[30:45] + ["injected"] * 5
    ci = kappa_bootstrap_ci(first, second)
    assert ci == kappa_bootstrap_ci(first, second)
    value = cohen_kappa(first, second)
    assert ci is not None and value is not None and ci[0] <= value <= ci[1]


def test_the_packet_is_deterministic_and_seed_dependent(samples: list[Sample]) -> None:
    intents = build.load_intents(version="v2")
    a = annotate.build_packet(samples, intents, seed=7)
    assert a == annotate.build_packet(samples, intents, seed=7)
    assert a.packet_id != annotate.build_packet(samples, intents, seed=8).packet_id


def test_the_packet_covers_every_intent_and_all_chinese_benign_text(
    packet: annotate.Packet, samples: list[Sample]
) -> None:
    intents = {i.intent_id for i in build.load_intents(version="v2")}
    injected = [r for r in packet.key.rows if r.label == "injected"]
    assert {r.intent_id for r in injected} == intents
    assert len(injected) == 2 * len(intents)
    assert len({r.sample_id for r in packet.key.rows}) == len(packet.key.rows)
    benign = {r.sample_id for r in packet.key.rows if r.label == "benign"}
    assert benign == {s.sample_id for s in samples if s.label == "benign" and s.language == "zh"}
    by_id = {s.sample_id: s for s in samples}
    assert all(by_id[r.sample_id].language == "zh" for r in packet.key.rows)
    assert len(packet.translations) == len(intents)


def test_the_annotator_page_does_not_reveal_labels_or_identities(packet: annotate.Packet) -> None:
    page = annotate.render_page(packet)
    # Identifiers may legitimately appear as ordinary words inside a text (an intent called
    # "checklist"), so check the page with every text body blanked out, plus the sample ids
    # (which never occur in prose) everywhere.
    blank = replace(
        packet,
        items=tuple(replace(i, text="") for i in packet.items),
        translations=tuple(replace(t, text_zh="", text_en="") for t in packet.translations),
    )
    shell = annotate.render_page(blank)
    secrets = {r.intent_id for r in packet.key.rows if r.intent_id}
    secrets |= {r.tier for r in packet.key.rows if r.tier} | {r.stratum for r in packet.key.rows if r.stratum}
    secrets |= {t.intent_id for t in packet.key.translations}
    leaks = sorted(s for s in secrets if s in shell) + [r.sample_id for r in packet.key.rows if r.sample_id in page]
    assert not leaks, leaks
    for field in ("plaintext_intent", "intent_id", "sample_id", "stratum", "transforms"):
        assert field not in page
    # Shuffled: item order is not the key order of anything recognisable.
    assert [i.item_id for i in packet.items] == [f"A{n:03d}" for n in range(1, len(packet.items) + 1)]
    assert [r.label for r in packet.key.rows[:12]] != ["injected"] * 12


def test_a_payload_cannot_close_the_embedding_script_element(packet: annotate.Packet) -> None:
    hostile = replace(packet.items[0], text="</script><img src=x onerror=alert(1)>")
    page = annotate.render_page(replace(packet, items=(hostile, *packet.items[1:])))
    assert page.count("</script>") == 2  # the data block and the code block, nothing else
    assert "<img src=x" not in page


def test_the_key_round_trips_through_disk(packet: annotate.Packet, tmp_path) -> None:  # type: ignore[no-untyped-def]
    page, key_path = annotate.write_packet(packet, tmp_path)
    assert page.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert annotate.load_key(key_path) == packet.key


def test_answers_are_validated_against_the_key(packet: annotate.Packet) -> None:
    key = packet.key
    good = {"format": 1, "packet_id": key.packet_id, "annotator": "x",
            "labels": {"A001": {"label": "benign"}, "A002": {"label": None}},
            "ratings": {"T01": {"meaning": 2, "fluency": 3}, "T02": {"meaning": 2}}}
    ann = annotate.parse_annotations(good, key)
    assert [a.item_id for a in ann.answers] == ["A001"]  # a skipped item is just absent
    assert [r.item_id for r in ann.ratings] == ["T01"]  # a half-rated pair is unrated
    for bad in (
        {**good, "packet_id": "other"},
        {**good, "format": 2},
        {**good, "labels": {"A999": {"label": "benign"}}},
        {**good, "labels": {"A001": {"label": "maybe"}}},
        {**good, "ratings": {"T01": {"meaning": 4, "fluency": 1}}},
        {**good, "ratings": {"A001": {"meaning": 1, "fluency": 1}}},
        [],
    ):
        with pytest.raises(MalformedAnnotation):
            annotate.parse_annotations(bad, key)


def test_a_perfect_second_annotator_scores_full_agreement(packet: annotate.Packet) -> None:
    report = annotate.build_report(packet.key, _perfect(packet.key))
    assert f"{len(packet.items)}/{len(packet.items)} (100%" in report
    assert "Cohen's kappa: **1.00**" in report
    assert "None." in report  # no disagreements
    assert "What this can and cannot show" in report


def test_unsure_and_unanswered_never_count_as_agreement(packet: annotate.Packet) -> None:
    key = packet.key
    perfect = _perfect(key)
    answers = list(perfect.answers)
    answers[0] = Answer(answers[0].item_id, "unsure")
    del answers[1]  # unanswered
    flipped = next(i for i, a in enumerate(answers) if a.label == "benign")
    answers[flipped] = Answer(answers[flipped].item_id, "injected")
    ann = replace(perfect, answers=tuple(answers))
    report = annotate.build_report(key, ann)
    n = len(key.rows)
    assert f"{n - 3}/{n}" in report
    assert "unanswered: 1" in report
    assert "Cohen's kappa: **1.00**" not in report


def test_translation_ratings_below_three_are_listed(packet: annotate.Packet) -> None:
    perfect = _perfect(packet.key)
    weak = replace(perfect.ratings[0], meaning=1)
    ann = replace(perfect, ratings=(weak, *perfect.ratings[1:-1]))  # last one unrated
    report = annotate.build_report(packet.key, ann)
    first_intent = packet.key.translations[0].intent_id
    last_intent = packet.key.translations[-1].intent_id
    assert f"rated below 3 on either scale: `{first_intent}`" in report
    assert f"Not rated: `{last_intent}`" in report


def test_the_exported_page_format_matches_what_the_parser_accepts(packet: annotate.Packet) -> None:
    """The page exports {format, packet_id, annotator, labels, ratings}; keep both ends in sync."""
    page = annotate.render_page(packet)
    assert "format: D.format" in page and "labels: state.labels" in page and "ratings: state.ratings" in page
    data = json.loads(page.split('type="application/json">')[1].split("</script>")[0].replace("\\u003c", "<"))
    assert data["format"] == annotate.FORMAT_VERSION and data["packet_id"] == packet.packet_id
