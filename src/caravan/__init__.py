"""Caravan — a declarative pipeline for small models on microcontrollers.

This module deliberately contains nothing but the version. Importing the package must stay free
of side effects and must never reach a training framework (Principle XII); the layering tests in
``tests/layering`` assert exactly that.
"""

from __future__ import annotations

#: A development version on the way to 0.1.0, which the roadmap defines as the manifest schema,
#: the mlp and conv1d templates, the build, train and quantize stages and the C-array export.
#: Only the schema and one template's parameter half exist so far. The string is provenance: it is
#: written into every run report and every exported artifact's record, so it must not claim a
#: milestone the code has not reached.
__version__ = "0.1.0rc1"

__all__ = ["__version__"]
