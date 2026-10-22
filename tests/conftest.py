"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support import MINIMAL, PILOT


@pytest.fixture
def pilot() -> Path:
    return PILOT


@pytest.fixture
def minimal() -> Path:
    return MINIMAL
