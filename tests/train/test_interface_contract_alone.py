"""SC-005 of feature 006: the model can be fed and read from its contract alone.

A firmware author who does not use Caravan receives ``model/interface.json`` and the C header. From
those two files — nothing from the manifest, the run report or Caravan's code — they must be able
to put raw records into every input and turn the model's output into a label name, and get the
answer Caravan gets. Since feature 008 that means raw values, input by input, at the named
positions: no scale, no vocabulary, nothing the model does itself.

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
from caravan.data.reader_bridge import assemble_inputs
from caravan.data.windows import plan_windows
from caravan.manifest._yaml import read_mapping
from caravan.runtime.measure import run_model
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
    (declared_output,) = contract["outputs"]

    # The header's named positions, which a runner would use instead of literal indices.
    def constant(name: str) -> int:
        match = re.search(rf"constexpr unsigned int g_model_data_{name} = (\d+);", header)
        assert match is not None, name
        return int(match.group(1))

    assert contract["preprocessing"] == "inside the model; pass raw values"
    window, stride = contract["window_size"], contract["stride"]
    with (SYNTHETIC_DATASET / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    def raw(entry: dict, text: str):
        # Raw values only: a number as it is, a category code as the integer, or by its table.
        if entry["type"] == "number":
            return float(text)
        if entry["text_codes"] is not None:
            return entry["text_codes"].get(text, 0)
        return int(text)

    interpreter = Interpreter(model_path=str(run_dir / "model" / "model.tflite"))
    interpreter.allocate_tensors()
    details = interpreter.get_input_details()
    tensor_out = interpreter.get_output_details()[constant(f"output_{declared_output['name']}")]
    labels = declared_output["labels"]

    answers = []
    for start in range(0, len(rows) - window + 1, stride):
        for entry in contract["inputs"]:
            position = constant(f"input_{entry['name']}")
            assert position == entry["position"]
            values = [raw(entry, rows[start + i][entry["name"]]) for i in range(window)]
            sample = np.asarray([values], dtype=np.dtype(entry["dtype"]))
            interpreter.set_tensor(details[position]["index"], sample)
        interpreter.invoke()
        answers.append(labels[int(np.argmax(interpreter.get_tensor(tensor_out["index"])[0]))])
    return answers


def from_caravan(run_dir) -> list[str]:
    """What Caravan itself predicts, through its own reader, windows and runtime."""
    resolved = read_mapping(run_dir / "resolved-manifest.yaml")
    features = resolved["input_features"]
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    records = read_records(dataset, features=tuple((f["name"], f["type"]) for f in features))
    plan = plan_windows(tuple("x" for _ in records.labels), 64)  # every complete window
    inputs = assemble_inputs(records, plan, features)
    raw = run_model(run_dir / "model" / "model.tflite", inputs, "label")
    labels = resolved["output_features"][0]["preprocessing"]["vocab"]
    return [labels[int(index)] for index in np.argmax(raw, axis=1)]


def test_the_contract_alone_reproduces_caravans_predictions(exported) -> None:
    alone = from_the_contract_alone(exported)
    caravan = from_caravan(exported)
    assert len(alone) == len(caravan) == 81
    assert alone == caravan


def test_the_contract_names_the_model(exported) -> None:
    contract = json.loads((exported / "model" / "interface.json").read_text(encoding="utf-8"))
    header = (exported / "model" / "model_data.h").read_text(encoding="utf-8")
    assert contract["model"] == {"name": "picket-mlp", "version": "0.2.0"}
    assert 'g_model_data_model_name[] = "picket-mlp";' in header
