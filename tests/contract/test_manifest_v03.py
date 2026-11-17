"""The manifest of caravan/v0.3 (feature 014, contracts/manifest-fields.md).

What changed: windows know their recordings, a window's label follows a rule, overlapping training
windows exist, and a windowed manifest that names no split leaves the type to the data. Every rule
of the new fields is refused at its own path; the resolved form fills in every default.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.manifest._yaml import dump_mapping
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve
from caravan.manifest.version import SCHEMA_VERSION
from tests.unit.test_features_schema import BASE


def manifest_with(tmp_path, change) -> Any:
    document = copy.deepcopy(BASE)
    change(document)
    path = tmp_path / "m.yaml"
    path.write_text(dump_mapping(document), encoding="utf-8")
    return load_manifest(path)


def resolved_with(tmp_path, change) -> dict[str, Any]:
    outcome = manifest_with(tmp_path, change)
    assert outcome.is_valid, [finding.as_dict() for finding in outcome.findings]
    return resolve(outcome.manifest)["preprocessing"]


def test_this_build_reads_v0_3_and_refuses_v0_2(tmp_path) -> None:
    assert SCHEMA_VERSION == "caravan/v0.3"
    outcome = manifest_with(tmp_path, lambda d: d.update(apiVersion="caravan/v0.2"))
    (finding,) = outcome.findings
    assert finding.rule == "V-1"
    assert finding.found == "caravan/v0.2"


def test_a_windowed_manifest_without_a_split_leaves_the_type_to_the_data(tmp_path) -> None:
    pre = resolved_with(tmp_path, lambda d: None)
    assert pre["split"]["type"] == "derived"
    assert pre["window_stride"] == pre["window_size"]
    assert pre["window_label"] == "all_equal"
    assert pre["recording_column"] is None


def test_a_number_output_takes_the_newest_row_by_default(tmp_path) -> None:
    def change(document: dict[str, Any]) -> None:
        document["output_features"] = [{"name": "level", "type": "number", "mae_increase_max": 0.5}]

    assert resolved_with(tmp_path, change)["window_label"] == "last"


@pytest.mark.parametrize(
    ("stated", "resolved"),
    [
        ("majority", "majority"),
        ("last", "last"),
        ({"any": "dos"}, {"any": "dos"}),
        ({"any": 1}, {"any": "1"}),
    ],
)
def test_a_stated_label_rule_is_kept(tmp_path, stated, resolved) -> None:
    pre = resolved_with(tmp_path, lambda d: d["preprocessing"].update(window_label=stated))
    assert pre["window_label"] == resolved


def test_the_group_split_carries_its_column(tmp_path) -> None:
    def change(document: dict[str, Any]) -> None:
        document["preprocessing"].update(
            window_stride=4, split={"type": "group", "column": "vehicle"}
        )

    pre = resolved_with(tmp_path, change)
    assert pre["split"] == {
        "type": "group",
        "probabilities": [0.7, 0.15, 0.15],
        "column": "vehicle",
    }
    assert pre["window_stride"] == 4


def test_overlap_is_allowed_with_the_derived_default(tmp_path) -> None:
    pre = resolved_with(tmp_path, lambda d: d["preprocessing"].update(window_stride=4))
    assert pre["window_stride"] == 4 and pre["split"]["type"] == "derived"


@pytest.mark.parametrize(
    ("change", "rule", "path"),
    [
        (
            lambda d: d["preprocessing"].update(window_stride=0),
            "CF-20",
            "preprocessing.window_stride",
        ),
        (
            lambda d: d["preprocessing"].update(window_stride=4, split={"type": "stratify"}),
            "CF-21",
            "preprocessing.window_stride",
        ),
        (
            lambda d: d["preprocessing"].update(window_label="mean"),
            "CF-22",
            "preprocessing.window_label",
        ),
        (
            lambda d: d["preprocessing"].update(recording_column="state"),
            "CF-23",
            "preprocessing.recording_column",
        ),
    ],
)
def test_each_rule_is_refused_at_its_path(tmp_path, change, rule, path) -> None:
    outcome = manifest_with(tmp_path, change)
    assert [(f.rule, f.path) for f in outcome.findings][:1] == [(rule, path)]


def test_a_majority_rule_on_a_number_output_is_refused(tmp_path) -> None:
    def change(document: dict[str, Any]) -> None:
        document["output_features"] = [{"name": "level", "type": "number", "mae_increase_max": 0.5}]
        document["preprocessing"]["window_label"] = "majority"

    (finding,) = manifest_with(tmp_path, change).findings
    assert finding.rule == "CF-22"


def test_the_notice_never_changes_the_exit_code(tmp_path, capsys) -> None:
    outcome = manifest_with(tmp_path, lambda d: d["preprocessing"].update(split={"type": "random"}))
    assert outcome.is_valid and len(outcome.notices) == 1
    assert main(["validate", str(tmp_path / "m.yaml"), "--no-report"]) == EXIT_OK
    assert "notice —" in capsys.readouterr().err


def test_a_split_by_recording_carries_no_notice(tmp_path) -> None:
    outcome = manifest_with(
        tmp_path, lambda d: d["preprocessing"].update(split={"type": "recording"})
    )
    assert outcome.is_valid and outcome.notices == []
