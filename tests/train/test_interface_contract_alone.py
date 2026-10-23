"""SC-005 of feature 006: the model can be fed and read from its contract alone.

A firmware author who does not use Caravan receives ``model/interface.json`` and the C header. From
those two files — nothing from the manifest, the run report or Caravan's code — they must be able
to turn raw records into the model's input and the model's output into a label name, and get the
answer Caravan gets.

Under ``tests/train`` because producing the export needs the training extra; the reading half uses
only the standard library, numpy and the desktop runtime, as such an author would.
"""

from __future__ import annotations

import csv
import json
import re

import numpy as np
import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.data.fingerprint import resolve_dataset
from caravan.data.reader import read_records
from caravan.data.reader_bridge import assemble_samples
from caravan.data.windows import plan_windows
from caravan.runtime.measure import predict
from tests.support import PILOT_FIXTURE, SYNTHETIC_DATASET
from tests.train.conftest import latest_run


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    root = tmp_path_factory.mktemp("contract")
    code = main(
        ["export", str(PILOT_FIXTURE), "--runs-dir", str(root / "runs"), "--cache-dir", str(root)]
    )
    assert code == EXIT_OK
    return latest_run(root / "runs")


def from_the_contract_alone(run_dir) -> list[str]:
    """What someone with nothing but the two files would write."""
    from ai_edge_litert.interpreter import Interpreter

    contract = json.loads((run_dir / "model" / "interface.json").read_text(encoding="utf-8"))
    header = (run_dir / "model" / "model_data.h").read_text(encoding="utf-8")
    (declared_input,) = contract["inputs"]
    (declared_output,) = contract["outputs"]

    # The header's named positions, which a runner would use instead of literal indices.
    def constant(name: str) -> int:
        match = re.search(rf"constexpr unsigned int g_model_data_{name} = (\d+);", header)
        assert match is not None, name
        return int(match.group(1))

    input_position = constant(f"input_{declared_input['name']}")
    output_position = constant(f"output_{declared_output['name']}")
    assert input_position == declared_input["position"]

    transformation = declared_input["transformation"]
    assert transformation["scaling"] == "none"
    columns, window = transformation["columns"], transformation["window"]
    with (SYNTHETIC_DATASET / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = [[float(row[name]) for name in columns] for row in csv.DictReader(handle)]
    records = np.asarray(rows, dtype=np.float32)
    starts = range(0, len(records) - window + 1, transformation["stride"])

    interpreter = Interpreter(model_path=str(run_dir / "model" / "model.tflite"))
    interpreter.allocate_tensors()
    tensor_in = interpreter.get_input_details()[input_position]["index"]
    tensor_out = interpreter.get_output_details()[output_position]["index"]
    scale, zero = declared_input["scale"], declared_input["zero_point"]
    labels = declared_output["interpretation"]["labels"]

    answers = []
    for start in starts:
        values = np.round(records[start : start + window] / scale) + zero
        sample = np.clip(values, -128, 127).astype(np.int8)[np.newaxis, ...]
        interpreter.set_tensor(tensor_in, sample)
        interpreter.invoke()
        answers.append(labels[int(np.argmax(interpreter.get_tensor(tensor_out)[0]))])
    return answers


def from_caravan(run_dir) -> list[str]:
    """What Caravan itself predicts, through its own reader, windows and runtime."""
    resolved = json.loads((run_dir / "data" / "schema.json").read_text(encoding="utf-8"))
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    records = read_records(dataset)
    plan = plan_windows(tuple("x" for _ in records.labels), 64)  # every complete window
    features, _ = assemble_samples(records, plan, ("x",))
    classes = predict(run_dir / "model" / "model.tflite", features)
    labels = ["normal", "dos", "fuzzy", "replay"]
    assert resolved["labels"] == labels
    return [labels[index] for index in classes]


def test_the_contract_alone_reproduces_caravans_predictions(exported) -> None:
    alone = from_the_contract_alone(exported)
    caravan = from_caravan(exported)
    assert len(alone) == len(caravan) == 81
    assert alone == caravan


def test_the_contract_names_the_model(exported) -> None:
    contract = json.loads((exported / "model" / "interface.json").read_text(encoding="utf-8"))
    header = (exported / "model" / "model_data.h").read_text(encoding="utf-8")
    assert contract["model"] == {"name": "picket-mlp", "version": "0.1.0"}
    assert 'g_model_data_model_name[] = "picket-mlp";' in header
