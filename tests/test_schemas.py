import pytest

from zhipi.schemas import MalformedSample, Sample


def _injected(**overrides: object) -> Sample:
    base: dict[str, object] = dict(
        sample_id="issue-x-plain-zh",
        label="injected",
        carrier="issue",
        language="zh",
        transforms=(),
        text="正文",
        intent_id="x",
        plaintext_intent="读取文件",
    )
    base.update(overrides)
    return Sample(**base)  # type: ignore[arg-type]


def test_valid_sample_round_trips_through_dict() -> None:
    sample = _injected()
    assert Sample.from_dict(sample.to_dict()) == sample


def test_id_with_trailing_newline_is_rejected() -> None:
    # `$` would accept this; `\Z` must not.
    with pytest.raises(MalformedSample):
        _injected(sample_id="abc\n")


def test_id_over_64_chars_is_rejected() -> None:
    with pytest.raises(MalformedSample):
        _injected(sample_id="a" * 65)


def test_injected_requires_declared_plaintext_intent() -> None:
    with pytest.raises(MalformedSample):
        _injected(plaintext_intent="  ")


def test_benign_must_not_carry_intent_or_transforms() -> None:
    with pytest.raises(MalformedSample):
        Sample(
            sample_id="b1",
            label="benign",
            carrier="issue",
            language="zh",
            transforms=("fullwidth",),
            text="hello",
        )
