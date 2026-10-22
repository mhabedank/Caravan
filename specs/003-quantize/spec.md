# Feature Specification: Quantize

**Feature Branch**: `003-quantize`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: the int8 conversion and the accuracy gate — convert the trained model
to the quantization the manifest states, prove the result is actually quantized, measure what it
cost on the test split, and fail the run when the cost exceeds what the manifest accepts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a deployable model, or a reason why not (Priority: P1)

The author has a trained model and a manifest that states what accuracy loss they accept. They run
one command and get either a quantized model with both accuracy figures recorded, or a failed run
that says how much accuracy the quantization cost and which layer lost it.

**Why this priority**: this is the stage that turns a trained model into something a
microcontroller can run, and it is the first stage with a *budget* in the constitution's sense —
a number in the manifest that decides whether the run produces an artifact at all. Everything
after it (export, analysis, verification, the card) reads what this stage writes.

**Independent Test**: quantize the pilot manifest against the synthetic fixture and confirm the
quantized model, both accuracy figures, the verdict, and the per-layer table when the gate fails.

**Acceptance Scenarios**:

1. **Given** a trained model and a manifest stating int8 and an accepted accuracy drop, **When**
   the author quantizes, **Then** the run directory holds the quantized model, and the report
   records the trained, converted and quantized accuracies, both differences, the threshold and the
   verdict.
2. **Given** that run, **When** the author reads the report, **Then** both accuracy figures name
   the split and the dataset version they were measured on, and the calibration record says how
   many samples were requested, how many were used and which split they came from.
3. **Given** a quantization that costs more accuracy than the manifest accepts, **When** the
   author quantizes, **Then** the run fails with a non-zero status, no quantized model is left
   behind, and the report carries the per-layer error table.
4. **Given** a manifest that states no quantization, **When** the author quantizes, **Then** the
   conversion still runs, the drop is reported as zero against the same measurement, and the gate
   passes — a stage that is asked for no quantization does not become a stage that does nothing.

---

### User Story 2 - Trust that it is really int8 (Priority: P1)

The author wants to know the model is genuinely quantized — every weight an integer, the input and
output integer with a scale and a zero point — because a model that is only partly quantized will
not fit the board it was built for, and will not say so.

**Why this priority**: as high as the gate, and for the same reason. The converter prints
`fully_quantize: 0` while producing a fully int8 model (checked 2026-10-22), so its own output
cannot be read as a verdict. A stage that reported "int8" because a library said so would be
making exactly the unverified claim Principle IV exists to prevent.

**Independent Test**: quantize the pilot manifest, then inspect the produced model's tensors
independently of the converter and confirm the report's claim matches what the file contains.

**Acceptance Scenarios**:

1. **Given** a manifest stating int8, **When** the quantized model is produced, **Then** the
   report records every tensor's type, the input and output types, and their scale and zero point,
   read from the produced file rather than from the conversion's output.
2. **Given** a conversion that leaves a floating-point tensor in a model declared int8, **When**
   the stage checks the result, **Then** the run fails naming the tensors that are not integers.
3. **Given** a manifest stating float16, **When** the model is produced, **Then** the recorded
   types are what float16 quantization produces, and the stage does not claim int8.

---

### User Story 3 - See what the quantization cost, per layer (Priority: P2)

When the gate fails, the author needs to know *where* the accuracy went, not only that it went.
They get a table naming each layer and how much its output changed under quantization, ordered so
the worst layer is first.

**Why this priority**: the constitution requires it, and without it a failed gate is a dead end —
the author's only options would be to loosen the threshold or give up, neither of which is acting
on the information.

**Independent Test**: force a failing gate on a manifest with a deliberately tight threshold and
confirm the table is emitted, ordered, and names layers that exist in the built model.

**Acceptance Scenarios**:

1. **Given** a failed accuracy gate, **When** the author reads the report, **Then** it carries one
   row per layer with that layer's error under quantization, worst first.
2. **Given** a passed gate, **When** the author reads the report, **Then** the table is absent,
   because a per-layer table is what a failure owes the author and not a routine artifact.

---

### User Story 4 - Read and run an exported model without a training framework (Priority: P2)

A contributor on the project's current Python, where no training framework can be installed, can
still run an exported model and measure it. Only the conversion itself needs the older interpreter.

**Why this priority**: it is the layering rule applied to the second half of the pipeline. Every
stage after this one — analysis, emulated verification, the benchmark, the card — reads an
exported model, and none of them should need a training framework to do it. Settling that here
means those stages inherit it instead of each solving it again.

**Independent Test**: with no training framework installed, run an already-exported model against
a dataset and get its accuracy; and confirm the measurement half imports no training framework.

**Acceptance Scenarios**:

1. **Given** an installation with the measurement part but no training framework, **When** a
   quantized model is run against a split, **Then** it produces accuracy and a confusion matrix.
2. **Given** that installation, **When** the author asks to quantize, **Then** the run fails with
   the environment-incomplete status, naming what is missing and on which Python it installs.
3. **Given** the measurement part, **When** the core is imported, **Then** no training framework
   and no interpreter is loaded until a stage asks for one.

---

### Edge Cases

- The manifest asks for more calibration samples than the training split holds: every available
  training sample is used, and the report records requested, used and available. The accuracy gate
  then decides whether that was enough — which is the honest arbiter, since "enough calibration
  data" has no answer independent of the result.
- The training split holds fewer samples than the documented floor for int8 calibration: the run
  continues and the report says so, because the manifest rule that demands at least that many is
  about what the author *states*, and what the data holds is a fact to report rather than a second
  prohibition.
- Quantization changes no prediction at all: the drop is zero, the gate passes, and both figures
  are still recorded — a zero that was measured is not the same as a figure nobody took.
- The quantized model's accuracy is *higher* than the float model's: recorded as a negative drop
  rather than clamped to zero, because clamping would hide a measurement worth looking at.
- The test split is small enough that one changed prediction exceeds the threshold: the gate still
  decides on the stated threshold, and the report records the split size so the verdict can be read
  with the resolution it actually had.
- The trained model is missing or unreadable: the run fails naming the artifact and the stage that
  should have produced it, rather than reporting a quantization failure.
- A manifest field this stage reads is edited: the result is produced again. Editing anything else
  reuses it — including a change to `export.targets`, which this stage does not read.
- The conversion itself fails: the run fails with what the converter reported, and no artifact is
  left behind.

## Out of Scope

Named here because each of these is something a reader might reasonably expect from a stage that
produces a deployable model, and each belongs to a later feature with its own driver:

- the C array and the other export formats, and the operator resolver and per-operator kernel
  coverage that go with them — the next feature;
- footprint analysis: flash, RAM and the peak-activation layer — v0.2, and the first stage to make
  a claim about a board;
- emulated verification, hardware benchmarks, the model card and publication;
- the `conv1d` template, which arrives with `pace-cnn`;
- any claim about hardware behaviour. This stage measures a model on a desktop interpreter, and
  says so: nothing it records is a latency, a flash figure or a memory figure for a target.

## Requirements *(mandatory)*

### Functional Requirements

**Producing the quantized model**

- **FR-001**: The tool MUST provide a command that converts the trained model of a run to the
  quantization the manifest states, and writes it as a run artifact.
- **FR-002**: Calibration samples MUST be drawn from the training split only. The test split MUST
  NOT be used for calibration, because a model calibrated on the data it is then measured against
  has a measurement that means nothing.
- **FR-003**: The number of calibration samples MUST be the number the manifest states, capped by
  what the training split holds, and the report MUST record requested, used and available.
- **FR-004**: The choice of calibration samples MUST be reproducible from the manifest's seed.
- **FR-005**: All three quantization settings the schema accepts MUST be handled with defined
  behaviour. A setting of none MUST still produce a converted model and a measured comparison.

**Proving what was produced**

- **FR-006**: The stage MUST determine what the produced model actually contains by reading the
  produced file, and MUST NOT derive that claim from the conversion tool's output or logs.
- **FR-007**: The report MUST record, for the produced model, the type of every tensor, the input
  and output types, and the input and output scale and zero point.
- **FR-008**: A model declared int8 whose tensors are not all integer MUST fail the run, naming the
  tensors that are not.
- **FR-009**: The stage MUST NOT describe a model as int8 unless the file says so.

**The gate**

- **FR-010**: Three accuracies MUST be measured on the test split, against the same dataset
  version: the trained model's, the converted model's before quantization, and the quantized
  model's. The gate MUST be the difference between the last two, because that difference is the
  loss *from quantization*, which is what the manifest's threshold is about. The difference between
  the first two MUST be recorded beside it, so a loss caused by conversion cannot hide inside a
  passing gate — with one baseline the two are indistinguishable, and they have different fixes.
- **FR-011**: The run MUST fail when the accuracy drop exceeds what the manifest accepts, with a
  non-zero status and a machine-readable reason.
- **FR-012**: A failed gate MUST leave no quantized-model artifact.
- **FR-013**: All three accuracy figures, both differences, the threshold and the verdict MUST be
  recorded whether the gate passes or fails.
- **FR-014**: There MUST NOT be any option, flag or variable that skips the gate, lowers the
  threshold or continues past a failure. Loosening the budget is an edit to the manifest.
- **FR-015**: A stage that cannot measure the comparison MUST fail rather than pass. Unknown is not
  within budget.
- **FR-016**: A failed gate MUST emit a per-layer error table, ordered worst first, naming layers
  that exist in the built model.

**Provenance**

- **FR-017**: Every number this stage records MUST state what it was measured against: the split,
  the dataset version and the number of samples.
- **FR-018**: The report MUST record the converter and the runtime that produced and measured the
  artifact, each with its version, and the Python version they ran on.
- **FR-019**: The quantized model's size in bytes MUST be recorded, next to the float model's, as
  measured rather than estimated.

**Reusing a result**

- **FR-020**: The stage MUST reuse its stored result when the manifest fields it reads, the dataset
  version and the trained model it converts are unchanged.
- **FR-021**: A change to a field this stage does not read MUST NOT cause a new conversion.
- **FR-022**: The report MUST record whether the result was produced or reused, and on what key.

**The measurement part**

- **FR-023**: Running and reading an exported model MUST NOT require a training framework, and MUST
  work on every Python version the project supports.
- **FR-024**: The default installation MUST NOT require or load either the conversion framework or
  the runtime, and the layering checks of the previous features MUST keep passing.
- **FR-025**: A command that needs a part which is not installed MUST fail with the
  environment-incomplete status and a message naming the part and the Python it installs on, never
  a traceback.
- **FR-026**: The project MUST stay within its budget of optional extras, and each extra's
  dependencies MUST carry the markers its Python window needs.

### Key Entities

- **Quantized model**: the converted model as a file, with the types and quantization parameters it
  actually contains — not what it was asked to contain.
- **Calibration sample set**: samples drawn from the training split, with the counts requested,
  used and available, and the seed that chose them.
- **Accuracy comparison**: three accuracy figures on one split and one dataset version — trained,
  converted, quantized — the two differences between them, the threshold the second difference was
  judged against, and the verdict.
- **Per-layer error row**: a layer, and how much its output changed under quantization. Exists only
  for a failed gate.
- **Tensor type record**: what the produced file says about each of its tensors, read from the file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pilot manifest quantizes end to end on the synthetic fixture in under 60 seconds,
  with no network access.
- **SC-002**: A passed run leaves the quantized model and a report carrying all three accuracy
  figures, both differences, the threshold and the verdict.
- **SC-003**: 100% of the numbers this stage records name their split, their dataset version and
  their sample count.
- **SC-004**: The report's claim about the model's tensor types matches an independent reading of
  the produced file, asserted by a test that reads the file rather than the report.
- **SC-005**: A deliberately tight threshold fails the run, leaves no quantized model and emits a
  per-layer table whose rows name layers of the built model.
- **SC-006**: No option anywhere can skip the gate or lower the threshold, asserted over the whole
  command surface.
- **SC-007**: Editing a field the stage does not read reuses the result; changing the quantization
  setting, the accepted drop, the calibration count, the seed, the dataset or the trained model
  produces a new one — in every one of those six cases.
- **SC-008**: Measuring an exported model succeeds in an environment with no training framework
  installed, on every Python version the project supports.
- **SC-009**: With a required part absent, the command exits with the environment-incomplete status
  and a message naming the part; no traceback appears and no run directory is left behind.
- **SC-010**: The default installation still pulls neither framework, and the dependency and extras
  budgets still hold.

## Constitution Alignment

| Principle | How this feature complies |
|---|---|
| I. Declarative Manifest | The quantization setting, the accepted drop and the calibration count come from the manifest only; no flag and no script changes them. |
| III. Reproducible by Construction | FR-004 makes the calibration choice reproducible; FR-020 to FR-022 extend the stage cache; the converter and runtime versions are recorded (FR-018). |
| IV. Measured, Emulated or Estimated | FR-006 and FR-019 are this principle in its sharpest form: what the file contains is read from the file, and the size is measured. No figure here is estimated, and none describes hardware. |
| V. Budgets Are Gates | FR-011 to FR-016 are the accuracy gate verbatim: it fails the stage, it cannot be silenced, unknown is not within budget, and a failure emits the per-layer table rather than only a verdict. |
| VI. Compliance Enforced by the Schema | Unchanged by this feature; a failed gate leaves no publishable artifact, which is what publication will later depend on. |
| VII. Targets and Templates Are Data | The stage reads no board description; `export.targets` is deliberately not in its read set, so adding a target does not re-quantize. |
| VIII. No Lock-In | The produced model is an open format, written as a file; no stage in this feature touches the network. |
| IX. Stable Manifest Contract | The schema gains no field. Every value this stage reads already exists in `caravan/v0`. |
| X. Built for Real Models | `picket-mlp` drives it: int8 is the only setting a named model uses, and the other two are handled because the schema already accepts them, not because a model asks. |
| XI. No Claude in Model Learning | Nothing here produces, labels or judges data. The calibration samples come from the author's own training split. |
| XII. Small Core, Few Dependencies | FR-023 to FR-026: conversion stays in the training extra, measurement gets one extra of its own whose dependency carries no training framework, and the core loads neither. |

Deviations: none.

## Assumptions

- **The measurement part is its own extra, not part of the training extra.** The interpreter the
  training framework ships is deprecated and announced for deletion, so using it would be building
  on something already leaving; and every stage after this one needs to read an exported model
  without a training framework. That makes a second extra the smaller cost, not a speculative one.
  It is named for the stage group the constitution lists it under rather than for the package it
  carries, because a product rename must not become a rename here.
- **Calibration is capped rather than refused** when the manifest asks for more samples than the
  training split holds (FR-003). The alternative — failing — would make the manifest's calibration
  count a second budget, and the budget that decides whether the quantization was good enough is
  already the accuracy gate. What is not acceptable is silence, so all three counts are recorded.
- **The accuracy gate is an absolute difference**, as `accuracy_drop_max` is written in the schema:
  a drop of 0.02 means two points of accuracy, not two percent of it.
- **On the committed fixture the gate's resolution is one changed prediction in twelve**, which is
  coarser than the pilot manifest's threshold. The acceptance test therefore asserts the
  mechanism — both figures recorded, a verdict reached, no artifact on failure — rather than a
  particular accuracy value. If quantization does flip a prediction on the fixture, the fixture
  manifest takes a wider threshold with the reason stated in the file, and it stays the only field
  in which the fixture differs from the pilot manifest besides the dataset path.
- **The per-layer error table comes from the conversion half**, which already has the framework,
  and is therefore available on the same Python the conversion needs. It is recorded only for a
  failed gate (FR-016, user story 3 scenario 2).
- **Every accuracy here is re-measured rather than read from the training report**, on the same
  split and dataset version, so the figures being compared were taken the same way. Reading one
  from an earlier run would compare a measurement with a memory.
- **The gate compares the converted model with the quantized one, not the trained model with the
  quantized one** (FR-010). With a single baseline, accuracy lost in conversion and accuracy lost
  in quantization are one number, and a threshold on their sum fails runs for the wrong reason or
  passes them while conversion quietly cost something. The planning phase settled this; it costs one
  extra conversion of a small model.
- No hardware, emulator or accelerator is needed to develop or test this feature. Nothing in it
  claims anything about hardware behaviour; the first such claim is the analysis stage.
