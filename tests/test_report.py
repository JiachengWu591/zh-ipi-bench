"""Pipeline test: evaluate -> raw rows -> report, using only the keyword baselines."""

import argparse

from zhipi import build, report, run_eval
from zhipi.cache import ResponseCache
from zhipi.defenses import EN_KEYWORDS, ZH_KEYWORDS
from zhipi.evaluate import evaluate


def _samples():  # type: ignore[no-untyped-def]
    return build.build_samples(build.load_intents(), build.load_hard_negatives())


def test_report_end_to_end(tmp_path) -> None:  # type: ignore[no-untyped-def]
    samples = _samples()
    for defense in (EN_KEYWORDS, ZH_KEYWORDS):
        run_eval.write_rows(defense.name, evaluate(defense, samples), tmp_path, append=False)

    raw = report.load_raw(tmp_path)
    assert set(raw) == {"keyword-en", "keyword-zh"}
    text = report.build_report(raw, samples, {}, tmp_path / "v0.jsonl")

    for condition in report.CONDITION_ORDER:
        assert condition in text
    assert "discusses_injection" in text
    assert "wrong-tool control" in text  # the caveats are part of the report
    assert "n/a" not in text.split("## False-positive")[0]  # nothing failed here


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
