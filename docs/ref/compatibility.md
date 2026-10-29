# Compatibility

What Caravan supports today, and how far each part has been verified. Each entry rests on a test, a
run report or a recorded [board run](board-runs/index.md), never on intention. What is planned is
on the [roadmap](../roadmap.md).

## Features

### Input types

Each type brings its preprocessing into the model, so a firmware passes raw values
([manifest reference](manifest/input-features.md)).

| Type | Passed by the firmware as | Inside the model |
|---|---|---|
| `number` | float32, the raw reading | standardised with the training part's statistics (`zscore`, `minmax`, `iq`, or none); a missing reading filled |
| `category` | int32: the integer itself, or for a text column the code `interface.json` lists | compared against the training part's vocabulary, with index 0 for unknown; an embedding (`dense`, the default) or `onehot` |
| `binary` | int32, 0 or 1 | used as one channel |

### Output types

| Type | Decision | int8 budget | Metrics |
|---|---|---|---|
| `category` | argmax over the classes; names in `model_data.h` | `accuracy_drop_max` | accuracy, confusion matrix |
| `binary` | the score against `threshold` (0.5) | `accuracy_drop_max` | accuracy, confusion matrix |
| `number` | the value, in the column's unit | `mae_increase_max` | MAE, MSE, RMSE, R² |

The metrics for a `number` output are the mean absolute error (MAE), the mean squared error (MSE),
its square root (RMSE), and the coefficient of determination (R²). The budget is set on MAE,
because it is in the column's own unit: a budget in degrees stays in degrees.

### Ludwig's types that Caravan does not have

Refused with {rule}`CF-14`:
- **`text`, `sequence`, `set`, `bag`:** need tokenizers and dynamic vocabularies at prediction
  time, which have no path inside a TensorFlow Lite Micro model.
- **`timeseries` as a whole sequence in one cell:** has no device path either. Caravan's
  `preprocessing.window_size`, rows forming a window, is how a time series reaches the model.
- **`image`, `audio`, `vector`, `date`, `h3`:** no model on the roadmap needs them yet (Principle
  X: a type is built when a named model needs it).

Source: the research note of 2026-10-24, section 5, on GitHub
(`docs/research/2026-10-24-typed-features-on-mcu.md`).

## Templates

`caravan templates` lists them. Parameters are in the
[manifest reference](manifest/model.md).

| Template | What it is | Driven by |
|---|---|---|
| `mlp` | dense layers over the window: `hidden` widths and `dropout` | the pilot, `picket-mlp` |
| `conv1d` | blocks of 1-D convolutions, optional batch normalisation and pooling, then an `average` or `flatten` head | `pace-cnn`, IMU activity recognition |

## Boards

`caravan boards` lists them. A board is a description file with a source for every value; adding
one needs no code.

| Board | Core, clock | RAM, flash | Accelerated kernels | Emulator |
|---|---|---|---|---|
| `esp32` | Xtensa LX6, 240 MHz | 520 KB, 4,096 KB | ESP-NN | none: Renode has no ESP32 platform |
| `s32k144` | Cortex-M4F, 80 MHz | 64 KB, 512 KB | CMSIS-NN | none: Renode has no S32K144 |
| `stm32h743` | Cortex-M7, 480 MHz | 1,024 KB, 2,048 KB | CMSIS-NN | Renode `stm32h743` (Caravan's emulated verification is planned) |

### How far each board has been verified

Verification has three rungs, each with its own label:
- **analysis on your computer:** `estimated`;
- **an emulator:** `emulated`;
- **the physical board:** `measured`.

Compiling the firmware is no rung: it shows the code builds, not how it behaves.

| Board | State | Evidence |
|---|---|---|
| `esp32` | **compiles, not yet run.** The firmware of [part 3 of the tutorial](../intro/tutorial03.md) builds with the example model for `esp32dev`: 62,856 bytes of RAM and 334,717 of flash, both <span class="prov estimated">estimated</span> by the linker (2026-10-27). The firmware workflow repeats the build on every release and on every change to it. No run on a board is recorded yet, so nothing here is <span class="prov measured">measured</span>. | the firmware workflow; `examples/esp32/` |
| `s32k144` | **export only.** Caravan writes the C files and the resolver; no firmware has been compiled for it. | — |
| `stm32h743` | **export only.** As above; emulated verification through Renode is planned. | — |

The fit check before training is `estimated` for every board. It compares lower bounds computed
from the model with the board's flash and RAM.

## The exported model

- **Quantization:** `int8`. Proven by reading the model file's tensors. Inputs are float32 or int32
  raw values, the output float32 after the model's own DEQUANTIZE. `float16` and `none` exist in
  the schema for comparison.
- **Formats:** `flatbuffer` (the `.tflite` file) and `c_array`. `onnx` is refused
  ({rule}`X-1`).
- **Runtime on the board:** TensorFlow Lite Micro. On the ESP32 that is Espressif's
  `esp-tflite-micro` component, version 1.4.1 in the board guide.
- **Operators.** The resolver can register the following, each through its own method in
  TensorFlow Lite Micro:

  `ADD`, `AVERAGE_POOL_2D`, `CAST`, `CONCATENATION`, `CONV_2D`, `DEPTHWISE_CONV_2D`, `DEQUANTIZE`,
  `EQUAL`, `FULLY_CONNECTED`, `LOGISTIC`, `MAXIMUM`, `MAX_POOL_2D`, `MEAN`, `MINIMUM`, `MUL`, `PACK`,
  `PAD`, `QUANTIZE`, `RELU`, `RESHAPE`, `SHAPE`, `SOFTMAX`, `STRIDED_SLICE`, `SUB`, `SUM`, `TANH`,
  `TRANSPOSE`.

  An operator outside this list refuses the export ({rule}`X-4`).
- **Accelerated operators,** from the kernel libraries' sources:
  - ESP-NN accelerates `ADD`, `AVERAGE_POOL_2D`, `CONV_2D`, `DEPTHWISE_CONV_2D`,
    `FULLY_CONNECTED`, `MAX_POOL_2D`, `MUL` and `SOFTMAX`.
  - CMSIS-NN accelerates these plus `PAD`, `TRANSPOSE` and `TRANSPOSE_CONV`.
  - Everything else runs on the runtime's reference kernels.

  `export.json` says, per board, which operators of your model are accelerated.

## Python and installation

| Installation | Python | What it gives |
|---|---|---|
| `caravan-ml` (the core) | 3.13, 3.14, 3.15 | `validate`, `render`, `templates`, `boards` |
| `caravan-ml[verify]` | 3.13, 3.14 | reading and running exported models (`ai-edge-litert`) |
| `caravan-ml[train,verify]` | 3.13 | every command: training and conversion need TensorFlow, which publishes nothing newer yet |

Installed from the GitHub release, not from the package index ([Installation](../intro/install.md)).

## Stages

| Stage | State |
|---|---|
| data, build with the fit check, train, quantize with the int8 gate, export | implemented |
| test windows for a board run | implemented (`export.test_windows`) |
| `analyze`: per-layer memory, latency estimate | planned, v0.2 |
| `verify` through an emulator | planned, v0.3 |
| `bench` on boards, following a public protocol; `card`; `publish` | planned, v1.0 |

## Known limits

- **Exporting needs both extras.** It needs the `train` extra even when training and quantization
  come from the cache, so Python 3.13. Recorded on the [roadmap](../roadmap.md) as deferred by the
  owner.
- **The working-memory figure the export prints is a floor.** A board needs more. The figure that
  counts is the one the runtime reports on the board, which
  [part 3 of the tutorial](../intro/tutorial03.md#what-you-have) prints as `arena: used ...`.
