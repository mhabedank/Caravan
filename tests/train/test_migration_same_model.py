"""SC-003 of feature 006: the migrated previous form and the pinned new form build one model.

The new form changes what the author writes, not what is trained. With the labels pinned in the
previous order the two manifests must produce byte-identical trained weights under the same seed —
the input's and output's names differ (``input``/``output`` against ``frames``/``attack``), and
names draw no random numbers. With the labels derived, the order of the output units differs and so
do the weights, by construction (research R11).
"""

from __future__ import annotations

import keras
import numpy as np

from caravan.cli.main import EXIT_OK, main
from caravan.stages.train import TRAINED_MODEL
from tests.support import PILOT_FIXTURE, PILOT_V01
from tests.train.conftest import latest_run


def trained_weights(manifest, root):
    code = main(
        ["train", str(manifest), "--runs-dir", str(root / "runs"), "--cache-dir", str(root / "c")]
    )
    assert code == EXIT_OK
    return keras.saving.load_model(latest_run(root / "runs") / TRAINED_MODEL).get_weights()


def test_both_forms_train_to_byte_identical_weights(tmp_path) -> None:
    migrated = trained_weights(PILOT_FIXTURE, tmp_path / "migrated")
    pinned = trained_weights(PILOT_V01, tmp_path / "pinned")
    assert len(migrated) == len(pinned)
    for a, b in zip(migrated, pinned, strict=True):
        assert a.dtype == b.dtype and a.shape == b.shape
        assert np.array_equal(a, b)
        assert a.tobytes() == b.tobytes()
