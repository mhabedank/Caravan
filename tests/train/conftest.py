"""Everything in this directory needs the training framework, and only this directory does.

The `test` job in continuous integration names `unit`, `contract`, `integration` and `layering`
explicitly and runs them on every Python in the matrix; `clean-environment` runs the whole tree
with no framework installed at all. So a test that needs the framework and lives anywhere else
turns two jobs red — which is why the rule is "all of them here, none of them elsewhere" and why
this directory disappears from collection when the framework is absent.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests.support import PILOT_FIXTURE

#: Not a skip marker: the directory is not collected at all. A skipped test that imports Keras at
#: module level would still fail at import time.
collect_ignore_glob = [] if importlib.util.find_spec("keras") is not None else ["test_*.py"]


@pytest.fixture
def fixture_manifest() -> Path:
    """The pilot manifest, pointed at the one committed dataset."""
    return PILOT_FIXTURE


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A run directory and a cache directory of this test's own, and nothing shared.

    ``monkeypatch.chdir`` as well, so a stray default path cannot write into the repository: a
    test that left a ``runs/`` directory behind would be a test that passes while breaking the
    rule it exists to check.
    """
    monkeypatch.chdir(tmp_path)
    runs = tmp_path / "runs"
    cache = tmp_path / "cache"
    return runs, cache


def latest_run(runs: Path) -> Path:
    """The most recent run directory, by modification time.

    Not by name: a run directory is ``<timestamp to the second>-<digest>``, so two runs inside one
    second order by digest rather than by time, and a test that assumed otherwise would read the
    wrong run's artifacts — intermittently, which is the worst kind.
    """
    return max(runs.iterdir(), key=lambda path: path.stat().st_mtime)


MANIFEST_TEMPLATE = """apiVersion: caravan/v0.2

model:
  name: rule-case
  version: 0.0.1
  template: mlp
  params:
    hidden: [4]

input_features:
  - {{name: a, type: number}}
  - {{name: b, type: number}}

output_features:
  - name: label
    type: category
    preprocessing: {{vocab: [{labels}]}}
    accuracy_drop_max: {accuracy_drop_max}

preprocessing:
  window_size: {window}
  split:
    type: {split_type}
    probabilities: [{train}, {val}, {test}]

dataset: {source}

trainer:
  epochs: {epochs}
  batch_size: 4
  learning_rate: {learning_rate}

export:
  targets: [stm32h743]
  representative_samples: 100
"""


def write_manifest(directory: Path, **overrides) -> Path:
    """A valid manifest whose dataset is whatever the test just wrote.

    The run rules are about the data disagreeing with a *valid* manifest, so every case here needs
    a manifest that passes validation and a dataset that does not match it.
    """
    settings = {
        "source": "data",
        "window": 4,
        "labels": "normal, attack",
        "accuracy_drop_max": 0.02,
        "train": 0.5,
        "val": 0.25,
        "test": 0.25,
        "split_type": "stratify",
        "epochs": 1,
        "learning_rate": 0.001,
    }
    stratified = overrides.pop("stratified", None)
    if stratified is not None:
        overrides["split_type"] = "stratify" if stratified in (True, "true") else "random"
    settings.update(overrides)
    path = directory / "manifest.yaml"
    path.write_text(MANIFEST_TEMPLATE.format(**settings), encoding="utf-8")
    return path


def write_records(directory: Path, rows: list[str], name: str = "records.csv") -> Path:
    """A data file written from lines, header included, exactly as given."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def pure_windows(labels: list[str], window: int, per_label: int) -> list[str]:
    """Rows forming ``per_label`` clean windows of ``window`` records for each label."""
    rows = []
    for label in labels:
        for index in range(window * per_label):
            rows.append(f"{label},{index % 7},{index % 5}")
    return rows
