"""The version the package reports is the version it was built as (research R3 of feature 007).

Written in two places, ``pyproject.toml`` and ``caravan.__version__``, and carried into every run
report and cache key. The release workflow checks the built package against its tag; this test
keeps the two places together on every commit in between.
"""

from __future__ import annotations

from importlib.metadata import version

from packaging.version import Version

from caravan import __version__


def test_the_module_reports_the_distribution_version() -> None:
    assert __version__ == version("caravan-ml")


def test_the_version_is_a_pep_440_version() -> None:
    assert str(Version(__version__)) == __version__
