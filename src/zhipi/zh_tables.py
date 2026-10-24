"""Hand-curated lookup tables behind the term-level Chinese transforms.

Everything here is data, kept apart from `transforms.py` so it can be read and reviewed on
its own. The tables are small on purpose: they cover the vocabulary the payloads in
`data/seed/intents.jsonl` actually use, nothing more. `tests/test_transforms.py` checks that
the traditional table covers every simplified character in those payloads, and a one-off
cross-check against OpenCC (not a dependency of this repository) agreed with it.

Safety: these tables only re-spell words that already appear in the payloads. They add no
new targets and no new capabilities.
"""

from __future__ import annotations

# Simplified -> traditional, one character at a time (the "s2t" direction only). It is a
# character-level map, so it does not pick regional phrasing (回复 stays 回復, not 回覆) and it
# leaves ambiguous characters alone (系, 粘, 制); that is acceptable for an obfuscation, which
# only needs to look like traditional text to a filter and read normally to a model. Where a
# character has two accepted traditional forms the common Taiwan form is used (为 -> 為, 里 -> 裡,
# 钟 -> 鐘); a cross-check against OpenCC differs from this table in exactly those three.
TRADITIONAL: dict[str, str] = dict(
    zip(
        "与个为么产仅仓们会关册写准则办务动单参后吗响围坏块处备复头审对将库应开当录怀户扩护报挥无时"
        "机条来构标样档检测点独献环现码确类紧约级线组终经结给绝统维编范补规视计认讨议记论评诊试话该"
        "说请读调贡败贴轮输边过运还这进释里针钟链错闭问险项须题风马骤内两于并",
        "與個為麼產僅倉們會關冊寫準則辦務動單參後嗎響圍壞塊處備復頭審對將庫應開當錄懷戶擴護報揮無時"
        "機條來構標樣檔檢測點獨獻環現碼確類緊約級線組終經結給絕統維編範補規視計認討議記論評診試話該"
        "說請讀調貢敗貼輪輸邊過運還這進釋裡針鐘鏈錯閉問險項須題風馬驟內兩於並",
        strict=True,
    )
)

# Words the payloads use, re-spelled as toneless pinyin syllables (what someone typing past a
# keyword filter might send). Longest keys are applied first.
PINYIN: dict[str, str] = {
    "维护者": "wei hu zhe",
    "忽略": "hu lue",
    "指令": "zhi ling",
    "读取": "du qu",
    "文件": "wen jian",
    "内容": "nei rong",
    "公开": "gong kai",
    "回复": "hui fu",
    "配置": "pei zhi",
    "调用": "diao yong",
    "工具": "gong ju",
    "附上": "fu shang",
    "复述": "fu shu",
    "环境": "huan jing",
    "粘贴": "zhan tie",
    "分诊": "fen zhen",
}

# Same words, swapped for a same-sound (same syllable and tone) character. Chosen so the
# result is still readable by a person or a model, as typo-style evasion is.
HOMOPHONE: dict[str, str] = {
    "忽略": "忽掠",
    "指令": "指另",
    "读取": "读娶",
    "文件": "文建",
    "内容": "内荣",
    "公开": "公揩",
    "回复": "回付",
    "配置": "配治",
    "调用": "调佣",
    "工具": "工巨",
    "附上": "付上",
    "复述": "付述",
    "环境": "环竟",
}

# 拆字: a word written as the components of its characters. Only characters that split cleanly
# into a left/right or top/bottom pair of ordinary components are included.
DECOMPOSE: dict[str, str] = {
    "读取": "讠卖耳又",
    "配置": "酉己罒直",
    "文件": "文亻牛",
    "内容": "冂人宀谷",
    "忽略": "勿心田各",
    "公开": "八厶一廾",
    "指令": "扌旨人マ",
    "工具": "工且八",
    "环境": "王不土竟",
    "调用": "讠周用",
    "附上": "阝付上",
}
