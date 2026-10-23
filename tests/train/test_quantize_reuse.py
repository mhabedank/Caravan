"""What re-quantizes and what does not — the coverage the analysis pass found missing.

The generic proof is ``tests/unit/test_cache_key_projection.py``, which walks every leaf of the
pilot manifest for every registered stage. This is the lived version: edit a manifest the way a
person edits one, run it again, and see which stages ran.
"""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, main
from caravan.stages.cache import OUTCOME_PRODUCED, OUTCOME_REUSED
from tests.train.conftest import latest_run, pure_windows, write_manifest, write_records

HEADER = "label,a,b"

#: The fixture manifest template of feature 002 carries int8 by default through the schema, so a
#: quantization setting has to be written in for these cases to be about this stage.
EXPORT_BLOCK = "export:\n  targets: [stm32h743]\n"
EXPORT_WITH = "export:\n  targets: [stm32h743]\n  quantization: int8\n"


def prepare(tmp_path, **overrides):
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 8)])
    manifest = write_manifest(tmp_path, **{"accuracy_drop_max": 0.5, **overrides})
    text = manifest.read_text(encoding="utf-8").replace(EXPORT_BLOCK, EXPORT_WITH)
    manifest.write_text(text, encoding="utf-8")
    return manifest


def quantize(manifest, tmp_path):
    code = main(
        [
            "quantize",
            str(manifest),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == EXIT_OK, f"expected a clean run, got exit {code}"
    report = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text("utf-8"))
    return {stage["name"]: stage["outcome"] for stage in report["stages"]}


def edit(manifest, old: str, new: str) -> None:
    text = manifest.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is not in the manifest, so this case tests nothing"
    manifest.write_text(text.replace(old, new), encoding="utf-8")


ALL_REUSED = {
    "data": OUTCOME_REUSED,
    "build": OUTCOME_REUSED,
    "fit": OUTCOME_REUSED,
    "train": OUTCOME_REUSED,
    "quantize": OUTCOME_REUSED,
}
ALL_PRODUCED = {
    "data": OUTCOME_PRODUCED,
    "build": OUTCOME_PRODUCED,
    "fit": OUTCOME_PRODUCED,
    "train": OUTCOME_PRODUCED,
    "quantize": OUTCOME_PRODUCED,
}
ONLY_QUANTIZE = {
    "data": OUTCOME_REUSED,
    "build": OUTCOME_REUSED,
    "fit": OUTCOME_REUSED,
    "train": OUTCOME_REUSED,
    "quantize": OUTCOME_PRODUCED,
}


def test_the_first_run_produces_all_three_and_the_second_reuses_all_three(tmp_path) -> None:
    manifest = prepare(tmp_path)
    assert quantize(manifest, tmp_path) == ALL_PRODUCED
    assert quantize(manifest, tmp_path) == ALL_REUSED


def test_renaming_the_model_re_runs_nothing_up_to_quantize(tmp_path) -> None:
    # model.name is read by the export alone, for the interface contract (feature 006): a new name
    # must not rebuild, retrain or re-quantize.
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    edit(manifest, "name: rule-case", "name: rule-case-renamed")
    assert quantize(manifest, tmp_path) == ALL_REUSED


def test_adding_a_target_board_re_runs_only_the_fit_check(tmp_path) -> None:
    # The case worth having a test for: a board is not an input to the quantized model, so adding
    # one must not re-quantize or retrain. ``export.targets`` is in the read set of the fit check
    # before training (feature 006) and of no stage that produces a model.
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    edit(manifest, "targets: [stm32h743]", "targets: [stm32h743, esp32]")
    assert quantize(manifest, tmp_path) == {**ALL_REUSED, "fit": OUTCOME_PRODUCED}


def test_changing_the_accepted_drop_re_quantizes_only(tmp_path) -> None:
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    edit(manifest, "accuracy_drop_max: 0.5", "accuracy_drop_max: 0.4")
    assert quantize(manifest, tmp_path) == ONLY_QUANTIZE


def test_changing_the_quantization_setting_re_quantizes_and_rechecks_the_fit(tmp_path) -> None:
    # The fit check reads the quantization too: the floors are counted at the stated element size
    # (feature 006), so a different setting is a different floor — and still no retraining.
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    edit(manifest, "quantization: int8", "quantization: none")
    assert quantize(manifest, tmp_path) == {**ONLY_QUANTIZE, "fit": OUTCOME_PRODUCED}


def test_changing_the_calibration_count_re_quantizes_only(tmp_path) -> None:
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    edit(manifest, "representative_samples: 100", "representative_samples: 120")
    assert quantize(manifest, tmp_path) == ONLY_QUANTIZE


def test_changing_the_seed_re_runs_everything_but_the_data_stage(tmp_path) -> None:
    # The data stage reads the declarations and the data, never the seed: what the data says does
    # not depend on how the weights were drawn (feature 006).
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    edit(manifest, "epochs: 1", "epochs: 1\n  seed: 11")
    assert quantize(manifest, tmp_path) == {**ALL_PRODUCED, "data": OUTCOME_REUSED}


def test_changing_a_byte_of_the_dataset_re_runs_everything(tmp_path) -> None:
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    records = tmp_path / "data" / "records.csv"
    records.write_text(
        records.read_text(encoding="utf-8").replace("normal,0,0", "normal,1,0", 1),
        encoding="utf-8",
    )
    assert quantize(manifest, tmp_path) == ALL_PRODUCED


def test_a_reused_quantization_reports_the_same_numbers(tmp_path) -> None:
    # The report is built from the stage's own artifact, so reuse cannot quietly drop the verdict
    # or the three accuracies.
    manifest = prepare(tmp_path)
    quantize(manifest, tmp_path)
    first = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text("utf-8"))
    quantize(manifest, tmp_path)
    second = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text("utf-8"))

    assert first["quantization"] == second["quantization"]
    assert [g for g in second["gates"] if g["name"] == "accuracy"]
