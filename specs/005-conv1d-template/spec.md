# Feature Specification: The conv1d Template

**Feature Branch**: `005-conv1d`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "The conv1d template: both halves, driven by pace-cnn."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Describe a convolutional model in a manifest (Priority: P1)

An author with a window of sensor samples wants a convolutional network rather than a stack of
dense layers, because the signal has shape in time and a convolution can use it. They write a
template identifier and a few parameters in the manifest, and the pipeline builds, trains,
quantizes and exports it exactly as it does the dense one.

**Why this priority**: It is the feature. Everything else here is a consequence of it, and it is
the last item v0.1 is waiting on.

**Independent Test**: Write a manifest naming the template, run the pipeline on the committed
synthetic fixture, and get a quantized, exported model.

**Acceptance Scenarios**:

1. **Given** a manifest naming the convolutional template with valid parameters, **When** it is
   validated, **Then** it is accepted and the resolved manifest shows the parameters with their
   defaults filled in.
2. **Given** that manifest, **When** the model is built, **Then** the report names the layers, the
   input and output shapes and the parameter count.
3. **Given** that model, **When** the pipeline runs through training, quantization and export,
   **Then** every stage behaves as it does for the existing template: the gate judges, the export
   writes its artifacts, and no stage needs a special case for this template.
4. **Given** a parameter the template cannot accept, **When** the manifest is validated, **Then**
   the rejection names the parameter, the value and what is accepted there.

---

### User Story 2 - Know what the architecture costs on the target (Priority: P1)

The author's choices here decide what the firmware must contain. A pooling head that saves
parameters can add an operator the board's accelerated library has no kernel for. The author needs
that visible from the artifacts the pipeline already produces, not from folklore.

**Why this priority**: It is what makes this template a *TinyML* template rather than a Keras
snippet. The export stage already records operators and coverage; this story is the requirement
that the template's choices show up truthfully there.

**Independent Test**: Export two models that differ only in the pooling head and compare the
recorded operator sets and coverage verdicts.

**Acceptance Scenarios**:

1. **Given** an exported convolutional model, **When** the export record is read, **Then** the
   operator set is the one the file contains, with each operator's node count.
2. **Given** a head that reduces over time, **When** coverage is recorded, **Then** the operator it
   introduces is recorded as a reference fallback on every built-in board, with its source and date.
3. **Given** the generated resolver, **When** it is read, **Then** each operator appears once, in
   the spelling the runtime uses.
4. **Given** two heads, **When** their records are compared, **Then** the difference in parameter
   count and in operator set is visible in the artifacts without running anything on hardware.

---

### User Story 3 - Serve the model that asked for the template (Priority: P2)

The template exists because a named model needs it. It has to express that model's shape — a window
of 128 samples across 9 channels, six classes — and it has to work at the committed fixture's much
smaller scale too, because the acceptance test may not use the real dataset.

**Why this priority**: Principle X: a template is built when a named model needs one. A template
that could not express the model that motivated it would be a guess with a test suite.

**Independent Test**: Build the template at both shapes and check the input and output shapes and
the parameter count in each report.

**Acceptance Scenarios**:

1. **Given** a window of 128 samples and 9 channels with six labels, **When** the model is built,
   **Then** its input and output shapes match and the parameter count is recorded.
2. **Given** the committed fixture's smaller window and fewer labels, **When** the model is built,
   **Then** it builds without a change to the parameters' meaning.
3. **Given** a window too short for the configured receptive field, **When** the manifest is
   validated or the model is built, **Then** it is refused with a message naming the window, the
   configuration that needs more of it, and what would fit.

---

### User Story 4 - Add a template without touching the core (Priority: P2)

Whoever adds the next template should not have to edit a list in the middle of the project. This
one is the proof that the registry built in feature 001 works as designed: a template is two files
and a registration, discovered rather than enumerated.

**Why this priority**: The claim was made in feature 001 and tested with a throwaway registration.
This is the first real second template, which is a different kind of evidence.

**Independent Test**: Add the template, run the listing command, and see it with its summary —
without any central file having changed.

**Acceptance Scenarios**:

1. **Given** the new template's two halves, **When** the templates are listed, **Then** it appears
   with a one-line summary saying what it is for.
2. **Given** the new template, **When** the core is imported in an installation with no training
   framework, **Then** nothing fails and the parameters still validate.
3. **Given** the registry, **When** the template is looked up, **Then** no central list of
   templates was edited to make that work.

---

### Edge Cases

- A window shorter than the configured receptive field: refused, naming the window and what would
  fit, rather than failing inside the framework with a shape error.
- A single convolution block with no pooling: valid, and the commonest small configuration.
- Pooling configured so that the sequence reaches length zero before the head: refused for the same
  reason as a too-short window, because it is the same arithmetic.
- The flattening head on a long window: valid, and the parameter count shows what it cost; the
  report is where the author sees that, not a warning.
- A channel count of one: valid — a single-channel window is still a window.
- Dropout at zero: no dropout layer appears at all, as in the existing template, because a
  zero-rate layer is noise in a per-layer table.
- The fixture's labels differ in number from the named model's: both work; the label count comes
  from the dataset section, not from the template.

## Out of Scope

The port of the named model, and anything that needs its dataset: that happens where the data is,
and no dataset enters this repository (Principle IX). The model card's figures. Any claim about the
accuracy or the latency of a model built here before it has been trained and measured where the
real data is. A second dataset fixture. Transfer learning, pre-trained weights. And every
architectural feature the named model does not need: dilation, residual connections, attention,
more than one input, more than one output head.

## Requirements *(mandatory)*

### Functional Requirements

**The template, and its two halves**

- **FR-001**: The project MUST provide a convolutional template, identified in a manifest by name,
  whose parameters are validated by the template itself.
- **FR-002**: The parameter half MUST be usable in an installation with no training framework: it
  validates a manifest, and validating a manifest needs no framework.
- **FR-003**: The builder half MUST be loaded by name when a stage needs it, and MUST NOT be
  imported by the core.
- **FR-004**: Registering the template MUST NOT require editing any central list of templates.
- **FR-005**: The listing of templates MUST show it with a one-line summary of what it is for.

**The parameters, and what they must express**

- **FR-006**: The parameters MUST express a sequence of convolution blocks, each with its own filter
  count and kernel width, because the named model's shape is a sequence of blocks.
- **FR-007**: The parameters MUST express optional downsampling between blocks.
- **FR-008**: The parameters MUST express the choice of head that turns the convolved sequence into
  a per-class score, with at least the two measured alternatives: reducing over time, and
  flattening.
- **FR-009**: The parameters MUST express optional normalisation inside a block, and optional
  dropout, with zero meaning the layer does not appear.
- **FR-010**: Every parameter MUST have a stated default where a default is meaningful, and the
  resolved manifest MUST show the effective value.
- **FR-011**: A rejected parameter MUST be named individually: which block, which value, and what
  is accepted there — not a complaint about the whole list.
- **FR-012**: The parameters MUST NOT offer anything the named model does not need (Principle X);
  the specification's out-of-scope list is the boundary.

**Shapes, and refusing what cannot be built**

- **FR-013**: The template MUST build for the named model's shape: a window of 128 samples across 9
  channels, with six labels.
- **FR-014**: The template MUST build for the committed fixture's shape, so the acceptance test
  needs no dataset that is not in this repository.
- **FR-015**: A configuration whose receptive field exceeds the window MUST be refused with a
  message naming the window, the configuration and what would fit.
- **FR-016**: A configuration that reduces the sequence to nothing before the head MUST be refused
  the same way.
- **FR-017**: The number of labels MUST come from the dataset section and not from the template's
  parameters.

**What the pipeline must say about it**

- **FR-018**: The build report MUST record the layers, the input and output shapes and the parameter
  count, in the same form as for the existing template.
- **FR-019**: The export record MUST carry the operator set the produced file contains, read from
  the file, with each operator's node count.
- **FR-020**: An operator this template introduces for which a board's accelerated library supplies
  no kernel MUST be recorded as a reference fallback, with the source and the date of that claim.
- **FR-021**: The generated resolver MUST name each of the template's operators exactly once, in the
  spelling the runtime uses.
- **FR-022**: No new resolver method mapping MUST be required for this template; a test MUST assert
  that every operator it can produce is already mapped, rather than leaving it to chance.

**Everything the pipeline already does, unchanged**

- **FR-023**: Every stage MUST treat this template as it treats the existing one: no stage may carry
  a special case for a template identifier.
- **FR-024**: The stage cache MUST apply: a changed parameter produces a new model, an unread field
  does not.
- **FR-025**: The accuracy gate MUST apply unchanged, and MUST be able to fail a run of this
  template.
- **FR-026**: The dependency and extras budget MUST be unchanged by this feature.

### Key Entities

- **Convolution block**: one stage of the architecture — a filter count, a kernel width, optional
  normalisation, optional downsampling, optional dropout.
- **Head**: what turns the convolved sequence into one score per class. The choice is the author's
  and its cost is recorded.
- **Template parameters**: the typed, validated set of blocks and head options, with defaults, that
  a manifest may carry for this template.
- **Receptive field**: how much of the window the configuration consumes; the quantity the refusals
  of FR-015 and FR-016 are computed from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manifest naming the template validates, renders, builds, trains, quantizes and
  exports end to end on the committed synthetic fixture, with the accuracy gate passing.
- **SC-002**: The template builds for the named model's shape — 128 samples, 9 channels, six labels
  — and for the fixture's shape, with both parameter counts recorded.
- **SC-003**: 100% of the operators the template can produce are already mapped to a resolver
  method, asserted by a test rather than assumed.
- **SC-004**: The exported operator set equals an independent reading of the exported file, for each
  of the two heads.
- **SC-005**: Every operator of an exported model has a coverage verdict for every target board,
  and each verdict carries its source and its date.
- **SC-006**: A configuration whose receptive field exceeds the window is refused with the window,
  the configuration and a fitting alternative all named, and nothing is built.
- **SC-007**: Each invalid parameter is refused with its own name and position, not as a list-level
  complaint, for every parameter the template has.
- **SC-008**: The parameter half validates manifests in an installation with no training framework,
  asserted in that installation.
- **SC-009**: No stage, command or report contains a branch on a template identifier.
- **SC-010**: The dependency count, the extras count and the default installation's size are
  unchanged from before this feature.

## Constitution Alignment

- **Principle I (own little code)**: the template is two small files over machinery that already
  exists; no new dependency.
- **Principle IV (no unverified claim)**: the operator consequences stated here were measured by
  converting and reading the file (see the research of this feature), and the named model's figures
  are quoted from the zoo's own measured records with their benchmark and date. Nothing here claims
  an accuracy or a latency for a model this project has not trained.
- **Principle V (budgets are gates)**: the accuracy gate applies unchanged and can fail this
  template's runs.
- **Principle VII (templates are data-like)**: a template is two files and a registration, not an
  edit to a central list (FR-004).
- **Principle X (build what a named model needs)**: every parameter traces to the named model's
  architecture; the out-of-scope list names what was left out because nothing needs it yet.
- **Principle XII (the layering rule)**: the parameter half imports no training framework (FR-002),
  the builder half is loaded by name (FR-003), and the budget is untouched (FR-026).

## Assumptions

- **The convolution is one-dimensional to the author and two-dimensional to the runtime.** Measured
  2026-10-22 with TF 2.21.0 at the named model's input shape, read back from the produced file: a
  one-dimensional convolution is converted to a two-dimensional one with a dummy spatial dimension
  added and removed by reshapes, and the runtime's resolver has no one-dimensional convolution at
  all. The template is therefore described to the author in one dimension, and the artifacts record
  what the file contains. The alternative — naming the template after the operator the file ends up
  with — would describe the machine to the author instead of the model.
- **The head is a parameter because its cost is real and goes both ways.** Measured on one
  two-block architecture at the named model's shape: reducing over time gives 6 distinct operators
  in 8 nodes, 7,920 bytes and 2,502 parameters; flattening gives 5 distinct operators in 7 nodes,
  12,896 bytes and 7,878 parameters. The reduction introduces an operator for which neither
  built-in accelerated library supplies a kernel, so it trades three times fewer parameters for one
  more operator on the reference implementation. Neither is the right default for everyone, so the
  author chooses and the export records what the choice cost.
- **Normalisation inside a block is offered because it is free at inference.** Measured the same
  day: it folds entirely into the preceding convolution — no additional operator, 648 bytes of
  folded weights. Offering it costs the author nothing on the target and can cost a great deal in
  training time saved.
- **Separable convolution is not offered yet.** It was measured — it adds a depthwise operator
  beside the pointwise one, and both are accelerated on both built-in libraries, so it would be
  cheap — but the named model does not need it, and Principle X says a template grows when a model
  asks. Recorded here so that the next model to want it finds the measurement rather than repeating
  it.
- **The committed fixture is the acceptance dataset.** The named model's real dataset never enters
  this repository (Principle IX), so the end-to-end test runs at the fixture's scale and the named
  model's shape is checked by building, not by training. What a Caravan-built version of that model
  actually achieves is measured where the data is, and this feature claims nothing about it.
- **The named model's own 0.1.0 is not what this reproduces.** Its measured figures come from the
  zoo's own int8 engine, not from the runtime this project targets. A version built through this
  pipeline is a new version, as the roadmap already records, and comparing the two is work for the
  place that has the data.
