# Quickstart: Declared Inputs and Outputs, and a Lean Manifest

**Feature**: 006 · **Date**: 2026-10-23

How to see this feature work, and how to see it refuse. Everything here runs on the committed
synthetic fixture.

The figures below were left blank in the plan and filled in from the first run of the code
(2026-10-23, TF 2.21.0, Keras 3.15.1, ai-edge-litert 2.3.0), as feature 004 did.

## Prerequisites

```bash
pip install -e ".[train,verify]"   # Python 3.13; the core scenarios need no extra at all
```

## 1. The old pilot still loads, and says what changed

```bash
caravan validate tests/fixtures/manifests/valid/picket-mlp.yaml
```

Expected:
- exit 0;
- `valid (migrated from caravan/v0 to caravan/v0.1)`;
- six `dropped` notices: `model.topic`, `model.task`, `compliance`, `verify`, `bench`, `publish`;
- three `moved` notices: `dataset.window`, `dataset.labels`, `export.accuracy_drop_max`;
- the file is unchanged afterwards (`git diff --exit-code` on it).

No extra is needed: migration and validation are core.

## 2. The new pilot validates, and render shows what will be derived

```bash
caravan validate tests/fixtures/manifests/valid/picket-mlp-v01.yaml
caravan render   tests/fixtures/manifests/valid/picket-mlp-v01.yaml
```

Expected:
- exit 0, with no notices;
- `columns: derived` and `labels: derived` in the rendered YAML;
- 33 non-blank, non-comment lines in the manifest (SC-001), the budget stated.

## 3. Refusals at validation

| Fixture under `tests/fixtures/manifests/invalid/` | Expected |
|---|---|
| `v01-removed-compliance.yaml` | exit 1, at `compliance`: "removed in caravan/v0.1: …" |
| `v01-two-inputs.yaml` | exit 1, CF-10 at `inputs`, naming the research note |
| `v01-label-as-input.yaml` | exit 1, CF-11 at `inputs[0].columns` |
| `v01-name-with-hyphen.yaml` | exit 1, CF-9 at `inputs[0].name` |

## 4. The whole pipeline on the new form

```bash
caravan export tests/fixtures/manifests/valid/picket-mlp-v01.yaml
```

Expected in the run directory, in addition to feature 004's set:
- `data/schema.json`:
  - `labels: [dos, fuzzy, normal, replay]` with `labels_source: derived`;
  - `input_columns` = every column but `label`, in file order;
- `resolved.yaml` holding those values in place of `derived`;
- `model/fit.json`:
  - `provenance: estimated`, with both floors and three `below` verdicts per resource;
  - flash floor **11,024 bytes** (kernels and biases of `hidden_1`, `hidden_2`, `output`);
  - RAM floor **352 bytes** (`hidden_1`: 320 in + 32 out), at most the export's floor of
    **640 bytes**;
  - the model file is **14,856 bytes**, 8 more than feature 004's 14,848: the signature now
    carries the declared names `frames` and `attack`;
  - the input's scale is **8.016**: one int8 step covers 8 units of raw data, so the payload
    columns (0 to 255) keep about 32 steps. That is the cause of research R11;
- `model/interface.json`:
  - input `frames` at position 0, output `attack` at position 0;
  - element type `int8`, with scales and zero points read from the file;
  - `scaling: none`;
- `model/model_data.h`:
  - `g_model_data_input_frames`, `g_model_data_output_attack`, `…_label_count = 4`;
  - the label array in `model_data.cc`;
- in each runner skeleton, `interpreter.input(g_model_data_input_frames)` and no literal index.

Run it twice: the second run reuses every stage, reads no data (the report's dataset section has no
`records`), and the interface files are byte-identical.

## 5. Feed the model from the contract alone (SC-005)

```bash
pytest tests/verify/test_interface_contract_alone.py
```

The test reads only `interface.json` and the header. It turns 64 raw records into the input tensor,
using `columns`, `window`, `scale` and `zero_point`, runs the model in the desktop runtime at the
contract's `position`, and maps the arg-max to a label. It asserts the same prediction Caravan's own
evaluation makes, on every test window of the fixture.

## 6. A model that cannot fit stops before training

```bash
caravan train tests/fixtures/manifests/gate/too-big-for-s32k144.yaml
```

Expected:
- exit 1, rule F-1;
- the board, the resource, the floor, the board's figure and the shortfall;
- no `model/trained.keras` and no training history in the run directory.

The fixture asks for an mlp wide enough that its weights alone exceed 512 KiB of flash.

## 7. Same weights through either form (SC-003)

```bash
pytest tests/train/test_migration_same_model.py
```

It trains the migrated pilot fixture, and a new-form copy that pins `normal, dos, fuzzy, replay`,
under the same seed, and compares the trained weights byte for byte.

## 8. Changing the boards does not retrain

Remove `esp32` from `export.targets` in a copy of the new pilot, and run `caravan export` on it
after scenario 4. Expected: `data`, `build`, `train` and `quantize` are reused; `fit` and `export`
run (Principle III; research R6).
