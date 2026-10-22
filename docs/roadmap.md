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
| Manifest schema, `validate`, `render`, package skeleton | v0.1 | **delivered** (feature 001) | `picket-mlp` |
| `mlp` template, parameter half | v0.1 | **delivered** (feature 001) | `picket-mlp` |
| build + train: the template's builder half, TensorFlow behind the `train` extra | v0.1 | next | `picket-mlp` |
| quantize: int8 with the accuracy gate, per-layer error table on failure | v0.1 | planned | `picket-mlp` |
| export: flatbuffer and C array, minimal operator resolver, per-operator kernel coverage | v0.1 | planned | `picket-mlp` |
| `conv1d` template, both halves | v0.1 | planned | **`pace-cnn`** (decided 2026-10-22) |

Feature numbers under `specs/` and git branch names are independent; features are named here
rather than numbered, because the numbering continues from 001 while a chore branch may carry any
name.

**The `conv1d` decision, 2026-10-22.** The design document put `conv1d` in v0.1. During feature
001 it was deferred, correctly, because Principle X builds a template when a named model needs one
and nothing did. `pace-cnn` — IMU activity recognition, a time-series model already published at
0.1.0 — is now the named driver, so `conv1d` returns to v0.1 where the design document had it.
It arrives with the feature that ports `pace-cnn`, not before.

**What the port is and is not.** Rebuilding `pace-cnn` through Caravan happens in the zoo, not
here: the manifest and the release record live there, and `conv1d` is Caravan's part of it. At
v0.1 the port makes the *recipe* reproducible — manifest, training, int8, C array. It does not
reproduce the *card*: the footprint and latency figures come from `analyze` (v0.2) and `bench`
(v1.0) and stay hand-made until then. And because a published version is immutable (zoo
Principle IX), a Caravan-built `pace-cnn` is a new version, not a replacement of 0.1.0.

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
TFLite sense and no TFLM kernels, so supporting it means a second export path and a second
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
