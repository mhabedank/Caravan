# Phase 0 Research: Quantize

Date: 2026-10-22 · Feature: 003 · Input: [spec.md](./spec.md)

Every claim below was produced by running the thing, on this machine, on 2026-10-22, against the
model feature 002 trains from the pilot manifest. Where a number came from a document instead, the
document is named and quoted.

## R1 — How the conversion is invoked

**Decision**: `tf.lite.TFLiteConverter.from_keras_model(model)` with `optimizations`, a
`representative_dataset`, `target_spec.supported_ops` restricted to the integer builtins, and
`inference_input_type` / `inference_output_type` set to int8.

**Evidence**: both documented paths were run on the trained pilot model and produced **the same
15,664 bytes**:

| Path | Result |
|---|---|
| `from_keras_model(model)` | 15,664 bytes |
| `model.export(dir)` then `from_saved_model(dir)` | 15,664 bytes |

`from_keras_model` exports a temporary saved model internally — it prints the same "Saved artifact
at /tmp/…" line — so the second path only moves that step into the project's own code.

**Rationale**: identical output, one fewer artifact to manage, and no temporary directory of ours to
clean up. **Alternatives considered**: the explicit export (rejected: more code, same bytes); the
`tflite_convert` command line (rejected: it cannot take a representative dataset, so it cannot do
int8 at all).

## R2 — Proving what was produced, without asking the converter

**Decision**: read the produced file with the runtime's own interpreter and record what *it* says:
every tensor's type, and the input and output type with scale and zero point.

**Evidence** — this is the finding the feature is built around. The converter prints:

```text
fully_quantize: 0, inference_type: 6, input_inference_type: INT8, output_inference_type: INT8
```

`fully_quantize: 0` reads like a verdict and is not one. Reading the produced file:

```text
input : int8 (1, 64, 5)  quant (0.9999967217445374, -128)
output: int8 (1, 4)      quant (0.00390625, -128)
tensor dtypes: {'int8': 9, 'int32': 9}      ← no float32 tensor anywhere
weights: mlp_1/hidden_1_1/MatMul int8 [32 320], mlp_1/output_1/MatMul int8 [4 16], …
```

Every tensor is int8 or int32 (the biases), the weights are int8, the input and output carry a
scale and a zero point. The model is fully quantized and the log line says the opposite.

**Rationale**: Principle IV in its sharpest form. A stage that reported "int8" because a library
printed something would be making exactly the unverified claim the principle exists to prevent —
and here the library's output would have led it to report the *wrong* thing.

**Alternatives considered**: parsing the flatbuffer through a pinned schema binding, which the
Technical Baseline names as the mechanism for footprint analysis (deferred: that arrives with the
analysis stage, and the interpreter already answers this question without a new dependency);
trusting `inference_input_type` from the conversion (rejected by the evidence above).

## R3 — The measurement extra

**Decision**: a second extra carrying `ai-edge-litert`, named `verify` after the stage group
Principle XII lists, not after the package. Conversion stays in `train`. 2 of the 4 extras the
constitution allows.

**Evidence**, both measured on 2026-10-22:

| | `train` extra | the measurement extra |
|---|---|---|
| Installed size | 1,971 MiB | **114 MiB** |
| Packages | 41 | **8** |
| Python | 3.13 only | 3.13 and **3.14** — not 3.15 |
| TensorFlow | yes | **no** |

On Python 3.14, with no TensorFlow installed or importable, the runtime read the int8 model's
tensor details and ran inference on it:

```text
python 3.14.6 · tensorflow imported? False
input : int8 (1, 64, 5) quant (0.9999967217445374, -128)
prediction: [[127 -128 -128 -128]] -> 0
still no tensorflow? True
```

**Correction, made after this section was first written.** It claimed the runtime "installs on
every Python this project supports". It does not: `ai-edge-litert` publishes cp310 through cp314
and **no cp315**, in 2.3.0 and in every recent version (checked against the index). The claim came
from verifying cp314 and assuming the next one followed — which is the kind of unverified step
this project's own rules exist against, so it is recorded here rather than quietly fixed. The extra
therefore carries a Python marker like `train` does, with a wider window, and the stage says so on
3.15 instead of letting a resolver fail.

**Rationale**, which survives the correction because it never rested mainly on Python coverage:
the interpreter TensorFlow ships warns that it "is deprecated and is scheduled for deletion in TF
2.20" — we are on 2.21, so the project would be building on something already announced as leaving.
And every stage after this one reads an exported model: analysis, emulated verification, the
benchmark, the card. Settling it here means they inherit it rather than each solving it again, and
they inherit it at 116 MiB rather than 1,971. Covering two of three Pythons instead of one is a
bonus, not the case.

**On the name**: `litert` was rejected because the Technical Baseline forbids vendor product names
for identifiers that outlive a release, and an extra's name is one — this is the second rename of
this product in two years. `analyze` was rejected because the constitution's extras are grouped as
training, verification, benchmarking and publication, and this is the verification group. That the
`verify` *stage* will later live behind the same extra is the point, not a collision.

**The cost, stated**: `caravan quantize` needs both extras, because it converts and measures.
`caravan-ml[train,verify]` on 3.13 to quantize; `caravan-ml[verify]` on any supported Python to
measure or read an exported model.

## R4 — Feeding an integer model

**Decision**: quantize the input with the model's **own** scale and zero point before feeding it —
`clip(round(x / scale) + zero_point, -128, 127)` as int8 — and take the arg-max of the int8 output
without dequantizing it.

**Rationale**: an int8 input tensor handed float data is not an error, it is a silent
misinterpretation of the bytes, and the accuracy figure that comes out would be nonsense that looks
like a measurement. The scale and zero point come from the file (R2), never from the data.
Dequantizing the output is unnecessary for a class decision because dequantization is monotonic;
it *is* necessary if a probability is ever reported, which this feature does not do.

**Alternatives considered**: converting with float input and output and letting the runtime quantize
internally (rejected: the deployed model on the board takes int8, so measuring a float-I/O variant
would measure something nobody deploys).

## R5 — Calibration

**Decision**: draw calibration samples from the **training split only**, with
`random.Random(train.seed)`, capped by what the split holds, and record requested, used and
available. The generator yields one sample at a time, shaped as the model's input.

**Rationale**: calibrating on the test split would make the accuracy comparison meaningless — the
quantization would have been fitted to the data it is then judged on. Capping rather than refusing
is argued in the spec's Assumptions: the arbiter of whether calibration was enough is the accuracy
gate, which is already there.

**What this means on the fixture**: the pilot manifest asks for 500 and the fixture's training
split holds 56. All 56 are used and all three numbers are recorded. The real dataset has thousands
of windows, where the cap never binds.

## R6 — The per-layer error table

**Decision**: `tf.lite.experimental.QuantizationDebugger`, run **only when the gate fails**, ranked
by `rmse / scale` descending.

**Evidence**: the debugger exists in TensorFlow 2.21 and produced a real table for the pilot model:

```text
columns: op_name,tensor_idx,num_elements,stddev,mean_error,max_abs_error,
         mean_squared_error,scale,zero_point,tensor_name
rows:    RESHAPE · FULLY_CONNECTED ×3 · SOFTMAX
```

**On the ranking metric**, from the LiteRT quantization-debugger guide: "The `RMSE / scale` is close
to `1 / sqrt(12)` (~ 0.289) when quantized distribution is similar", and "The larger the value is,
it's more likely for the layer not being quantized well." The guide's own example flags layers above
0.7 as candidates for selective quantization.

So the table reports `rmse / scale` per layer with 0.289 named as the reference, and **does not turn
either number into a gate of its own**. The gate is the author's `accuracy_drop_max`; these values
are the evidence that lets them act on a failure, which is what Principle V asks a failed gate to
emit.

**Cost, stated**: the debugger performs a second, instrumented conversion and runs the model once
per calibration sample. That is why it runs on failure only — a routine cost on every successful
run would be paid by everyone to serve nobody.

**Risk, recorded**: the debugger uses the deprecated interpreter internally (it emits the same
deletion warning). If a future TensorFlow removes it, the per-layer table needs a new source, and
the obvious candidate is computing it ourselves from per-layer outputs. That is a real piece of work
and it is not this feature's.

## R7 — Which float accuracy the gate compares against

**Decision**: measure **three** accuracies on the test split, and gate on the third difference:

| Number | Measured with | What it answers |
|---|---|---|
| the trained model's | the training framework, Keras | what training achieved |
| the converted float model's | the runtime | what *conversion* cost |
| the quantized model's | the runtime | what the deployed model does |

The gate is `float flatbuffer → quantized`, because that difference isolates quantization, which is
what `accuracy_drop_max` is about ("the maximum accuracy loss accepted from quantization",
Principle V). The trained-to-converted difference is recorded beside it.

**Rationale**: with one baseline, a loss caused by conversion and a loss caused by quantization are
indistinguishable, and a gate on their sum would fail runs for the wrong reason — or pass them while
conversion quietly cost something. Two differences cost one extra conversion of a tiny model and one
extra measurement pass, and they separate two questions that have different answers and different
fixes. For `quantization: none` the second and third models are the same and the gated difference is
zero by construction, which is the correct reading of "no quantization, no quantization loss".

**This refines FR-010**, which says "the float model's accuracy": the spec is updated to name which
float model the gate uses, because "the float model" is ambiguous between the two and the difference
between them is the thing worth separating.

## R8 — The two settings no model asks for

**Decision**: `float16` converts with float16 weights and records the types the file actually
contains; `none` converts without quantization. Both are measured and gated exactly like int8. The
stage never describes a model as int8 unless the file says int8 (FR-009).

**Rationale**: the schema already accepts all three, so a manifest can state them and a stage that
crashed on two of three would be a schema contract that is not kept. Implementing them is a branch
in the converter's options, not a feature. Principle X is satisfied by *driving* on int8: only int8
has a named model, and the other two get behaviour rather than attention.

## R9 — Sizes

**Decision**: both the trained model's and the quantized model's size in bytes come from the
filesystem, recorded next to each other. No compression ratio is reported as a headline.

**Rationale**: Principle IV — a size that is measured is worth printing; a ratio invites being read
as a footprint claim, and the flash a board needs is the analysis stage's figure, not this one's.
The number here is honest about being the size of a file on a laptop.

## R10 — What the stage reads

**Decision**:

- `reads` = `export.quantization`, `export.accuracy_drop_max`, `dataset.representative_samples`,
  `dataset.split`, `dataset.labels`, `dataset.window`, `train.seed`
- `reads_dataset` = true, `upstream` = `train`
- **not** read: `export.targets`, `export.formats`, everything in `compliance`, `publish`, `bench`
  and `verify`

**Rationale**: the projection of feature 002 means a field the stage needs and did not declare is
missing the moment it runs, so this list is checked by the code rather than by review. `targets` is
deliberately out: adding a board must not re-quantize, because the quantized model does not depend
on which boards it is destined for. `train.seed` is in, because it chooses the calibration samples.

## R11 — Continuous integration

**Decision**: a job of its own, `measure`, on a 3.13 and 3.14 matrix, installing `.[verify]` and
running `tests/verify`. The `test` matrix stays free of extras on all three Pythons, the `train`
job installs `.[train,verify]` and runs everything, and `clean-environment` is untouched.

**Rationale**: the first plan put the verify extra into the `test` matrix, which cannot work — on
3.15 the extra does not resolve, so the job would fail to install before running anything. The
window the extra actually has is what decides the matrix, which is the shape of the correction
above: a claim about where something runs has to be built from where it installs, not the other way
round. The one job that must stay free of both extras is `clean-environment`, and it does.

## R12 — Where the quantized model goes

**Decision**: `model/quantized.tflite` in the run directory, with `quantization.json` beside it
carrying the tensor record, the three accuracies, the calibration counts and the verdict. The
per-layer table, when there is one, goes into `quantization-error.csv` as the debugger's own
columns plus the computed `rmse_over_scale`, and into the report.

**Rationale**: the same shape feature 002 used — the stage writes one machine-readable artifact that
the report is built from, so a *reused* result reports the same numbers as the run that produced it.
The error table is a separate file because it exists only sometimes, and because its natural form is
a table a person may want to open in something else.

**Naming**: `quantized.tflite` uses the file extension the format actually has; the *format
identifier* in the manifest stays `flatbuffer`, which is the vendor-neutral name the constitution
requires for identifiers that outlive a release.
