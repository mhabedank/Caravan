# Quickstart: validating typed features

Figures marked *to be measured* are filled in from the actual run.

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
- the trained and quantized accuracies are *to be measured* (spike: 1.000 / 1.000);
- the model size is *to be measured* (spike: 28,192 B);
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

Expected: int8 accuracy at least 0.918 on 2,947 test windows (*to be measured*), with
standardisation done by the model.
