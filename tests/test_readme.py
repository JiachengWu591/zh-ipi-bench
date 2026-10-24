"""The two README front pages must stay in step: links resolve, the language switch works in
both directions, and both show the same generated figure."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from zhipi.run_eval import ROOT

READMES = ("README.md", "README.zh-CN.md")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _relative_targets(text: str) -> list[str]:
    targets = []
    for target in LINK.findall(text):
        if re.match(r"[a-z]+:", target) or target.startswith("#"):
            continue
        targets.append(target.split("#")[0])
    return targets


@pytest.mark.parametrize("name", READMES)
def test_relative_links_resolve(name: str) -> None:
    missing = [t for t in _relative_targets(_text(name)) if t and not (ROOT / Path(t)).exists()]
    assert not missing, missing


def test_language_switch_links_both_ways() -> None:
    assert "[简体中文](README.zh-CN.md)" in _text("README.md").split("\n\n")[1]
    assert "[English](README.md)" in _text("README.zh-CN.md").split("\n\n")[1]


@pytest.mark.parametrize("name", READMES)
def test_both_readmes_embed_the_generated_figure(name: str) -> None:
    assert "](assets/results.svg)" in _text(name)


def test_the_headline_numbers_agree_across_languages() -> None:
    """A translation that drifts from the English numbers is worse than none."""
    def figures(text: str) -> set[str]:
        found = {m.rstrip(",.") for m in re.findall(r"\d[\d,.]*%?", text)}
        return {m for m in found if len(re.sub(r"\D", "", m)) >= 2 or m.endswith("%")}

    english, chinese = _text("README.md"), _text("README.zh-CN.md")
    for key in ("239", "717", "81", "97%", "80%", "1,288", "803", "226"):
        assert key in english and key in chinese, key
    assert figures(english) <= figures(chinese), sorted(figures(english) - figures(chinese))
