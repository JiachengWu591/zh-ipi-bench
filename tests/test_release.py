"""Tests for result packaging and the offline reproduction check."""

import json

from zhipi import build, release, verify


def test_pack_copies_rows_but_not_caches_or_trial_runs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = tmp_path / "raw_v1"
    (src / "cache").mkdir(parents=True)
    (src / "cache" / "judge.jsonl").write_text("{}\n", encoding="utf-8")
    (src / "keyword-en.jsonl").write_text("{}\n", encoding="utf-8")
    (src / "run_meta.json").write_text("{}", encoding="utf-8")
    (src / "e2e_weak-spike.jsonl").write_text("{}\n", encoding="utf-8")
    (src / "notes.txt").write_text("x", encoding="utf-8")
    dest = tmp_path / "rows"
    copied = release.pack_rows({"v1": src}, dest)
    assert sorted(p.name for p in copied) == ["keyword-en.jsonl", "run_meta.json"]
    assert not (dest / "v1" / "cache").exists()


def test_fingerprint_is_content_identity_and_matches_the_pinned_manifest() -> None:
    manifest = json.loads(release.MANIFEST.read_text(encoding="utf-8"))["datasets"]
    for version in build.VERSIONS:
        samples = build.build_version(version)
        assert release.fingerprint(samples) == manifest[version]["fingerprint"], version
        assert len(samples) == manifest[version]["samples"]
    # a one-character change must change the identity
    samples = build.build_version("v0")
    changed = [samples[0].__class__(**{**samples[0].__dict__, "text": samples[0].text + "x"}), *samples[1:]]
    assert release.fingerprint(changed) != release.fingerprint(samples)


def test_the_dataset_card_has_no_unfilled_placeholders(tmp_path) -> None:  # type: ignore[no-untyped-def]
    entries = release.dataset_entries(tmp_path)
    card = release.render_card(entries)
    assert "{v0_" not in card and "{v1_" not in card and "{v2_" not in card
    assert f"{entries['v2']['samples']:,}" in card
    assert card.startswith("---\nlicense: cc-by-4.0")


def test_build_dist_writes_the_files_a_dataset_upload_needs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = release.build_dist(tmp_path / "dist")
    for name in ("README.md", "MANIFEST.json", "data/v0.jsonl", "data/v1.jsonl", "data/v2.jsonl",
                 "seed/intents.jsonl", "seed/benign.jsonl"):
        assert (out / name).exists(), name


def test_the_released_results_reproduce_offline() -> None:
    """Every dataset rebuilds to its pinned checksum and every committed table is a pure
    function of the committed rows. This is the reproducibility guarantee, enforced in CI."""
    results = verify.run()
    failed = [(name, detail) for name, ok, detail in results if not ok]
    assert not failed, failed
    assert len(results) == len(build.VERSIONS) + len(verify.JOBS)
