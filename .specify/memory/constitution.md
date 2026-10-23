<!--
Sync Impact Report
==================
Version change: 3.0.0 → 4.0.0
Bump rationale: MAJOR. Principle IX is redefined incompatibly: the migration it required for every
schema version is no longer required before Caravan 1.0.0. Source: the owner's decision of
2026-10-23 — "wir machen erst eine backward compatibility, wenn wir bewusst auf 1.0.0 sind, vorher
ist alles variabel" — after feature 006 had shipped a full caravan/v0 → caravan/v0.1 migration that
Principle IX 3.0.0 demanded.

Modified principles:
- IX. Stable Manifest Contract → IX. Manifest Contract: Variable Until 1.0.0, Stable From It.
  Before 1.0.0 the schema, CLI, run report and artifacts may change without migration or
  compatibility. Kept in every phase: a declared schema version, no rewrite of the user's file,
  rejection of unknown fields with path and accepted values, actionable errors, and refusal (never
  reinterpretation) of a manifest whose version the build does not implement, now including an
  undeclared version, which used to be read as the oldest. A breaking change still gets a new
  version identifier and a change note. 1.0.0 is a deliberate amendment; from it, the former
  migration rules apply in full.

Modified sections:
- Technical Baseline: "would otherwise become a schema migration" → "a breaking schema change".
- Development Workflow: the release gate asks for a change note per breaking schema change, and
  from 1.0.0 also its migration.

Unchanged on purpose: Principle III (the Caravan version in every provenance record, which is what
keeps an old manifest reproducible without migration), Principle XI.

Follow-up (not done by this amendment):
- Feature 006 (PR #11): remove the caravan/v0 → caravan/v0.1 migration, its notices in validate,
  render and the run report, the `.notices.json` fixtures and the migration fixture directory;
  refuse caravan/v0 and an undeclared version with the change note; rewrite the remaining previous-
  form fixtures and tests to the new form; turn the migration section of
  docs/manifest-migrations.md into a change note; adjust spec 006 (FR-005, FR-006, SC-002, User
  Story 1) and rule V-2, which accepted an undeclared version.

Previous report: 2.4.0 → 3.0.0
Bump rationale: MAJOR. Principle VI is redefined incompatibly: the compliance block it made
mandatory is now forbidden, and the model card leaves the pipeline. Principles I, II, V, VIII and
X gain rules, and X's test for what may be built is widened. Source: the owner's decisions of
2026-10-23 (docs/design/2026-10-23-owner-decisions.md, D1–D6) and the two research notes of the
same date (docs/research/2026-10-23-*.md), plus a question round on four points the decisions
left open.

The owner ran Caravan from an empty folder and reviewed the manifest. The verdict on compliance
was "compliance komplett raus": a lean product, with compliance not part of the feature set, and
a metadata or compliance layer as a possible paid offering on top. Caravan cannot check a licence
statement, a sensor's units or a permitted use anyway; a field it cannot check and no stage reads
is cost without return.

Modified principles:
- I. Declarative Manifest, One Model per File: inputs and outputs are declared with a kind, and
  the output kind says what the model does (D4); several of each where the runtime supports them;
  the minimal manifest no longer names compliance; a field no stage reads MUST NOT exist (R1, D2);
  a value that follows from the data, such as the label set, MUST NOT be required (R2).
- II. Embedded Targets Only: scope is set by the target, not the domain; images, audio, event
  sequences such as CAN with timestamps and running windows are named in scope (D5).
- III. Reproducible by Construction: the caching example no longer mentions compliance text or a
  model card.
- IV. Measured, Emulated or Estimated: "model card" replaced by reports and export documentation.
- V. Budgets Are Gates, Not Warnings: quality budget per declared output; new fit check before
  training against lower bounds only — it fails when a floor exceeds a board and otherwise
  records `estimated` figures and is explicitly not the budget gate (D4; question round: "hard on
  certain failure").
- VI. Compliance Is Enforced by the Schema → VI. The Data Is the Author's; Caravan Asks Only What
  It Uses. Compliance layer and model card forbidden; no information required that no stage reads;
  the author holds the data rights and Caravan never claims to have checked one; project policy
  sits on top. Kept from the old VI: no datasets, raw data or credentials in the repository;
  publication as the only uploading stage (D1, D2; question round: "card ganz raus").
- VIII. No Lock-In: the export MUST carry the interface contract — names and indices, shapes,
  types, scale and zero point, pre-model transformations, label order — and runners bind by name
  (research finding: the C array carries only the byte array; question round: "in VIII").
- X. Built for Real Models: a documented application class (research notes with sources, public
  dataset or benchmark, shown to run on the target class) is the second accepted justification
  beside a named model; runtime support alone is not (question round: "belegte Anwendung").

Modified sections:
- Preamble: the pipeline description gains the fit check and the interface contract and loses
  the model card; mobility is one domain, not the boundary.
- Project Scope: the zoo's compliance regime is the zoo's, enforced by its release gate.
- Pipeline & Artifact Contract: stage list without `card` and with `export`; the card rule is
  replaced by "no model card; numbers reach a table only through a report".
- Technical Baseline: model licences are the author's choice, neither assigned nor checked.
- Resources & Cost Discipline: "model card" in the credential rule becomes "exported artifact".
- Development Workflow: the publish gate drops compliance and usage class and gains "no dataset,
  raw data or credential among the files to upload".
- XII layering list: "card rendering and release records" become "run reports and the interface
  contract".

Unchanged on purpose: Principle XI (admits no deviation) and the credential and cost rules.

Zoo check: the zoo constitution (v3.0.0) governs zoo releases and keeps its own compliance
regime; it places no compliance duty on Caravan. Removing compliance here does not conflict.

Follow-up (not done by this amendment):
- Code: remove the `compliance` section, `dataset.license` and `dataset.permitted_use`, rules
  CF-3, CF-5 and CF-8 and the compliance parts of `resolve.py`, with a v0 migration note
  (Principle IX); remove `topic` and `task`; derive labels from data; declared inputs and
  outputs; the fit check before training; the interface contract in the export.
- Docs: README (compliance block, model card in the stage list), CONTRIBUTING if it mentions them,
  and spec texts that cite the old Principle VI.
- Templates under .specify/templates were not changed (scope of this command).
- Open: whether the publish stage is still wanted now that there is no card to publish with it.

Previous report: 2.3.2 → 2.4.0
Bump rationale: MINOR. It narrows what a MUST requires of one stage, after feature 004 found that
the stage cannot satisfy it and that this document already names the stage that can.

Principle VIII required: "The export MUST document the runtime, the operator set and the tensor
arena size it requires." The runtime and the operator set come from data and are exact. The arena
figure cannot be produced by the export at all: the runtime plans that memory with its own
allocator, on the target, from the operators it actually linked, and the analysis tool available in
the runtime extra reports the model size and its buffer split and no arena (checked 2026-10-22).

Two figures *can* be computed from the model file, and the difference between them is the reason
this amendment is not a loosening. The sum of the read-write tensors is an upper bound on the
tensor area, because the runtime reuses one buffer for tensors whose lifetimes do not overlap — and
it bounds the whole arena in neither direction, because scratch buffers are not in it. The peak of
simultaneously live tensors *is* a lower bound on the arena, because any planner must hold at once
what is live at once. On the pilot model: 720 bytes summed, 648 bytes peak. Emitting the first and
calling it the arena would have been a Principle IV violation committed to avoid a Principle VIII
one.

The Verification section already said where the real figure comes from — "Emulation verifies that
the firmware builds, that the model loads, that the tensor arena fits" — so the two sections
disagreed with each other, and the export's clause was the one that could not be met. It now asks
the export for a computed floor with its method named, and points at the stage that establishes
what a board needs.

Modified sections:
- Principle VIII: the export's documentation clause; the arena figure becomes a computed floor
  with its method, and the required figure is attributed to emulated verification.

Previous report: 2.3.1 → 2.3.2
Bump rationale: PATCH. It corrects a measured figure and adds no rule. 2.3.1 recorded the weight
of the read-only runtime as "116 MiB and 8 packages". Re-measured on 2026-10-22, the number is
114 MiB and 7 packages: a default installation is 7 MiB and 7 packages, the same environment with
the runtime extra is 121 MiB and 14, and the extra's own addition is the difference — `ai-edge-
litert`, `backports-strenum`, `flatbuffers`, `ml-dtypes`, `numpy`, `protobuf`, `tqdm`. The old
figure matched neither the whole environment nor the addition, and had been copied into nine other
files before anyone subtracted one from the other. The argument it supports is untouched: 114
against 1,971 is the same argument as 116 against 1,971.

Modified sections:
- Technical Baseline: the runtime's weight is the re-measured figure, with the base installation
  stated so the subtraction is visible rather than taken on trust.

Previous report: 2.3.0 → 2.3.1
Bump rationale: PATCH. It resolves a question this document itself deferred and adds no rule. The
Technical Baseline said the Keras-on-JAX alternative "reopens when the quantize stage is built",
and it has been built (feature 003). The answer is no: there is no int8 conversion path that avoids
the training framework today — `ai-edge-litert` 2.3.0 is a runtime, not a converter, and the
vendor's own conversion documentation describes only the framework path (checked 2026-10-22). So
conversion keeps the framework, and the floor lowered in 2.3.0 stays until a stable TensorFlow
ships for the project's current Python.

Asking the question did change something, though, and the baseline now records it: *reading and
running* an exported model needs no training framework, at 114 MiB against the conversion half's
1,971 (corrected from 116 in 2.3.2). The four stages that only read a model — footprint analysis, emulated verification, the
benchmark, the card — are therefore not dragged along by the conversion's weight, and reach one
Python version further (3.14; the runtime publishes no cp315 wheel either).

Modified sections:
- Technical Baseline: the deferred question is answered, with the evidence and the date; the
  footprint-analysis bullet records that the runtime it needs is installable everywhere.

Previous report: 2.2.0 → 2.3.0
Bump rationale: MINOR. It grants something 2.2.0 assumed was already possible and is not.
2.2.0 let an extra "declare a narrower Python window than the project". Python packaging offers
no such thing: `requires-python` is metadata of the whole distribution, and an extra can only
carry environment markers on its own dependencies. With a floor of 3.14 and a framework that
ships only for 3.13, `pip install caravan-ml[train]` cannot succeed on any interpreter — the
extra 2.2.0 permitted could not be installed at all. So 2.2.0 solved the governance question and
left the mechanical one, and the planning gate of feature 002 failed on it.

What is granted: the published floor MAY be lowered to the extra's floor, under five conditions
that keep the policy's substance — current and previous stable still supported *and tested*, the
reason recorded with the version and date, markers so the default installation is untouched, an
actionable message when the stage is run outside the window, and a return to the policy floor
once the framework ships. The fifth condition is the one that makes this bearable: a lowered
floor must be tested, or the support claim in the metadata is simply false.

Checked 2026-10-22 against the live index: TensorFlow 2.21.0 (stable) publishes cp310 through
cp313. 2.22.0rc0 does publish cp314 wheels, but depends on `keras-nightly`, so it resolves only
with pre-releases globally enabled — it cannot be a declared dependency of a published
distribution. That rc is also the evidence that this window closes soon, and the closing
condition is now concrete rather than aspirational: a stable TensorFlow with a cp314 wheel that
depends on a released `keras`.

Modified principles:
- XII. Small Core, Few Dependencies: how an extra's narrower window is actually expressed, and
  what lowering the published floor costs.

Modified sections:
- Technical Baseline: the wheel evidence, the rc that depends on a nightly, and the floor of 3.13
  with its closing condition.

Previous report: 2.1.0 → 2.2.0
Bump rationale: MINOR. Not a clarification: it grants something Principle XII did not address.
The principle lists "moved behind an extra" as a remedy when a dependency cannot be installed on
the project's Python versions, but says nothing about what window that extra may then declare —
and the training stage needs the answer now. TensorFlow publishes no wheel for either Python
version this project supports (checked 2026-10-22: cp310 through cp313, against a floor of 3.14),
so without this the training extra could not exist at all.

An extra may now declare a narrower Python window than the project, stating the window and the
reason, and may never narrow the default installation. The owner chose this over moving the
project's floor, which would have handed the Python policy to a dependency — the failure the
principle exists to prevent.

Modified principles:
- XII. Small Core, Few Dependencies: an extra's own Python window.

Modified sections:
- Technical Baseline: records that TensorFlow has no wheel for the supported Python versions, and
  that the training extra therefore carries its own window.

Previous report: 2.0.1 → 2.1.0
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
microcontrollers and other constrained hardware. One YAML manifest per model declares the data,
the model's inputs and outputs and the boards it must fit; the pipeline does the rest:
architecture from a template, a fit check against the boards before training, training, int8
quantization, TFLite and C-array export with the model's interface contract, footprint analysis,
emulated verification, hardware benchmark and, optionally, publication.

Caravan was started as the build tool for the embedded models of the Mobility Model Zoo
(https://github.com/mhabedank/mobility-model-zoo). It is not a mobility tool: mobility is one
domain it serves, and the zoo is one of its users. It lives in its own repository under
Apache-2.0, so that models built with it stay portable and the framework stays usable outside
the zoo. Its goal is not a better neural architecture search than research projects achieve; its
goal is a lean pipeline that is reproducible, honest about its numbers and usable by someone who
owns one board.

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
- The manifest MUST declare the model's inputs and outputs, each with a kind. The output kind
  states what the model does; there MUST NOT be a separate field that restates it. A manifest MAY
  declare several inputs and several outputs wherever the target runtime supports them; one input
  and one output remain the short form.
- Every field MUST have either a documented default or be required by the schema. A minimal
  manifest — the data, the declared inputs and outputs, the template and the target boards with
  their budgets — MUST be sufficient to run the pipeline.
- Every field MUST be read by at least one stage. A field that no stage reads MUST NOT exist,
  however descriptive it is.
- A value that follows from the data, such as the set of class labels, MUST NOT be required in the
  manifest. It MAY be stated to pin it, and the value a run derived MUST be recorded in the
  resolved manifest of that run.
- There MUST NOT be a defaults section, an inheritance mechanism or any other way for one part of
  a manifest to set values for another. Defaults resolve from exactly two places: the template
  and the board description.

Rationale: Hand-built models in notebooks are what the framework exists to replace. A manifest that
can hold code would drift back into the same unreproducible state within two models. Declared
inputs and outputs come from Ludwig and are kept because they make plain what a model is for; the
owner found a manifest without them harder to read than one with them. The rule that every field is
read by a stage, and that nothing the data already says is asked again, came from the first run
from an empty folder: two fields no stage read, and a label list that repeated the data, were the
first things the owner questioned. The ban on a defaults section comes from Ludwig, where
type-global defaults overridden per feature produced a hierarchy whose own documentation has to
warn about repeated type keys, silently ignored settings and a scope that covers only part of the
configuration.

### II. Embedded Targets Only

- In scope: models that run on microcontrollers and comparable constrained hardware, in any
  domain. That includes regular sensor series and running-window models (motion and activity
  recognition, machine condition monitoring, battery state of health), event sequences such as
  whole CAN frames with their timestamps (intrusion detection), position and GNSS data, audio
  (keyword spotting) and images (visual wake words and other small vision models), on the boards
  whose memory allows them. Mobility is one domain among these, not the boundary.
- What decides scope is the target, not the domain: a model is in scope when it is meant to run
  on constrained hardware, and out of scope when it is not.
- Out of scope, explicitly: cloud, desktop and LLM or text models of the zoo (the `scout` and
  `cairn` families and their successors). They are built and released without Caravan.
- Out of scope, explicitly: becoming an inference runtime, a SoC or peripheral description
  language, a cycle-accurate simulator, or a research-grade neural architecture search.
- A feature that serves only out-of-scope models MUST be rejected, however small it is.

Rationale: The usable scope is the product. A framework that also tries to be an LLM pipeline
toolkit serves neither well, and a narrow target class is what makes budgets, footprints and
board verification meaningful at all. The narrowness belongs to the target, not to the domain:
the applications that run on microcontrollers — keyword spotting, visual wake words, anomaly
detection on machine sound and vibration, activity recognition — are the same kind of problem
whether a car, a machine or a wearable carries the board (research note of 2026-10-23).

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
  the dataset version. A change that a stage does not read MUST NOT invalidate it; editing a
  field that only a later stage reads, such as a budget threshold, MUST NOT trigger retraining.
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
- The label MUST appear wherever the number appears: machine-readable run reports, the export's
  documentation and any published table. A number without a label MUST NOT be rendered.
- Latency, throughput and energy MUST NOT be reported as `measured` unless they come from a
  physical board. Emulation results MUST NOT be presented as hardware results.
- Estimates are permitted and useful. Where a measurement for the same model and board exists,
  a report MUST give the measurement, and MAY give the estimate beside it with its error.
- A claim that a model fits a board MAY rest on `estimated` or `emulated` evidence only while it
  is labeled as such.
- A memory figure derived from the model graph is `estimated` by definition, whatever the quality
  of the derivation, and MUST be reported together with the safety margin applied to it. The
  margin MUST be policy, documented once, not a per-model guess.
- A memory figure taken from the runtime's own allocation report is `emulated` or `measured`
  according to where that runtime ran. The generated runner MUST obtain it from the runtime
  rather than recomputing it.

Rationale: A number about hardware is only worth as much as its provenance, and the value of
Caravan's reports is that the numbers are honest. A heuristic estimate is a fine starting point; an
unlabeled one is a false measurement. The rule for memory is not pessimism about our own analysis:
the arena a TFLM model needs cannot be derived from the exported file, and the runtime's own report
of it is documented to omit scratch buffers and the memory planner's working memory, so it can read
lower than the smallest arena that works. An estimate is therefore the honest ceiling of static
analysis, and the margin is part of the number.

### V. Budgets Are Gates, Not Warnings

- Every manifest MUST state the quality and footprint budgets that matter for its model: the
  maximum quality loss accepted from quantization, for each declared output, and the target boards
  whose memory and flash it must fit.
- Before training, the pipeline MUST check the built model against every target board, using
  only figures that bound the need from below: the size of the weights at the stated
  quantization, and the computed floor on working memory (Principle VIII). When a floor exceeds
  what a board offers, the run MUST fail before training starts, because no training can make
  that model fit. When it does not, the check records its figures as `estimated` and the run
  continues; a passing pre-check is not a claim that the model fits, and the footprint gate after
  quantization and emulation remains the gate. This is the one check that may pass without
  determining whether the budget holds, and it may do so only because it is not the budget gate.
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
contributor can act on. The check before training exists because Caravan knows the boards: the
owner's point was that a model with several inputs or an image input may simply not fit, that
this is for the author to evaluate rather than for the framework to forbid, and that the
framework can say so before anyone spends the training time. Checking against lower bounds only
keeps that early verdict honest — a model it stops cannot fit, and a model it passes is still
owed the real gate.

### VI. The Data Is the Author's; Caravan Asks Only What It Uses

- Caravan MUST NOT contain a compliance layer: no risk or privacy class, no intended-use or
  known-limits fields, no licence or permitted-use fields, no usage-class derivation and no model
  card. Caravan produces models, run reports and exports, and nothing that certifies them.
- Caravan MUST NOT require of the author any information about the data that no stage reads —
  units, sensor metadata, provenance records or descriptions included (Principle I). What a stage
  needs, it asks for; what a stage can observe in the data, it measures and reports, and MUST NOT
  turn into a requirement.
- Responsibility for the rights to the data, and for the use of a model trained on it, lies with
  whoever brings the data. Caravan MUST NOT claim, in a report, a log, an export or a published
  artifact, to have checked a licence, a permission or a use.
- A project MAY add its own policy on top of Caravan — declarations, licence rules, a review step,
  a model card — and MUST be able to do so without editing Caravan. Caravan MUST NOT hard-code one
  project's policy as the framework's rule.
- Datasets, raw source data and credentials MUST NOT be stored in the repository. Small
  synthetic test fixtures are the only data the repository carries.
- Publication MUST be an explicit, separately invoked stage. No other stage may upload anything.

Rationale: The owner wants a lean product, and a tool that demands compliance work before it does
anything useful is not used — at least not at first. Caravan also cannot know a user's data:
whether a licence statement is true, what a sensor's units were, or who may use the result. A
field it cannot check and no stage reads is work for the user with nothing in return, and a
compliance block that looks checked is worse than none, because downstream readers mistake it for
a clean bill. Compliance is therefore a layer above Caravan, not a part of it: the zoo keeps its
own regime — declarations, usage classes, model cards — enforced by its own release gate, and a
compliance layer for other users is a candidate for a separate offering. What stays here are the
two rules that protect the project itself: no data and no credentials in the repository, and no
upload except by the one stage that is asked to.

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
  export MUST document the runtime, the operator set, and a **computed floor** on the working
  memory the model needs, with the method that produced it named. It MUST NOT present that floor
  as the figure a target requires: the runtime plans that memory with its own allocator on the
  target, so the required figure is established by emulated verification (see Verification), and
  the export MUST say so beside the floor.
- The export MUST carry the model's interface contract in a plain, documented form readable
  without Caravan: every input and output by name with its index in the converted model, its
  shape and element type, its quantization scale and zero point, every transformation Caravan
  applies to raw data before the model (scaling, window length and stride, channel order) —
  stated as none where there is none — and the order of the class labels of every class output.
  A runner MUST bind inputs and outputs by name, never by position alone, because the converter
  does not guarantee to keep the declared order.
- No stage required to build, train, quantize, export, analyze or verify a model may depend on a
  hosted service. Publication to a model hub is optional and is the only stage allowed to require
  network access.
- Caravan MUST run on a single developer machine with no accounts, no license keys and no
  registration.

Rationale: The zoo's models are meant to run on the user's own hardware; a build tool that binds
them to a service would undo that at the source. It is also the difference between this
framework and the commercial tools it is an alternative to. Portability can fail without any
service, too: a byte array whose label order and input scaling live only in Caravan's run
directory is a model nobody else can feed correctly. The C array export of feature 004 carries
the byte array and its length and nothing else (checked 2026-10-23), so the contract is required
here rather than left to each runner.

### IX. Manifest Contract: Variable Until 1.0.0, Stable From It

- Every manifest MUST declare the schema version it is written against, and the framework MUST
  NOT rewrite the user's file.
- **Before Caravan 1.0.0** the manifest schema, the command line, the run report and the exported
  artifacts MAY change in any release, without migration and without backward compatibility.
  Nothing written for an earlier pre-1.0.0 release is promised to load in a later one.
- What does not vary before 1.0.0 is honesty about it. A breaking schema change MUST get a new
  schema version identifier and a short change note naming the affected fields and the edit an
  author makes by hand. A manifest that declares a version this build does not implement — older
  or newer — or declares none MUST be refused, naming the version it implements and pointing at
  the change note. It MUST NOT be silently reinterpreted or partly read.
- Unknown or misspelled fields MUST be rejected with the field path and the accepted values;
  unknown input MUST NOT be ignored. Validation errors MUST be actionable: field path, what was
  wrong, what is accepted. These hold before and after 1.0.0.
- **1.0.0 is a deliberate decision**, recorded as an amendment of this constitution before that
  release, not a version number that happens to arrive. From that release onward:
  - the framework MUST carry one registered migration per schema version and MUST upgrade an
    older manifest to the current version in memory on every load;
  - the run report MUST record both the declared version and the effective version after
    migration;
  - a breaking change requires a new schema version, and its migration MUST exist before the
    change is released;
  - a manifest that validated under a published stable version MUST keep loading through
    migration.

Rationale: The owner decided on 2026-10-23 that Caravan owes no backward compatibility before it
deliberately reaches 1.0.0: until then the product is still finding its shape, and a migration for
every step turns each simplification into twice the work — feature 006 spent a schema migration,
a notice per removed field and a fixture directory on manifests nobody had to keep. Reproducibility does not
depend on it either: Principle III records the Caravan version in every artifact's provenance, and
the zoo pins the version it builds with, so an old manifest is rebuilt with the version that read
it. What stays is refusal with a reason, because a manifest read wrongly is worse than one not read
at all. From 1.0.0 the manifest becomes the public interface and the archival record it was always
meant to be, and Ludwig's answer — a registry of per-version transforms applied on every load, on
a copy — applies in full.

### X. Built for Real Models

- Every stage, template, input or output kind, board description and manifest field MUST be
  justified by one of two things, named in its spec:
  1. a named model that needs it, in the zoo or elsewhere; or
  2. a documented application class: a use that is shown to run on the target class of hardware,
     with a public dataset or benchmark for it, recorded in the project's research notes with its
     sources.
  Speculative generality — a capability justified by neither — MUST NOT be built.
- A capability the target runtime supports is in reach, not in scope: runtime support makes a
  feature possible, and an application or a model makes it due.
- `picket-mlp` is the pilot model. The first version of the framework is complete when that model
  is built, exported and documented entirely through the pipeline.
- A shared abstraction MUST be extracted only when a second model or a second application class
  needs it, not in advance.
- A feature whose only justification is parity with another tool MUST be rejected.
- Scope creep is a constitution matter: a change that widens the framework beyond the stages and
  targets its roadmap names MUST be justified in its spec against Principle II.

Rationale: A framework built ahead of its users fits none of them. Growing it against one real
model at a time is also what keeps the first release reachable. A tool meant for more than one
domain cannot wait for its own author to build a model in every one, so a documented application
is accepted as the second kind of need — documented, because "someone might want it" is what
speculative generality always says. The applications researched on 2026-10-23 (MLPerf Tiny's
four tasks and the uses around them) are the first entries.

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
  run reports and the interface contract MUST NOT import a training framework. Training and
  quantization live behind an optional extra. A test MUST assert that importing the core does not
  import the training framework, and MUST fail the build when it does.
- Install budget: a cold installation of the default package into a clean environment MUST stay
  within a documented time and size budget, measured in continuous integration and gated like any
  other budget (Principle V).
- Python versions: the project MUST support the current and the previous stable Python minor
  version. A dependency that prevents that is replaced, vendored in the small, or moved behind an
  extra. A dependency MUST NOT set the project's Python policy.
- An extra MAY declare a narrower Python window than the project, where the framework it carries
  publishes no wheel for the project's versions. It MUST state that window and the reason, it MUST
  NOT narrow the default installation, and the window MUST close once the framework ships for the
  project's current version. A user who installs no extra is never affected, which is what makes
  this bearable rather than a quiet retreat from the policy.
- That window is not a packaging feature: `requires-python` belongs to the whole distribution, and
  an extra can only carry environment markers on its own dependencies. Where the extra's framework
  ships solely for versions below the project's floor, the published floor MAY therefore be lowered
  to the extra's floor, and only under all five of these conditions:
  1. the current and the previous stable minor version remain supported **and tested** — the
     lowered version MUST be tested too, or the support stated in the metadata is false;
  2. the lowered floor is recorded with the framework that caused it, the version checked and the
     date;
  3. the extra's dependencies carry environment markers, so a default installation on the
     project's current Python is unaffected;
  4. a stage behind the extra, run on an interpreter outside the extra's window, MUST fail with a
     message naming the window and the reason — never with a resolution error or a traceback;
  5. the floor returns to the policy floor once the framework ships for the project's current
     version, and the obligation is recorded where it will be seen.
  A lowered floor also means the core keeps running on the lower version, which is a real
  constraint on what the core may use. That cost is the price of the extra existing at all, and it
  is paid knowingly or not at all.
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
- The zoo's compliance regime — data declarations, usage classes, licences, model cards and
  release records — belongs to the zoo and is enforced by the zoo's own release gate on what
  Caravan produces. Caravan carries none of it (Principle VI), which is not a conflict with the
  zoo constitution: the zoo's stricter rules still govern every zoo release.
- The framework proceeds iteratively: each version delivers one usable step of the pipeline, and
  each step is exercised end to end by the pilot model before the next is added.

## Pipeline & Artifact Contract

- The pipeline is a sequence of stages: build (with the fit check before training), train,
  quantize, export, analyze, verify, bench, publish. Each stage MUST be separately invocable and
  MUST be resumable from the artifacts of the stage before it.
- A stage MUST declare the artifacts it reads and writes. Communication between stages goes
  through declared artifacts on disk, never through hidden global state.
- Every run MUST write a machine-readable report containing its inputs, its provenance record
  (Principle III), its results with provenance labels (Principle IV) and its gate outcomes.
- Every run MUST write the fully resolved manifest beside its report: every default expanded,
  every template and board value applied, as it was actually used. It is an artifact of the run,
  not an optional command, so that two runs can be compared field by field.
- The command line interface is the contract for users and for continuous integration. Its exit
  codes MUST distinguish a failed gate from a crash.
- Caravan renders no model card (Principle VI). A number Caravan reports MUST reach any table it
  publishes only through a run report, never typed in by a person.
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
- TensorFlow publishes no stable wheel for either Python version this project supports: 2.21.0
  ships cp310 through cp313 (checked 2026-10-22 against the package index). 2.22.0rc0 does ship
  cp314 wheels, but it depends on `keras-nightly`, so it resolves only with pre-releases globally
  enabled and cannot be a declared dependency of a published distribution. The training extra
  therefore carries Python 3.13, and the published floor is 3.13 under the conditions in
  Principle XII — including the one that matters most: 3.13, 3.14 and 3.15 are all tested. The
  window closes, and the floor returns to 3.14, when a stable TensorFlow ships a cp314 wheel and
  depends on a released `keras`. The rc says that is near.
- The alternative — Keras 3 on a JAX backend, which does install on 3.14 and 3.15 (jaxlib ships
  cp314 and cp315, torch ships cp314, checked 2026-10-22) — was rejected because the path from
  there to int8 TFLite on those Python versions does not exist. **Settled by building the quantize
  stage** (feature 003, 2026-10-22): `ai-edge-litert` 2.3.0 is a *runtime* — its dependencies are
  numpy, flatbuffers and protobuf, it has no converter, and the vendor's conversion documentation
  describes only the framework path. Conversion therefore keeps the training framework, and
  training on one framework while converting on another would mean two frameworks in a project
  whose central rule is to have few. This reopens only if a framework-free converter appears.
- Reading and running an exported model, by contrast, needs **no** training framework: 114 MiB and
  7 packages added to a 7 MiB, 7-package default installation, against 1,971 MiB and 41 for the
  conversion half (measured 2026-10-22; the figure was 116 and 8 before 2.3.2 re-measured it). The
  interpreter the training framework ships is also deprecated and announced for deletion. So the
  runtime they use is an extra of its own, with its own window: `ai-edge-litert` publishes cp310
  through cp314 and no cp315 (checked 2026-10-22), so it reaches one version further than the
  conversion half and still not the project's current stable. Both windows are stated under
  Principle XII rather than rounded to "everywhere".
- Identifiers that outlive a release — schema field values, format names, artifact names — MUST
  NOT be vendor product names. A product rename would otherwise become a breaking schema change.
- Interface: a Python command line application. Manifest validation uses a schema library with
  strict, typed models.
- Emulation: Renode, using its own declarative platform descriptions. Caravan does not define a
  platform description language of its own.
- Footprint analysis reads the exported model file as data: the flatbuffer is parsed through a
  pinned schema binding, never by importing the training framework (Principle XII), and never
  rewritten, because a round-tripped flatbuffer can fail to load. The binding is pinned because
  operator definitions change between runtime versions. The runtime that provides it installs on
  3.13 and 3.14 (feature 003), so this stage is not tied to the conversion's single version.
- Hyperparameter search, when introduced, treats the board budget as a constraint rather than an
  objective, and is bounded by the roadmap, not by research ambition.
- License: Apache-2.0 for the framework, so that it stays commercially usable. The licence of a
  model built with Caravan is its author's choice; Caravan neither assigns nor checks one
  (Principle VI).
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
  write a credential into a report, a log or an exported artifact.
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
- Gate before a framework release: the version follows semantic versioning, a change note exists
  for every breaking schema change (and, from 1.0.0, its migration — Principle IX), and the pilot
  manifest runs green.
- Gate before the publish stage runs: all budget gates passed, provenance labels present, no
  dataset, raw source data or credential among the files to upload, and credentials supplied by
  the environment.
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

**Version**: 4.0.0 | **Ratified**: 2026-10-22 | **Last Amended**: 2026-10-23
