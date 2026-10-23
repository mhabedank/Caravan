# Contract: the fit check before training

Stage `fit`, between `build` and `train`. Its upstream is `build`. It reads `export.targets` and
`export.quantization` (data model, *Stages*).

## What it computes

Two lower bounds, by the method in research R6. Only layers certain to remain operators of their
own after conversion are counted.

| Floor | Counted layers | Element size by `export.quantization` |
|---|---|---|
| flash: weight floor | Dense, Conv (kernel and bias) | int8: kernel 1, bias 4 · float16: 2 / 2 · none: 4 / 4 |
| ram: working-memory floor | Dense, Conv, pooling, global pooling (input + output elements; the largest one) | int8: 1 · float16: 4 · none: 4 |

Not counted, because each may vanish, be fused or run in place: Flatten, Reshape, Dropout,
normalisation and stand-alone activation layers. Counting any of them could make a floor exceed
the true need, and then the check could stop a model that fits.

## What it decides

| Per board and resource | Outcome |
|---|---|
| floor ≤ the board's figure × 1024 | `below`, recorded |
| floor > the board's figure × 1024 | `exceeds`, recorded with the shortfall |
| any `exceeds` | rule **F-1**: the stage fails, exit code 1, nothing is trained |

The board's figure is `flash_kb` or `ram_kb` from its description, with the source the description
records (Principle VII). A missing figure fails the board, as unknown is not within budget. The
board schema makes that case unreachable today (research R6).

## F-1, as printed

```text
picket-mlp.yaml: export.targets — the built model cannot fit 1 target board before any training:
    s32k144 ram: the working-memory floor is 70,000 bytes and the board has 65,536 (short by 4,464)
    method: largest input + output of a Dense, Conv or pooling layer at 1 byte (int8); layer conv_1
    a floor is a lower bound: no training can make this model fit that board
```

## `model/fit.json` on a pass

```json
{
  "provenance": "estimated",
  "quantization": "int8",
  "floors": [
    {"resource": "flash", "floor_bytes": 6000, "method": "...", "counted_layers": ["hidden_1", "hidden_2", "output"]},
    {"resource": "ram", "floor_bytes": 416, "method": "...", "counted_layers": ["hidden_1"]}
  ],
  "verdicts": [
    {"board": "s32k144", "resource": "flash", "floor_bytes": 6000, "board_bytes": 524288,
     "board_source": "...", "verdict": "below"}
  ],
  "not_a_fit_claim": "A pass means only that no lower bound exceeds a board. Whether the model fits is established after quantization and by emulated verification."
}
```

The numbers are illustrative. The run report gains a `fit` section built from this file, as it has a
quantization section built from `quantization.json`.

## What it may not do

- Override, relax or pre-empt the later footprint gate (FR-020). A model that passes here and fails
  later has failed.
- Offer an option that skips it. The existing test that no command has a skip flag
  (`tests/contract/test_no_skip_option.py`) covers the new stage.
- Report a figure without the label `estimated` (Principle IV).

## Its own check

A test asserts, for both pilot templates, that the working-memory floor here is at most the
working-memory floor the export computes from the converted graph (feature 004). If that ever
fails, one of the two is no longer a lower bound.
