<!--
Sync Impact Report
==================
Version change: 2.0.1 → 2.1.0
Bump rationale: MINOR. Owner direction of 2026-10-22: the zoo's dataset-declaration regime fits
the zoo, but a framework that requires it makes every other user adopt one project's compliance
machinery before they may use the tool at all. Principle VI demanded exactly that. The obligation
moves to where the data comes from — the author — and what Caravan enforces changes from "a
declaration exists" to "the author's own statements are kept, and an unverified claim is marked
unverified".

Nothing that was compliant becomes non-compliant, so this is MINOR rather than MAJOR: resolving
declarations stays permitted, it is merely no longer required of the framework.

Modified principles:
- VI. Compliance Is Enforced by the Schema: the usage class is derived from what the manifest
  states and marked unknown where terms are unstated; a dataset reference needs a statement, not
  a registry entry; stated terms are enforced against the author; a project may require
  declarations as its own policy, and the framework may not require one of everybody.

Previous report: 2.0.0 → 2.0.1
Bump rationale: PATCH. Resolves the one deferred item and adds no rule: the distribution on the
package index is named `caravan-ml`, decided by the owner on 2026-10-22 after a check showed the
bare name `caravan` held by an unrelated project whose last release was in 2015 (an AWS SWF
helper, MIT). The command line application keeps the name `caravan`.

Modified sections:
- Technical Baseline: TODO(DISTRIBUTION_NAME) replaced by the decided name.

Previous report: 1.1.0 → 2.0.0
Bump rationale: MAJOR, and the bump type is a judgement call the owner may overrule. Seven of
the eight amendments below are additions (MINOR). The eighth redefines the central obligation of
Principle IX: an older manifest is migrated rather than refused. An implementation built to
satisfy 1.1.0 by refusing old manifests violates 2.0.0, so practice that was compliant is
non-compliant now — the test this constitution's own governance section sets for MAJOR. Read as
an extension of IX rather than a redefinition, this is 1.2.0 instead; nothing else in the
amendment set would change.

Source: the research note docs/research/2026-10-22-prior-art-learnings.md, section F, applied on
owner approval of 2026-10-22. Each amendment closes a trap that a cited source shows is real.

Modified principles:
- I. Declarative Manifest: no defaults or inheritance section; defaults resolve from the template
  and the board description only (Ludwig's defaults block, note A3).
- IV. Provenance labels: a memory figure derived from the model graph is `estimated` by
  definition and carries the margin applied; a figure from the runtime's own allocation report is
  `emulated` or `measured` by where it ran (TFLM arena, note C1).
- V. Budgets Are Gates: peak activation memory is reported with the layer that causes it, and a
  failed accuracy gate emits the per-layer quantization error table (MCUNetV2 note B1, TF
  quantization debugger note C4).
- VII. Targets and Templates Are Data: emulator support is stated honestly, `none` included, with
  its source; an accelerated kernel library named by a board is a build-level claim, so the
  export records per operator whether an accelerated kernel was linked and emits a minimal
  operator resolver (CMSIS-NN note C2, Renode note C3).
- IX. Stable Manifest Contract: the framework carries a registered migration per schema version
  and upgrades an older manifest in memory, never rewriting the user's file; refusal is reserved
  for a version it does not know (Ludwig's migration registry, note A1).

Modified sections:
- Pipeline & Artifact Contract: every run writes the fully resolved manifest beside its report
  (note A4).
- Target Hardware & the Verification Ladder: hardware benchmarks follow an established public
  protocol so results are comparable outside this project (MLPerf Tiny, note D).
- Technical Baseline: the runtime is named TFLM / LiteRT for Microcontrollers, the converter
  toolchain is pinned by package and version in the provenance record, and format identifiers
  avoid vendor product names (LiteRT rename, note E1).

Added sections: none. Removed sections: none.

Previous reports, newest first:
- 1.0.0 → 1.1.0 (MINOR, 2026-10-22): added Principle XII (Small Core, Few Dependencies) on owner
  direction, from having contributed to Ludwig — a dependency and install budget, a layering rule
  keeping the training framework out of the core, and integrations only behind a removable
  boundary. Its numbers (six direct runtime dependencies, four extras) are the owner's to set;
  changing one is a PATCH amendment.
- none → 1.0.0 (MAJOR, 2026-10-22): first ratified constitution for a new repository. Its
  principle and section lists, and the decisions it took on the design document's open questions,
  follow below and still await review.

Source of this draft: the Caravan design document of 2026-10-22 (context, positioning,
decisions, repo layout, manifest schema, pipeline stages, roadmap, open questions) and the
mobility-model-zoo constitution v3.0.0, whose rules carry over where both projects apply.

Added principles:
- I. Declarative Manifest, One Model per File
- II. Embedded Targets Only
- III. Reproducible by Construction
- IV. Measured, Emulated or Estimated — Always Labeled
- V. Budgets Are Gates, Not Warnings
- VI. Compliance Is Enforced by the Schema
- VII. Targets and Templates Are Data, Not Forks
- VIII. No Lock-In: Portable Artifacts, Local Execution
- IX. Stable Manifest Contract
- X. Built for Real Models
- XI. No Claude in Model Learning or Extraction

Added sections: Project Scope & Relationship to the Mobility Model Zoo; Pipeline & Artifact
Contract; Target Hardware & the Verification Ladder; Technical Baseline; Resources & Cost
Discipline; Development Workflow & Quality Gates; Governance.

Removed sections: none.

Decisions this draft takes on open questions of the design document, for the owner to confirm
or overrule in review:
- Q3 (latency heuristic): answered by Principle IV. Estimates are allowed and MUST carry the
  provenance label `estimated`; latency MUST NOT be reported as `measured` without a physical
  board.
- Q4 (schema stability): answered by Principle IX. `caravan/v0` is explicitly unstable, unknown
  fields are rejected rather than ignored, and breaking changes are documented migrations.
- Q5 (compliance field): answered by Principle VI. The simplified EU AI Act class stays a
  required enum, extended by a required free-text `intended_use` and `known_limits`; a review
  flag is deliberately NOT introduced, because the release gate already requires owner approval.
- Q6 (templates enum vs plugin): answered by Principle VII. Templates are a registry from the
  start; v0.1 registers only `mlp` and `conv1d`.
- Q2 (HF token handling): answered by "Resources & Cost Discipline" and the publish gate.
  Credentials come from the environment only; a publish run that reads them from the repository
  MUST fail.
- Q1 (PyPI distribution name): deferred in 1.0.0, resolved in 2.0.1 as `caravan-ml`.
- Q7 (forest template) and Q8 (Renode board coverage) are implementation questions, not
  governance; they belong in the spec of the feature that introduces them.

Deferred items: none remain. The one deferred item of 1.0.0, TODO(DISTRIBUTION_NAME), was
resolved in 2.0.1 as `caravan-ml`.
-->

# Caravan Constitution

Caravan is an open, declarative pipeline framework for small machine learning models that run on
microcontrollers and other constrained hardware. One YAML manifest per model describes what is
to be built; the pipeline does the rest: architecture from a template, training, int8
quantization, TFLite and C-array export, footprint analysis against a target board, emulated
verification, hardware benchmark, model card and publication.

Caravan is the build tool for the embedded models of the Mobility Model Zoo
(https://github.com/mhabedank/mobility-model-zoo) and lives in its own repository under
Apache-2.0, so that models built with it stay portable and the framework stays usable outside
the zoo. Its goal is not a better neural architecture search than research projects achieve; its
goal is a pipeline that is reproducible, honest about its numbers and usable by someone who owns
one board.

## Core Principles

### I. Declarative Manifest, One Model per File

- One model version is described by exactly one manifest file. The manifest describes **what** is
  built, never **how** it is built in code.
- Model architecture MUST come from a registered template plus parameters. A manifest MUST NOT
  carry executable code, model definitions, shell commands or file paths outside its declared
  fields.
- Running the pipeline for a model MUST NOT require editing framework code. If a model cannot be
  expressed in the manifest, the gap is a missing template, target or field, and is fixed in the
  framework, not in a per-model script.
- Notebooks MUST NOT be part of the workflow of any pipeline stage. They MAY be used for
  exploration, and their findings enter the framework as code and tests.
- Every field MUST have either a documented default or be required by the schema. A minimal
  manifest (model, dataset, export, compliance) MUST be sufficient to run the pipeline.
- There MUST NOT be a defaults section, an inheritance mechanism or any other way for one part of
  a manifest to set values for another. Defaults resolve from exactly two places: the template
  and the board description.

Rationale: Hand-built models in notebooks are what the framework exists to replace. A manifest
that can hold code would drift back into the same unreproducible state within two models. The
ban on a defaults section comes from Ludwig, where type-global defaults overridden per feature
produced a hierarchy whose own documentation has to warn about repeated type keys, silently
ignored settings and a scope that covers only part of the configuration.

### II. Embedded Targets Only

- In scope: models that run on microcontrollers and comparable constrained hardware — time series
  and feature models for CAN bus intrusion detection, GNSS and V2X attack detection, motion and
  activity recognition, machine condition monitoring, battery state of health, and the like.
- Out of scope, explicitly: cloud, desktop and LLM or text models of the zoo (the `scout` and
  `cairn` families and their successors). They are built and released without Caravan.
- Out of scope, explicitly: becoming an inference runtime, a SoC or peripheral description
  language, a cycle-accurate simulator, or a research-grade neural architecture search.
- A feature that serves only out-of-scope models MUST be rejected, however small it is.

Rationale: The usable scope is the product. A framework that also tries to be an LLM pipeline
toolkit serves neither well, and a narrow target class is what makes budgets, footprints and
board verification meaningful at all.

### III. Reproducible by Construction

- Every artifact MUST be reproducible from versioned configuration: the manifest, the pinned
  dataset version and the pinned framework and toolchain versions. Reproduction MUST NOT require
  undocumented local state.
- Every stage that involves randomness MUST take its seed from the manifest and MUST record the
  effective seed in its output.
- Every artifact MUST carry a provenance record: Caravan version, manifest hash, dataset
  identifier and version, template identifier, converter and compiler versions, and the date of
  the run.
- Stage results MUST be cached by a key derived from the manifest fields that stage reads plus
  the dataset version. A change that a stage does not read MUST NOT invalidate it; editing
  compliance text or a model card MUST NOT trigger retraining.
- Where the toolchain allows it, repeated runs MUST produce byte-identical exported model files.
  Where it does not, the deviation MUST be documented and the resulting metric variance reported.

Rationale: The zoo promises reproducible, dated releases. A pipeline whose outputs depend on the
machine it ran on cannot keep that promise, and caching by a precise key is what keeps an honest
pipeline fast enough to use.

### IV. Measured, Emulated or Estimated — Always Labeled

- Every number Caravan reports about a model's behaviour on hardware MUST carry exactly one
  provenance label:
  - `estimated` — derived analytically from the model graph, a cost model or a heuristic;
  - `emulated` — produced by a simulator or emulator, with the platform description named;
  - `measured` — produced on a named physical board, with firmware and clock settings recorded.
- The label MUST appear wherever the number appears: machine-readable run reports, the model card
  and any published table. A number without a label MUST NOT be rendered.
- Latency, throughput and energy MUST NOT be reported as `measured` unless they come from a
  physical board. Emulation results MUST NOT be presented as hardware results.
- Estimates are permitted and useful. Where a measurement for the same model and board exists,
  the card MUST report the measurement, and MAY report the estimate beside it with its error.
- A claim that a model fits a board MAY rest on `estimated` or `emulated` evidence only while it
  is labeled as such.
- A memory figure derived from the model graph is `estimated` by definition, whatever the quality
  of the derivation, and MUST be reported together with the safety margin applied to it. The
  margin MUST be policy, documented once, not a per-model guess.
- A memory figure taken from the runtime's own allocation report is `emulated` or `measured`
  according to where that runtime ran. The generated runner MUST obtain it from the runtime
  rather than recomputing it.

Rationale: The model cards are the product of the zoo, and their value is that the numbers are
honest. A heuristic estimate is a fine starting point; an unlabeled one is a false measurement.
The rule for memory is not pessimism about our own analysis: the arena a TFLM model needs cannot
be derived from the exported file, and the runtime's own report of it is documented to omit
scratch buffers and the memory planner's working memory, so it can read lower than the smallest
arena that works. An estimate is therefore the honest ceiling of static analysis, and the margin
is part of the number.

### V. Budgets Are Gates, Not Warnings

- Every manifest MUST state the quality and footprint budgets that matter for its model: the
  maximum accuracy loss accepted from quantization, and the target boards whose memory and flash
  it must fit.
- A violated budget MUST fail its stage with a non-zero exit code and a machine-readable reason.
  It MUST NOT be reported as a warning and MUST NOT produce exportable artifacts.
- Budget thresholds live in the manifest. There MUST NOT be a command-line flag, environment
  variable or configuration switch that skips or silences a gate. Loosening a budget is an edit
  to the manifest, visible in version control.
- A stage that cannot determine whether a budget holds MUST fail, not pass. Unknown is not
  within budget.
- Peak activation memory MUST be reported together with the layer that causes it. An aggregate
  figure alone MUST NOT be the output of the analysis stage.
- A failed gate MUST emit what is needed to act on it, not only a verdict: a failed accuracy gate
  MUST emit the per-layer quantization error table, and a failed footprint gate MUST emit the
  per-layer memory profile.
- Automatic scaling of a template to fit a budget, where implemented, MUST record what it
  changed and MUST remain subject to the same gates.

Rationale: Warnings are read once and then never again. A gate that can be silenced by a flag
becomes a gate that is always silenced, and the budget is the entire reason an embedded model is
built the way it is. Peak memory is named with its layer because it is concentrated, not spread:
in most convolutional designs the first few blocks use an order of magnitude more memory than the
rest, so one early tensor decides whether a model fits, and that tensor is the only thing a
contributor can act on.

### VI. Compliance Is Enforced by the Schema

- The compliance block is a required part of every manifest: risk class, privacy class, intended
  use and known limits. A manifest without it is invalid, not merely incomplete.
- A publish stage MUST refuse any model whose compliance block is missing or whose required
  fields are empty, and MUST refuse before any network call is made.
- Restrictions carry over from inputs to the model: the usage class of a model is the most
  restrictive of its training data, base model, teacher outputs and third-party models. Caravan
  MUST derive the usage class from what the manifest states about those inputs, MUST write it into
  the model card and release record, and MUST NOT allow publication under a license less
  restrictive than the class it derives. Where an input's terms are unstated, the usage class is
  `unknown`, and Caravan MUST mark it `unknown` wherever it appears rather than assume the
  author's chosen license is supported.
- Responsibility for the rights to the data lies with whoever brings the data. Caravan MUST
  require the author to **state** what their data permits; it MUST NOT require that the statement
  resolve against a declaration registry, because demanding one project's compliance machinery of
  every user is a form of lock-in (Principle VIII) and would put a framework between a user and
  their own data.
- What Caravan does enforce is the author's own statements, which costs a user nothing who makes
  none: a dataset the manifest marks as not permitted for training MUST NOT be usable as training
  data by any stage, and a model trained on it MUST NOT be publishable. An unstated term is
  reported as unverified, in the run report and on the model card, and MUST NOT be rendered as a
  checked fact.
- A project MAY require more of itself — resolution against its own declarations, a licence
  whitelist, a review step — and MUST be able to express that as its own policy on top of
  Caravan. Caravan MUST NOT hard-code one project's policy as the framework's rule.
- Datasets, raw source data and credentials MUST NOT be stored in the repository.
- Publication MUST be an explicit, separately invoked stage. No other stage may upload anything.

Rationale: "Compliance comes first" only holds if it is mechanical. A required schema field is
checked on every run by every contributor; a review checklist is checked when someone remembers.
But mechanical is not the same as omniscient, and the line between them is what the framework may
honestly claim. Caravan cannot know whether a licence statement is true, so it does not pretend to
check one: it insists the author says something, holds them to what they said, and marks the rest
as unverified so that nobody downstream mistakes silence for a clean bill. The zoo's stricter
regime — declarations with origin, licence and permitted use, resolved before a dataset may be
used — remains the zoo's, enforced by the zoo's own release gate, where it belongs.

### VII. Targets and Templates Are Data, Not Forks

- A new target board MUST be added as one declarative board description. Adding a board MUST NOT
  require changes to framework code.
- A board description MUST carry every value the analysis and export stages read (core, clock,
  memory, flash, accelerated kernels, interfaces, toolchain and emulator support), and MUST record
  the source of each value, so a datasheet claim can be checked.
- Templates MUST be a registry: a template is a module that registers itself under a stable
  identifier and validates its own parameters. Adding a template MUST NOT require editing a
  central enumeration of templates.
- Model requirements MUST be derived from the model, not from the board: the analysis stage
  produces a hardware requirement record ("needs at least this much memory and flash, needs an
  FPU, needs int8 kernels") which is then resolved against the board descriptions.
- A board description MUST state its emulator support as it is, including none, and MUST name the
  source of that claim. An emulator platform MUST NOT be named in a board description unless it
  exists.
- An accelerated kernel library named by a board description is a claim about the build, not
  about the model: acceleration is selected per operator and can depend on operand shapes, and an
  operator without an accelerated kernel falls back to the reference implementation silently.
  The export stage MUST therefore record, per operator of the converted graph, whether an
  accelerated kernel is linked for the target, and MUST emit an operator resolver containing
  exactly the operators the model uses.
- Where a third party supplies a board description or template, it MUST pass the same validation
  and the same gates as a built-in one.

Rationale: The board matrix and the model families both grow, and they grow fastest when growth
costs a data file rather than a pull request to the core. Deriving requirements from the model
also lets a contributor find out what hardware a model needs before buying any.

### VIII. No Lock-In: Portable Artifacts, Local Execution

- Exported artifacts MUST be standard formats that are usable without Caravan: a TFLite
  flatbuffer, a plain C array with its header, and a runner skeleton that builds with the board's
  own open toolchain.
- A model built with Caravan MUST remain deployable by someone who does not use Caravan. The
  export MUST document the runtime, the operator set and the tensor arena size it requires.
- No stage required to build, train, quantize, export, analyze or verify a model may depend on a
  hosted service. Publication to a model hub is optional and is the only stage allowed to require
  network access.
- Caravan MUST run on a single developer machine with no accounts, no license keys and no
  registration.

Rationale: The zoo's models are meant to run on the user's own hardware; a build tool that binds
them to a service would undo that at the source. It is also the difference between this framework
and the commercial tools it is an alternative to.

### IX. Stable Manifest Contract

- Every manifest MUST declare the schema version it is written against. A manifest that declares
  none MUST be treated as the oldest version the framework knows.
- The framework MUST carry one registered migration per schema version and MUST upgrade an older
  manifest to the current version in memory on every load. It MUST NOT rewrite the user's file.
  The run report MUST record both the declared version and the effective version after migration.
- Refusal is reserved for a declared version the framework does not know. It MUST then name the
  versions it implements.
- Unknown or misspelled fields MUST be rejected with the field path and the accepted values. A
  manifest MUST NOT be silently reinterpreted and unknown input MUST NOT be ignored.
- While the schema version is `v0`, breaking changes are permitted, but each one MUST ship its
  migration together with a note that names the affected fields and the change required.
- From the first stable schema version onward, a breaking change requires a new schema version,
  and its migration MUST exist before the change is released. A manifest that validated under a
  published stable version MUST keep loading through migration.
- Validation errors MUST be actionable: field path, what was wrong, what is accepted.

Rationale: The manifest is the public interface of the framework and it is also the archival
record of how a published model was built. Silent reinterpretation of an old manifest would
quietly break the reproducibility the zoo relies on — but refusing it is no better, because it
turns the record of every published model into dead weight the moment the schema moves. Ludwig
settled this by keeping the framework version inside the configuration and running a registry of
per-version transforms on every load, on a copy; migrating in memory and never rewriting the file
is cheap to add while the registry is empty and expensive to retrofit after the first migration
is needed.

### X. Built for Real Models

- Every stage, template, board description and manifest field MUST be driven by a named model
  that needs it, in the zoo or from a named external need. Speculative generality MUST NOT be
  built.
- `picket-mlp` is the pilot model. The first version of the framework is complete when that model
  is built, exported and documented entirely through the pipeline.
- A shared abstraction MUST be extracted only when a second model needs it, not in advance.
- A feature whose only justification is parity with another tool MUST be rejected.
- Scope creep is a constitution matter: a change that widens the framework beyond the stages and
  targets its roadmap names MUST be justified in its spec against Principle II.

Rationale: A framework built ahead of its users fits none of them. Growing it against one real
model at a time is also what keeps the first release reachable.

### XI. No Claude in Model Learning or Extraction

Claude means every model of Anthropic's Claude family, under any name and through any access
path: consumer apps, Claude Code, the Anthropic API, cloud platforms and resellers.

- Caravan MUST NOT contain a stage, template, default, example or documented workflow in which
  Claude produces training data, labels, synthetic or augmented data, teacher or distillation
  outputs, evaluation judgments, or any signal used for model selection, threshold tuning or
  architecture search.
- Caravan MUST NOT be used to replicate, imitate or approximate Claude's capabilities, behaviour
  or outputs.
- Where a run records the models that produced its inputs, a run that records a Claude model MUST
  fail its gate.
- Claude MAY be used as a development assistant for the framework itself: code, tests, specs,
  plans, documentation and compliance records. What it writes in that role MUST NOT become model
  input data.
- This principle carries over from the zoo constitution (v3.0.0, Principle XI) and admits no
  deviation. A plan that would violate it is rejected, not justified.

Rationale: The owner rules out any use of Claude for building or teaching other AI. A tool that
builds models must make that ban structural, not a matter of how each user happens to use it.

### XII. Small Core, Few Dependencies

- The feature set is closed by the roadmap. The command line interface has one fixed set of
  verbs, and adding a verb requires an amendment.
- Dependency budget: the default installation MUST have at most six direct runtime dependencies,
  and the project MUST have at most four optional extras, grouped by stage (training,
  verification, benchmarking, publication).
- Layering: manifest validation, the board database, footprint analysis, the requirement record,
  card rendering and release records MUST NOT import a training framework. Training and
  quantization live behind an optional extra. A test MUST assert that importing the core does not
  import the training framework, and MUST fail the build when it does.
- Install budget: a cold installation of the default package into a clean environment MUST stay
  within a documented time and size budget, measured in continuous integration and gated like any
  other budget (Principle V).
- Python versions: the project MUST support the current and the previous stable Python minor
  version. A dependency that prevents that is replaced, vendored in the small, or moved behind an
  extra. A dependency MUST NOT set the project's Python policy.
- The published distribution MUST NOT carry an upper version bound on a dependency unless a
  concrete incompatibility is documented with a reference, and the bound MUST be removed once it
  is fixed upstream.
- Integrations (experiment trackers, pipeline orchestrators, model hubs, hyperparameter search)
  are optional extras behind a stable internal interface. The core MUST NOT import them, and
  removing one MUST NOT change the behaviour of any stage. An integration that cannot be removed
  without editing stage code MUST be rejected, however useful it is.
- Code the project could own in a few hundred readable lines MUST NOT become a dependency, and a
  dependency used in one place MUST be isolated behind one module.

Rationale: Ludwig, the framework that inspired this one, declares 40 direct dependencies, 140
including its ten extras, and requires Python 3.12 or newer. The owner of this project
contributed to Ludwig and found that weight to be the dominant cost of working on it: a Python
version bump stayed blocked because too many transitive dependencies did not work. Every rule
above is aimed at that outcome. A small, well-executed feature set is the product here; an
integration that drags the core along with it is a defect, not a feature.

## Project Scope & Relationship to the Mobility Model Zoo

- Caravan and the zoo are separate repositories with separate release cycles. The zoo depends on
  Caravan; Caravan MUST NOT depend on the zoo, and MUST NOT contain zoo-specific model code,
  datasets or credentials.
- The zoo pins the Caravan version it builds with, and records that version in the release record
  of every model built through the pipeline.
- Where both constitutions apply to a model published through Caravan, the zoo constitution
  governs and the stricter rule wins. Caravan's constitution MUST NOT be amended into conflict
  with it; if a conflict appears, the amendment is rejected and reported.
- Caravan MAY be used outside the zoo. Features that only the zoo needs belong in the zoo.
- The framework proceeds iteratively: each version delivers one usable step of the pipeline, and
  each step is exercised end to end by the pilot model before the next is added.

## Pipeline & Artifact Contract

- The pipeline is a sequence of stages: build, train, quantize, analyze, verify, bench, card,
  publish. Each stage MUST be separately invocable and MUST be resumable from the artifacts of the
  stage before it.
- A stage MUST declare the artifacts it reads and writes. Communication between stages goes
  through declared artifacts on disk, never through hidden global state.
- Every run MUST write a machine-readable report containing its inputs, its provenance record
  (Principle III), its results with provenance labels (Principle IV) and its gate outcomes.
- Every run MUST write the fully resolved manifest beside its report: every default expanded,
  every template and board value applied, as it was actually used. It is an artifact of the run,
  not an optional command, so that two runs can be compared field by field.
- The command line interface is the contract for users and for continuous integration. Its exit
  codes MUST distinguish a failed gate from a crash.
- The model card MUST be rendered from the manifest and the run reports. A card MUST NOT be
  hand-edited into a release, and a number MUST NOT reach a card except through a report.
- A failed gate MUST leave no publishable artifact behind.

## Target Hardware & the Verification Ladder

- Verification proceeds in rungs, each with its own provenance label: analysis on the development
  machine (`estimated`), emulation of the target platform (`emulated`), and the physical board
  (`measured`).
- Emulation verifies that the firmware builds, that the model loads, that the tensor arena fits
  and that inference results match the host reference. It MUST NOT be used for timing claims.
- Hardware benchmarks are the only source of latency, throughput and energy numbers. They MAY be
  run manually and MUST record the board, firmware, clock and toolchain.
- Hardware benchmarks MUST follow an established public protocol rather than one invented here,
  so that results are comparable outside this project: a stated minimum duration and iteration
  count per run, the median of a stated number of runs, a single inference stream, and a
  measurement window that excludes pre- and post-processing. The protocol and its source MUST be
  named in the report.
- A board whose emulator support is experimental or missing MUST say so in its description, and a
  model targeting it MUST be verified on the next rung available.
- The target matrix is open and grows by board description (Principle VII). Boards already on the
  bench come first; a new board is justified in the spec that adds it.

## Technical Baseline

These choices are architectural and apply until amended with a stated rationale:

- Inference runtime on target: TensorFlow Lite for Microcontrollers, now documented as LiteRT for
  Microcontrollers, with CMSIS-NN kernels, chosen for portability across the whole target matrix.
  Caravan does not implement a runtime (Principle II).
- Training and conversion: Keras/TensorFlow with post-training int8 quantization as the default
  deployment format. The converter toolchain MUST be pinned by package name and version in the
  provenance record, because which package provides it is moving.
- Identifiers that outlive a release — schema field values, format names, artifact names — MUST
  NOT be vendor product names. A product rename would otherwise become a schema migration.
- Interface: a Python command line application. Manifest validation uses a schema library with
  strict, typed models.
- Emulation: Renode, using its own declarative platform descriptions. Caravan does not define a
  platform description language of its own.
- Footprint analysis reads the exported model file as data: the flatbuffer is parsed through a
  pinned schema binding, never by importing the training framework (Principle XII), and never
  rewritten, because a round-tripped flatbuffer can fail to load. The binding is pinned because
  operator definitions change between runtime versions.
- Hyperparameter search, when introduced, treats the board budget as a constraint rather than an
  objective, and is bounded by the roadmap, not by research ambition.
- License: Apache-2.0 for the framework, so that both framework and models stay commercially
  usable; model licenses follow Principle VI.
- The command line application is named `caravan`; the distribution on the package index is
  named `caravan-ml`. The bare name is held by an unrelated project whose last release was in
  2015, and reclaiming it is not a dependency of any release.

## Resources & Cost Discipline

- Work MUST use local compute first, then a flat-rate subscription, then pay-per-use services.
  Choosing a more expensive tier MUST be justified in the plan.
- Continuous integration runs unit tests and emulated verification. Hardware benchmarks run on
  the hardware-in-the-loop bench, through a self-hosted runner when one is registered, or
  manually with the results recorded.
- Hardware purchases follow the pilot: a board is bought when a planned model targets it. Boards
  already owned are used before new ones are acquired.
- Credentials for publication MUST come from the environment of the run. A stage MUST fail if it
  finds credentials in the repository, in a manifest or in a board description, and MUST NOT
  write a credential into a report, a log or a model card.
- Every spec that incurs cash cost MUST state a cash budget, and any key used MUST carry a hard
  spending limit at or below it.

## Development Workflow & Quality Gates

- Every spec and every plan MUST list the principles it touches and state how it complies. The
  plan's constitution check MUST be verified before design work and again after it.
- Gate before merging a change to a stage: unit tests for the changed behaviour pass, and the
  pilot manifest runs end to end through every implemented stage in continuous integration.
- Gate before merging any change: the layering test passes (no training framework reachable from
  the core) and the install budget holds (Principle XII).
- Gate before adding a dependency or an extra: the spec names what it replaces, why the code
  cannot be owned in a few hundred lines, which extra it belongs to, that the budget still holds,
  and that it does not constrain the Python policy (Principle XII).
- Gate before adding a board description: every field the implemented stages read is present, and
  the source of each value is recorded.
- Gate before reporting a number: the number carries its provenance label (Principle IV) and
  comes from a run report, not from a person.
- Gate before a framework release: the version follows semantic versioning, the manifest schema
  compatibility statement is present, migration notes exist for every breaking schema change, and
  the pilot manifest runs green.
- Gate before the publish stage runs: compliance complete, usage class derived and no less
  restrictive than the chosen license, all budget gates passed, provenance labels present, and
  credentials supplied by the environment.
- Gate before any labeling, data generation or evaluation run: no model in the run is Claude
  (Principle XI).
- Any deviation from a principle MUST be documented in the plan with a rationale and the simpler
  alternative that was rejected. Principle XI admits no deviation.

## Governance

- This constitution takes precedence over other practices and guidance in this repository.
- Where the zoo constitution also applies, it governs and the stricter rule wins (see "Project
  Scope & Relationship to the Mobility Model Zoo").
- Amendments require a written rationale and a version bump, recorded with the amendment.
- Versioning follows semantic versioning:
  - MAJOR: a principle is removed or redefined in a backward-incompatible way, or governance
    rules change incompatibly.
  - MINOR: a principle or section is added, or guidance is materially expanded.
  - PATCH: clarifications, wording and typo fixes that do not change meaning, and resolution of a
    deferred TODO that adds no new rule.
- Compliance review: every spec, plan and review MUST check compliance with the principles it
  touches. Non-compliance blocks the gate in question until it is resolved or justified as a
  documented deviation.

**Version**: 2.1.0 | **Ratified**: 2026-10-22 | **Last Amended**: 2026-10-22
