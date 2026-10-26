"""Caravan — a declarative pipeline for small models on microcontrollers.

This module deliberately contains nothing but the version. Importing the package must stay free
of side effects and must never reach a training framework (Principle XII); the layering tests in
``tests/layering`` assert exactly that.
"""

from __future__ import annotations

#: The second release candidate of 0.1.0: every stage from the manifest to the C array, with typed
#: features (feature 008). The string is provenance: it is
#: written into every run report and every exported artifact's record, so it must not claim a
#: milestone the code has not reached.
__version__ = "0.1.0rc2"

__all__ = ["__version__"]
