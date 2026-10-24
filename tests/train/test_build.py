"""`caravan build`: the shape report, and that building is not a quality judgement."""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from caravan.stages.build import BUILT_MODEL, BUILT_REPORT
from tests.support import FIXTURE_FEATURES, SYNTHETIC_DATASET
from tests.train.conftest import latest_run


def build(manifest, runs, cache, *extra):
    return main(
        ["build", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache), *extra]
    )


def test_the_pilot_manifest_builds_and_reports_its_shape(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    assert build(fixture_manifest, runs, cache) == EXIT_OK

    run_dir = latest_run(runs)
    assert (run_dir / BUILT_MODEL).is_file()
    description = json.loads((run_dir / BUILT_REPORT).read_text(encoding="utf-8"))

    # One input per feature, its window from the manifest, its element type from its type
    # (feature 008, research R2); the output's units are the labels fitted on the training part.
    assert len(description["inputs"]) == FIXTURE_FEATURES
    by_name = {entry["name"]: entry for entry in description["inputs"]}
    assert by_name["can_id"] == {"name": "can_id", "dtype": "int32", "shape": [64]}
    assert by_name["dlc"] == {"name": "dlc", "dtype": "float32", "shape": [64]}
    assert description["output_shape"] == [4]
    assert description["template"] == "mlp"


def test_the_parameter_count_equals_the_layer_table(fixture_manifest, workspace) -> None:
    # If these two disagree, one of them is wrong and a reader has no way to tell which.
    runs, cache = workspace
    build(fixture_manifest, runs, cache)
    description = json.loads((latest_run(runs) / BUILT_REPORT).read_text(encoding="utf-8"))
    assert description["parameter_count"] == sum(
        layer["parameters"] for layer in description["layers"]
    )
    assert description["parameter_count"] == (
        description["trainable_parameters"] + description["non_trainable_parameters"]
    )


def test_an_implausible_model_still_builds_and_shows_why_it_is_implausible(
    fixture_manifest, workspace, tmp_path
) -> None:
    # Acceptance scenario 2 of user story 2. Building is not a quality judgement: a template
    # parameter wrong by an order of magnitude is cheapest to notice *here*, and the way to notice
    # it is a parameter count that is visibly absurd. Since feature 006 the fit check after the
    # build also refuses it — 18 million weights fit none of the three boards — and that refusal
    # comes after the build, so the built model and its description are still there to look at.
    runs, cache = workspace
    source = fixture_manifest.read_text(encoding="utf-8")
    absurd = tmp_path / "absurd.yaml"
    # The dataset reference is relative to the manifest, so a manifest written somewhere else
    # needs an absolute one.
    absurd.write_text(
        source.replace("hidden: [32, 16]", "hidden: [4096, 4096]").replace(
            "dataset: ../../datasets/synthetic", f"dataset: {SYNTHETIC_DATASET}"
        ),
        encoding="utf-8",
    )

    assert build(fixture_manifest, runs, cache) == EXIT_OK
    small = json.loads((latest_run(runs) / BUILT_REPORT).read_text(encoding="utf-8"))
    assert build(absurd, runs, cache) == EXIT_RULE
    run_dir = latest_run(runs)
    large = json.loads((run_dir / BUILT_REPORT).read_text(encoding="utf-8"))
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))

    assert large["parameter_count"] > 100 * small["parameter_count"]
    assert [finding["rule"] for finding in report["findings"]] == ["F-1"]


def test_the_report_records_the_framework_that_built_it(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    build(fixture_manifest, runs, cache)
    description = json.loads((latest_run(runs) / BUILT_REPORT).read_text(encoding="utf-8"))
    assert description["framework"]["name"] == "tensorflow"
    assert description["framework"]["version"]
    assert description["keras_version"]
