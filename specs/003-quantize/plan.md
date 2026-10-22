# Implementation Plan: Quantize

**Branch**: `003-quantize` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-quantize/spec.md`

## Summary

One stage and one extra. `caravan quantize` converts the trained model to the quantization the
manifest states, calibrating from the training split; reads the produced file to find out what it
actually contains; measures three accuracies on the test split with the runtime the board will use
a relative of; and fails the run when the loss from quantization exceeds what the manifest accepts,
emitting the per-layer error table on the way out.

The technical approach follows from one measurement and one discovery. The measurement: the
runtime that can read and run an exported model costs **116 MiB and no TensorFlow**, against the
training extra's 1,971 MiB (research R3).
So the feature splits along that line — conversion in the `train` extra on 3.13, everything that
reads or runs a model in a new `verify` extra, anywhere. The discovery: the converter prints
`fully_quantize: 0` while producing a fully int8 model (R2), so the stage's claim about what it
produced is read from the file and never from the tool.

Where this feature differs from its two predecessors is that it is the first with a **gate**. The
run's outcome depends on a number the author wrote, so the mechanics of that number — which two
models are compared, on which split, with what resolution — are the design, not a detail.

## Technical Context

**Language/Version**: Python, floor 3.13 as feature 002 left it. The question the Technical Baseline
left open is now closed: there is no conversion path that avoids the training framework
(`ai-edge-litert` 2.3.0 is a runtime, and the LiteRT conversion docs describe only the TensorFlow
path), so conversion stays on 3.13 and the floor stays. Measurement, by contrast, runs on all three.

**Primary Dependencies**: unchanged in the default installation — `pydantic` and `ruamel.yaml`, 2 of
6. A second extra appears: `verify = ["ai-edge-litert>=2.3; python_version < '3.15'"]` — a marker
like the `train` extra's, with a wider window, because the runtime publishes no cp315 wheel either.
The plan first said "no marker, it installs everywhere"; that was checked against one wheel tag
instead of the index, and the correction is in research R3. That is 2 of the 4 extras the
constitution allows, and the budget is now half spent — the remaining two are benchmarking and publication, exactly as the constitution groups them.

**Storage**: files only. `model/quantized.tflite`, `quantization.json` and, on failure,
`quantization-error.csv` in the run directory; the stage cache of feature 002 holds the result.

**Testing**: `pytest`. The suites split three ways by what they need: `tests/unit` and
`tests/contract` need nothing, `tests/verify` needs the runtime extra (all three Pythons), and
`tests/train` needs both (3.13 only). The acceptance test lives in `tests/train`, because
quantizing requires converting.

**Target Platform**: any machine with a supported Python. Conversion additionally needs 3.13 and the
training extra. No hardware, no emulator, no network.

**Project Type**: single Python package exposing a command line application; two optional extras.

**Performance Goals**: quantize end to end on the fixture in under 60 seconds (SC-001); the measured
figure from the plan's own trial run is in the quickstart. A reused result performs no conversion.

**Constraints**: the gate cannot be silenced by anything (Principle V); the core loads neither
framework; calibration never touches the test split; no figure this stage records describes
hardware.

**Scale/Scope**: one stage, one extra, three quantization settings of which one has a driver, three
accuracies, one gate, one diagnostic table. Roughly 900 lines of implementation and a comparable
amount of test code.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

### Before research

| Principle | Gate | Verdict |
|---|---|---|
| I. Declarative Manifest | Threshold and settings from the manifest only | PASS — the stage receives a projection of seven fields and can read nothing else |
| III. Reproducible by Construction | Provenance, cache, seeded choices | PASS — FR-004 seeds the calibration draw; FR-018 records both tools and the interpreter version; FR-020 to FR-022 extend the cache |
| IV. Measured, Emulated or Estimated | No unlabeled or unverified figure | PASS — and this is the feature where the principle does the most work: FR-006 reads the file rather than the log, FR-019 measures sizes, and no figure here describes hardware |
| V. Budgets Are Gates | A gate that fails the stage and cannot be silenced | PASS — FR-011 to FR-016, including the per-layer table a failure owes the author |
| VI. Compliance Enforced by the Schema | Nothing claimed about data rights | PASS — unchanged; a failed gate leaves no publishable artifact, which publication will later rely on |
| VII. Targets and Templates Are Data | Boards stay data | PASS by absence — `export.targets` is deliberately not in the read set |
| VIII. No Lock-In | Portable artifacts, no network | PASS — a flatbuffer on disk, offline |
| IX. Stable Manifest Contract | No schema churn | PASS — the schema gains no field; all seven values already exist in `caravan/v0` |
| X. Built for Real Models | A named model drives it | PASS — `picket-mlp` drives int8; `float16` and `none` get defined behaviour because the schema accepts them, not because a model asks |
| XI. No Claude in Model Learning | No model data from Claude | PASS — calibration samples come from the author's training split |
| XII. Small Core, Few Dependencies | Budgets, layering, Python policy | PASS — see below |

**Principle XII deserves its own paragraph this time**, because the feature adds an extra and the
principle's whole point is that extras are where weight hides. The addition is justified by
measurement rather than by taste: the alternative is measuring with the interpreter TensorFlow
ships, which that framework itself warns "is deprecated and is scheduled for deletion in TF 2.20",
and which would confine every later stage that reads an exported model to 3.13 and 1,971 MiB. The
new extra is 116 MiB, has no TensorFlow in its graph, reaches one Python version further than the
conversion half, and is what the four stages after this one will use. Two extras of four, and the remaining two are the
groups the constitution already names.

No violations. Complexity Tracking stays empty.

### After design

Re-checked once the design existed. Four things it surfaced:

1. **"The float model" was two different models.** FR-010 compared the quantized model with "the
   float model's accuracy", which is either the trained Keras model or the converted float
   flatbuffer — and the difference between *those two* is a loss caused by conversion. With one
   baseline the two losses are one number, and a threshold on their sum fails runs for the wrong
   reason or passes them while conversion quietly cost something. Resolved by measuring three
   accuracies and gating on the second difference (R7), and the spec was amended rather than left
   ambiguous. **PASS, and it is the design decision of this feature.**
2. **The gate's resolution on the fixture is coarser than its threshold.** Twelve test windows means
   one changed prediction is 0.083, against a threshold of 0.02. A test asserting "the gate passes"
   would be asserting that quantization changed nothing, which is luck rather than a property.
   Resolved by asserting the mechanism on the fixture and gating the *threshold arithmetic* in unit
   tests, where any resolution can be constructed. **PASS, with the limitation recorded in the
   spec's Assumptions rather than hidden in a test.**
3. **The per-layer table would have been produced on every run.** It costs a second instrumented
   conversion and one inference per calibration sample. Produced only on failure, which is also
   what the constitution asks for — a failed gate must emit what is needed to act on it, and a
   passing run has nothing to act on. **PASS.**
4. **Principle IV cuts against a tempting number.** A compression ratio — "4.1× smaller" — is the
   obvious headline and it reads as a footprint claim, which this stage has no standing to make.
   Both sizes are recorded, measured, and no ratio is computed (R9). The flash figure a board needs
   belongs to the analysis stage. **PASS.**

No deviation. One spec amendment, made in the open.

## Project Structure

### Documentation (this feature)

```text
specs/003-quantize/
├── spec.md                 # Feature specification
├── plan.md                 # This file
├── research.md             # Phase 0: R1–R12, each one an experiment
├── data-model.md           # Phase 1: entities, validation rules
├── quickstart.md           # Phase 1: runnable validation scenarios
├── contracts/
│   ├── cli.md              # the quantize verb, its output, the gate's exit code
│   ├── quantized-model.md  # what is produced, and what is read back from it
│   └── gate.md             # the accuracy gate: the three numbers, the arithmetic, the table
├── checklists/
│   └── requirements.md     # Specification quality checklist
└── tasks.md                # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
pyproject.toml                       # the verify extra; pytest marker for the runtime
src/caravan/
├── env.py                           #   gains the runtime's presence check and its message
├── cli/
│   ├── main.py                      #   gains the quantize verb
│   └── quantize.py                  # NEW
├── stages/
│   └── quantize.py                  # NEW — spec, conversion, the gate, the table
├── convert/                         # NEW — conversion, extra `train`, Python 3.13
│   ├── __init__.py
│   ├── tflite.py                    #   the converter options per quantization setting
│   └── debugger.py                  #   the per-layer table, on failure only
├── runtime/                         # NEW — reading and running a model, extra `verify`
│   ├── __init__.py
│   ├── inspect.py                   #   tensor types, scales, zero points — read from the file
│   └── measure.py                   #   quantise the input, run, count, confusion matrix
└── run/
    └── report.py                    #   gains the quantization and gate sections

tests/
├── unit/                            # the gate arithmetic, the calibration draw, the ranking
├── contract/                        # the verb's surface, exit codes, no silencing option
├── verify/                          # NEW — needs the runtime extra only; all three Pythons
│   └── conftest.py                  #   importorskip on the runtime
├── train/                           # the acceptance test and the conversion tests
└── layering/                        # extended: neither framework reachable from the core
```

**Structure Decision**: `convert/` and `runtime/` are separate packages because they are separately
installable, and the directory layout should say so. A reader looking at `runtime/` should be able
to tell, without reading imports, that nothing in it may touch the training framework — and the
layering test asserts exactly that per directory rather than per module.

`stages/quantize.py` stays core and framework-free, loading its halves by name when it runs, which
is the pattern feature 002 established: importing a stage must not import what the stage uses.

## Complexity Tracking

No constitution violations to justify. The one addition that needed an argument — a second extra —
is argued with two measurements in research R3 and a deprecation notice from the framework itself,
not with a preference.
