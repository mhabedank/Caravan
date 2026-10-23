# Feature Specification: Declared Inputs and Outputs, and a Lean Manifest

**Feature Branch**: `006-declared-io`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: the go-ahead for the follow-up named after constitution 3.0.0: remove
compliance, `topic` and `task` from the manifest; derive the labels from the data; declare inputs
and outputs; check the fit to the boards before training; carry the interface contract in the
export. Sources: the owner's decisions D1, D2, D4 and R1, R2 in
`docs/design/2026-10-23-owner-decisions.md`, and constitution 3.0.0 Principles I, V, VI, VIII, X.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Write a manifest that asks only for what Caravan uses (Priority: P1)

The owner wrote the pilot manifest from an empty folder and questioned the fields first: `topic`
and `task`, which no stage reads; a label list that repeats what the data's label column already
says; a licence, a permitted use and a whole compliance block that Caravan cannot check. An
author writes the data source, what goes in, what comes out, the template and the boards, and
nothing else. A manifest written for the previous form still loads, and the author is told what
was dropped.

**Why this priority**: It is the first thing every user meets, and constitution 3.0.0 makes the
current form non-compliant: Principle VI forbids the compliance layer and Principle I forbids
fields no stage reads. Every later story writes into the manifest this story defines.

**Independent Test**: Write the pilot manifest in the new form, without `topic`, `task`, labels,
licence or compliance, and validate and train it on the synthetic fixture. Then load the
committed pilot manifest in the old form and check that it loads, with one notice per dropped
field.

**Acceptance Scenarios**:

1. **Given** a manifest without `compliance`, `topic`, `task`, `dataset.license`,
   `dataset.permitted_use` and a label list, **When** it is validated, **Then** it is valid.
2. **Given** a manifest that still carries any of those fields in the new form, **When** it is
   validated, **Then** it is rejected as an unknown field, with the field path and a note saying
   the field was removed and why, so the author learns it is gone rather than misspelt.
3. **Given** a manifest in the previous form, **When** it is loaded, **Then** it migrates in
   memory without the file being rewritten, every dropped field is named in a notice, and the run
   report records the declared and the effective schema version.
4. **Given** a previous-form manifest that stated `permitted_use: benchmark-only` together with a
   `publish` section, **When** it is loaded, **Then** it migrates, and the notice says that this
   statement is no longer enforced by Caravan (Principle VI), rather than dropping it silently.

---

### User Story 2 - Declare what goes in and what comes out (Priority: P1)

The author states the model's input and its output, each with a kind. The output kind says what
the model does: a `class` output says it classifies, and from which column of the data. The input
says which columns go in and, for a series, how many records form one sample. Labels follow from
the data: Caravan reads the output column and finds the class names itself. An author who needs a
fixed order states the labels to pin it.

**Why this priority**: It is decision D4 and the reason the owner preferred Ludwig's form: the
manifest says plainly what the model is for. It also removes the duplicated label list (R2),
which is the commonest way for a manifest and its data to disagree.

**Independent Test**: Validate and train the pilot model with an input of kind `series` over the
feature columns and a window of 64, and an output of kind `class` over the `label` column, with no
label list. The run's resolved manifest lists the four labels in sorted order, and training
produces the same samples as the previous form did.

**Acceptance Scenarios**:

1. **Given** a `class` output with no label list, **When** a run reads the data, **Then** the
   labels are the distinct values of the output column across all files, in sorted order, and the
   resolved manifest of that run records them.
2. **Given** a `class` output with a pinned label list, **When** the data holds a value the list
   does not name, or the list names a value the data never holds, **Then** the run fails with a
   finding naming the values on each side.
3. **Given** an input that names no columns, **When** the data is read, **Then** every column not
   used by an output is an input column, in file order, and the resolved manifest records them.
4. **Given** an input that names a column the data does not have, **When** the data is read,
   **Then** the run fails naming the column and the columns the data has.
5. **Given** a template that consumes a window and an input without one, or a template that does
   not and an input with one, **When** the manifest is validated, **Then** it is rejected as
   today, at the input's window field.
6. **Given** a `class` output whose column holds a single distinct value, **When** a run reads the
   data, **Then** it fails: a classifier needs at least two classes.

---

### User Story 3 - Learn before training that a model cannot fit a board (Priority: P2)

Caravan knows the boards. Before it spends training time, it checks the built model against every
target board, using only figures that bound the need from below: the size of the weights at the
stated quantization, and a computed floor on working memory. When even the floor exceeds a board,
the run stops before training and says by how much. When it does not, the run continues and the
figures are recorded as estimates; the real footprint gate stays where it is.

**Why this priority**: It is part of D4 and Principle V in 3.0.0. It matters most once inputs grow
— images, wider windows — and the pilot model passes it with a wide margin, which is why it comes
after the stories that change the manifest.

**Independent Test**: Build the pilot model and read the pre-training figures for all three
boards in the run report, each labelled `estimated`. Then build a model whose weights exceed the
smallest board's flash and check that the run fails before any training starts.

**Acceptance Scenarios**:

1. **Given** a built model whose weight floor exceeds a target board's flash, or whose
   working-memory floor exceeds its RAM, **When** the build stage runs, **Then** it fails with the
   gate exit code, names each board, the resource, the floor and what the board offers, and no
   training starts.
2. **Given** a built model whose floors are within every board, **When** the build stage runs,
   **Then** the run report records each figure with the label `estimated`, the method that
   produced it, and the statement that passing this check is not a claim that the model fits.
3. **Given** a model that passes the check, **When** a later footprint gate fails, **Then** that
   later failure stands; the pre-check never overrides it.
4. **Given** an unchanged manifest and an unchanged dataset, **When** the build runs again, **Then**
   the check's result is reused from the stage cache like the rest of the build.

---

### User Story 4 - Hand a firmware author everything needed to feed the model (Priority: P2)

A firmware author who does not use Caravan receives the exported model. With it comes the
interface contract: each input and output by name and index, its shape and element type, its
quantization scale and zero point, what Caravan did to the raw data before the model, and the
order of the class labels. The C header carries the same label order and the indices, so the
runner can map the output to a class name without opening another file.

**Why this priority**: It is Principle VIII in 3.0.0. Today the C header carries only the byte
array and its length, so the label order lives only in Caravan's run directory and the model
cannot be used correctly without Caravan.

**Independent Test**: Export the pilot model, delete Caravan, and from the contract alone write
down how to turn 64 raw CAN records into the input tensor and the output index into a label
name. Compare with what Caravan did.

**Acceptance Scenarios**:

1. **Given** an exported model, **When** the contract is read, **Then** it names every input and
   output of the converted model with the name the runner binds by, the index in the converted
   model, shape, element type, scale and zero point, as read from the model file rather than
   assumed from the manifest.
2. **Given** an exported model, **When** the contract is read, **Then** it states every
   transformation before the model — the input columns in order, the window length and the stride
   between windows — and states input scaling as none, because this feature adds none.
3. **Given** a `class` output, **When** the C header is read, **Then** it declares the label names
   in output order and the number of labels, and the indices of the input and output.
4. **Given** the same quantized model exported twice, **When** the contracts and headers are
   compared, **Then** they are byte for byte identical.

### Edge Cases

- The output column also appears in an input's column list: rejected at validation, because a
  model would be trained on its own answer.
- Two files of a dataset disagree about which labels exist: the labels are the union across all
  files; a file that holds none of a label is not an error, because a stratified split already
  reports a label that ran out (rule DS-8).
- Labels that differ only in case or surrounding whitespace: kept as distinct values exactly as the
  data spells them; the derived list shows both, so the author sees the problem.
- A label column with numeric values: treated as names, sorted as text, so `10` sorts before `2`;
  the resolved manifest shows the order, and an author who wants numeric order pins the list.
- `caravan render` runs without reading the data: the resolved manifest it prints shows the labels
  and the input columns as derived at run time, not as an empty list.
- A board description without a RAM or flash figure: the pre-training check cannot compare and
  fails for that board (Principle V: unknown is not within budget). Every built-in board has both.
- A quantization of `none` or `float16`: the weight floor uses the size of the stated element type.
- A previous-form manifest that declares no schema version: treated as the oldest version and
  migrated, as today.
- An input and an output with the same name: rejected at validation, because names are what a
  runner binds by.
- A second input or a second output: rejected at validation with the message that one of each is
  implemented, and why — Principle X, and the research note that found no documented
  microcontroller application for several series inputs or class outputs.

## Requirements *(mandatory)*

### Functional Requirements

**Lean manifest**

- **FR-001**: The manifest MUST NOT accept `compliance`, `model.topic`, `model.task`,
  `dataset.license`, `dataset.permitted_use` or a dataset-level label list. A manifest in the new
  form that carries one MUST be rejected with the field path and a message that the field was
  removed, citing the reason in one sentence.
- **FR-002**: Every remaining manifest field MUST be read by at least one implemented stage. The
  sections of stages that do not exist yet — `verify`, `bench` and `publish` — MUST be removed
  with the other fields and return with their stages (constitution 3.0.0, Principle I).
- **FR-003**: Validation rules that exist only for the removed fields — personal data against risk
  class (CF-3), publication needs compliance (CF-5), benchmark-only data not published (CF-8),
  training not permitted (DS-9) — MUST be removed, and their identifiers MUST NOT be reused.
- **FR-004**: The resolved manifest and the run report MUST NOT contain any removed field or any
  statement that a licence, a permission or a use was checked.
- **FR-005**: A manifest in the previous form MUST migrate in memory to the new form on load,
  without rewriting the file. The migration MUST: drop each removed field with a notice naming it;
  turn `dataset.window` and the feature columns into an input of kind `series`; turn the `label`
  column and `dataset.labels` into a `class` output whose labels are pinned in the stated order;
  and record the declared and effective schema versions in the run report.
- **FR-006**: The migration MUST ship with a note naming every affected field and the change
  required, as Principle IX requires of a breaking change while the schema is pre-stable.

**Declared inputs and outputs**

- **FR-007**: The manifest MUST declare its inputs and its outputs, each with a name and a kind,
  in a form that holds a list of each, so that adding a second input or output later is not a
  breaking change.
- **FR-008**: This feature MUST implement the input kind `series` — numeric columns of the data,
  read as records in sequence, with an optional window length — and the output kind `class` —
  one column of the data whose values are class names, one class per sample. Every other kind
  MUST be rejected at validation with the kinds that are implemented.
- **FR-009**: An input MAY name its columns. When it names none, its columns MUST be every column
  of the data not used by the output, in file order.
- **FR-010**: A `class` output MUST name its column; it MUST default to `label`, the column the
  data contract names today.
- **FR-011**: A `class` output MAY state its labels to pin their order. When it states none, a run
  MUST derive them as the distinct values of the output column across all files, sorted as text,
  and MUST fail if fewer than two remain.
- **FR-012**: When a `class` output states its labels, a run MUST fail if the data holds a value
  the list does not name or the list names a value no file holds, and the finding MUST name the
  values on each side.
- **FR-013**: The labels and input columns a run used MUST be recorded in that run's resolved
  manifest and run report. `caravan render`, which reads no data, MUST show where they will come
  from rather than an empty value.
- **FR-014**: The window MUST belong to the `series` input. The existing rule that a windowed
  template needs a window and an unwindowed one must not have one (CF-6) MUST apply to it.
  Windows remain non-overlapping; their stride equals their length and is recorded as such.
- **FR-015**: A column MUST NOT be both an input column and an output column. Declaration names
  MUST be unique across inputs and outputs.
- **FR-016**: For the pilot model, the new form and the migrated previous form MUST produce the
  same samples, the same split and the same trained model under the same seed.

**Fit check before training**

- **FR-017**: After building the model and before training it, the pipeline MUST compute, for each
  target board, a lower bound on flash (the weights at the stated quantization) and a lower bound
  on working memory (the peak of activations that must be live at once in the built model), and
  compare each with the board description.
- **FR-018**: When a lower bound exceeds what a board offers, the run MUST fail before training
  with the gate exit code, and the finding MUST name the board, the resource, the bound, the
  board's figure and the shortfall, for every board that fails.
- **FR-019**: When no bound exceeds a board, the run MUST continue, and the run report MUST record
  every figure with the provenance label `estimated`, the method that produced it, and the
  statement that a pass is not a claim that the model fits.
- **FR-020**: The pre-training check MUST NOT replace, relax or pre-empt any later footprint gate.
  There MUST be no option that skips it.
- **FR-021**: A board without a stated RAM or flash figure MUST fail the check for that resource,
  naming the missing value.

**Interface contract in the export**

- **FR-022**: The export MUST write an interface contract beside the exported model, in a plain,
  documented text form readable without Caravan.
- **FR-023**: The contract MUST name every input and output of the converted model with the name a
  runner binds by, its index in the converted model, its shape, element type, scale and zero
  point, read from the converted model file rather than from the manifest.
- **FR-024**: The contract MUST state the transformation from raw data to the input: the input
  columns in order, the window length and the stride, and input scaling stated explicitly as none.
- **FR-025**: For a `class` output, the contract MUST give the label names in output order.
- **FR-026**: The C header MUST declare, for every `class` output, the number of labels and the
  label names in output order, and for every input and output its index in the converted model.
- **FR-027**: The contract and the header MUST be byte-identical across two exports of the same
  quantized model, and MUST be listed in the export report with size and digest like every other
  artifact.

**One of each, in a form that holds more**

- **FR-028**: This feature MUST accept exactly one input and one output. A second input or output
  MUST be rejected at validation, naming what is implemented and why: several inputs or outputs
  arrive with the first named model or documented application class that needs them (Principle
  X; `docs/research/2026-10-23-multi-io-on-mcu.md`).
- **FR-029**: The output MAY state its maximum quality loss from quantization; when it states none,
  the documented default MUST apply. The manifest-wide `export.accuracy_drop_max` moves to the
  output, as Principle V in 3.0.0 places the budget per declared output, and the migration
  (FR-005) MUST carry a stated value over.
- **FR-030**: The built model's input and output MUST carry the declared names, so that the
  interface contract can map each declared name to the index the converted model uses (FR-023).

### Key Entities

- **Input declaration**: a unique name, a kind (`series` in this feature), the columns it reads
  (stated or derived), and for a series an optional window length.
- **Output declaration**: a unique name, a kind (`class` in this feature), the column it reads,
  the labels (pinned or derived), and its maximum quality loss from quantization.
- **Derived values**: the input columns and the labels a run found in the data, recorded in the
  run's resolved manifest.
- **Fit pre-check record**: per board and resource, the computed lower bound, the board's figure,
  the verdict, the method, and the label `estimated`.
- **Interface contract**: per input and output of the converted model, name, index, shape, element
  type, scale and zero point; the transformation from raw data; the label order.
- **Migration notice**: per dropped or moved field of a previous-form manifest, the field path and
  what happened to it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pilot manifest in the new form has no field that no stage reads, and is at least
  a fifth shorter, counted in non-blank, non-comment lines, than the committed previous form (43
  lines).
- **SC-002**: Every manifest in the repository's valid fixtures that was valid before this feature
  loads after it through migration, with one notice per dropped field and no other change in
  behaviour.
- **SC-003**: The pilot model trained from the new form and from the migrated previous form under
  the same seed produces byte-identical trained weights.
- **SC-004**: A model too large for a target board fails before training, so a run that would have
  failed the footprint gate after training fails in the build stage instead, with no training
  time spent.
- **SC-005**: Someone without Caravan can, from the exported contract and header alone, map 64
  raw records to the model input and the model output to a label name; checked by a test that
  reads only those two files and reproduces Caravan's prediction on the synthetic fixture.
- **SC-006**: No exported artifact, report, log or resolved manifest contains a compliance field,
  a licence statement or a claim that one was checked.

## Assumptions

- The data stays CSV or TSV with a header row, as in feature 002. New data formats are a separate
  feature.
- Input scaling, overlapping windows, splits by file or block, and shipped splits (proposals P4 and
  P5) are out of scope; the contract states the transformation as it is today.
- `render` and `validate` writing to the shell (D3), run directory naming (D6) and renaming
  `representative_samples` (R3) are separate, smaller features.
- The working-memory floor before training is computed from the built model's layer shapes; it is
  a lower bound by construction and may be lower than the floor the export computes from the
  converted model. Both are labelled `estimated`.
- The zoo, which carries its own compliance regime, is unaffected: it enforces its rules on what
  Caravan produces, through its own release gate.
- Principle X: the input kind `series` and the output kind `class` are justified by the pilot
  models `picket-mlp` and `picket-conv1d`. Several inputs and outputs are not built here. The owner
  first chose to build them now, on condition that a documented application justified them; the
  research round of 2026-10-23 (`docs/research/2026-10-23-multi-io-on-mcu.md`) found none for
  several series inputs or class outputs on microcontrollers — only several outputs for image
  detection and recurrent state carried as extra inputs and outputs — and the owner then chose the
  declaration form alone. The likely first users are object detection and stateful recurrent
  models, each of which also needs new input or output kinds.
