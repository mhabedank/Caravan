"""The test part has one implementation, shared by the gate and the board's windows (feature 009).

The end-to-end agreement — the export's windows come from the same test part the quantize stage
measured — is checked in ``test_test_windows.py`` against a real run. Here: what ``form_parts``
returns, on the synthetic fixture, is the split's test part, in split order, every time.
"""

from __future__ import annotations

import numpy as np

from caravan.data.fingerprint import resolve_dataset
from caravan.data.reader import read_records
from caravan.data.reader_bridge import assemble_targets
from caravan.data.test_part import form_parts, split_labels
from caravan.data.windows import plan_windows, split_for
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import merge_fitted, resolve
from caravan.stages import quantize
from caravan.stages.base import project
from tests.support import FIXTURE_COLUMNS, PILOT, SYNTHETIC_DATASET, pilot_fitted


def _projection() -> dict:
    outcome = load_manifest(PILOT)
    assert outcome.manifest is not None
    return project(merge_fitted(resolve(outcome.manifest), pilot_fitted()), quantize.SPEC)


def _records():
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    features = (("can_id", "category"), *((name, "number") for name in FIXTURE_COLUMNS[1:]))
    return read_records(dataset, features=features)


def test_the_test_part_is_the_split_test_part_in_split_order() -> None:
    inputs = _projection()
    output = quantize.output_of(inputs)
    records = _records()
    parts = form_parts(records, inputs, output)

    plan = plan_windows(records.labels, inputs["preprocessing.window_size"], parts=records.parts)
    split = split_for(
        plan,
        inputs["preprocessing.split"],
        seed=int(inputs["random_seed"]),
        labels=split_labels(output["type"], plan.labels),
    )
    assert parts.split.test == split.test

    features, targets = parts.test()
    expected = assemble_targets(plan, output)[list(split.test)]
    assert np.array_equal(targets, expected)
    assert set(features) == set(FIXTURE_COLUMNS)
    assert all(len(values) == len(split.test) for values in features.values())
    assert not set(parts.split.test) & set(parts.split.train)


def test_forming_twice_gives_the_same_windows() -> None:
    inputs = _projection()
    output = quantize.output_of(inputs)
    first = form_parts(_records(), inputs, output).test()
    second = form_parts(_records(), inputs, output).test()
    assert np.array_equal(first[1], second[1])
    for name in first[0]:
        assert np.array_equal(first[0][name], second[0][name])
