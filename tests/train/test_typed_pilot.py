"""The typed pilot, with labels derived and nothing pinned, passes int8 from raw values (T015).

Feature 008, SC-003 and SC-004, on the guide's own manifest (``examples/picket-mlp.yaml``). Before
this feature the same data with derived labels failed the int8 gate (0.75 trained, 0.50 quantized,
feature 006 R11), because CAN identifiers and payload bytes shared one int8 input scale.

SC-004 is checked the way a firmware author would: the raw values of each test window, read from
the CSV file with nothing but the standard library, fed to the exported model by input name — no
scaling, no vocabulary, nothing from Caravan but the file and its contract.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.data.windows import plan_windows, split_for
from caravan.manifest._yaml import read_mapping
from tests.support import FIXTURE_COLUMNS, SYNTHETIC_DATASET
from tests.train.conftest import latest_run

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "picket-mlp.yaml"


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    root = tmp_path_factory.mktemp("typed-pilot")
    code = main(
        [
            "export",
            str(EXAMPLE),
            "--runs-dir",
            str(root / "runs"),
            "--cache-dir",
            str(root / "cache"),
        ]
    )
    assert code == EXIT_OK
    return latest_run(root / "runs")


def test_the_int8_gate_passes_with_derived_labels(exported) -> None:
    # SC-003.
    report = json.loads((exported / "report.json").read_text(encoding="utf-8"))
    gate = report["quantization"]["gate"]
    assert gate["metric"] == "accuracy"
    assert gate["verdict"] == "pass"
    assert report["quantization"]["model"]["fully_integer"] is True
    labels = report["data"]["output"]["fitted"]
    assert labels["labels_source"] == "derived"


def test_the_report_lists_every_feature_with_what_was_fitted(exported) -> None:
    report = json.loads((exported / "report.json").read_text(encoding="utf-8"))
    features = report["data"]["features"]
    assert [feature["name"] for feature in features] == list(FIXTURE_COLUMNS)
    assert features[0]["type"] == "category" and features[0]["fitted"]["cut"] >= 0
    assert all(feature["fitted"]["scale"] > 0 for feature in features[1:])
    assert report["data"]["ignored_columns"] == []


def raw_test_windows(run: Path) -> tuple[dict[str, np.ndarray], list[str]]:
    """The test part's windows, raw, from the CSV file and the run's resolved manifest."""
    resolved = read_mapping(run / "resolved-manifest.yaml")
    with (SYNTHETIC_DATASET / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = [row["label"] for row in rows]
    window = resolved["preprocessing"]["window_size"]
    plan = plan_windows(labels, window)
    split = split_for(
        plan,
        resolved["preprocessing"]["split"],
        seed=resolved["random_seed"],
        labels=sorted(set(plan.labels)),
    )
    starts = [plan.kept[position] for position in split.test]
    inputs = {
        "can_id": np.array(
            [[int(rows[s + i]["can_id"]) for i in range(window)] for s in starts], np.int32
        ),
        **{
            name: np.array(
                [[float(rows[s + i][name]) for i in range(window)] for s in starts], np.float32
            )
            for name in FIXTURE_COLUMNS[1:]
        },
    }
    return inputs, [plan.labels[position] for position in split.test]


def test_raw_values_by_input_name_give_the_trained_models_classes(exported) -> None:
    # SC-004.
    import keras
    from ai_edge_litert.interpreter import Interpreter

    import caravan.templates.builders.preprocessing  # noqa: F401  (registers the layers)

    inputs, _ = raw_test_windows(exported)
    trained = keras.saving.load_model(exported / "model" / "trained.keras")
    expected = np.argmax(trained.predict(inputs, verbose=0)["label"], axis=1)

    runner = Interpreter(model_path=str(exported / "model" / "model.tflite")).get_signature_runner()
    count = len(expected)
    got = np.array(
        [
            int(np.argmax(runner(**{k: v[i : i + 1] for k, v in inputs.items()})["label"]))
            for i in range(count)
        ]
    )
    budget = json.loads((exported / "report.json").read_text(encoding="utf-8"))["quantization"][
        "gate"
    ]["budget"]
    agreement = float((got == expected).sum() / count)
    assert agreement >= 1 - budget, (agreement, got, expected)
