"""How an entry is stored, and the three properties that keep the store trustworthy."""

from __future__ import annotations

import json

import pytest

from caravan.stages import cache as cache_module
from caravan.stages.cache import copy_into_run, entry_dir, insert, load, new_work_dir


def store_one(cache_dir, key="sha256:abc", stage="build", text="first"):
    work = new_work_dir(cache_dir, stage)
    (work / "model").mkdir(parents=True)
    (work / "model" / "built.json").write_text(text, encoding="utf-8")
    return insert(
        cache_dir,
        stage,
        key,
        work,
        artifacts=("model/built.json",),
        inputs={"model.template": "mlp"},
        dataset_version="sha256:data",
        upstream_key=None,
        run_id="20261022T000000Z-aaaaaaaa",
    )


def test_an_entry_round_trips(tmp_path) -> None:
    entry = store_one(tmp_path / "cache")
    again = load(tmp_path / "cache", "build", "sha256:abc")
    assert again is not None
    assert again.artifacts == entry.artifacts
    assert again.produced_by_run == "20261022T000000Z-aaaaaaaa"
    assert again.inputs == {"model.template": "mlp"}


def test_a_missing_entry_is_a_miss_not_an_error(tmp_path) -> None:
    assert load(tmp_path / "cache", "build", "sha256:nothing") is None


def test_an_entry_whose_artifact_was_deleted_is_a_miss(tmp_path) -> None:
    # FR-018. A cache that failed a run because its own bookkeeping is damaged would be worse
    # than one that recomputes.
    cache_dir = tmp_path / "cache"
    store_one(cache_dir)
    (entry_dir(cache_dir, "build", "sha256:abc") / "model" / "built.json").unlink()
    assert load(cache_dir, "build", "sha256:abc") is None


def test_a_truncated_record_is_a_miss(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    store_one(cache_dir)
    (entry_dir(cache_dir, "build", "sha256:abc") / "result.json").write_text("{not json", "utf-8")
    assert load(cache_dir, "build", "sha256:abc") is None


def test_the_copy_in_the_run_directory_is_a_copy(tmp_path) -> None:
    # Not a hard link: a later run could otherwise mutate a cached artifact through its link, and
    # the cache would start handing out something it never stored.
    cache_dir = tmp_path / "cache"
    entry = store_one(cache_dir)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    copy_into_run(entry, run_dir)

    copied = run_dir / "model" / "built.json"
    assert copied.read_text(encoding="utf-8") == "first"
    copied.write_text("tampered", encoding="utf-8")
    assert (entry.path / "model" / "built.json").read_text(encoding="utf-8") == "first"


def test_a_stage_that_did_not_write_a_declared_artifact_is_an_error(tmp_path) -> None:
    # The constitution's stage contract says a stage declares what it writes. A declaration that
    # is not kept has to be loud, not a partial entry somebody trusts later.
    cache_dir = tmp_path / "cache"
    work = new_work_dir(cache_dir, "build")
    with pytest.raises(RuntimeError, match="declared artifacts it did not write"):
        insert(
            cache_dir,
            "build",
            "sha256:abc",
            work,
            artifacts=("model/built.json",),
            inputs={},
            dataset_version=None,
            upstream_key=None,
            run_id=None,
        )
    assert load(cache_dir, "build", "sha256:abc") is None


def test_storing_the_same_key_again_replaces_it_whole(tmp_path) -> None:
    # Only reachable under --fresh or a race, and in both cases the content is a recomputation of
    # the same inputs — so the entry is replaced rather than merged, and never left half-written.
    cache_dir = tmp_path / "cache"
    store_one(cache_dir, text="first")
    store_one(cache_dir, text="second")
    entry = load(cache_dir, "build", "sha256:abc")
    assert entry is not None
    assert (entry.path / "model" / "built.json").read_text(encoding="utf-8") == "second"
    assert sorted(path.name for path in entry.path.iterdir()) == ["model", "result.json"]


def test_the_record_explains_itself(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    store_one(cache_dir)
    record = json.loads(
        (entry_dir(cache_dir, "build", "sha256:abc") / "result.json").read_text("utf-8")
    )
    # An entry a person can read without the tool: what it is, what it came from, and when.
    assert record["stage"] == "build"
    assert record["inputs"] == {"model.template": "mlp"}
    assert record["dataset_version"] == "sha256:data"
    assert record["produced_at"].endswith("Z")
    assert record["tool"]


def test_the_key_carries_no_path_separator_or_colon_into_the_filesystem(tmp_path) -> None:
    path = entry_dir(tmp_path, "build", "sha256:abcdef")
    assert ":" not in path.name
    assert path.name == "sha256-abcdef"


def test_canonical_json_is_stable_against_key_order() -> None:
    first = cache_module.canonical_json({"b": 1, "a": {"d": 2, "c": 3}})
    second = cache_module.canonical_json({"a": {"c": 3, "d": 2}, "b": 1})
    assert first == second
