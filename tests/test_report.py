"""Pipeline test: evaluate -> raw rows -> report, using only the keyword baselines."""

import argparse

from zhipi import build, report, run_eval, transforms
from zhipi.cache import ResponseCache
from zhipi.defenses import EN_KEYWORDS, ZH_KEYWORDS
from zhipi.evaluate import evaluate


def _samples():  # type: ignore[no-untyped-def]
    return build.build_version("v0")


def test_report_end_to_end(tmp_path) -> None:  # type: ignore[no-untyped-def]
    samples = _samples()
    for defense in (EN_KEYWORDS, ZH_KEYWORDS):
        run_eval.write_rows(defense.name, evaluate(defense, samples), tmp_path, append=False)

    raw = report.load_raw(tmp_path)
    assert set(raw) == {"keyword-en", "keyword-zh"}
    text = report.build_report(raw, samples, {}, tmp_path / "v0.jsonl")

    for condition in report.CONDITION_ORDER:
        # v0 has no buried samples and none of the v3 transforms
        if "buried" not in condition and condition.split("/")[1] not in transforms.V3_TRANSFORMS:
            assert condition in text
    assert "Intent-level view" not in text
    assert "discusses_injection" in text
    assert "wrong-tool control" in text  # the caveats are part of the report
    assert "n/a" not in text.split("## False-positive")[0]  # nothing failed here


def test_v1_report_has_tier_and_new_strata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    samples = build.build_version("v1")
    run_eval.write_rows(EN_KEYWORDS.name, evaluate(EN_KEYWORDS, samples), tmp_path, append=False)
    text = report.build_report(report.load_raw(tmp_path), samples, {}, tmp_path / "v1.jsonl")
    assert "## Detection by payload tier and placement" in text
    for row in ("explicit / default", "judge_targeted / buried"):
        assert row in text
    for stratum in ("asks_humans_for_info", "long_benign"):
        assert stratum in text
    assert "19 hand-written intents" in text


def test_two_hf_models_keep_separate_provenance(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Regression: both used to be stored under 'hf-classifier', so the second run
    erased the first one's model id and pinned revision."""
    data = tmp_path / "v0.jsonl"
    data.write_text("{}\n", encoding="utf-8")
    for model, rev in (("org/model-a", "a" * 40), ("org/model-b", "b" * 40)):
        key = run_eval.meta_key("hf-classifier", argparse.Namespace(hf_model=model))
        run_eval.write_meta(key, {"model_id": model, "revision": rev}, data, tmp_path)
    import json

    meta = json.loads((tmp_path / "run_meta.json").read_text(encoding="utf-8"))
    assert meta["hf-classifier:org/model-a"]["revision"] == "a" * 40
    assert meta["hf-classifier:org/model-b"]["revision"] == "b" * 40
    assert run_eval.meta_key("qwen3guard", argparse.Namespace()) == "qwen3guard"


def test_paired_cell_counts_lost_and_gained_on_matched_samples() -> None:
    from zhipi.evaluate import Row
    from zhipi.report import paired_cell
    from zhipi.schemas import Sample

    def row(cond_transforms: tuple[str, ...], lang: str, intent: str, flagged: bool) -> Row:
        sample = Sample(
            sample_id=f"issue-{intent}-{'_'.join(cond_transforms) or 'plain'}-{lang}",
            label="injected", carrier="issue", language=lang, transforms=cond_transforms,
            text="t", intent_id=intent, plaintext_intent="p", tier="explicit",
        )
        return Row(sample, flagged, True)

    rows = [
        row((), "zh", "a", True), row(("zero_width",), "zh", "a", False),   # lost
        row((), "zh", "b", True), row(("zero_width",), "zh", "b", True),    # same
        row((), "zh", "c", False), row(("zero_width",), "zh", "c", True),   # gained
    ]
    assert paired_cell(rows, "zh/plain", "zh/zero_width") == "1↓/1↑ of 3, p=1.00"
    assert paired_cell(rows, "zh/plain", "zh/fullwidth") == "n/a"


def test_auroc_section_appears_only_for_detectors_with_scores(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from zhipi.defenses import Verdict

    class Scored:
        name = "scored"

        def detect(self, text: str) -> Verdict:  # higher score for text mentioning the target file
            hit = ".env" in text and "sandbox" in text
            return Verdict(flagged=hit, score=0.9 if hit else 0.1)

    class Unscored:
        name = "unscored"

        def detect(self, text: str) -> Verdict:
            return Verdict(flagged=False)

    samples = _samples()
    for d in (Scored(), Unscored()):
        run_eval.write_rows(d.name, evaluate(d, samples), tmp_path, append=False)
    text = report.build_report(report.load_raw(tmp_path), samples, {}, tmp_path / "v0.jsonl")
    section = text.split("## Threshold-free view: AUROC")[1].split("## Detection by payload tier")[0]
    header = [line for line in section.splitlines() if line.startswith("| language")][0]
    assert "scored" in header and "unscored" not in header


def test_raw_and_report_paths_keep_v0_where_it_was() -> None:
    from pathlib import Path

    assert run_eval.raw_dir_for(Path("x/v0.jsonl")) == run_eval.RAW_DIR
    assert run_eval.raw_dir_for(Path("x/v1.jsonl")).name == "raw_v1"
    assert run_eval.report_path_for(Path("x/v0.jsonl")).name == "phase1.md"
    assert run_eval.report_path_for(Path("x/v1.jsonl")).name == "v1.md"


def test_report_marks_incomplete_cells(tmp_path) -> None:  # type: ignore[no-untyped-def]
    class Flaky:
        name = "flaky"

        def detect(self, text: str):  # type: ignore[no-untyped-def]
            raise TimeoutError

    samples = _samples()
    run_eval.write_rows("flaky", evaluate(Flaky(), samples), tmp_path, append=False)
    text = report.build_report(report.load_raw(tmp_path), samples, {}, tmp_path / "v0.jsonl")
    assert "n/a ⚠" in text


def test_stability_counts_samples_whose_verdict_changes() -> None:
    def row(sid: str, rep: int, flagged: bool) -> dict[str, object]:
        return {"sample_id": sid, "repeat": rep, "flagged": flagged, "completed": True}

    raw = [row("a", 0, True), row("a", 1, True), row("b", 0, True), row("b", 1, False)]
    assert report.stability(raw) == (1, 2)
    assert report.stability([row("a", 0, True)]) is None


def test_make_defenses_builds_baselines_without_heavy_imports() -> None:
    args = argparse.Namespace()
    defenses, _ = run_eval.make_defenses("keyword-en", args, 0, ResponseCache(None))
    assert [d.name for d in defenses] == ["keyword-en"]


def test_load_dotenv_sets_names_skips_empty_and_never_overrides(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    env = tmp_path / ".env"
    env.write_text(
        "# comment\nZHIPI_T_NEW=abc\nZHIPI_T_EMPTY=\nZHIPI_T_KEEP='from-file'\nnot a pair\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ZHIPI_T_NEW", raising=False)
    monkeypatch.delenv("ZHIPI_T_EMPTY", raising=False)
    monkeypatch.setenv("ZHIPI_T_KEEP", "from-shell")
    assert run_eval.load_dotenv(env) == ["ZHIPI_T_NEW"]
    import os

    assert os.environ["ZHIPI_T_NEW"] == "abc"
    assert "ZHIPI_T_EMPTY" not in os.environ
    assert os.environ["ZHIPI_T_KEEP"] == "from-shell"
    os.environ.pop("ZHIPI_T_NEW")  # set directly by the loader; don't leak into later tests


def test_dry_run_makes_no_calls_and_writes_nothing(tmp_path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    data = tmp_path / "v0.jsonl"
    build.write_jsonl(_samples(), data)
    monkeypatch.setattr(
        "sys.argv",
        ["run_eval", "--defense", "deepseek-judge", "--repeats", "3", "--dry-run",
         "--data", str(data), "--out-dir", str(tmp_path / "raw")],
    )
    run_eval.main()
    out = capsys.readouterr().out
    assert "678 calls" in out and "billed" in out
    assert not (tmp_path / "raw").exists()


def test_v3_study_report_shows_the_new_transforms_paired_and_at_intent_level(tmp_path) -> None:  # type: ignore[no-untyped-def]
    samples = build.build_version("v3_study")
    run_eval.write_rows(ZH_KEYWORDS.name, evaluate(ZH_KEYWORDS, samples), tmp_path, append=False)
    text = report.build_report(report.load_raw(tmp_path), samples, {}, tmp_path / "v3_study.jsonl")
    for condition in ("zh/plain", "zh/traditional", "zh/pinyin", "zh/homophone", "zh/char_decomp"):
        assert condition in text
    for label in ("transform: traditional script", "transform: character decomposition"):
        assert label in text
    for stratum in ("traditional_text", "pinyin_text", "char_breakdown_text", "homophone_text"):
        assert stratum in text
    assert "### Intent-level view of the v3 transforms" in text
    assert "31 intents × 2 carriers per condition" in text
    # comparisons whose baseline is absent from the slice are left out, not printed as n/a rows
    assert "language: Chinese vs the English control" not in text
    assert "placement: buried" not in text


def test_intent_level_cell_counts_intents_not_samples() -> None:
    from zhipi.evaluate import Row
    from zhipi.report import intent_level_cell
    from zhipi.schemas import Sample

    def row(carrier: str, transforms: tuple[str, ...], flagged: bool, intent: str = "a") -> Row:
        return Row(
            Sample(sample_id=f"{carrier}-{intent}-{'_'.join(transforms) or 'plain'}-zh", label="injected",
                   carrier=carrier, language="zh", transforms=transforms, text="x", intent_id=intent,
                   plaintext_intent="p", tier="explicit"),
            flagged, True,
        )

    # intent "a": plain flagged in both carriers, variant in one -> one intent down (not two samples)
    rows = [row("issue", (), True), row("email", (), True), row("issue", ("pinyin",), True), row("email", ("pinyin",), False)]
    assert intent_level_cell(rows, "zh/plain", "zh/pinyin").startswith("1↓/0↑ of 1 intents")
    assert intent_level_cell([row("issue", (), True), row("issue", ("pinyin",), True)], "zh/plain", "zh/pinyin") == "no change (n=1 intents)"
