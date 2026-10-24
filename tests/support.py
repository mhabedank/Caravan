"""Paths and helpers shared by the test suites."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "manifests" / "valid"
INVALID = FIXTURES / "manifests" / "invalid"
BOARDS = FIXTURES / "boards"

PILOT = VALID / "picket-mlp.yaml"
#: The smallest valid manifest.
MINIMAL = VALID / "pilot-min.yaml"
#: Valid manifests that a gate stops at run time (feature 006: the fit check).
GATE = FIXTURES / "manifests" / "gate"

#: The typed pilot pointed at the one committed dataset, everything fitted on the training part
#: (feature 008), and the same with the label order and the vocabulary pinned.
PILOT_FIXTURE = VALID / "picket-mlp-fixture.yaml"
PILOT_FIXTURE_PINNED = VALID / "picket-mlp-fixture-pinned.yaml"
#: The convolutional template on the same dataset.
CONV1D_FIXTURE = VALID / "picket-conv1d-fixture.yaml"
SYNTHETIC_DATASET = FIXTURES / "datasets" / "synthetic"

#: What the committed fixture is, in numbers, so a test can assert against the shape rather than
#: against whatever the file happens to contain. Changing the generator means changing these.
FIXTURE_RECORDS = 5184
FIXTURE_WINDOWS_KEPT = 80
FIXTURE_WINDOWS_DISCARDED = 1
FIXTURE_FEATURES = 5
FIXTURE_LABELS = ("dos", "fuzzy", "normal", "replay")
#: The pilot's input features in manifest order, and their types.
FIXTURE_COLUMNS = ("can_id", "dlc", "b0", "b1", "b2")


def pilot_fitted() -> dict:
    """What fitting the pilot gives, in the shape of data/preprocessing.json, with round numbers.

    For the core tests that need a resolved manifest with fitted values merged in — the cache keys,
    the interface contract — and must not depend on a training framework to produce them.
    """
    number = {"normalization": "zscore", "shift": 100.0, "scale": 50.0, "fill": 0.0}
    return {
        "input_features": {
            "can_id": {
                "vocab": [291, 608, 790, 1072],
                "codes": [291, 608, 790, 1072],
                "text_codes": None,
                "cut": 3,
                "unknown_index": 0,
                "missing": -1,
            },
            **{name: dict(number) for name in FIXTURE_COLUMNS[1:]},
        },
        "output": {"labels": list(FIXTURE_LABELS), "labels_source": "derived"},
    }


def invalid_cases() -> list[tuple[str, Path, dict]]:
    """Every invalid manifest fixture with the result its sibling file expects."""
    cases = []
    for manifest in sorted(INVALID.glob("*.yaml")):
        expected = json.loads(manifest.with_suffix(".expected.json").read_text(encoding="utf-8"))
        cases.append((manifest.stem, manifest, expected))
    return cases


#: The fixed-split variant of the committed dataset (feature 007): the same records with a `split`
#: column. Derived at test time from the one committed file rather than committed as a second
#: dataset (feature 002, FR-013). Per label, windows 0-11 are `train`, 12-15 `validation`, 16-19
#: `test`; the last `normal` window names `test` in its first half and `validation` in its
#: second, so it is mixed by part and discarded; the committed mixed-label window is `train` and is
#: discarded by label.
SPLIT_COUNTS = {"train": 48, "val": 16, "test": 15}
SPLIT_DISCARDED = 1


def write_split_dataset(destination: Path) -> Path:
    """Write the fixed-split dataset into ``destination`` and return the directory."""
    lines = (SYNTHETIC_DATASET / "records.csv").read_text(encoding="utf-8").splitlines()
    header, rows = lines[0].split(","), lines[1:]
    window = len(rows) // (len(FIXTURE_LABELS) * 20 + 1)
    out = [",".join(["label", "split", *header[1:]])]
    for index, row in enumerate(rows):
        label, rest = row.split(",", 1)
        number, position = divmod(index, window)
        within = number % 20
        if number >= len(FIXTURE_LABELS) * 20:
            part = "train"
        elif label == "normal" and within == 19:
            part = "test" if position < window // 2 else "validation"
        else:
            part = "train" if within < 12 else "validation" if within < 16 else "test"
        out.append(f"{label},{part},{rest}")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "records.csv").write_text("\n".join(out) + "\n", encoding="utf-8")
    return destination


#: The output columns the test-time datasets of feature 008 add (T031). The committed fixture's
#: ``label`` stays in them and, read by no feature, is reported as ignored.
BINARY_OUTPUT = "is_attack"
NUMBER_OUTPUT = "payload_mean"
FIXTURE_WINDOW = 64


def _fixture_rows() -> tuple[list[str], list[list[str]]]:
    lines = (SYNTHETIC_DATASET / "records.csv").read_text(encoding="utf-8").splitlines()
    return lines[0].split(","), [line.split(",") for line in lines[1:]]


def write_binary_dataset(destination: Path) -> Path:
    """The fixture with ``is_attack``: ``no`` for a normal record, ``yes`` for any other."""
    header, rows = _fixture_rows()
    out = [",".join([*header, BINARY_OUTPUT])]
    out += [",".join([*row, "no" if row[0] == "normal" else "yes"]) for row in rows]
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "records.csv").write_text("\n".join(out) + "\n", encoding="utf-8")
    return destination


def write_number_dataset(destination: Path) -> Path:
    """The fixture with ``payload_mean``: the mean of b0, b1 and b2 over each window's records.

    Written on every record of the window, so the records of one window agree, as a window's
    output must. The remainder records that fill no window get their own mean.
    """
    header, rows = _fixture_rows()
    columns = [header.index(name) for name in ("b0", "b1", "b2")]
    out = [",".join([*header, NUMBER_OUTPUT])]
    for start in range(0, len(rows), FIXTURE_WINDOW):
        block = rows[start : start + FIXTURE_WINDOW]
        values = [float(row[column]) for row in block for column in columns]
        mean = f"{sum(values) / len(values):.4f}"
        out += [",".join([*row, mean]) for row in block]
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "records.csv").write_text("\n".join(out) + "\n", encoding="utf-8")
    return destination
