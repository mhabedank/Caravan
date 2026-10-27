"""The own-project guide's worked example runs, as written (feature 009, T038).

The guide's manifest is read from the guide itself: the ```yaml block whose first line is
``# example: own-project``. The data is generated here, at test time, in the shape the guide shows
(no dataset enters the repository): a machine whose ``state`` is ``fault`` when its vibration is
high, over windows of 16 rows. The test is that someone following the guide gets a validated,
exported model with test windows for the board — not that the example is a good model.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main
from tests.train.conftest import latest_run

pytest.importorskip("ai_edge_litert")

GUIDE = Path(__file__).resolve().parents[2] / "docs" / "guides" / "own-project.md"
MARKER = "# example: own-project"


def guide_manifest() -> str:
    blocks = re.findall(r"^```yaml\n(.*?)^```$", GUIDE.read_text(encoding="utf-8"), re.M | re.S)
    marked = [block for block in blocks if block.startswith(MARKER)]
    assert len(marked) == 1, f"{GUIDE.name} needs exactly one yaml block starting {MARKER!r}"
    return marked[0]


def write_machine_data(directory: Path, windows: int = 60, window: int = 16) -> None:
    """Two files, a header row each, one row per time step; every third window is a fault."""
    rng = random.Random(7)
    header = "timestamp,temperature,vibration,mode,door,state"
    rows: list[str] = []
    for index in range(windows):
        fault = index % 3 == 0
        mode = ("idle", "run", "clean")[index % 3 if not fault else 1]
        door = "open" if rng.random() < 0.3 else "closed"
        for step in range(window):
            vibration = (0.85 if fault else 0.2) + rng.uniform(-0.08, 0.08)
            temperature = 40 + rng.uniform(0, 15) + (5 if fault else 0)
            rows.append(
                f"2026-10-01T{index:04d}:{step:02d},{temperature:.2f},{vibration:.3f},"
                f"{mode},{door},{'fault' if fault else 'ok'}"
            )
    directory.mkdir(parents=True)
    half = len(rows) // 2 // window * window
    (directory / "2026-10-01.csv").write_text("\n".join([header, *rows[:half]]) + "\n")
    (directory / "2026-10-02.csv").write_text("\n".join([header, *rows[half:]]) + "\n")


def test_the_guides_example_validates_and_exports_with_test_windows(workspace, tmp_path) -> None:
    runs, cache = workspace
    project = tmp_path / "machine"
    write_machine_data(project / "data")
    manifest = project / "manifest.yaml"
    manifest.write_text(guide_manifest(), encoding="utf-8")

    assert main(["validate", str(manifest), "--no-report"]) == EXIT_OK
    code = main(["export", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    assert code == EXIT_OK
    run = latest_run(runs)

    schema = json.loads((run / "data" / "schema.json").read_text(encoding="utf-8"))
    assert schema["ignored_columns"] == ["timestamp"]
    record = json.loads((run / "export.json").read_text(encoding="utf-8"))
    windows = record["test_windows"]
    assert windows["written"] == min(8, windows["available"])
    assert set(windows["per_class"]) == {"ok", "fault"}
    assert (run / "model" / "test_windows.h").is_file()
    assert (run / "runner" / "esp32" / "main.cc").is_file()
