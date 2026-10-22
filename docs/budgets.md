# Budgets

Caravan gates the budgets of the models it builds. It gates its own too, because a budget that is
not measured is a warning, and warnings are read once (Principle V).

## The numbers

| Budget | Limit | Measured | Where it is checked |
|---|---|---|---|
| Direct runtime dependencies | 6 | **2** (`pydantic`, `ruamel.yaml`) | `tests/layering/test_declared_dependencies.py` |
| Optional extras | 4 | **2** (`train`, `verify`) | same test |
| Cold install, time | 30 s | **3.1 s** | the `install-budget` job in CI |
| Cold install, size | 50 MB | **9 MiB** installed, 7 packages | same job |
| Python versions supported | current and previous stable minor, and any lowered floor | 3.13, 3.14 and 3.15 | the `test` matrix in CI |
| Python window of the `train` extra | narrower, stated and dated | 3.13 only | the `train` job in CI |
| Published floor, and when it returns to 3.14 | recorded, with the condition that closes it | 3.13 — see below | the obligation below |
| Weight of both extras together | recorded, not gated | **2,028 MiB** installed, 44 packages | printed by the `train` job in CI |
| Weight of the `verify` extra alone | recorded, not gated | **121 MiB** installed, 14 packages | printed by the same job |
| Python window of the `verify` extra | narrower than the project, stated and dated | 3.13 and 3.14 — no cp315 wheel | the `measure` matrix in CI |

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

## Two extras, and why the second one is cheap

Feature 003 added `verify`, and the numbers are the argument for it:

| | `train` | `verify` |
|---|---|---|
| Installed | 1,971 MiB | **121 MiB** |
| Packages | 41 | **14** |
| Python | 3.13 only | 3.13 and **3.14** — not 3.15 |
| Training framework in its graph | yes | **no** |
| What it does | builds, trains, converts | reads and runs an exported model |

Each column is a whole environment, which is the figure a reader can check in a job log. The
default installation is inside both — 7 MiB and 7 packages, measured the same way, by editable
install on 3.13, rather than the 9 MiB the table above measures from a wheel — so the extra adds
**114 MiB and 7 packages**: `ai-edge-litert`, `backports-strenum`, `flatbuffers`, `ml-dtypes`,
`numpy`, `protobuf`, `tqdm`. Measured on 2026-10-22, the `verify` column at 121 MiB on a runner and
on a development container alike; both extras together come to 2,028 MiB and 44 packages on 3.13.

The split is not tidiness. Conversion needs the training framework and therefore 3.13 — there is
no framework-free converter today, which feature 003 checked rather than assumed. But *reading* an
exported model needs none, and four stages do nothing else: footprint analysis, emulated
verification, the benchmark and the model card. Had they borrowed the conversion half they would
each have been confined to 3.13 and 1,971 MiB, and they would have been built on an interpreter
the framework itself warns is "scheduled for deletion".

**A correction worth leaving visible.** This page first said the `verify` extra installs on every
Python the project supports, and a test forbade a `python_version` marker on it to keep that true.
It is not true: `ai-edge-litert` publishes cp310 through cp314 and **no cp315**, in 2.3.0 and every
recent version (checked 2026-10-22). The claim came from verifying cp314 and assuming the next tag
followed. So the extra carries a marker like `train` does, with a wider window, the test now
*requires* one, and `caravan quantize` on 3.15 names the window instead of letting a resolver fail.

The case for the extra survives it, because the case was never mainly about Python coverage:
114 MiB against 1,971, and no training framework in its graph. Covering two of three Pythons
instead of one is a bonus.

**The obligation**: when a cp315 wheel ships, the marker widens, the `measure` matrix gains 3.15
and this paragraph goes. A CI step fails the build if the runtime ever resolves on 3.15 while the
marker still excludes it, so the widening cannot go unnoticed.

**The two remaining slots** are benchmarking and publication, which is exactly how the
constitution groups them. The budget is half spent and the half that is spent is accounted for.

## What the budget does not cover

Development dependencies (`pytest`, `ruff`, `packaging`) and the build backend (`hatchling`) are
not installed by users and do not count. The training extra is heavy: **1,971 MiB installed and 41
packages** in a `train`-only environment on 2026-10-22, of which TensorFlow alone is about 1.9 GiB.
The `verify` extra is not: 114 MiB added, 121 MiB in all, with no training framework in its graph.
A development container measured 2,017 MiB for the same 41 packages the same day — the two differ by
machine and by patch version of Python, exactly as the install-budget figures above do. What the
`train` job prints now is the two extras together, 2,028 MiB and 44 packages, because it installs
both to run the whole suite; no job prints `train` alone any more, so the figure for it is dated
here rather than attributed to a log.

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

The `verify` row was corrected the same way. It read 116 MiB and 8 packages — a number that
matched neither of the two things it could have meant: the whole environment the job measures
(121 MiB, 14 packages) or the extra's own addition over the default installation (114 MiB, 7
packages). It was carried into nine other files before anyone subtracted one from the other. Both
figures are now stated, with the column header saying which is which, and the package list above
makes the count checkable without a measurement at all.

## Changing a number

The dependency and extras limits come from the constitution (Principle XII). Changing one is a
PATCH amendment with a stated reason, not a decision inside a feature. The install budget numbers
live in the spec of the feature that measures them (SC-003) and in the CI job that enforces them.
