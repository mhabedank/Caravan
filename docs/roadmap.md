# Roadmap

What Caravan plans to deliver, and what it has decided not to. A plan, not a commitment.

This record exists because two decisions in this project's first day lived only in a conversation:
the design document itself, and a deferred constitutional obligation with no named owner. A plan
that is not written down is not a plan, and a non-goal that is not written down comes back as a
proposal three months later.

## How to change this file

Borrowed from the zoo's roadmap discipline, because the same honesty rules apply:

- **`planned` never changes.** It records the version an item was *first* planned for, so a slip
  stays visible.
- **Moving an item appends a line**, with the date and the reason. It does not rewrite the
  original.
- **Dropping an item records it**, with the date and the reason, rather than deleting the row.
- An item counts as delivered when it is merged and the version it belongs to is released.

Nothing reads this file mechanically today. If it ever needs to be checked by a tool, it becomes
YAML like the zoo's.

## v0.1 — the pipeline from manifest to C array

| Item | Planned | State | Driver |
|---|---|---|---|
| Manifest schema, `validate`, `render`, package skeleton | v0.1 | **delivered** in 0.1.0 | `picket-mlp` |
| `mlp` template, parameter half | v0.1 | **delivered** in 0.1.0 | `picket-mlp` |
| build + train: the template's builder half, TensorFlow behind the `train` extra | v0.1 | **delivered** in 0.1.0 | `picket-mlp` |
| quantize: int8 with the accuracy gate, per-layer error table on failure | v0.1 | **delivered** in 0.1.0 | `picket-mlp` |
| export: flatbuffer and C array, minimal operator resolver, per-operator kernel coverage | v0.1 | **delivered** in 0.1.0 | `picket-mlp` |
| `conv1d` template, both halves | v0.1 | **delivered** in 0.1.0 | **`pace-cnn`** (decided 2026-10-22) |
| Declared inputs and outputs, labels and columns from the data, the fit check before training, the interface contract in the export | v0.1 | **delivered** in 0.1.0 | `picket-mlp` |
| A fixed split from a column of the data; the framework's output in `framework.log`; the entry guide; the release workflow | v0.1 | **delivered** in 0.1.0 | **`pace-cnn`** (the split); the release |
| Typed features in Ludwig's names: one input per column (`number`, `category`, `binary`), preprocessing fitted on the training part and built into the model, outputs `category`, `binary`, `number`; manifest `caravan/v0.2` | v0.1 | **delivered** in 0.1.0 | `picket-mlp` (derived labels pass int8); **`pace-cnn`** |
| Export with only the runtime installed, when training and quantization are cached | v0.1 | **deferred** by the owner, 2026-10-23 | a known limit of 0.1.0 |
| The documentation site; test windows in the export (`export.test_windows`); the first exported model on a microcontroller, with its leg of the route and a firmware build before every release | v0.1 | **in progress** | the owner's goal for rc3, 2026-10-26 |

**The goal for rc3, 2026-10-26.** In the owner's words: complete documentation, "eine kleine
Landingpage, dann Dokumentation der Schnittstelle, also wie funktioniert die CLI, wie funktioniert
das [YAML]-Format, was sind momentan die Kompatibilitäten … und was wird in Zukunft gehen". Then
"ein, zwei kleine Projekte … Ende zu Ende wirklich bis auf den Mikrocontroller drauf". Both are
built:
- this site;
- [the route](route/index.md), whose third leg puts an exported model on a generic ESP32.

What a board run establishes is recorded in [board runs](board-runs/index.md), and the
[compatibility page](compatibility.md) states how far each board has been verified. Tagging rc3 is
the owner's decision, after their own projects have run.

**The release, 2026-10-23.** Candidate `v0.1.0rc1` first: the version to try by hand and the
version the `pace-cnn` port pins. `v0.1.0` follows once the port has run and every Caravan defect it
found is fixed; [the release note](releases/0.1.0.md) says what is in it and what is not. Installed
from the GitHub release; the package index is not used for 0.1.0 (owner decision).

**The `conv1d` decision, 2026-10-22.** The design document put `conv1d` in v0.1. During feature
001 it was deferred, correctly, because Principle X builds a template when a named model needs one
and nothing did. `pace-cnn` — IMU activity recognition, a time-series model already published at
0.1.0 — is now the named driver, so `conv1d` returns to v0.1 where the design document had it.
It arrives with the feature that ports `pace-cnn`, not before.

**v0.1 is complete as a framework.** Every stage from manifest to C array exists, both templates
exist, and the pilot fixture runs end to end through all of them. What remains for a *release* is
not a feature: it is the two obligations recorded below (the Python floor, and the environment check
that asks for more than it needs), and the port itself — which is work in the zoo, with the real
data, and is not Caravan's to do.

**What the conv1d template measured on the way in.** Keras `Conv1D` converts to `CONV_2D`: the
converter adds a dummy spatial dimension and removes it with reshapes, and the runtime's resolver
has no one-dimensional convolution at all. `MaxPooling1D` becomes `MAX_POOL_2D` and
`GlobalAveragePooling1D` becomes `MEAN`, for which neither `cmsis-nn` nor `esp-nn` supplies a
kernel. So the head is a parameter with a measured trade: on the fixture, the reducing head gives
six operators in eight nodes at 7,888 bytes with four of six accelerated. `BatchNormalization`
folds entirely into the preceding convolution — no operator, 648 bytes of folded weights — which is
why it is offered. Separable convolution was measured too and is deliberately *not* offered: no
named model needs it (Principle X), and the measurement is in the release note
so the next model that wants it finds it rather than repeating it.

**What the port is and is not.** Rebuilding `pace-cnn` through Caravan happens in the zoo, not
here: the manifest and the release record live there, and `conv1d` is Caravan's part of it. At
v0.1 the port makes the *recipe* reproducible — manifest, training, int8, C array. It does not
reproduce the *card*: the footprint and latency figures come from `analyze` (v0.2) and `bench`
(v1.0) and stay hand-made until then. And because a published version is immutable (zoo
Principle IX), a Caravan-built `pace-cnn` is a new version, not a replacement of 0.1.0.

**What that work changed about every number before it.** The conversion now fixes the model's
input batch to one, because a board runs one window at a time. The converted mlp previously carried
`SHAPE`, `STRIDED_SLICE`, `PACK` and `RESHAPE` to compute a flatten shape from a dimension that
never varies — four kernels in flash and four resolver entries for arithmetic whose answer was
known. On the pilot fixture the quantized model went from six distinct operators in eight nodes to
three in five, and from 15,664 bytes to 14,848. The function is unchanged within float32 round-off
— the decisions identical, the scores inside a thousandth of a percent, checked on an `mlp` and on a
`conv1d` model. Bit-identity was claimed first and a runner disproved it, which is why the claim
here is round-off and not equality. It happens inside the conversion, so that the model the
accuracy gate measures is the model that ships. Converting twice
would have meant two models and two accuracies, with the shipped one ungated.

**An obligation that work recorded rather than improvised.** `caravan export` needs both extras,
although the export *stage* needs only the runtime that reads a model file. The cause is the
environment check in the pipeline runner: it asks for every part the plan *could* need rather than
every part it *will* need, and a cached upstream result is what makes the difference. So an author
on Python 3.14 holding a quantized model from a 3.13 machine cannot export it, even though nothing
the stage does requires anything their installation lacks.

Fixing it means consulting the cache before the environment check, which needs the dataset
resolved, which collides with two invariants that work wrote down on purpose: the run directory
is created *before* the dataset is resolved, so a dataset that disagrees with the manifest lands in
a report rather than only on a terminal; and a missing extra creates no run directory at all. One
of the two has to move, and which one is a decision with reasons on both sides. It is not a thing
to improvise inside a feature about exporting, so it is written down here instead.

**The Python floor, and when it comes back up.** That work lowered the published floor from 3.14
to 3.13, because TensorFlow publishes no stable wheel above 3.13 and Python packaging has no
per-extra version window — a single `requires-python` covers the package and all its extras. All
three of 3.13, 3.14 and 3.15 are tested, so the claim in the metadata is true. The floor returns to `>=3.14` and the
3.13 job is deleted as soon as a stable TensorFlow ships a cp314 wheel depending on a released
`keras`; 2.22.0rc0 already ships the wheel and depends on `keras-nightly`, so the wait is for the
final release (still a candidate, checked 2026-10-23). This is the one open obligation of v0.1 that is not a planned item.

**The conversion question is answered, and the floor stays.** The Technical Baseline left open
whether an int8 conversion path exists without the training framework, to be settled when the
quantize stage was built. It was: there is none today — the standalone runtime package is a
runtime, not a converter, and the vendor's conversion documentation describes only the framework
path (checked 2026-10-22). So conversion keeps the framework and the published floor stays at 3.13
until a stable TensorFlow ships for the current Python.

What *did* come out of asking is the other half: **reading and running** an exported model needs no
training framework at all, and costs 114 MiB against 1,971. That work put that in its own extra,
so the four stages after it — analysis, emulated verification, the benchmark and the card — inherit
it instead of each solving it again.

Its window is 3.13 and 3.14: the runtime publishes no cp315 wheel either (checked 2026-10-22).
Wider than the conversion half's single version, and still not everywhere — which this roadmap
said wrongly before the extra was measured against the index rather than against one tag.

## v0.2 — footprint analysis

| Item | Planned | State | Note |
|---|---|---|---|
| `analyze`: per-layer activation memory, peak with the layer that causes it, flash, latency estimate | v0.2 | planned | the arena cannot be derived from the flatbuffer; see the prior-art note, C1 |
| Hardware requirement record, resolved against the board descriptions | v0.2 | planned | |
| Automatic template scaling when a budget is exceeded | v0.2 | planned | |
| `smallcnn` template | v0.2 | planned | needs a named driver before it is built |
| `forest` template over ONNX | v0.2 | **dropped 2026-10-22** | see below |

**`forest` dropped, 2026-10-22.** The design document planned a tree-model template reaching the
microcontroller through ONNX. A random forest has no tensor arena, no int8 quantization in the
TFLite sense and no kernels in TensorFlow Lite for Microcontrollers (TFLM), so supporting it
means a second export path and a second
on-device runtime — which Principle II refuses ("not becoming an inference runtime") and the
technical baseline rules out by fixing TFLM.

`picket-forest`, the one model this would serve, is published at 0.2.1 and works. Porting it would
buy reproducibility for a single model at the cost of a whole second path. Principle X's rule
applies: extract when the *second* model needs it. If a second tree model ever appears, this
becomes a live question again — and a constitutional one, not a feature.

## v0.3 — verification without hardware

| Item | Planned | State | Note |
|---|---|---|---|
| `verify` through Renode | v0.3 | planned | the only trustworthy memory figure for a board not on the bench |
| Requirement mapping, model to board | v0.3 | planned | |

Renode models no S32K144 (checked 2026-10-22). The emulated rung exists for `stm32h743` and the
Arduino Nano 33 BLE, and not for the ESP32 or the S32K144 — which is why the next board to acquire
is a Nucleo-H743 or a Nano 33 BLE rather than the S32K144: only there can emulated and measured
results be compared, which is the only way the v0.2 estimator ever gets calibrated.

## v0.4 — search, deliberately small

| Item | Planned | State | Note |
|---|---|---|---|
| Hyperparameter search over template parameters, board budget as a constraint | v0.4 | planned | not a research-grade architecture search (Principle II) |

## v1.0 — hardware and publication

| Item | Planned | State |
|---|---|---|
| `bench` on the board matrix, following a public measurement protocol | v1.0 | planned |
| `card`: the model card rendered from manifest and run reports | v1.0 | planned |
| `publish`: upload, credentials from the environment only | v1.0 | planned |

The benchmark protocol follows MLPerf Tiny's shape — a stated minimum duration and iteration
count, the median of a stated number of runs, a window excluding pre- and post-processing — so
that numbers are comparable outside this project.

## Deliberate non-goals

Not "later": **no**. Each is a decision with a reason, recorded so it is not re-proposed as an
improvement.

| Non-goal | Why |
|---|---|
| A second on-device runtime, including tree models over ONNX | Principle II; the technical baseline fixes TFLM + CMSIS-NN |
| An inference runtime of our own | Principle II; TFLM exists and is portable across the whole target matrix |
| A SoC or peripheral description language | Renode's own descriptions are already declarative |
| Cycle-accurate emulation | emulation verifies that it builds, loads, fits and computes correctly; latency comes from hardware |
| Research-grade neural architecture search | the usable pipeline is the point, not beating MIT at NAS |
| Cloud, desktop or LLM models | out of scope by Principle II; the zoo builds those without Caravan |
| One repository per model | decided 2026-10-22 for the zoo: it already separates models under `zoo/models/<name>/`, its constitution requires one release gate, one pipeline and one roadmap record, and N repositories would turn one schema migration into N pull requests |
