# Feature Specification: Export

**Feature Branch**: `004-export`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Export: the artifacts a microcontroller actually needs, and the proof of what they contain."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get the set of artifacts a firmware author can actually use (Priority: P1)

An author has a model that passed the accuracy gate. What they need next is not a Python object: it
is a file they can flash, a C source form of it they can compile into firmware, and a statement of
what the runtime on the board must be able to execute. One command produces all of it into the run
directory, or refuses and says why.

**Why this priority**: Without this the pipeline stops one step short of its purpose. Everything
before it produces a model that only Caravan can open; this is the step that makes it somebody
else's to deploy, which is the whole claim of Principle VIII.

**Independent Test**: Run the command on the pilot fixture after quantization and check the run
directory holds the serialised model, a C array with its header, and a record of what the model
needs. Delete Caravan from the machine afterwards and the artifacts are still usable.

**Acceptance Scenarios**:

1. **Given** a run whose quantized model passed the gate, **When** the export command runs, **Then**
   the run directory holds the serialised model, a C array with a header declaring its length, and
   a report naming every artifact with its size and digest.
2. **Given** a manifest that names an export format this feature does not implement, **When** the
   command runs, **Then** it refuses with the named rule and the format, and writes no artifact —
   it does not quietly export the formats it does know.
3. **Given** a run whose quantized model failed the accuracy gate, **When** the export command
   runs, **Then** it refuses, because there is nothing a failed gate may hand to a board.
4. **Given** the same quantized model exported twice, **When** the two C arrays are compared,
   **Then** they are byte for byte identical.

---

### User Story 2 - Know what the model really needs, not what a tool on a laptop adds (Priority: P1)

The resolver the firmware links decides which kernels exist on the device. It must contain exactly
the operators of the model: one too few and inference fails on the board, one too many and flash
pays for a kernel nothing calls. The author needs that list to come from the model, not from
whatever a desktop tool did while loading it.

**Why this priority**: The failure is silent in the worst direction. A resolver built from a
desktop interpreter's node list contains a delegate node that exists only on the desktop; the
firmware would be built against an operator the target's runtime has never heard of. This is the
same error as the converter's log line in feature 003, in a different tool.

**Independent Test**: Read the operator set from the model file with no training framework
installed, and compare it with what the desktop interpreter reports. The two differ, and the
export agrees with the file.

**Acceptance Scenarios**:

1. **Given** a quantized model, **When** the export reads its operator set, **Then** the set comes
   from the model file and carries each operator's name, its builtin code and its version.
2. **Given** the same model loaded by a desktop interpreter that inserts a node of its own,
   **When** the two lists are compared, **Then** the export's list does not contain that node.
3. **Given** the operator set, **When** the resolver is emitted, **Then** it names exactly those
   operators, each exactly once, and nothing else.
4. **Given** a model containing an operator that is not a built-in one, **When** the export runs,
   **Then** it records the operator by its custom name and states that a custom kernel must be
   supplied, rather than emitting a resolver that pretends it is built in.

---

### User Story 3 - Ship the graph that was measured (Priority: P1)

The accuracy gate of feature 003 measured a model. If export shipped a differently shaped graph,
the gate's numbers would describe something other than the artifact, and the author would be
deploying a model whose accuracy nobody measured.

**Why this priority**: It is the honesty of every number upstream. It also happens to make the
exported model smaller and its operator set shorter, but that is the bonus, not the reason.

**Independent Test**: Export the pilot fixture and compare the operator set and the byte size of
the exported model with the one the quantize stage measured. They are the same model.

**Acceptance Scenarios**:

1. **Given** a trained model whose input batch is not fixed, **When** it is converted for a target,
   **Then** the conversion fixes the batch to one, because a board runs one window at a time.
2. **Given** a model converted with the batch fixed, **When** its predictions are compared with the
   float model's on the same inputs, **Then** they agree exactly before quantization — fixing the
   batch is a reshaping of the graph, not a change to the function.
3. **Given** a run, **When** the exported model and the model the gate measured are compared,
   **Then** they are the same bytes.
4. **Given** the change to the conversion, **When** the quantize stage runs again, **Then** its
   recorded operator count and model size are the new ones, and the report says what it measured.

---

### User Story 4 - See where the accelerated kernels actually apply (Priority: P2)

A board description says it has an accelerated kernel library. That is a claim about the build, not
about the model: acceleration is chosen per operator, and an operator with no accelerated kernel
falls back to the reference implementation without saying so. The author needs to see, per
operator, which side of that line it falls on — before they are surprised by a latency figure.

**Why this priority**: It changes what an author expects rather than what they can build, so it
ranks below the artifacts themselves. But it is a constitutional requirement and the one place
where a board's `accel` field stops being decoration.

**Independent Test**: Export for the three built-in boards and read the coverage record: every
operator of the model appears once per target, with a verdict and the source of that verdict.

**Acceptance Scenarios**:

1. **Given** a target board that declares an accelerated library, **When** the export runs, **Then**
   the report states for every operator of the graph whether that library supplies a kernel for it.
2. **Given** an operator with no accelerated kernel, **When** the export runs, **Then** the
   fallback to the reference implementation is recorded as a fallback, not omitted.
3. **Given** a coverage verdict, **When** the report is read, **Then** the verdict names the source
   it came from and the date that source was read.
4. **Given** two targets with different accelerated libraries, **When** the export runs, **Then**
   coverage is recorded per target, because the answer differs between them.

---

### User Story 5 - Find out what is still the author's job (Priority: P2)

The export cannot build firmware: it does not know the author's board bring-up, their sensor code
or their build system. What it can do is hand over a runner skeleton and an honest list of what
remains — which runtime, which operators, which working memory figure, and which of those numbers
this stage is not entitled to state.

**Why this priority**: It is what turns a pile of artifacts into something a person can act on, and
it is where this feature states its own limits rather than implying it has none.

**Independent Test**: Read the emitted skeleton and the requirements record; every value the author
must supply is named, and no value is presented as measured when it was computed on a desktop.

**Acceptance Scenarios**:

1. **Given** a target board, **When** the export runs, **Then** the emitted skeleton names the
   runtime that board declares and references the emitted resolver and C array.
2. **Given** the requirements record, **When** it is read, **Then** it names the runtime, the
   operator set, and the working-memory figure the author must set, each labelled with where the
   value came from.
3. **Given** the working-memory figure, **When** it is read, **Then** it is labelled as a floor
   computed from the model file on a desktop, and the record states that the figure a board needs
   is established by measurement, not here.
4. **Given** the emitted skeleton, **When** the report is read, **Then** nothing claims the
   skeleton has been compiled, because nothing in this feature compiles it.

---

### Edge Cases

- A manifest names a format this feature does not implement (`onnx`): refused by name, with no
  partial export. The same shape of refusal as the unimplemented quantization settings of feature
  003.
- A manifest names several target boards whose accelerated libraries differ: coverage is recorded
  per target; the artifacts that do not depend on the target are written once.
- A manifest names a target board whose description declares no accelerated library: coverage says
  so for every operator, which is a verdict and not a gap.
- The model contains a custom operator: recorded as custom, with the resolver stating that the
  author must register a kernel for it.
- The model has more than one subgraph: refused rather than exporting the first one, because a
  resolver for one subgraph of several is wrong in a way nothing downstream would notice.
- The quantized model of the run is missing, because the gate failed or the stage never ran: the
  export refuses and names which stage must run first.
- The same run is exported twice: the second one reuses the stored result, as every stage does.
- An operator appears many times in the graph: the resolver names it once, and the coverage record
  states both how many nodes use it and the single verdict for that operator.

## Out of Scope

Footprint analysis, emulated verification, hardware benchmarks, the model card and publication —
each is its own stage. The `conv1d` template. Board-specific build files for each toolchain. ONNX
and any other export format beyond the serialised model and its C form. Compiling, linking or
running the emitted skeleton. And any claim about latency, flash use or working-memory use on a
target: this stage reads a file on a desktop and says what it read.

## Requirements *(mandatory)*

### Functional Requirements

**The artifacts**

- **FR-001**: The tool MUST provide a command that writes the export artifacts of a run for the
  formats the manifest names, into the run directory, leaving the inputs untouched.
- **FR-002**: The serialised model MUST be written as a run artifact, byte for byte the model the
  accuracy gate measured.
- **FR-003**: The C array MUST be a source file holding nothing but bytes of `unsigned char`, with
  a header that declares the array and its length, compilable on its own with no Caravan-specific
  include and no framework type anywhere in it. It is compiled by the same toolchain as the runtime
  that consumes it, which is C++; the *array* is plain, the file is not C89 (research R3).
- **FR-004**: The C array MUST round-trip: the bytes it declares MUST equal the bytes of the
  serialised model.
- **FR-005**: The C array MUST be deterministic — the same model exports to identical bytes, with no
  timestamp, path or hostname in it.
- **FR-006**: A format the manifest names which this feature does not implement MUST fail the run
  with its own named rule and the format's name, and MUST leave no artifact of any format.
- **FR-007**: The report MUST name every artifact written, with its size in bytes and its digest.
- **FR-008**: A run whose quantized model does not exist, or whose accuracy gate failed, MUST be
  refused, naming the stage that has to run first.

**The operator set and the resolver**

- **FR-009**: The operator set MUST be read from the model file. A list obtained from a runtime that
  loaded the model MUST NOT be used for it.
- **FR-010**: The report MUST record, for every operator of the graph, its name, its builtin code,
  its version and how many nodes use it.
- **FR-011**: The emitted resolver MUST name exactly the operators of the graph, each exactly once,
  and MUST NOT name any other.
- **FR-012**: A custom operator MUST be recorded by its custom name, and the resolver MUST state
  that the author has to register a kernel for it.
- **FR-013**: A model with more than one subgraph MUST fail the run with its own named rule rather
  than exporting one subgraph.
- **FR-014**: The report MUST record the number of nodes as well as the number of distinct
  operators, because the resolver's length is the second and the graph's cost is the first.

**The graph that ships is the graph that was measured**

- **FR-015**: Conversion MUST fix the model's input batch to one.
- **FR-016**: Fixing the batch MUST NOT change the function the model computes: the fixed-batch
  model's predictions MUST equal the trained model's on the same inputs, before quantization.
- **FR-017**: The exported model MUST be the same bytes as the model the accuracy gate of feature
  003 measured.
- **FR-018**: The quantize stage's recorded figures MUST describe the fixed-batch graph, since that
  is the graph that is measured and exported.

**Accelerated kernel coverage**

- **FR-019**: For every target the manifest names and every operator of the graph, the report MUST
  record whether the accelerated library that target declares supplies a kernel for that operator.
- **FR-020**: Each coverage verdict MUST carry the source it came from and the date that source was
  read.
- **FR-021**: An operator with no accelerated kernel MUST be recorded as falling back to the
  reference implementation.
- **FR-022**: A target whose description declares no accelerated library MUST produce a stated
  verdict for every operator, not an absent one.
- **FR-023**: Coverage MUST NOT be presented as a statement about speed. It states which kernel is
  available to be linked, and nothing about how long anything takes.

**What the author must still supply**

- **FR-024**: The export MUST emit a runner skeleton that names the runtime the target board
  declares and references the emitted resolver and C array.
- **FR-025**: The report MUST state the runtime, the operator set and the working-memory figure
  required to run the model, each labelled with the source of the value.
- **FR-026**: The working-memory figure MUST be labelled as a floor computed from the model file on
  a desktop, and the report MUST state that the figure a target actually needs is established by
  measurement in a later stage.
- **FR-027**: Nothing in the report or the artifacts MUST claim the skeleton has been compiled,
  linked or run.

**Provenance, caching and the layering rule**

- **FR-028**: Every number this stage records MUST state what it was measured or computed against,
  and by what means.
- **FR-029**: The stage MUST reuse its stored result when the manifest fields it reads and its
  upstream result are unchanged, and MUST record whether the result was produced or reused.
- **FR-030**: A change to a field this stage does not read MUST NOT cause a new export.
- **FR-031**: Reading the model file, deriving the operator set, emitting the resolver and the C
  array, and recording coverage MUST all work with no training framework installed.
- **FR-032**: The default installation MUST NOT require either the conversion framework or the
  runtime, and the project MUST stay within its budget of dependencies and extras.

### Key Entities

- **Export set**: the artifacts of one run for one manifest — the serialised model, the C array and
  its header, the resolver, the skeleton — each with a size and a digest.
- **Operator record**: one operator of the graph: name, builtin code, version, node count, and
  whether it is built in or custom.
- **Coverage verdict**: one (target, operator) pair: covered or falling back, with the source and
  the date of the claim.
- **Requirements record**: what a firmware author must supply — runtime, operator set, working
  memory — each with the provenance of the value and, where the value is a floor, that label.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pilot fixture exports end to end after quantization, writing the serialised model,
  the C array with its header, the resolver and the skeleton, in under 30 seconds.
- **SC-002**: The operator set the export records equals the set read independently from the model
  file, and differs from the desktop interpreter's node list — asserted, not assumed.
- **SC-003**: The emitted resolver names exactly the distinct operators of the graph: no operator
  missing, none added.
- **SC-004**: The generated array source and header compile standing alone with a host C++
  compiler, and the array's bytes equal the serialised model's — the equality checked on the bytes,
  not on a length. The resolver is not compiled here: it includes the runtime's headers, which this
  feature does not vendor, and compiling it is emulated verification's job.
- **SC-005**: Two exports of the same model produce identical bytes for every generated file.
- **SC-006**: 100% of the operators of the graph have a coverage verdict for every target the
  manifest names, and 100% of those verdicts carry a source and a date.
- **SC-007**: The exported model and the model the accuracy gate measured are the same bytes, and
  the fixed-batch graph's float predictions equal the trained model's exactly.
- **SC-008**: Every number in the export report names what it was computed or measured against, and
  no figure about a target's behaviour appears anywhere in it.
- **SC-009**: The proving half — reading the model, the operator set, the resolver, the C array and
  coverage — runs green in an environment with no training framework installed.
- **SC-010**: Exporting a manifest that names an unimplemented format exits with the rule status,
  names the format, and leaves the run directory with no export artifact in it.

## Constitution Alignment

- **Principle IV (no unverified claim)**: the operator set is read from the file rather than from a
  tool's description of it (FR-009), and the working-memory figure carries the label of what it is
  (FR-026). The feature states where it is not entitled to a number (FR-023, FR-027).
- **Principle V (budgets are gates)**: the export happens only for a model that passed the accuracy
  gate (FR-008); nothing here can route around it.
- **Principle VII (boards are data)**: the accelerated library comes from the board description, and
  its coverage is recorded per operator as a build claim (FR-019 to FR-022).
- **Principle VIII (no lock-in)**: the artifacts are a standard serialised model, a plain C array
  with its header, and a runner skeleton (FR-002, FR-003, FR-024), and the export documents the
  runtime and the operator set it requires (FR-025).
- **Principle XII (the layering rule)**: the proving half needs no training framework (FR-031), and
  the default installation stays as light as it is (FR-032).
- **Open against Principle VIII**: that principle also requires the export to document "the tensor
  arena size it requires". No desktop tool can supply that figure — the runtime plans that memory
  with its own allocator on the target, and the model-analysis tool available here reports model and
  buffer sizes and no arena (checked 2026-10-22). This specification therefore documents a floor and
  says where the real figure comes from (FR-026). If the principle means a measured figure, it needs
  an amendment naming the stage that can honestly supply it. The plan's constitution check decides
  which, and the decision is written down either way.

## Assumptions

- **The batch is fixed at conversion, not at build.** Training keeps a dynamic batch, because
  training one window at a time would change both the speed and the dynamics of training. The
  trained model is cloned onto a batch of one before conversion. Verified 2026-10-22: the clone's
  float predictions are bit-identical to the trained model's, maximum absolute difference 0.0,
  checked on an mlp and on a conv1d model; the converted result falls from six distinct operators to
  three and from 8,656 to 7,856 bytes. The alternative — converting a concrete function with a
  fixed signature — does not work: the graph keeps variable-reading nodes and calibration fails with
  `variable != nullptr was not true` (TF 2.21.0).
- **This changes feature 003's recorded numbers.** The quantize stage converts, so fixing the batch
  changes what it measures and reports. That is the point: the gate's numbers now describe the
  artifact that ships. The alternative, converting twice, would mean two models and two accuracies,
  and the one that shipped would be the one nobody gated.
- **The operator set is read through the schema binding that ships with the runtime extra.** It
  needs no training framework, which is what lets the proving half run everywhere the runtime
  installs. The alternative, vendoring a schema binding of our own, is a dependency and a pin for
  something already present.
- **Coverage is a static table per accelerated library, sourced and dated, not a probe.** Whether a
  kernel is *selected* can depend on operand shapes at build time; what this stage records is
  whether the library supplies a kernel for the operator at all. Recording the stronger claim would
  need the toolchain, which belongs to a later stage. The weaker claim is stated as the weaker
  claim (FR-023).
- **The skeleton is emitted, not validated.** No ARM or Xtensa toolchain is installed here and the
  runtime is not vendored, so compiling it is not possible in this feature and would be an
  unverified claim if asserted. Compiling and running belong to emulated verification.
- **`onnx` stays declared in the schema and refused by the stage.** Removing it from the schema
  would be a breaking schema change for a format the roadmap still intends; accepting it silently
  would be worse. A named refusal is the same pattern the unimplemented quantization settings use.
- **The export writes the model again under its own name.** The run already holds the quantized
  model from feature 003, with identical bytes. The export set is what an author takes away, so it
  carries its own copy next to the array, the header and the resolver rather than a reference into
  another stage's output. Fifteen kilobytes against a self-contained set of artifacts is the right
  trade; the report records both paths and their shared digest so the duplication is visible.
- **One artifact set per run, with target-dependent parts per target.** The serialised model, the C
  array and the resolver do not depend on the board; coverage and the skeleton's runtime do. The
  layout follows that split rather than copying everything per target.
