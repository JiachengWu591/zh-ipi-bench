"""Chinese-specific payload transforms.

Each transform is a pure, deterministic `str -> str`. They are applied to the
*payload only*, never to the carrier around it: holding the host fixed is what
makes a comparison out of the results instead of a collection of anecdotes
(the same design rule as injection-blast-radius's attack corpus).

Everything here is dependency-free. The four original transforms work on characters; the
four added for v3 (traditional, pinyin, homophone, char_decomp) are lookups in small
hand-curated tables (`zh_tables.py`), so they re-spell only vocabulary the payloads already
use. Classical-Chinese rewriting is still planned and not stubbed in, so nothing in the
registry claims to do what it does not (see docs/THREAT_MODEL.md).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from . import zh_tables

Transform = Callable[[str], str]

ZERO_WIDTH_SPACE = "\u200b"
_CJK_START, _CJK_END = 0x4E00, 0x9FFF


def _is_cjk(ch: str) -> bool:
    return _CJK_START <= ord(ch) <= _CJK_END


def fullwidth(text: str) -> str:
    """ASCII -> fullwidth forms (`.env` -> `．ｅｎｖ`), space -> U+3000.

    Applies to the whole payload, file paths included: a fullwidth path is
    itself the attack being tested (a model reads it fine; a byte-level filter
    does not match it), not collateral damage.
    """
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if ch == " ":
            out.append("　")
        elif 0x21 <= code <= 0x7E:
            out.append(chr(code + 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def zero_width(text: str, every: int = 2) -> str:
    """Insert U+200B after every `every` consecutive CJK characters."""
    out: list[str] = []
    run = 0
    for ch in text:
        out.append(ch)
        if _is_cjk(ch):
            run += 1
            if run == every:
                out.append(ZERO_WIDTH_SPACE)
                run = 0
        else:
            run = 0
    return "".join(out)


def space_split(text: str) -> str:
    """Put an ASCII space between adjacent CJK characters (`忽 略 指 令`)."""
    out: list[str] = []
    for index, ch in enumerate(text):
        out.append(ch)
        if _is_cjk(ch) and index + 1 < len(text) and _is_cjk(text[index + 1]):
            out.append(" ")
    return "".join(out)


# Longest keys first so that "公开" is not eaten by a shorter overlapping key.
_CODE_MIX_TERMS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        {
            "忽略": "ignore",
            "指令": "instructions",
            "读取": "read",
            "文件": "file",
            "内容": "contents",
            "公开": "public",
            "回复": "reply",
            "配置": "config",
            "调用": "call",
            "工具": "tool",
            "维护者": "maintainer",
        }.items(),
        key=lambda pair: -len(pair[0]),
    )
)


def code_mix(text: str) -> str:
    """Replace key Chinese terms with English ones: natural 中英夹杂 phrasing."""
    for zh, en in _CODE_MIX_TERMS:
        text = text.replace(zh, en)
    return text


def _replace_terms(text: str, table: dict[str, str], *, pad: bool = False) -> str:
    """Replace every key in `table`, longest keys first so a short key cannot eat part of a
    longer one. With `pad`, the replacement is set off by single spaces (romanised or
    component text jammed against Chinese is unreadable to anyone, which would test
    legibility rather than the detector)."""
    for key in sorted(table, key=lambda k: (-len(k), k)):
        text = text.replace(key, f" {table[key]} " if pad else table[key])
    if pad:
        text = re.sub(r" {2,}", " ", text).strip(" ")
    return text


def traditional(text: str) -> str:
    """Simplified -> traditional characters (繁體): text a simplified-only filter or a
    simplified-trained classifier may not recognise, and that a model reads as normal."""
    return "".join(zh_tables.TRADITIONAL.get(ch, ch) for ch in text)


def pinyin(text: str) -> str:
    """Key terms as toneless pinyin (`读取` -> `du qu`): romanised, so no Chinese keyword matches."""
    return _replace_terms(text, zh_tables.PINYIN, pad=True)


def homophone(text: str) -> str:
    """Key terms with a same-sound character (谐音; `读取` -> `读娶`): a typo-style evasion."""
    return _replace_terms(text, zh_tables.HOMOPHONE)


def char_decomp(text: str) -> str:
    """Key terms written as the components of their characters (拆字; `读取` -> `讠卖耳又`)."""
    return _replace_terms(text, zh_tables.DECOMPOSE, pad=True)


REGISTRY: dict[str, Transform] = {
    "fullwidth": fullwidth,
    "zero_width": zero_width,
    "space_split": space_split,
    "code_mix": code_mix,
    "traditional": traditional,
    "pinyin": pinyin,
    "homophone": homophone,
    "char_decomp": char_decomp,
}

# The transforms added in v3 (v0-v2 are frozen and use only the first four).
V3_TRANSFORMS: tuple[str, ...] = ("traditional", "pinyin", "homophone", "char_decomp")


def apply(names: Sequence[str], text: str) -> str:
    """Apply the named transforms left to right. Unknown name -> KeyError."""
    for name in names:
        if name not in REGISTRY:
            raise KeyError(f"unknown transform {name!r} (have: {sorted(REGISTRY)})")
        text = REGISTRY[name](text)
    return text
