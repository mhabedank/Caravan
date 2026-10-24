# Feature Specification: Typed Features, Ludwig-Style, with Their Preprocessing on the Device

**Feature Branch**: `008-typed-features`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Wenn möglich Benennung wie bei Ludwig. Sonst verwirre ich mich." —
*Where possible, Ludwig's naming; otherwise I get confused.* This follows decision D7
(`docs/design/2026-10-23-owner-decisions.md`): inputs and outputs name their columns, each with a
type, and each type brings its preprocessing, ideally inside the model on the microcontroller. The
conditions and limits are in `docs/research/2026-10-24-typed-features-on-mcu.md`. `v0.1.0` waits
for this feature (D7).

## Context

The owner worked through the example of `v0.1.0rc1` and found the manifest opaque:

- the input says only `frames` and the output only `attack`;
- no column is named, so nothing says what goes in, what comes out and what is ignored;
- `kind: series` explains nothing;
- there are no data types.

Every input column is read as a number. That is wrong for a CAN identifier, which is a code, not a
magnitude, and it is the reason the synthetic example fails the int8 gate when its labels are
derived (feature 006, research R11).

Ludwig, which the owner knows from contributing to it, answers all of this:
- each column is a feature with a `name` and a `type`;
- each type brings its own preprocessing, fitted on the data and replayed at prediction;
- anything not listed is ignored.

The research of 2026-10-24 established what of this can run inside a model on TFLite Micro, the
runtime Caravan exports for. Its six conditions (section 6 of the note) are the frame of this
specification.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Name the columns and their types, as in Ludwig (Priority: P1)

An author who knows Ludwig writes a Caravan manifest without a second vocabulary: input features
and output features, each a column with a name and a type, and per-type preprocessing options
where they want to change a default. Columns the manifest does not name are ignored, visibly.

**Why this priority**: It is the owner's direct objection to the current form and the first thing
every author meets. Every later story depends on the declaration this story defines.

**Independent Test**: Rewrite the pilot manifest with each CSV column named and typed, and
validate it. Then remove one column from the list and check that the run reports it as ignored.

**Acceptance Scenarios**:

1. **Given** a manifest whose `input_features` list `can_id` as `category` and `dlc`, `b0`, `b1`
   and `b2` as `number`, and whose `output_features` list `label` as `category`, **When** it is
   validated, **Then** it is valid, and `render` shows every feature with its full, resolved
   preprocessing.
2. **Given** a data file with a column the manifest does not name, **When** a run reads the data,
   **Then** the column is not used, and the run report lists it as ignored.
3. **Given** a feature whose name is not a column of the data, **When** a run reads the data,
   **Then** it stops with a finding naming the feature and the columns the data has.
4. **Given** a feature of a type this build does not implement (for example `text`), **When** it is
   validated, **Then** it is refused, naming the implemented types and why the others are absent
   (no device path, research section 5).
6. **Given** an output feature of type `binary` or `number`, **When** the model is trained,
   quantized and exported, **Then** it uses that type's loss, metrics, int8 budget and device
   decision (FR-004).
5. **Given** a manifest in the form of `v0.1.0rc1`, **When** it is loaded, **Then** it is refused
   with the schema version this build reads and the change note, as constitution 4.0.0 requires.

---

### User Story 2 - Each type brings its preprocessing, and the device needs none written (Priority: P1)

The author states types; Caravan learns each type's preprocessing from the training data and builds
it into the exported model. The firmware passes raw values, one per column and time step, and
writes no preprocessing of its own.

**Why this priority**: It is the owner's second requirement in D7: "für jeden Typen … die Logik
mitbringen". It is also what fixes the precision failure of the synthetic example (R11 of feature
006, section 3 of the research), so it decides whether a model trained on mixed-range columns
survives int8.

**Independent Test**:
- Export the typed pilot.
- Feed the exported model raw values taken from the data file: integer codes for `can_id`, raw
  numbers for the rest.
- Compare its outputs with the trained model's on the same windows.
- Check that the interface contract tells a firmware author the type and form of every input.

**Acceptance Scenarios**:

1. **Given** a `number` feature, **When** the model is trained, **Then** its normalisation is
   fitted on the training part only, recorded in the run, and applied inside the exported model, so
   the device passes the raw value.
2. **Given** a `category` feature whose raw values are integer codes, **When** the model is
   exported, **Then** the device passes the raw code. The model maps it to its class. A code never
   seen in training maps to a reserved "unknown" class rather than to a wrong one.
3. **Given** a `category` feature whose raw values are text (for example `"walking"`), **When** the
   model is exported, **Then** the interface contract carries the table from text to the integer
   code the device must pass, because a microcontroller passes no text (research section 1).
4. **Given** a `binary` feature, **When** the model is exported, **Then** the device passes 0 or 1,
   and the table from the data's spelling (yes/no, true/false…) to 0 and 1 is in the interface
   contract.
5. **Given** the typed synthetic pilot with labels derived from the data, **When** it is exported,
   **Then** the int8 gate passes. Today it fails at 0.75 trained against 0.50 quantized (R11).

---

### User Story 3 - The firmware binds every input by name, with its type (Priority: P2)

A firmware author reads the interface contract and the C header and knows, per input feature, its
name, its position, the element type to pass (integer code or number) and the window length.
Nothing depends on the order inputs happen to have in the converted file.

**Why this priority**: Several inputs of different types are new to Caravan's export, and the
converter reorders inputs (research section 4). Without this, a correct model receives values in
the wrong slots.

**Independent Test**: Export a model with five input features, feed it through the contract's names
only, and compare with the trained model.

**Acceptance Scenarios**:

1. **Given** a model with several input features, **When** it is exported, **Then** the interface
   contract and the header give each input's name, position, element type and shape.
2. **Given** the converter places inputs in a different order than the manifest, **When** the model
   is calibrated and exported, **Then** calibration and the contract both follow names, and the
   model's outputs match the trained model's within the gate.

---

### User Story 4 - Change only a default, the Ludwig way (Priority: P3)

An author who wants every number feature min-max scaled instead of z-scored says so once, in a
`defaults` section keyed by type, as in Ludwig, rather than on every feature.

**Why this priority**: Ludwig authors expect it, and it keeps typed manifests short. Nothing breaks
without it.

**Independent Test**: Set `defaults: {number: {preprocessing: {normalization: minmax}}}` and check
that `render` shows minmax on every number feature that does not override it.

**Acceptance Scenarios**:

1. **Given** a `defaults` entry for a type, **When** the manifest is resolved, **Then** every
   feature of that type takes it unless the feature states its own value.
2. **Given** a `defaults` entry for a type with no feature, **When** it is validated, **Then** it is
   accepted, and `render` shows it.

---

### Edge Cases

- **A number column constant on the training part** (standard deviation 0): it scales by 1, as
  Ludwig does, and the run says so.
- **A number column with missing cells**: filled per `missing_value_strategy`. The default is a
  constant 0, as in Ludwig. The fill value is fitted on the training part only.
- **A category with more distinct values than `most_common`**: the most frequent values in the
  training part are kept, and the rest map to "unknown". The run says how many were cut.
- **A category value that appears only in the test part**: maps to "unknown". This is the honest
  behaviour of the device, so the test score includes it.
- **The output column also named as an input**: refused, as today (CF-11).
- **The fixed-split column named as a feature**: refused, as today (CF-13).
- **A category input that arrives on the device as a number with decimals**: the contract says
  integer; the firmware author passes an integer.
- **A model with many input features**: each is its own input tensor, so the arena grows with
  them. The fit check before training counts them.

## Requirements *(mandatory)*

### Functional Requirements

**Declaration, in Ludwig's names**

- **FR-001**: The manifest MUST declare `input_features` and `output_features`, each a list of
  features with `name` (the column) and `type`, and optional `preprocessing` options per feature,
  using Ludwig's option names where Ludwig has the option.
- **FR-002**: Columns not named by any feature, the split column, or the label column MUST NOT be
  used, and every run MUST list the ignored columns.
- **FR-003**: The implemented input types MUST be `number`, `binary` and `category`. A feature of
  another Ludwig type MUST be refused, naming the implemented types and the reason (no device path).
- **FR-004**: The implemented output types MUST be `category`, `binary` and `number`, one output
  feature per model (owner decision 2026-10-24). Each type brings what Ludwig gives it:
  - **`category`**: softmax over the labels with cross-entropy loss and optional `class_weights`.
    The device decision is the arg-max, and the labels are in the header.
  - **`binary`**: one output with binary cross-entropy and an optional `positive_class_weight`. The
    device decision is `threshold`, default 0.5, shipped in the contract.
  - **`number`**: regression with `loss` `mean_squared_error` (default), `mean_absolute_error` or
    `huber`. An optional output `normalization` is fitted on the training part and inverted in the
    model. An optional `clip` bounds the prediction.

  Each output type MUST state its int8 budget in its own metric (Principle V):
  - `category` and `binary`: the accuracy lost to quantization (`accuracy_drop_max`, as today);
  - `number`: the increase of the mean absolute error, in the column's own unit
    (`mae_increase_max`).

  The gate and the per-layer error table work for each.
- **FR-005**: The way rows become samples MUST be declared once, as `preprocessing.window_size`
  (the number of consecutive rows per sample, windows never overlapping, as today). The split MUST
  be declared as Ludwig declares it: `preprocessing.split` with `type` `random`, `stratify` or
  `fixed`, `probabilities` for the first two and `column` for the latter two. The fixed split MUST
  read Ludwig's values `0`, `1`, `2`, and also the words `train`, `validation`, `test`.
- **FR-006**: A `defaults` section keyed by type MUST set preprocessing defaults for all features of
  that type, overridable per feature.
- **FR-007**: The schema version MUST change, and a manifest in the previous form MUST be refused
  with the change note (constitution 4.0.0). The change note MUST give the edit from the `v0.1.0rc1`
  form to this one.
- **FR-008**: Ludwig naming MUST cover everything Ludwig and Caravan share (owner decision
  2026-10-24):
  - `input_features`, `output_features`, `preprocessing` (with `split` and `window_size`) and
    `defaults`;
  - the training settings as `trainer` with Ludwig's names: `epochs`, `batch_size`,
    `learning_rate`, `optimizer.type` and `early_stop` (the patience; −1 disables, as in Ludwig).

  Caravan keeps its own sections only where Ludwig has no counterpart: the model template (the
  architecture for a microcontroller), the dataset path, the seed, the export with its formats and
  boards, and the calibration sample size. The change note lists each exception with its reason.

**Preprocessing per type, learned once, run on the device**

- **FR-009**: `number`:
  - `normalization` MUST be `zscore` (default), `minmax`, `iq` or `null`;
  - `missing_value_strategy` MUST be `fill_with_const` (default, `fill_value` 0) or
    `fill_with_mean`.
- **FR-010**: `category`:
  - the vocabulary MUST be learned from the training part, ordered by frequency, and capped by
    `most_common`;
  - index 0 MUST always be "unknown", for values cut by the cap or never seen;
  - an explicit `vocab` list MAY pin the vocabulary and its order;
  - `encoder` MUST be `dense` (default, as in Ludwig: an embedding of `embedding_size`) or
    `onehot`.
- **FR-011**: `binary`: values MUST map to 0 and 1 with Ludwig's recognised spellings, and
  `fallback_true_label` for other spellings.
- **FR-012**: Every fitted statistic MUST come from the training part only (not validation or test,
  unlike Ludwig), and MUST be recorded in the run directory and in the interface contract.
- **FR-013**: The exported model MUST apply the preprocessing itself:
  - the device passes, per input feature and time step, an integer code for `category` and
    `binary` and a number for `number`;
  - the model normalises, maps codes to classes (with "unknown"), and embeds or one-hot encodes;
  - no preprocessing step MAY use an operation the microcontroller runtime lacks (research
    section 1).
- **FR-014**: Each input feature MUST be its own input of the exported model, so that each has its
  own quantisation (research section 3).
- **FR-015**: Where raw values are text (a `category` or `binary` column spelled in words), the
  interface contract MUST carry the table from text to the integer the device passes.

**Export and contract**

- **FR-016**: The interface contract and the C header MUST give, per input feature, its name,
  position, element type, shape and type, and per output its name, labels and decision.
- **FR-017**: Calibration and binding MUST follow input names, never the order inputs have in the
  converted file.
- **FR-018**: The fit check before training MUST count every input, including the preprocessing
  tables and constants the model carries.

**What stays**

- **FR-019**: The int8 accuracy gate, the fit check, the stage cache keyed by what each stage reads,
  the run report and the fixed split's semantics MUST work for typed features as they do today.
- **FR-020**: The pilot, the convolutional fixture, the example and the `pace-cnn` port MUST be
  rewritten in the new form. The `pace-cnn` port then passes raw sensor values and lets the model
  standardise them; today its converter does that.

### Key Entities

- **Input feature**: a column, a type, preprocessing options, an encoder where the type has one.
- **Output feature**: a column, a type, the accuracy budget, the labels in output order.
- **Fitted preprocessing**: per feature the statistics or vocabulary learned from the training
  part. It is Caravan's counterpart of Ludwig's training-set metadata.
- **Defaults**: preprocessing options per type.
- **Input binding**: per input feature, its name, position, element type, shape and text table.
  It is what the firmware needs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Someone who knows Ludwig reads the typed pilot manifest and names, without help,
  which columns go in, which comes out and which are ignored.
- **SC-002**: Every key in a typed manifest that Ludwig also has carries Ludwig's name and meaning.
  Each exception is listed in the change note with its reason.
- **SC-003**: The typed synthetic pilot, with labels derived from the data, passes the int8 gate.
  Today it fails at 0.75 against 0.50.
- **SC-004**: On every example and fixture, the exported model fed raw values agrees with the
  trained model fed the same raw values to within the stated accuracy budget.
- **SC-005**: A firmware author writes no preprocessing code. The runner skeleton passes raw values
  by input name and nothing else.
- **SC-006**: The `pace-cnn` port in the new form reaches at least the int8 accuracy of its
  `v0.1.0rc1` run (0.918 on 2,947 test windows), with standardisation moved from the converter into
  the model.
- **SC-007**: A `binary` and a `number` output each train, pass their own int8 budget and
  export with their device decision, on a synthetic fixture derived at test time from the committed
  one.

## Assumptions

- Ludwig naming is followed where Ludwig has the concept:
  - `input_features`, `output_features`, `name`, `type`;
  - `preprocessing` with `normalization`, `missing_value_strategy`, `fill_value`, `most_common`,
    `fallback_true_label`;
  - `encoder` with `type` and `embedding_size`;
  - `defaults`;
  - `preprocessing.split` with `type`, `probabilities` and `column`.
- **Exceptions carry a Caravan name**, because Ludwig has nothing for them: the window over rows
  (`preprocessing.window_size`, named after Ludwig's per-feature timeseries option), the accuracy
  budget per output, the boards, the quantization and the export formats.
- **Defaults on a microcontroller.**
  - `most_common` defaults to 32, not Ludwig's 10,000, because every vocabulary entry costs a
    comparison and weights on the device.
  - `embedding_size` defaults to `min(vocabulary size, 4)`, not 50. The plan measured 4 against 8
    and against one-hot on the pilot: same accuracy, 28 KB against 37 KB and 87 KB (plan research
    R4).
- **Out of scope:**
  - `set`, `bag`, `sequence`, `text`, `image`, `audio`, `date`, `h3` and `vector`: no device path,
    or no named model needs them (Principle X);
  - `log1p` normalisation;
  - outlier handling;
  - overlapping windows;
  - several output features;
  - output calibration.
- **Derived labels are ordered by frequency** in the training part, Ludwig's order, no longer
  alphabetically as in feature 006. A model that relied on the old order pins
  `preprocessing.vocab`. The change note says so.
- **Two deliberate differences from Ludwig:**
  - statistics come from the training part only;
  - index 0 of a category is always "unknown".
- `v0.1.0` waits for this feature (D7). After it, feature 007's remaining tasks resume.
- Nothing trains, labels or evaluates with a Claude model (Principle XI). No data enters the
  repository.

## Constitution Check

| Principle | How this feature complies |
|---|---|
| I — declarative, every field read | every feature and preprocessing option is read by the data, build, train, quantize or export stage; unlisted columns are visibly ignored |
| III — reproducible | fitted preprocessing comes from the training part, is part of the stage keys, and is recorded in the run |
| IV — provenance | the gate and every number still state their split and dataset version |
| V — budgets before training | the fit check counts the added inputs and preprocessing constants |
| VI — the data is the author's | no field asks about rights; text tables come from the data |
| VIII — export contract | per-input name, position, type, shape and text table in the contract; binding by name |
| IX — variable until 1.0.0 | a new schema version and a change note; the previous form is refused |
| X — built for real models | input types limited to what `picket-mlp` and `pace-cnn` need and what has a device path. The `binary` and `number` outputs serve documented application classes of the research of 2026-10-23 (detection, and estimation such as state of charge), as Principle X since 3.0.0 allows |
| XI — no Claude in learning | untouched |
| XII — small core | no new verb; the preprocessing layers are Caravan's own, inside the train extra; no dependency added |
