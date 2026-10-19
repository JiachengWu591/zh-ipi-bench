"""Qwen3Guard-Gen as a Defense, labelled as a *wrong-tool control*.

Qwen3Guard is a content-safety moderator, not a prompt-injection detector. Its
only injection-adjacent signal is a `Jailbreak` category on user input. It is
included on purpose: it shows what a strong, Chinese-capable moderator does when
asked a question it was not built for, so a high score from a purpose-built
detector can be told apart from "any guard model does this". Do not present its
numbers as injection-detection performance.

Three flagging rules are derived from one model pass (the raw label is kept in
`Verdict.detail`), so changing the rule never needs a re-run:

- `unsafe`      : Safety == Unsafe
- `unsafe+ctrv` : Safety in {Unsafe, Controversial}
- `jailbreak`   : the Jailbreak category is present
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..defenses import Verdict

MODEL_ID = "Qwen/Qwen3Guard-Gen-0.6B"

_SAFETY = re.compile(r"Safety:\s*(Safe|Unsafe|Controversial)")
_CATEGORIES_LINE = re.compile(r"Categories:\s*(.*)")
_CATEGORY = re.compile(
    r"(Violent|Non-violent Illegal Acts|Sexual Content or Sexual Acts|PII|"
    r"Suicide & Self-Harm|Unethical Acts|Politically Sensitive Topics|"
    r"Copyright Violation|Jailbreak|None)"
)

RULES = ("unsafe", "unsafe+ctrv", "jailbreak")


def parse_output(content: str) -> tuple[str | None, tuple[str, ...]]:
    """Return (safety label or None, categories). None means unparseable."""
    match = _SAFETY.search(content)
    label = match.group(1) if match else None
    line = _CATEGORIES_LINE.search(content)
    categories = tuple(_CATEGORY.findall(line.group(1))) if line else ()
    return label, categories


def flag(rule: str, label: str, categories: tuple[str, ...]) -> bool:
    if rule == "unsafe":
        return label == "Unsafe"
    if rule == "unsafe+ctrv":
        return label in ("Unsafe", "Controversial")
    if rule == "jailbreak":
        return "Jailbreak" in categories
    raise ValueError(f"unknown rule {rule!r} (have: {RULES})")


class Qwen3GuardRunner:
    def __init__(
        self,
        model_id: str = MODEL_ID,
        revision: str | None = None,
        device: str | None = None,
        max_new_tokens: int = 64,
    ) -> None:
        import torch  # noqa: PLC0415
        from transformers import (  # noqa: PLC0415
            AutoModelForCausalLM,
            AutoTokenizer,
        )

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        # float32 on CPU: bf16 matmuls are slow there and the model is small.
        dtype = torch.float32 if self.device == "cpu" else "auto"
        model: Any = AutoModelForCausalLM.from_pretrained(
            model_id, revision=revision, torch_dtype=dtype
        )
        self.model = model.to(self.device).eval()
        self.revision = getattr(self.model.config, "_commit_hash", None) or revision
        self._memo: dict[str, tuple[str | None, tuple[str, ...]]] = {}

    def classify(self, text: str) -> tuple[str | None, tuple[str, ...]]:
        if text in self._memo:
            return self._memo[text]
        prompt = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": text}], tokenize=False
        )
        inputs = self.tokenizer([prompt], return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=self.max_new_tokens, do_sample=False
            )
        new_ids = out[0][len(inputs.input_ids[0]) :].tolist()
        content = self.tokenizer.decode(new_ids, skip_special_tokens=True)
        result = parse_output(content)
        self._memo[text] = result
        return result

    def metadata(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "device": self.device,
            "decoding": "greedy",
            "max_new_tokens": self.max_new_tokens,
            "role": "wrong-tool control (content moderation, not injection detection)",
        }


@dataclass
class Qwen3GuardDefense:
    runner: Qwen3GuardRunner
    rule: str = "unsafe+ctrv"

    def __post_init__(self) -> None:
        if self.rule not in RULES:
            raise ValueError(f"unknown rule {self.rule!r} (have: {RULES})")
        self.name = f"qwen3guard-gen-0.6b/{self.rule}"

    def detect(self, text: str) -> Verdict:
        label, categories = self.runner.classify(text)
        if label is None:  # unparseable output: fail closed, not a detection
            return Verdict(flagged=True, completed=False, detail="unparseable")
        return Verdict(
            flagged=flag(self.rule, label, categories),
            detail=f"{label}|{','.join(categories)}",
        )
