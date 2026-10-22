# Quickstart: Export

**Feature**: 004 · **Date**: 2026-10-22

How to see this feature work, and how to see it refuse. Everything here runs on the committed
synthetic fixture — no dataset leaves or enters the repository (Principle IX).

## Prerequisites

The proving half needs only the runtime:

```bash
pip install -e ".[verify]"
```

Producing a model to export needs the conversion half as well, and therefore Python 3.13:

```bash
pip install -e ".[train,verify]"
```

If the editable install is older than the extras in `pyproject.toml`, reinstall it: extras are
resolved when the install happens, not when the test runs. A suite that fails on a missing extra
which `pip list` shows as present is this, every time.

## The happy path

```bash
caravan quantize tests/fixtures/manifests/valid/picket-mlp-fixture.yaml
caravan export   tests/fixtures/manifests/valid/picket-mlp-fixture.yaml
```

Expected, on the second command:

- exit 0
- `model/model.tflite`, `model/model_data.cc`, `model/model_data.h`, `model/resolver.h`,
  `runner/{s32k144,stm32h743,esp32}/main.cc` and `export.json` in the run directory
- **three** distinct operators — `RESHAPE`, `FULLY_CONNECTED`, `SOFTMAX` — in **five** nodes (the
  fixture's mlp has three hidden layers, so `FULLY_CONNECTED` accounts for three of the five)
- **14,848 bytes**, down from the 15,664 feature 003 recorded before the batch was fixed (measured
  2026-10-22; the figure was deliberately left unpredicted in this document until the code ran)
- coverage: two of three operators accelerated on every board, `RESHAPE` falling back on all three
- a working-memory floor of **640 bytes**, with its method named and with the sentence saying what
  it omits

## Check the thing most likely to be wrong

The operator set is the one claim where a plausible implementation gives a wrong answer that only
shows up on hardware. Check it against the file directly:

```bash
python - <<'PY'
import json, pathlib
from ai_edge_litert import schema_py_generated as schema
from ai_edge_litert.interpreter import Interpreter

run = sorted(pathlib.Path("runs").iterdir())[-1]
report = json.loads((run / "export.json").read_text())
model = run / "model" / "model.tflite"

names = {v: k for k, v in vars(schema.BuiltinOperator).items() if isinstance(v, int)}
m = schema.Model.GetRootAsModel(bytearray(model.read_bytes()), 0)
codes = [names[m.OperatorCodes(i).BuiltinCode()] for i in range(m.OperatorCodesLength())]

it = Interpreter(model_path=str(model)); it.allocate_tensors()
print("from the file       :", sorted(set(codes)))
print("from the interpreter:", sorted({o["op_name"] for o in it._get_ops_details()}))
print("what the report says:", sorted(o["name"] for o in report["graph"]["operators"]))
PY
```

The interpreter's list contains `DELEGATE`, which exists only on this machine. The report's list
must equal the file's, and must not contain it. That is FR-009, and it is the reason this stage
reads the file.

## Check the C array round-trips

```bash
python - <<'PY'
import pathlib, re
run = sorted(pathlib.Path("runs").iterdir())[-1]
source = (run / "model" / "model_data.cc").read_text()
array = bytes(int(b, 16) for b in re.findall(r"0x([0-9a-fA-F]{2})", source))
print("array bytes equal the model's:", array == (run / "model" / "model.tflite").read_bytes())
print("header declares the same length:",
      f"= {len(array)};" in (run / "model" / "model_data.h").read_text())
PY
```

## Check it is deterministic

```bash
caravan export tests/fixtures/manifests/valid/picket-mlp-fixture.yaml --fresh
# then compare the generated files of the two runs
diff -r runs/<first>/model runs/<second>/model && echo "identical"
```

`--fresh` is what makes this a real check: without it the second run would reuse the cached result
and prove nothing about determinism.

## See it refuse

**A format this version does not implement.** Add `onnx` to `export.formats` in a copy of the
manifest:

```
manifest.yaml: X-1 export.formats names a format caravan cannot produce yet: onnx
    implemented: flatbuffer, c_array
    nothing was written; remove the format or wait for the feature that adds it
```

Exit 1, and — the part worth checking — **no** artifact of the other two formats either. A run that
exported two of three requested formats and exited 0 would be the quiet half-success this project
does not do.

**No model to export.** Run `export` on a manifest that has not been quantized, or whose gate
failed:

```
manifest.yaml: X-2 there is no quantized model in this run to export
    run `caravan quantize` first; a failed accuracy gate leaves nothing exportable
```

**A board naming an unknown accelerated library.** Point a manifest at a board fixture whose
`accel` is a library with no coverage data:

```
manifest.yaml: X-5 board 'xyz' declares accelerated library 'fast-nn', which caravan has no
    sourced kernel coverage for
    add caravan/targets/kernels/fast-nn.yaml with its source and the date it was read
```

Not "unknown" next to every operator. The refusal is the point: a coverage table is a source
somebody read, and that cost is what makes the verdicts worth anything.

## Run the suite the way continuous integration does

```bash
pytest tests -q                                   # everything, with both extras
VIRTUAL_ENV=/tmp/verify-only pytest tests -q      # the proving half, no training framework
```

The second one is the layering rule: reading a model, deriving its operator set, generating the
resolver and the C array, and recording coverage all have to pass with no training framework
installed.
