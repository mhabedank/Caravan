# Feature Specification: Build and Train

**Feature Branch**: `002-build-and-train`

**Created**: 2026-10-22

**Status**: Draft — one clarification open (dataset format)

**Input**: User description: "Build and train: the template's builder half and the first two pipeline stages. `caravan build` constructs the model from the template and its parameters; `caravan train` trains it on the dataset the manifest names, writing checkpoints, the trained model and the quality metrics into the run directory and the run report. The `train` extra carries the builder half and the training framework, installed separately and never reachable from the core. The stage cache of Principle III: a stage result is reused when the manifest fields that stage reads and the dataset version are unchanged. Out of scope: quantization, export, footprint analysis, emulated verification, hardware benchmarks, publication, the conv1d template, and any claim about hardware behaviour."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Train the pilot model from its manifest (Priority: P1)

The author has a manifest and a dataset. They run one command and get a trained model, its
checkpoints and its quality metrics, written into a run directory beside a report that says what
every number was measured against. No notebook, no bespoke script.

**Why this priority**: this is the premise of the whole project. Feature 001 made the manifest
checkable; this is the first feature where the manifest *produces* something. Until it exists,
Caravan cannot replace the hand-built model it was written to replace.

**Independent Test**: run the training command on the pilot manifest against the synthetic fixture
dataset and confirm the artifacts, the metrics and the report. No other story needs to work first.

**Acceptance Scenarios**:

1. **Given** the pilot manifest and a dataset that matches it, **When** the author trains,
   **Then** the run directory holds the trained model, the best and the final checkpoint, the
   metrics and the report, and the command exits with a success status.
2. **Given** that run, **When** the author reads the report, **Then** every quality metric names
   the split it was measured on and the dataset version it was measured against.
3. **Given** that run, **When** the author reads the report, **Then** the effective seed, epochs,
   batch size, optimizer, learning rate, early-stopping setting and patience are all recorded,
   whether they came from the manifest or from a default.
4. **Given** a dataset the author marked as not permitted for training, **When** the author
   trains, **Then** the run is refused, naming the field that forbids it, and nothing is trained.
5. **Given** a dataset that does not exist at the path the manifest names, **When** the author
   trains, **Then** the run fails naming the path, and the message says the reference was not
   resolved rather than reporting an internal error.
6. **Given** training that diverges to a non-finite loss, **When** it does, **Then** the run fails,
   says so, and leaves no trained-model artifact behind.

---

### User Story 2 - See the model before paying for training (Priority: P2)

Before spending training time, the author asks what the manifest actually describes: the input and
output shape and how many parameters the model has. They get an answer in seconds plus the time to
read the dataset once — the dataset's version is part of what identifies the result, and it is a
hash of its bytes, about a second per gigabyte — and they get the same artifact the training stage
will consume.

**Why this priority**: a template parameter that is wrong by an order of magnitude is cheapest to
notice here. It is also the structural half of the pipeline — training needs a model to train —
so it has to exist regardless; separating it means the author can use it on its own.

**Independent Test**: run the build command on the pilot manifest and on a manifest with an absurd
hidden-layer width, and confirm the reported shapes and parameter counts differ as expected.

**Acceptance Scenarios**:

1. **Given** the pilot manifest, **When** the author builds, **Then** the input shape, the output
   shape and the parameter count are reported and recorded, and the built model is written as a
   run artifact.
2. **Given** a manifest whose template parameters are valid but implausible, **When** the author
   builds, **Then** it still succeeds and the parameter count makes the implausibility visible —
   building is not a quality judgement.
3. **Given** a built model, **When** the author trains with the same manifest, **Then** the
   training stage consumes that artifact rather than rebuilding it from scratch.

---

### User Story 3 - Do not retrain for a change that cannot affect training (Priority: P2)

The author fixes a typo in the intended-use text, or adds a known limit, and runs the pipeline
again. Nothing retrains: the previous result is reused, and the report says it was reused. When
they change a hidden-layer width, the seed or the dataset, it does retrain.

**Why this priority**: the constitution requires it (Principle III), and training is the first
stage expensive enough for it to matter. Without it, the honest habit of keeping compliance text
current becomes a reason to avoid touching the manifest.

**Independent Test**: train, edit a field no stage reads, train again and confirm the result was
reused; then edit a field the stage reads and confirm it retrained.

**Acceptance Scenarios**:

1. **Given** a completed training run, **When** the author edits compliance text or the
   publication target and trains again, **Then** the previous result is reused and the report
   records the reuse.
2. **Given** a completed training run, **When** the author changes a template parameter, the seed,
   a training setting or the dataset version, **Then** the model is retrained.
3. **Given** a completed training run, **When** the author asks explicitly for a fresh run,
   **Then** it retrains and the report records that the reuse was bypassed deliberately.

---

### User Story 4 - Install the tool without a training framework and still get a clear answer (Priority: P3)

A contributor installs the default package to check manifests. They try to train, and are told in
one sentence that training needs a separately installed extra, which extra it is, and that their
manifest was not the problem.

**Why this priority**: it is the layering rule of Principle XII made visible to a user instead of
only to a test. The failure it prevents — a stack trace about a missing module — is the first
impression a new contributor would otherwise get.

**Independent Test**: with the training framework absent, run build and train and confirm the exit
status, the message naming the extra, and the absence of a traceback.

**Acceptance Scenarios**:

1. **Given** only the default installation, **When** the author builds or trains, **Then** the
   command exits with the status that means "your environment is missing something", not the one
   that means "your manifest broke a rule", and the message names the extra to install.
2. **Given** only the default installation, **When** the author checks or resolves a manifest,
   **Then** it works exactly as before — the layering checks of feature 001 pass unchanged.
3. **Given** the training extra installed, **When** the author trains, **Then** the framework and
   its version are recorded in the run report.

---

### Edge Cases

- The dataset exists but its labels disagree with the manifest's: rejected, naming both sets.
- The dataset has fewer samples than the split needs, so a part would be empty: rejected, because
  a part with no data cannot be trained on, tuned on or measured against.
- The dataset's feature width disagrees with what the manifest's window implies: rejected, naming
  both numbers.
- A window spans a change of label: discarded, and counted as discarded in the report.
- Every window spans a change of label, so nothing is left to train on: rejected, naming how many
  records were read and how many windows were discarded.
- A cell is empty or not a number: rejected, naming the file, the record and the column.
- The dataset is a directory: its files are read in sorted name order as one sequence, so a window
  may not straddle two files unless they are consecutive in that order.
- `patience` is zero with early stopping on: a stated behaviour, not an accident.
- Training is interrupted: no trained-model artifact is left behind, and the report says the run
  did not finish.
- The same manifest is trained twice with the same seed: the report records the seed, and the
  claim made about reproducibility is only the one that holds — see Assumptions.
- The cache would be reused but the previous run's artifacts have been deleted: it retrains rather
  than failing.
- The dataset changes while the manifest does not: the dataset version is part of the cache key,
  so it retrains.
- Two runs of the same manifest land in the same second: handled by feature 001 — a run never
  overwrites another's directory.

## Requirements *(mandatory)*

### Functional Requirements

**Building a model**

- **FR-001**: The tool MUST provide a command that constructs the model described by the manifest's
  template and parameters, and writes it as an artifact of the run.
- **FR-002**: Building MUST report the input shape, the output shape and the parameter count, and
  MUST record them in the run report.
- **FR-003**: Building MUST NOT train, evaluate or judge the model. An implausible but valid
  parameter set MUST build successfully, with the parameter count left to speak for itself.
- **FR-004**: Building MUST read the dataset's shape to determine the input, and MUST NOT read the
  dataset's contents. The manifest MUST NOT be required to restate a shape the dataset already
  carries.

**Training a model**

- **FR-005**: The tool MUST provide a command that trains a built model on the dataset the manifest
  names, using the manifest's epochs, batch size, optimizer, learning rate, early-stopping setting,
  patience and seed.
- **FR-006**: Training MUST write the trained model, the best checkpoint by the validation metric
  and the final checkpoint into the run directory.
- **FR-006a**: The quality metrics MUST be measured on the validation split, because the model was
  selected on it, and on the test split, because it is the reference. They MUST NOT be measured on
  the training split: a number from data the model fitted is not evidence, and reporting it beside
  the others invites the comparison.
- **FR-007**: Every quality metric MUST state what it was measured against: which split, and which
  dataset version. A metric without that statement MUST NOT be reported.
- **FR-008**: The effective value of every training setting MUST be recorded, whether it came from
  the manifest or from a default.
- **FR-009**: Training MUST be refused when the manifest states that the dataset is not permitted
  for training, naming the field that forbids it. This is the author's own statement, enforced.
- **FR-010**: The dataset reference MUST be resolved here: a path that does not exist, cannot be
  read, or holds no usable data MUST fail with the path named and the reason stated. What the
  reference points at is specified under *Reading the dataset* below.
- **FR-011**: A dataset that disagrees with the manifest MUST be rejected, naming both sides of
  the disagreement — at minimum its label names against the manifest's labels, in both directions,
  and too few records to fill a single window against the window the manifest states. The manifest
  declares no feature width, so there is nothing for the data's feature count to disagree with:
  the width comes from the data (FR-004), and two files that disagree with *each other* about
  their columns are the rejection that replaces it.
- **FR-012**: A run that fails, diverges to a non-finite loss, or is interrupted MUST leave no
  trained-model artifact, and its report MUST say that the run did not finish.
- **FR-013**: A dataset MUST NOT be written into the repository. The only committed data is the
  synthetic fixture the tests need.

**Reusing a result**

- **FR-014**: A stage result MUST be reused when the manifest fields that stage reads and the
  dataset version are unchanged.
- **FR-015**: A change to a field the stage does not read MUST NOT cause retraining. Editing
  compliance text or the publication target MUST reuse the previous result.
- **FR-016**: The run report MUST record the key the reuse decision was made on, and whether the
  result was reused or produced.
- **FR-017**: The author MUST be able to ask for a fresh run explicitly, and that request MUST be
  recorded in the report. This is a cache bypass, not a gate being silenced: every rule still runs.
- **FR-018**: A reusable result whose artifacts are missing MUST cause a fresh run rather than a
  failure.

**The training extra**

- **FR-019**: The default installation MUST NOT require or load a training framework, and the
  layering checks of feature 001 MUST pass unchanged.
- **FR-020**: Building and training without the extra installed MUST fail with a message naming
  the extra to install, and with the status that means the environment is incomplete rather than
  the one that means a rule was broken. No traceback MUST reach the user.
- **FR-021**: The extra's Python window MUST be stated with its reason, and MUST NOT narrow the
  default installation. Packaging has no per-extra window, so the window MUST be expressed as all
  three of: a published floor that admits it, an environment marker on every dependency the extra
  carries, and a message naming the window and the reason when a stage is run outside it. Every
  version the published floor admits MUST be tested — a floor that is claimed and not tested is a
  false claim (Principle XII, conditions 1 to 4, constitution v2.3.0).
- **FR-022**: The framework and its version MUST be recorded in the run report of any run that
  used it.

**Reading the dataset**

- **FR-023**: A dataset reference MUST resolve to raw, record-level tabular data in delimited text
  form — one file, or a directory whose files are read in sorted name order as one continuous
  sequence. Each file MUST carry a header row. One column MUST be named `label` and MUST hold the
  class name; every other column MUST be a numeric feature, taken in the order the header gives.
  A cell that is missing or not a number MUST be rejected, naming the file, the record and the
  column.
- **FR-024**: When the manifest states a window, a sample MUST be that many consecutive records in
  sequence order, and windows MUST NOT overlap. When the manifest states no window, one record
  MUST be one sample — a path no manifest can reach at 0.1.0, because the only registered template
  requires a window, so it is proven by a direct test of the rule rather than through a manifest.
- **FR-025**: A window whose records do not all carry the same label MUST be discarded rather than
  given a label it cannot be known to have, and the number of windows discarded for that reason
  MUST be recorded in the run report alongside the number kept.

### Key Entities

- **Built model**: the untrained model as the template constructs it, with its shapes and parameter
  count; an artifact of a build run and the input of a training run.
- **Trained model**: the model after training, with the metrics that describe it.
- **Checkpoint**: a saved state of training — the best by validation metric, and the final one.
- **Quality metric**: a number about the model's behaviour, inseparable from the split and dataset
  version it was measured against.
- **Dataset**: raw, record-level data outside the repository, referenced by the manifest, resolved
  for the first time in this feature, carrying a version and a shape.
- **Sample**: what the model sees — one window of consecutive records, or one record when the
  manifest states no window. Windowing happens here, not before the tool is called.
- **Stage result**: what a stage produced, together with the key that decides whether it can be
  reused.
- **Training extra**: the separately installed part that carries the template's builder half and
  the training framework.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pilot manifest builds and trains end to end on the synthetic fixture in under 60
  seconds on an ordinary laptop, with no network access.
- **SC-002**: A successful training run leaves every promised artifact: built model, trained model,
  best checkpoint, final checkpoint, metrics, resolved manifest and report.
- **SC-003**: 100% of the quality metrics in a run report name their split and their dataset
  version.
- **SC-004**: Editing compliance text and training again performs no training at all, and the
  report says the result was reused.
- **SC-005**: Changing a template parameter, the seed, a training setting or the dataset version
  retrains, in every one of those four cases.
- **SC-006**: With no training framework installed, building and training both exit with the
  environment-incomplete status and a message naming the extra; no traceback appears.
- **SC-007**: The default installation still pulls no training framework, and the dependency and
  extras budgets still hold.
- **SC-008**: Every disagreement between dataset and manifest in the test library is rejected with
  both sides named.
- **SC-009**: The repository contains no dataset other than the synthetic fixture, and the fixture
  is under 200 KB.
- **SC-010**: The fixture contains at least one window that spans a change of label, and the run
  report states how many windows were discarded and how many were kept.

## Constitution Alignment

| Principle | How this feature complies |
|---|---|
| I. Declarative Manifest | Training settings come from the manifest only; no per-model script, no notebook in any stage. |
| III. Reproducible by Construction | FR-008 records every effective setting; FR-014 to FR-018 implement the stage cache the principle requires; the seed is recorded and the reproducibility claim is limited to what holds (Assumptions). |
| IV. Measured, Emulated or Estimated | No hardware number is produced, so no provenance label is claimed. FR-007 applies the same habit to quality metrics: a number is inseparable from what it was measured against. |
| V. Budgets Are Gates | No budget is evaluated in this feature. FR-017's cache bypass is explicitly not a gate being silenced, and is recorded. |
| VI. Compliance Enforced by the Schema | FR-009 enforces the author's own statement about what their data permits — the whole of what the framework claims about data rights. |
| VII. Targets and Templates Are Data | The template's builder half registers alongside its parameter half; adding a template still edits no central list. |
| VIII. No Lock-In | Training runs locally; no stage in this feature touches the network. |
| IX. Stable Manifest Contract | The schema gains no field in this feature, so the contract is untouched: the dataset's format is a convention the data meets, not a field the manifest restates. |
| X. Built for Real Models | `picket-mlp` drives everything here; `conv1d` waits for `pace-cnn`. |
| XI. No Claude in Model Learning | Nothing in this feature uses Claude to produce, label or judge data. The training run records the framework that produced its outputs. |
| XII. Small Core, Few Dependencies | FR-019 to FR-022: the framework lives in one extra, the core keeps its budget, and the extra's narrower Python window is stated with its reason. |

Deviations: none.

## Assumptions

- **The reproducibility claim is deliberately narrow.** Training on the same seed is not promised
  to be bit-identical: thread counts, kernel implementations and hardware make that untrue in
  general, and claiming it would be the kind of overstatement Principle IV exists to prevent. What
  is promised: the seed and every effective setting are recorded, and the fixture training is
  reproducible on one machine within a stated tolerance. Bit-exactness becomes meaningful at the
  quantized model, which is the next feature's business.
- **The quality metrics are a fixed, documented set for classification** — accuracy, macro
  precision, recall and F1, per-class recall, and the confusion matrix. The manifest does not
  choose them yet; a field for that can arrive when a model needs something this set does not
  cover. Adding a schema field speculatively would be the churn Principle IX warns about.
- **Building reads the dataset's shape, not its contents** (FR-004), so that the input shape has
  one source of truth. The alternative — declaring the feature width in the manifest — lets the
  manifest and the data disagree, and then one of them is wrong without anyone knowing.
- The synthetic fixture stands in for the real dataset in every test. The real HCRL Car-Hacking
  data is never committed, and the author's own training runs use their copy of it.
- The `train` extra's Python window is 3.13 because TensorFlow publishes no stable wheel for 3.14 or
  3.15 (checked 2026-10-22). Planning found that this costs more than the spec first assumed:
  packaging has no per-extra Python window, so the published floor moves to 3.13 as well, and 3.13,
  3.14 and 3.15 are all tested — see research R1 and Principle XII as amended in constitution
  v2.3.0. The default installation gains a version rather than losing one, and the floor returns to
  3.14 when the framework ships for the current Python.
- No hardware, emulator or accelerator is needed to develop or test this feature. A CPU is enough
  for the fixture.
- **The dataset is raw and record-level, and Caravan windows it** (FR-023, FR-024). The
  alternative — pointing at arrays somebody else already windowed — would make `dataset.window` a
  claim about work done elsewhere, which the tool could not keep honest. The cost is accepted: the
  tool reads a text format rather than a prepared one, and the author keeps their raw data.
- **A window whose records disagree about the label is discarded** (FR-025) rather than labelled by
  majority or by its last record. Both of those invent a label for a sample that genuinely has
  two, and a tie in a majority rule has no honest answer. Discarding loses a small number of
  boundary windows, and the report says how many — which is the same habit Principle IV applies to
  measurements. If the ported model needs the boundary windows, this is the decision to revisit.
- **The label column is named `label`, and every other column is a feature.** The manifest gains no
  field for this: a convention the data must meet is cheaper than a schema the manifest must
  restate, and Principle IX warns against fields added before a model needs them.
