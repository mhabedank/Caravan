"""Everything here needs the model runtime, and nothing here needs a training framework.

That is the division the `verify` extra exists for: these tests run on 3.13, 3.14 and 3.15, where
the training framework is not installable on two of the three. The `test` matrix job installs this
extra and collects this directory on all three, which is the only way to hold the claim that
reading and running an exported model works on every Python the project supports.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

#: Not a skip marker: the directory is not collected at all, because a module that imports the
#: runtime at import time would fail before a skip could take effect.
collect_ignore_glob = (
    [] if importlib.util.find_spec("ai_edge_litert") is not None else ["test_*.py"]
)

MODELS = Path(__file__).resolve().parent.parent / "fixtures" / "models"


@pytest.fixture
def int8_model() -> Path:
    """A committed int8 model — the thing to read on a Python where no converter can run."""
    path = MODELS / "example-int8.tflite"
    if not path.is_file():  # pragma: no cover - committed with the suite
        pytest.skip(f"{path} is not committed")
    return path


@pytest.fixture
def float_model() -> Path:
    path = MODELS / "example-float.tflite"
    if not path.is_file():  # pragma: no cover - committed with the suite
        pytest.skip(f"{path} is not committed")
    return path
