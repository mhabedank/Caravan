# Quickstart: validating typed features

Figures are from the runs of 2026-10-24 (Python 3.13.16, TF 2.21.0, ai-edge-litert 2.3.0).

## 1. The previous form is refused

```bash
caravan validate tests/fixtures/manifests/invalid/v-1-previous-version.yaml   # a v0.1 manifest
```

Expected: exit 1, V-1 at `apiVersion`, naming `caravan/v0.2` and `docs/manifest-changes.md`.

## 2. The typed pilot reads like Ludwig

```bash
caravan validate examples/picket-mlp.yaml
caravan render examples/picket-mlp.yaml --stdout
```

Expected:
- valid;
- `render` lists every feature with its full preprocessing and encoder;
- the defaults are resolved in.

## 3. Derived labels pass int8 (SC-003)

```bash
caravan export examples/picket-mlp.yaml
```

Expected:
- the gate passes with derived labels;
- trained 1.000, converted 1.000, quantized 1.000 on the 12 test windows (spike: 1.000 / 1.000);
- the model is 27,608 B, 12 distinct operators in 32 nodes (spike: 28,192 B with the unknown slot
  computed in float; the RELU anchor of research R3 keeps the one-hot in int8);
- `data.ignored_columns` is empty, and `data.features` shows the fitted values from the training
  part.

## 4. Raw values in, same answers out (SC-004)

```bash
pytest tests/train/test_typed_pilot.py
```

It feeds the exported model raw CSV values by input name and compares with the trained model on the
test windows.

## 5. Unknown codes and the input order

```bash
pytest tests/train/test_preprocessing_layers.py tests/train/test_input_order.py
```

Expected:
- a code never seen in training lands in the unknown slot;
- the converter reorders the five inputs;
- calibration and the contract follow the names.

## 6. Binary and number outputs (SC-007)

```bash
pytest tests/train/test_output_types.py
```

Expected:
- each trains, passes its own budget (accuracy for `binary`, MAE increase for `number`) and
  exports;
- the decision is in the contract.

## 7. The pace-cnn port in the new form (SC-006)

```bash
python ports/pace-cnn/convert.py <archive> <out>        # writes raw values, no standardisation
caravan export ports/pace-cnn/pace-cnn.yaml
```

Expected: int8 accuracy at least 0.918 on 2,947 test windows, with standardisation done by the
model. Measured: 0.9169 with the manifest's seed 0 (trained 0.9087), 0.927 to 0.933 with seeds 1
to 3; 24,776 B. SC-006 is missed by three windows with seed 0 and met by every other seed tried
(research R16).
