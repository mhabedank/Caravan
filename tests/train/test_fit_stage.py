"""User story 3 of feature 006: a model that cannot fit a board stops before any training.

The arithmetic is tested in ``tests/unit/test_fit_floors.py``; this is the lived version — a run,
its report, what it leaves behind, and what a board change re-runs.
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from caravan.manifest.errors import RULE_FLOOR_EXCEEDS_BOARD
from caravan.stages.cache import OUTCOME_PRODUCED, OUTCOME_REUSED
from caravan.stages.fit import FIT_RECORD
from caravan.stages.train import HISTORY, TRAINED_MODEL
from tests.support import FIXTURES, GATE, PILOT_FIXTURE
from tests.train.conftest import latest_run


def run(verb, manifest, root, *extra) -> tuple[int, dict]:
    code = main(
        [
            verb,
            str(manifest),
            "--runs-dir",
            str(root / "runs"),
            "--cache-dir",
            str(root / "c"),
            *extra,
        ]
    )
    run_dir = latest_run(root / "runs")
    return code, json.loads((run_dir / "report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("fit")
    code, report = run("build", PILOT_FIXTURE, root)
    assert code == EXIT_OK
    return root, report


def test_the_pilot_passes_with_estimated_figures(built) -> None:
    root, report = built
    record = json.loads((latest_run(root / "runs") / FIT_RECORD).read_text(encoding="utf-8"))
    assert record["provenance"] == "estimated"
    assert [floor["resource"] for floor in record["floors"]] == ["flash", "ram"]
    assert {verdict["verdict"] for verdict in record["verdicts"]} == {"below"}
    assert {verdict["board"] for verdict in record["verdicts"]} == {"s32k144", "stm32h743", "esp32"}
    assert "not a claim" in record["not_a_fit_claim"] or "only that" in record["not_a_fit_claim"]
    assert report["fit"] == record


def test_the_build_verb_runs_the_check(built) -> None:
    _, report = built
    assert [stage["name"] for stage in report["stages"]] == ["data", "build", "fit"]


def test_a_model_too_big_for_a_board_stops_before_training(tmp_path) -> None:
    code, report = run("train", GATE / "too-big-for-s32k144.yaml", tmp_path)

    assert code == EXIT_RULE
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_FLOOR_EXCEEDS_BOARD)
    assert finding["path"] == "export.targets"
    assert len(finding["found"]) == 1
    # Kernels 320 x 2048 + 2048 x 256 + 256 x 4 = 1,180,672 int8 bytes, biases 2,308 x 4 int32
    # bytes = 9,232: 1,189,904 against 512 KiB.
    assert finding["found"][0] == (
        "s32k144 flash: the floor is 1,189,904 bytes and the board has 524,288 (short by 665,616)"
    )
    assert [stage["name"] for stage in report["stages"]] == ["data", "build"]
    run_dir = latest_run(tmp_path / "runs")
    assert not (run_dir / TRAINED_MODEL).exists()
    assert not (run_dir / HISTORY).exists()
    assert not (run_dir / FIT_RECORD).exists()


def test_changing_the_boards_reruns_the_check_and_never_the_training(tmp_path) -> None:
    manifest = tmp_path / "pilot.yaml"
    text = PILOT_FIXTURE.read_text(encoding="utf-8").replace(
        "../../datasets/synthetic", str(FIXTURES / "datasets" / "synthetic")
    )
    manifest.write_text(text, encoding="utf-8")
    code, _ = run("train", manifest, tmp_path)
    assert code == EXIT_OK

    manifest.write_text(
        text.replace("targets: [s32k144, stm32h743, esp32]", "targets: [s32k144, stm32h743]"),
        encoding="utf-8",
    )
    code, report = run("train", manifest, tmp_path)
    assert code == EXIT_OK
    assert {stage["name"]: stage["outcome"] for stage in report["stages"]} == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_REUSED,
        "fit": OUTCOME_PRODUCED,
        "train": OUTCOME_REUSED,
    }
