"""Resolve which Hugging Face commit a model was actually loaded from.

`model.config._commit_hash` is not reliably populated across transformers
versions, and a run that cannot say which weights it used is not reproducible. The
hub cache records the resolved commit under `refs/<revision>`, so read it from there.
"""

from __future__ import annotations

from pathlib import Path


def resolved_revision(
    model_id: str, requested: str | None, cache_dir: Path | None = None
) -> str | None:
    if cache_dir is None:
        from huggingface_hub import constants  # noqa: PLC0415 - optional dependency

        cache_dir = Path(constants.HF_HUB_CACHE)
    ref = cache_dir / f"models--{model_id.replace('/', '--')}" / "refs" / (requested or "main")
    if ref.exists():
        return ref.read_text(encoding="utf-8").strip()
    if requested and len(requested) == 40:  # already a full commit hash
        return requested
    return None
