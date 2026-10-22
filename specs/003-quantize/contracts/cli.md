# Contract: `caravan quantize`

Date: 2026-10-22 · Feature: 003 · Extends [feature 002's CLI contract](../../002-build-and-train/contracts/cli.md)

Everything in the 001 and 002 contracts still holds: the streams, the message form, the exit codes,
the rule that no option skips a rule or lowers a threshold, and the stderr limitation the training
framework imposes. This document adds one verb to the table that contract carries.

## `caravan quantize <manifest>`

Everything `train` does, then converts the trained model, proves what the conversion produced,
measures the cost, and judges it against the manifest's threshold.

| Option | Meaning | Default |
|---|---|---|
| `--runs-dir <path>` | where the run directory is created | `./runs` |
| `--cache-dir <path>` | where stage results are stored | `./.caravan/cache` |
| `--fresh` | ignore cached results and produce them again; recorded | off |
| `--json` | the run's outcome on standard output as one JSON document | off |
| `-q`, `--quiet` | suppress the human summary | off |

There is **no** option that lowers `accuracy_drop_max`, skips the gate, continues past a failed
gate, or keeps the artifact of a failed run. Loosening the budget is an edit to the manifest, where
version control can see it (Principle V).

Human output on success:

```text
picket-mlp-fixture.yaml: quantized int8 — 15,664 bytes from 57,448 (model/quantized.tflite)
    tensors: int8 9, int32 9 — fully integer, input int8 scale 1.000000 zero -128
    calibration: 56 of 500 requested, drawn from 56 available in the train split, seed 42
    test, 12 windows, dataset sha256:8fac6d55c7e…
      trained 0.667  converted 0.667  quantized 0.667
      conversion cost 0.000  quantization cost 0.000  accepted 0.020  → pass
    run: runs/20261022T191204Z-b271d5b3
```

Human output on a failed gate, before the per-layer table:

```text
picket-mlp-fixture.yaml: the accuracy gate failed — quantization cost 0.083, accepted 0.020
    test, 12 windows: converted 0.667 → quantized 0.583
    one changed prediction in 12 windows is 0.083, so this split cannot resolve 0.020
    worst layers by rmse/scale (reference 0.289, the guide flags above 0.7):
      0.94  FULLY_CONNECTED  mlp_1/hidden_1_1/MatMul
      0.41  FULLY_CONNECTED  mlp_1/output_1/MatMul
    no model was written; the table is in quantization-error.csv
    run: runs/20261022T191210Z-b271d5b3
```

The third line of that message is not decoration. A threshold finer than the split can resolve is a
threshold that cannot be judged, and saying so is the difference between a verdict the author can
act on and a number that looks authoritative.

## Exit codes

Unchanged from feature 002, with the gate mapped onto the existing meanings:

| Code | Meaning here |
|---|---|
| 0 | the model was quantized and the gate passed, or the result was reused |
| 1 | a rule said no — an invalid manifest, a run rule of feature 002, or **a failed gate (Q-4)** |
| 2 | usage error |
| 3 | internal failure of the tool itself |
| 4 | the environment is incomplete: the conversion part or the runtime part is not installed |

A failed gate is exit **1**, not a code of its own: it is a budget saying no, which is the same
category of answer as a rule saying no, and the constitution asks only that it be distinguishable
from a crash. The report's `gates` list and the finding's rule identifier are what tell a machine
*which* no it was.

## When a part is missing

Two parts, two messages, both actionable and neither a traceback:

```text
picket-mlp.yaml: quantize needs the train extra to convert, which is not installed
    install it with: pip install "caravan-ml[train,verify]"
```

```text
picket-mlp.yaml: quantize needs the verify extra to measure, which is not installed
    install it with: pip install "caravan-ml[verify]"
    this one installs on every Python caravan supports
```

On Python 3.14 or newer the first becomes the window-and-reason message feature 002 defined, since
no amount of installing will put TensorFlow there.

## What this command never does

- It never writes a quantized model for a run whose gate failed.
- It never reaches the network.
- It never reports a figure about hardware: no latency, no flash, no RAM. The sizes it prints are
  the sizes of files on the machine it ran on, and the accuracies are measured on a desktop
  interpreter. The first claim about a board is the analysis stage's.
- It never computes a compression ratio. Both sizes are there; a ratio reads as a footprint claim
  this stage has no standing to make.
