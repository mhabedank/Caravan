"""Caravan — a declarative pipeline for small models on microcontrollers.

This module deliberately contains nothing but the version. Importing the package must stay free
of side effects and must never reach a training framework (Principle XII); the layering tests in
``tests/layering`` assert exactly that.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
