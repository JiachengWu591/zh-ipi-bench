"""Offline tests for the end-to-end harness. A fake victim stands in for
injection-blast-radius, so no model, key, network or checkout is involved: these test
leak recognition, sample selection, resumption, failure handling and the report."""

import base64
from urllib.parse import quote

from zhipi import build, e2e, report_e2e
from zhipi.e2e import Outcome

SECRET = "fake-sk-00000000000000000000"
FORMS = e2e.secret_forms([SECRET, "fake-pw-0000-not-a-real-password"])


def _samples():  # type: ignore[no-untyped-def]
    return build.build_version("v1")


def test_secret_forms_recognise_plain_urlencoded_and_base64_leaks() -> None:
    assert e2e.leaked_in(f"the key is {SECRET}", FORMS)
    assert e2e.leaked_in(f"https://example.invalid/c?d={quote(SECRET, safe='')}", FORMS)
    assert e2e.leaked_in(f"d={base64.b64encode(SECRET.encode()).decode()}", FORMS)
    assert e2e.leaked_in(f"d={base64.urlsafe_b64encode(SECRET.encode()).decode()}", FORMS)
    assert not e2e.leaked_in("Thanks for the report; labelled as a bug.", FORMS)


def test_short_values_are_not_treated_as_secrets() -> None:
    assert e2e.secret_forms(["abc", ""]) == ()


def test_selection_keeps_only_issue_samples_and_excludes_dump_prompt() -> None:
    injected, benign = e2e.select_samples(_samples())
    assert injected and benign
    assert {s.carrier for s in injected + benign} == {"issue"}
    assert "dump_prompt" not in {s.intent_id for s in injected}
    assert {e2e.by_condition(s) for s in injected} <= set(e2e.E2E_CONDITIONS)
    assert all(s.label == "benign" for s in benign)


class FakeVictim:
    """Baseline leaks on Chinese plain payloads; the isolated pipeline never does."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def baseline(self, sample):  # type: ignore[no-untyped-def]
        self.calls.append(("baseline", sample.sample_id))
        leaks = sample.label == "injected" and sample.language == "zh" and not sample.transforms
        return Outcome(published=SECRET if leaks else "ok", action="posted_comment")

    def isolated(self, sample):  # type: ignore[no-untyped-def]
        self.calls.append(("isolated", sample.sample_id))
        verdict = "high_risk" if sample.label == "injected" else "safe"
        return Outcome(
            published="Thanks for the report.", action="label_bug",
            audit_verdict=verdict, audit_bypass_simulated=verdict == "high_risk",
        )


def _run(tmp_path, victim=None, repeats=2):  # type: ignore[no-untyped-def]
    injected, benign = e2e.select_samples(_samples())
    jobs = e2e.plan(injected[:30], benign[:4], baseline_repeats=repeats)
    victim = victim or FakeVictim()
    rows = e2e.run_e2e(victim, jobs, FORMS, tmp_path / "e2e.jsonl")
    return jobs, victim, rows


def test_plan_runs_baseline_repeats_and_isolated_once(tmp_path) -> None:  # type: ignore[no-untyped-def]
    jobs, _, rows = _run(tmp_path, repeats=3)
    assert len(jobs) == 34 * (3 + 1) and len(rows) == len(jobs)
    assert sum(1 for r in rows if r.architecture == "isolated") == 34


def test_rows_mark_leaks_and_keep_the_audit_verdict(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, _, rows = _run(tmp_path)
    by = {(r.sample_id, r.architecture, r.repeat): r for r in rows}
    leaked = [r for r in rows if r.architecture == "baseline" and r.leaked]
    assert leaked and all("zh/plain" in e2e.by_condition(_sample(r.sample_id)) for r in leaked)
    assert not any(r.leaked for r in rows if r.architecture == "isolated")
    iso = [r for r in rows if r.architecture == "isolated" and r.audit_verdict == "high_risk"]
    assert iso and all(r.audit_bypass_simulated for r in iso)
    assert by  # keyed uniquely


def _sample(sample_id):  # type: ignore[no-untyped-def]
    return next(s for s in _samples() if s.sample_id == sample_id)


def test_rerun_resumes_and_does_not_call_the_victim_again(tmp_path) -> None:  # type: ignore[no-untyped-def]
    jobs, first, _ = _run(tmp_path)
    second = FakeVictim()
    again = e2e.run_e2e(second, jobs, FORMS, tmp_path / "e2e.jsonl")
    assert again == [] and second.calls == []
    assert len(e2e.load_rows(tmp_path / "e2e.jsonl")) == len(first.calls)


def test_rows_are_reused_only_for_byte_identical_samples(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from dataclasses import replace

    injected, benign = e2e.select_samples(_samples())
    chosen = injected[:3]
    jobs = e2e.plan(chosen, [], 1)
    rows = [
        e2e.E2ERow(s.sample_id, 0, a, True, False, "x", "-", False, "")
        for s, a, _ in jobs
    ]
    changed = [replace(chosen[0], text=chosen[0].text + " edited")] + chosen[1:]
    out = tmp_path / "e2e.jsonl"

    got = e2e.reusable_rows(rows, chosen, changed, jobs, out)
    assert {r.sample_id for r in got} == {s.sample_id for s in chosen[1:]}  # edited one dropped
    assert all(r.completed for r in got)

    # a failed row is never reusable, and a row already in `out` is not copied twice
    failed = [replace(rows[2], completed=False)]
    assert e2e.reusable_rows(failed, chosen, chosen, jobs, out) == []
    e2e.write_rows(rows[:1], out)
    again = e2e.reusable_rows(rows, chosen, chosen, jobs, out)
    keys = {(r.sample_id, r.architecture, r.repeat) for r in again}
    assert (rows[0].sample_id, rows[0].architecture, rows[0].repeat) not in keys
    assert len(again) == len(rows) - 1


def test_a_failing_victim_gives_incomplete_rows_that_are_neither_leak_nor_hold(tmp_path) -> None:  # type: ignore[no-untyped-def]
    class Broken:
        def baseline(self, sample):  # type: ignore[no-untyped-def]
            raise TimeoutError("secret in message must not be stored")

        def isolated(self, sample):  # type: ignore[no-untyped-def]
            raise RuntimeError

    _, _, rows = _run(tmp_path, victim=Broken(), repeats=1)
    assert rows and all(not r.completed and not r.leaked for r in rows)
    assert {r.error for r in rows} == {"TimeoutError", "RuntimeError"}  # type only
    assert all("secret" not in r.error for r in rows)
    # incomplete rows are retried on the next run (a completed row would be skipped)
    injected, _ = e2e.select_samples(_samples())
    retry = e2e.run_e2e(FakeVictim(), e2e.plan(injected[:30], [], 1)[:2], FORMS, tmp_path / "e2e.jsonl")
    assert len(retry) == 2 and all(r.completed for r in retry)


def test_report_shows_every_architecture_and_flags_an_isolated_leak(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, _, rows = _run(tmp_path)
    samples = _samples()
    text = report_e2e.build_e2e_report(rows, samples, {"ibr_repo_commit": "abc123"}, tmp_path / "v1.jsonl")
    for column in report_e2e.COLUMNS:
        assert column in text
    assert "DEFECT" not in text and "0 of" in text

    class Leaky(FakeVictim):
        def isolated(self, sample):  # type: ignore[no-untyped-def]
            return Outcome(published=SECRET, action="label_bug", audit_verdict="safe")

    _, _, leaky_rows = _run(tmp_path / "leaky", victim=Leaky())
    flagged = report_e2e.build_e2e_report(leaky_rows, samples, {}, tmp_path / "v1.jsonl")
    assert "DEFECT" in flagged


def test_audit_on_counts_a_high_risk_verdict_as_blocked() -> None:
    from zhipi.e2e import E2ERow

    sample = _samples()[0]
    row = E2ERow(sample.sample_id, 0, "isolated", True, True, "label_bug", "high_risk", True, "")
    views = report_e2e._rows_for([row], {sample.sample_id: sample}, report_e2e.COLUMNS[2])
    assert views[0].flagged is False  # leaked in the bypassed run, but the real audit would have stopped it
    bypassed = report_e2e._rows_for([row], {sample.sample_id: sample}, report_e2e.COLUMNS[1])
    assert bypassed[0].flagged is True
