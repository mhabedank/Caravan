# Budgets

Caravan gates the budgets of the models it builds. It gates its own too, because a budget that is
not measured is a warning, and warnings are read once (Principle V).

## The numbers

| Budget | Limit | Measured | Where it is checked |
|---|---|---|---|
| Direct runtime dependencies | 6 | **2** (`pydantic`, `ruamel.yaml`) | `tests/layering/test_declared_dependencies.py` |
| Optional extras | 4 | **0** | same test |
| Cold install, time | 30 s | **3.1 s** | the `install-budget` job in CI |
| Cold install, size | 50 MB | **9 MiB** installed, 7 packages | same job |
| Python versions supported | current and previous stable minor | 3.14 and 3.15 | the `test` matrix in CI |

Measured on 2026-10-22 against `caravan_ml-0.1.0-py3-none-any.whl` in an empty environment with
the package index cache disabled. The installed set is `caravan-ml`, `pydantic`, `pydantic-core`,
`ruamel-yaml`, `annotated-types`, `typing-extensions` and `typing-inspection`.

## Why the headroom is not spare capacity

The gap between 9 MiB and the 50 MB limit, and between two dependencies and six, is reserved for
the features that cannot avoid it:

- the analysis stage needs to read an exported model file and do shape arithmetic, which means a
  flatbuffer schema binding and a numeric library;
- the model card needs a template renderer.

That is four of the six slots accounted for. The budget is meant to bind when something heavy is
proposed, not to be renegotiated at that moment — which is why the command line is built on
`argparse` from the standard library rather than spending a slot on convenience.

## What the budget does not cover

Development dependencies (`pytest`, `ruff`, `packaging`) and the build backend (`hatchling`) are
not installed by users and do not count. The training extra, when it arrives, will be heavy — that
is expected and is the whole point of the layering rule: the weight is confined to one optional
extra, and `caravan validate` keeps working without it.

## Changing a number

The dependency and extras limits come from the constitution (Principle XII). Changing one is a
PATCH amendment with a stated reason, not a decision inside a feature. The install budget numbers
live in the spec of the feature that measures them (SC-003) and in the CI job that enforces them.
