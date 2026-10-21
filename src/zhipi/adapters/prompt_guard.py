"""Llama Prompt Guard 2 (86M) as a Defense.

The model card lists the languages it was *evaluated* on as English, French,
German, Hindi, Italian, Portuguese, Spanish and Thai. Chinese is not among
them, so its behaviour on Chinese is exactly the open question this adapter
exists to measure; do not read a Chinese result as a regression from a claimed
capability.

The repo is gated (Llama 4 Community License plus an access form), so loading
needs a Hugging Face token whose account has been granted access. This module
never reads or prints the token; `huggingface_hub` picks it up from the
environment (`HF_TOKEN`) or its own login store.

The model has a 512-token window. Longer inputs are split into overlapping
windows and the *maximum* malicious probability is taken, which is the card's
own advice (segment and scan) with the most conservative aggregation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..defenses import Verdict
from ._hf import resolved_revision

MODEL_ID = "meta-llama/Llama-Prompt-Guard-2-86M"
MAX_TOKENS = 512
STRIDE = 64


def malicious_index(
    id2label: Mapping[int, str], positive: tuple[str, ...] = ("malicious",)
) -> int:
    """Index of the positive (injection) class. Raises rather than guessing."""
    wanted = {p.lower() for p in positive}
    matches = [i for i, name in id2label.items() if name.strip().lower() in wanted]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one of {sorted(wanted)} in {dict(id2label)}")
    return matches[0]


def aggregate(chunk_scores: list[float]) -> float:
    if not chunk_scores:
        raise ValueError("no chunk scores")
    return max(chunk_scores)


class PromptGuard2Runner:
    """Loads a sequence-classification model once and memoizes scores by text.

    Despite the name it serves any binary injection classifier with a 512-token
    window: pass `model_id` and the label(s) that mean "injection".
    """

    def __init__(
        self,
        model_id: str = MODEL_ID,
        revision: str | None = None,
        device: str | None = None,
        positive_labels: tuple[str, ...] = ("malicious",),
        role: str = "",
        max_tokens: int = MAX_TOKENS,
        stride: int = STRIDE,
    ) -> None:
        import inspect

        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        self._torch = torch
        self.max_tokens = max_tokens
        self.stride = stride
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_id, revision=revision
        )
        self.model = model.to(self.device).eval()
        self._malicious = malicious_index(self.model.config.id2label, positive_labels)
        self.labels = dict(self.model.config.id2label)
        self.role = role
        self.revision = resolved_revision(model_id, revision)
        # Some tokenizers (ModernBERT's, for one) return token_type_ids that the model's
        # forward() does not accept; only pass what it takes.
        self._accepts = set(inspect.signature(self.model.forward).parameters)
        self._memo: dict[str, float] = {}

    def score(self, text: str) -> float:
        if text in self._memo:
            return self._memo[text]
        enc: Any = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_tokens,
            stride=self.stride,
            return_overflowing_tokens=True,
            padding=True,
            return_tensors="pt",
        )
        enc.pop("overflow_to_sample_mapping", None)
        enc.pop("num_truncated_tokens", None)
        batch = {k: v.to(self.device) for k, v in enc.items() if k in self._accepts}
        with self._torch.no_grad():
            logits = self.model(**batch).logits
        probs = self._torch.softmax(logits, dim=-1)[:, self._malicious].tolist()
        result = aggregate([float(p) for p in probs])
        self._memo[text] = result
        return result

    def metadata(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "device": self.device,
            "max_tokens": self.max_tokens,
            "stride": self.stride,
            "aggregation": "max over windows",
            "labels": {str(k): v for k, v in self.labels.items()},
            "role": self.role,
        }


@dataclass
class PromptGuard2Defense:
    runner: PromptGuard2Runner
    threshold: float = 0.5
    name: str = "prompt-guard-2-86m"

    def detect(self, text: str) -> Verdict:
        score = self.runner.score(text)
        return Verdict(flagged=score >= self.threshold, score=score)
