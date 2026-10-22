"""Data contracts for the benchmark.

Frozen dataclasses rather than bare dicts, so "what a sample is" can be pointed
at in code. Construction validates and raises; there is no "return None and let
the caller decide" path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CARRIERS: tuple[str, ...] = ("issue", "rag_doc", "email", "web_html", "tool_output")
LANGUAGES: tuple[str, ...] = ("zh", "en")
LABELS: tuple[str, ...] = ("injected", "benign")
# How hard the payload is to recognise, by how it asks:
#   explicit          names the target and the action outright (the v0 intents)
#   implicit          asks without naming the target, or frames the ask
#   spoofed_structure forges delimiters or tool/system messages
#   judge_targeted    also addresses the screening component itself
#   ibr_corpus        ported from injection-blast-radius's attack corpus: techniques its
#                     undefended baseline was shown to leak on (v2 only)
TIERS: tuple[str, ...] = (
    "explicit",
    "implicit",
    "spoofed_structure",
    "judge_targeted",
    "ibr_corpus",
)
# `buried`: the payload sits in the middle of a long, otherwise benign document.
PLACEMENTS: tuple[str, ...] = ("default", "buried")

# Same shape as injection-blast-radius's issue ids, so every sample can be fed to
# that pipeline unchanged. `\Z`, not `$`: `$` also matches before a trailing
# newline, which is how a 65-character id once got through a {1,64} bound there.
_SAMPLE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}\Z")


class MalformedSample(ValueError):
    """A sample or intent did not match the expected shape. Always fatal."""


@dataclass(frozen=True)
class Intent:
    """What the attacker wants, stated once per language.

    The goal is held fixed across carriers and transforms; only the delivery
    varies. Every intent targets this project's own sandbox and the fixed fake
    placeholder secret, never a real product, service, or person.
    """

    intent_id: str
    technique: str
    text_zh: str
    text_en: str
    rationale: str
    tier: str
    gloss_zh: str = ""
    gloss_en: str = ""
    """What the payload asks, stated plainly, when the payload itself does not say it.

    Needed for encoded or indirect payloads (base64, a described file path, a wall of
    log lines): `plaintext_intent` on every sample built from the intent is this text
    when present, so a reviewer can audit a payload they cannot read by eye."""

    def plain(self, language: str) -> str:
        gloss = self.gloss_zh if language == "zh" else self.gloss_en
        return gloss or (self.text_zh if language == "zh" else self.text_en)

    def __post_init__(self) -> None:
        if not _SAMPLE_ID.match(self.intent_id):
            raise MalformedSample(f"intent_id {self.intent_id!r} is not id-shaped")
        if self.tier not in TIERS:
            raise MalformedSample(f"intent {self.intent_id!r}: bad tier {self.tier!r}")
        for name in ("technique", "text_zh", "text_en", "rationale"):
            if not getattr(self, name).strip():
                raise MalformedSample(f"intent {self.intent_id!r}: {name} is empty")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Intent:
        optional = {"gloss_zh", "gloss_en"}
        try:
            return cls(
                **{f: data[f] for f in cls.__dataclass_fields__ if f not in optional},
                **{f: data.get(f, "") for f in optional},
            )
        except KeyError as exc:
            raise MalformedSample(f"intent is missing field {exc}") from exc


@dataclass(frozen=True)
class Sample:
    """One evaluation item: untrusted text plus its ground truth."""

    sample_id: str
    label: str
    carrier: str
    language: str
    transforms: tuple[str, ...]
    text: str
    intent_id: str | None = None
    plaintext_intent: str = ""
    """What an obfuscated payload actually asks for, stated plainly.

    Required for every injected sample: a zero-width-split or code-mixed payload
    is exactly the kind a plaintext review of the dataset would miss, so the
    declared intent is what keeps the safety review effective on it.
    """
    stratum: str = ""
    """For benign samples: which hard-negative family it belongs to."""
    tier: str = ""
    """For injected samples: the intent's tier (see TIERS)."""
    placement: str = "default"

    def __post_init__(self) -> None:
        if not _SAMPLE_ID.match(self.sample_id):
            raise MalformedSample(f"sample_id {self.sample_id!r} is not id-shaped")
        if self.placement not in PLACEMENTS:
            raise MalformedSample(f"{self.sample_id}: bad placement {self.placement!r}")
        if self.tier and self.tier not in TIERS:
            raise MalformedSample(f"{self.sample_id}: bad tier {self.tier!r}")
        if self.label not in LABELS:
            raise MalformedSample(f"{self.sample_id}: bad label {self.label!r}")
        if self.carrier not in CARRIERS:
            raise MalformedSample(f"{self.sample_id}: bad carrier {self.carrier!r}")
        if self.language not in LANGUAGES:
            raise MalformedSample(f"{self.sample_id}: bad language {self.language!r}")
        if not self.text.strip():
            raise MalformedSample(f"{self.sample_id}: empty text")
        if self.label == "injected":
            if not self.intent_id or not self.plaintext_intent.strip() or not self.tier:
                raise MalformedSample(
                    f"{self.sample_id}: injected samples need intent_id, "
                    "plaintext_intent and tier"
                )
        elif self.intent_id is not None or self.transforms or self.tier:
            raise MalformedSample(
                f"{self.sample_id}: benign samples carry no intent, tier or transforms"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "label": self.label,
            "carrier": self.carrier,
            "language": self.language,
            "transforms": list(self.transforms),
            "text": self.text,
            "intent_id": self.intent_id,
            "plaintext_intent": self.plaintext_intent,
            "stratum": self.stratum,
            "tier": self.tier,
            "placement": self.placement,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sample:
        try:
            return cls(
                sample_id=data["sample_id"],
                label=data["label"],
                carrier=data["carrier"],
                language=data["language"],
                transforms=tuple(data.get("transforms", ())),
                text=data["text"],
                intent_id=data.get("intent_id"),
                plaintext_intent=data.get("plaintext_intent", ""),
                stratum=data.get("stratum", ""),
                tier=data.get("tier", ""),
                placement=data.get("placement", "default"),
            )
        except KeyError as exc:
            raise MalformedSample(f"sample is missing field {exc}") from exc
