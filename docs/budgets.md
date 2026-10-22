# Budgets

Caravan gates the budgets of the models it builds. It gates its own too, because a budget that is
not measured is a warning, and warnings are read once (Principle V).

## The numbers

| Budget | Limit | Measured | Where it is checked |
|---|---|---|---|
| Direct runtime dependencies | 6 | **2** (`pydantic`, `ruamel.yaml`) | `tests/layering/test_declared_dependencies.py` |
| Optional extras | 4 | **1** (`train`) | same test |
| Cold install, time | 30 s | **3.1 s** | the `install-budget` job in CI |
| Cold install, size | 50 MB | **9 MiB** installed, 7 packages | same job |
| Python versions supported | current and previous stable minor, and any lowered floor | 3.13, 3.14 and 3.15 | the `test` matrix in CI |
| Python window of the `train` extra | narrower, stated and dated | 3.13 only | the `train` job in CI |
| Published floor, and when it returns to 3.14 | recorded, with the condition that closes it | 3.13 — see below | the obligation below |
| Weight of the `train` extra | recorded, not gated | **1,971 MiB** installed, 41 packages | printed by the `train` job in CI |

Measured on 2026-10-22 against `caravan_ml-0.1.0.dev1-py3-none-any.whl` in an empty environment with
the package index cache disabled. The installed set is `caravan-ml`, `pydantic`, `pydantic-core`,
`ruamel-yaml`, `annotated-types`, `typing-extensions` and `typing-inspection`.

The same measurement on a GitHub-hosted runner the same day: **0.25 s and 7 MiB**. The figures
differ by machine, which is the point of gating the limit rather than the number — 30 s and 50 MB
hold on a laptop and on a runner alike, and a heavy dependency breaches them on both.

## Why the headroom is not spare capacity

The gap between 9 MiB and the 50 MB limit, and between two dependencies and six, is reserved for
the features that cannot avoid it:

- the analysis stage needs to read an exported model file and do shape arithmetic, which means a
  flatbuffer schema binding and a numeric library;
- the model card needs a template renderer.

That is four of the six slots accounted for. The budget is meant to bind when something heavy is
proposed, not to be renegotiated at that moment — which is why the command line is built on
`argparse` from the standard library rather than spending a slot on convenience.

## The training extra's own window, and the floor that moved with it

`tensorflow` 2.21.0 publishes wheels for cp310 through cp313 and none for 3.14 or 3.15 — neither
version this project supported (checked 2026-10-22 against the package index). 2.22.0rc0 *does*
ship a cp314 wheel, but it depends on `keras-nightly`, so it resolves only with pre-releases
enabled for every package in the graph and cannot be a dependency of a published distribution.

Principle XII allows an extra to carry a narrower Python window than the project. What it cannot do
is carry its own `requires-python`: that field belongs to the whole distribution, and an extra can
only put environment markers on its dependencies. With a floor of 3.14, `pip install
caravan-ml[train]` would fail on every interpreter — 3.13 refused by the distribution, 3.14 refused
by the framework. The published floor is therefore **3.13**, under the five conditions in Principle
XII as amended in constitution v2.3.0.

What that means in practice:

- `pip install caravan-ml` works on 3.13, 3.14 and 3.15, and all three are tested — a floor that is
  claimed and not tested is a false claim, which is why the matrix grew rather than the metadata.
- `pip install caravan-ml[train]` installs the framework on 3.13. On 3.14 and 3.15 it installs
  Caravan's training code and no framework, and `build` and `train` then say so, naming the window
  and the reason rather than failing in the resolver or with a traceback.
- The core must keep running on 3.13, which is a real constraint on what the core may use. That is
  the cost, and it is paid knowingly.

**The obligation this creates.** When a stable TensorFlow ships a cp314 wheel and depends on a
released `keras` — 2.22's release candidate says that is near — the extra moves to it, the floor
returns to `>=3.14`, the 3.13 job is deleted and this section goes away. Until then the obligation
lives here, in the roadmap and in research R1 of feature 002, which holds the evidence.

## What the budget does not cover

Development dependencies (`pytest`, `ruff`, `packaging`) and the build backend (`hatchling`) are
not installed by users and do not count. The training extra is heavy: **1,971 MiB installed and 41
packages** on a GitHub-hosted runner, printed by the `train` job on 2026-10-22, of which TensorFlow
alone is about 1.9 GiB. A development container measured 2,017 MiB for the same 41 packages the
same day — the two differ by machine and by patch version of Python, exactly as the install-budget
figures above do.

That is roughly 220 times the default installation, and it is expected rather than tolerated: it is
the whole point of the layering rule. The weight is confined to one optional extra, `caravan
validate` keeps working without it, and the size is *recorded* rather than gated, because a number
set by TensorFlow's wheel is not one this project can act on.

The first estimate written here was "roughly 700 MB", taken from the size of the wheel. The
measurement is nearly three times that, because a wheel is compressed and because 40 packages come
with it. It is corrected rather than quietly dropped: an unmeasured number in a document about
measured budgets is the thing this page exists against. The same goes for the figure the table
carries now — it is the one a reader can check in a job log, not the one a laptop happened to
produce.

## Changing a number

The dependency and extras limits come from the constitution (Principle XII). Changing one is a
PATCH amendment with a stated reason, not a decision inside a feature. The install budget numbers
live in the spec of the feature that measures them (SC-003) and in the CI job that enforces them.
