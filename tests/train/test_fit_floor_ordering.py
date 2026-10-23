"""The fit check's memory floor never exceeds the export's (feature 006, contracts/fit-check.md).

Two lower bounds on the same quantity, computed two ways: before training from the built model's
layers, and after export from the converted graph's tensor lifetimes (feature 004). If the first
ever came out larger, one of them would no longer be a lower bound — and the check before training
could stop a model that fits.
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.stages.fit import FIT_RECORD
from tests.support import PILOT_V01, VALID
from tests.train.conftest import latest_run

CONV1D = VALID / "picket-conv1d-fixture.yaml"


@pytest.mark.parametrize("manifest", [PILOT_V01, CONV1D], ids=["mlp", "conv1d"])
def test_the_fit_floor_is_at_most_the_export_floor(manifest, tmp_path) -> None:
    code = main(
        ["export", str(manifest), "--runs-dir", str(tmp_path / "r"), "--cache-dir", str(tmp_path)]
    )
    assert code == EXIT_OK
    run_dir = latest_run(tmp_path / "r")
    fit = json.loads((run_dir / FIT_RECORD).read_text(encoding="utf-8"))
    exported = json.loads((run_dir / "export.json").read_text(encoding="utf-8"))
    fit_ram = next(floor for floor in fit["floors"] if floor["resource"] == "ram")
    assert fit_ram["floor_bytes"] <= exported["graph"]["working_memory"]["floor_bytes"]
