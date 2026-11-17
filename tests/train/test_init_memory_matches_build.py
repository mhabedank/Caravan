"""The memory ``caravan init`` shows before building is what ``build`` checks (feature 013, R13).

The same floors from the same records: the estimate is built from the templates' own ``layers``,
``build`` from the built Keras model. A category input is left out where its vocabulary, learned
on the training part, would differ from the distinct values init sees in the whole sample.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.init.session import Session
from tests.train.conftest import latest_run

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"

CASES = [
    ("synthetic", "category", "mlp", {"can_id": None}),
    ("synthetic", "category", "conv1d", {"can_id": None}),
    ("synthetic", "category", "conv2d", {"can_id": None}),
    ("frames", "category", "conv2d", {}),
    ("anomaly", "anomaly", "autoencoder", {}),
]


@pytest.mark.parametrize(("name", "kind", "template", "inputs"), CASES)
def test_the_estimate_equals_the_floors_of_build(tmp_path, name, kind, template, inputs) -> None:
    session = Session(
        {"dataset": str(DATA / name), "boards": ["stm32h743"], "output_type": kind}, cwd=tmp_path
    )
    proposal = dict(session.value("inputs"))
    proposal.update(inputs)
    assert session.accept("inputs", proposal) is None
    assert session.accept("template", template) is None
    assert session.fill() == []
    target, findings = session.write()
    assert not findings
    estimate = session.estimate()
    assert estimate is not None

    runs = tmp_path / "runs"
    code = main(["build", str(target), "--runs-dir", str(runs), "--cache-dir", str(tmp_path / "c")])
    assert code == EXIT_OK
    record = json.loads((latest_run(runs) / "model" / "fit.json").read_text(encoding="utf-8"))
    built = {floor["resource"]: floor["floor_bytes"] for floor in record["floors"]}
    assert built == {"flash": estimate.flash.floor_bytes, "ram": estimate.ram.floor_bytes}
