# Quickstart: Validating Quantize

Date: 2026-10-22 · Feature: 003

Each scenario maps to a success criterion of [spec.md](./spec.md). Details live in the contracts;
this is the run guide.

## Prerequisites

Two extras, and they do not need the same Python:

```bash
# Converting needs the training framework, so Python 3.13
uv venv --python 3.13 .venv313
uv pip install --python .venv313 -e ".[train,verify]"

# Measuring needs only the runtime — any supported Python, 114 MiB
uv pip install -e ".[verify]"
```

The second line is the point of the split: a contributor who only wants to read or run an exported
model does not install 1,971 MiB to do it.

## 1 — Quantize the pilot model (SC-001, SC-002)

```bash
time caravan quantize tests/fixtures/manifests/valid/picket-mlp-fixture.yaml
```

Expect: exit 0 within the 60-second budget; `model/quantized.tflite` and `quantization.json` in the
run directory; and the summary of [contracts/cli.md](./contracts/cli.md) — the size, the tensor
counts, the calibration line, the three accuracies and the verdict.

## 2 — Prove it is really int8, without believing the report (SC-004)

```bash
python - <<'PY'
import glob, collections
from ai_edge_litert.interpreter import Interpreter
interp = Interpreter(model_path=glob.glob("runs/*/model/quantized.tflite")[-1])
interp.allocate_tensors()
print(collections.Counter(d["dtype"].__name__ for d in interp.get_tensor_details()))
print(interp.get_input_details()[0]["dtype"], interp.get_input_details()[0]["quantization"])
PY
```

Expect: every tensor `int8` or `int32`, input `int8` with a scale and a zero point — and the same
numbers the report claims. This is the scenario that matters most: the converter prints
`fully_quantize: 0` for exactly this model, so the only trustworthy source is the file.

## 3 — A failing gate leaves nothing behind and explains itself (SC-005)

```bash
sed 's/accuracy_drop_max: 0.02/accuracy_drop_max: 0.0/' \
  tests/fixtures/manifests/valid/picket-mlp-fixture.yaml > /tmp/tight.yaml
caravan quantize /tmp/tight.yaml ; echo "exit: $?"
```

A threshold of zero accepts no loss at all, so the gate fails on any change. Expect: exit 1; no
`model/quantized.tflite` in that run directory; `quantization-error.csv` present; and the report
carrying a `Q-4` finding, a failed `accuracy` gate entry, and the per-layer table ordered worst
first with the 0.289 reference stated.

## 4 — Nothing can silence the gate (SC-006)

```bash
caravan quantize --help | grep -iE 'force|skip|ignore|allow|disable|override|threshold|accuracy'
uv run pytest tests/contract/test_no_skip_option.py -q
```

Expect: no output from the first command, and the contract test passing. The threshold comes from
the manifest's resolved form and from nowhere else.

## 5 — What retrains, what re-quantizes, and what does neither (SC-007)

| Change | Expected |
|---|---|
| `compliance.intended_use` | all three stages reused |
| `export.targets` | all three reused — this stage does not read it |
| `export.accuracy_drop_max` | build and train reused, quantize produced |
| `export.quantization` | build and train reused, quantize produced |
| `dataset.representative_samples` | build and train reused, quantize produced |
| `train.seed` | all three produced |
| a byte of the dataset | all three produced |

```bash
jq '.stages[] | {name, outcome}' runs/*/report.json | tail -6
```

## 6 — Measuring works with no training framework (SC-008)

```bash
uv run --python 3.15 pytest tests/verify -q          # the runtime extra only
uv run --python 3.15 python -c "
import sys, caravan.stages.quantize, caravan.runtime.measure
print([m for m in sys.modules if m.split('.')[0] in {'tensorflow','keras'}])"
```

Expect: the measurement tests pass on 3.15, where TensorFlow cannot even be installed, and the
printed list is empty — including after importing the stage, because a stage must not import what
it loads by name.

## 7 — A missing part is answered, not crashed (SC-009)

```bash
uv build
uv venv --python 3.14 /tmp/no-extras
VIRTUAL_ENV=/tmp/no-extras uv pip install dist/caravan_ml-*.whl
/tmp/no-extras/bin/caravan quantize picket-mlp.yaml ; echo "exit: $?"
```

Expect: exit 4, a message naming the part and the Python it installs on, no traceback, and no run
directory left behind.

## 8 — The budgets still hold (SC-010)

```bash
uv run pytest tests/layering -q
```

Expect: two extras of the four allowed, every dependency of the train extra still carrying its
Python marker, the verify extra carrying none because it installs everywhere, and the default
installation still pulling neither framework.
