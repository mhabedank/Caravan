# Quickstart: validating feature 010

Runnable checks that the three additions work end to end. Each uses a committed synthetic fixture;
no real dataset is needed. Details of fields and messages are in [data-model.md](data-model.md) and
[contracts/rules.md](contracts/rules.md).

## Prerequisites

```bash
uv sync --python 3.13 --extra train --extra verify
```

## 1. The templates are registered (core only)

```bash
caravan templates
```

Expected: `autoencoder`, `conv1d`, `conv2d`, `mlp`, each with its summary. The same command in an
installation without extras lists the same four (SC-009).

## 2. Anomaly detection from normal data (User Story 1)

```bash
caravan validate examples/anomaly-autoencoder.yaml
caravan export examples/anomaly-autoencoder.yaml
```

Expected:
- `metrics.json` gives `auc` on `val` and `test` and the window counts per condition;
- `quantization.json` has a `gate` with `metric: auc` and `verdict: pass`, a `threshold` computed on
  validation normals, and `detection` rates on the test part;
- `model/interface.json` has one output of type `anomaly`, `decision: threshold`, the threshold, and
  `abnormal_when: score >= threshold`.

Gate failure: a copy of the manifest with `auc_drop_max: 0` (or a budget below the measured drop)
fails at quantize with Q-4 and leaves no model (SC-002).

## 3. A plane of feature frames (User Story 2)

```bash
caravan validate examples/frames-conv2d.yaml
caravan export examples/frames-conv2d.yaml
```

Expected: the build report's input shape is (12, 8) and the first layer reshapes it to (12, 8, 1);
the export's operator set contains CONV_2D, DEPTHWISE_CONV_2D and AVERAGE_POOL_2D, each accelerated on
all three boards; the gate passes.

Refusal: setting a block's kernel to `[3, 9]` is refused at validation with CF-6 on the columns axis.

## 4. Images (User Story 3)

```bash
caravan validate examples/images-conv2d.yaml
caravan export examples/images-conv2d.yaml
```

Expected:
- the resolved manifest shows `height: 16, width: 16, num_channels: 3` taken from the data;
- `model/interface.json` gives the input as uint8 [1, 16, 16, 3], scale 1.0, zero point 0;
- `model/test_windows.h` holds `uint8_t` images;
- the gate passes.

Refusals (each a fixture or a test): a second input beside the image (CF-19); a window with an image
(CF-19); `template: mlp` with an image (CF-19); a missing image file (DS-17).

## 5. The reference shapes (build and fit check only)

```bash
uv run pytest tests/train/test_reference_shapes.py -q
```

Expected: `hum-fan`'s architecture builds with 35,280 parameters (SC-003); the keyword-spotting
reference with 24,908 (SC-006); MobileNetV1 at width 0.25 with the count computed from its blocks,
and the fit check refuses it on `s32k144` before training (SC-013).

## 6. The whole suite and the gates

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
```

The layering tests prove no framework is imported by the core; the budget tests prove no
dependency or extra was added (SC-011).
