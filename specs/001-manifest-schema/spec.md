# Feature Specification: Manifest Schema and Package Skeleton

**Feature Branch**: `001-manifest-schema`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Manifest schema and package skeleton. Scope: (1) `caravan validate` — validate a manifest against the schema (apiVersion caravan/v0), strict: unknown or misspelled fields rejected with field path and accepted values; a declared schema version is migrated in memory through a registered migration per version, the user's file is never rewritten, and both declared and effective version are recorded; refusal only for an unknown declared version, naming the versions implemented. (2) `caravan render` — write the fully resolved manifest with every default expanded, as a run artifact beside the run report, so two runs can be compared field by field. (3) Package skeleton: distribution name caravan-ml, CLI name caravan, Apache-2.0 LICENSE, pyproject.toml, .gitignore, and the two Principle XII checks as executable tests — a layering test asserting that importing the core does not import a training framework, and an install-budget check for a cold install of the default package. Out of scope for this feature: training, quantization, export, board analysis, verification, benchmarking, publication, and any TensorFlow dependency. Acceptance: the picket-mlp pilot manifest validates and renders; defaults resolve only from the template and the board description (no defaults section); the `split` field inconsistency between the design document's example manifest (list form) and its pydantic sketch (object form) is resolved to the object form."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find out whether a manifest is sound, before anything expensive runs (Priority: P1)

A model author writes one manifest file describing the model they want built. Before any training
time, hardware time or dataset download is spent, they ask the tool whether that manifest is
sound. They get either a plain confirmation, or a rejection that names the offending field, says
what was wrong with it, and lists what would be accepted there.

**Why this priority**: This is the whole premise of a declarative pipeline. Every later stage
reads the manifest, so an unchecked manifest means a failure that surfaces minutes or hours
later, in a stage that has nothing to do with the mistake. It is also the smallest slice that
delivers value on its own: an author can use it to author manifests long before a single model is
trained through the pipeline.

**Independent Test**: Run the check against the pilot manifest and against a library of
deliberately broken manifests — one per rule — and confirm that each is accepted or rejected for
the stated reason.

**Acceptance Scenarios**:

1. **Given** the pilot manifest for the first model, **When** the author checks it, **Then** the
   tool reports it as valid and exits with a success status.
2. **Given** a manifest with a misspelled field name, **When** the author checks it, **Then** the
   tool rejects it, names the path of the offending field and lists the field names accepted at
   that position.
3. **Given** a manifest whose compliance block is missing, **When** the author checks it, **Then**
   the tool rejects it and names compliance as the missing requirement.
4. **Given** a manifest whose split ratios do not add up to one, **When** the author checks it,
   **Then** the tool rejects it, names the split field and states the rule it broke.
5. **Given** a manifest naming a template that does not exist, **When** the author checks it,
   **Then** the tool rejects it and lists the templates that are registered.
6. **Given** a manifest naming a target board that does not exist, **When** the author checks it,
   **Then** the tool rejects it and lists the boards that are known.
7. **Given** a file that is not readable as a manifest at all, **When** the author checks it,
   **Then** the tool reports what it could not read and where, without an internal error trace.

---

### User Story 2 - See exactly what the pipeline will use (Priority: P2)

The author asks the tool to write out the manifest as the pipeline will actually read it: every
default filled in, every template and board value applied, nothing implicit left. They keep that
file as the record of the run and compare it against the record of another run to see what
changed.

**Why this priority**: Defaults that are invisible are the main way a declarative tool becomes
unpredictable, and a run whose effective configuration was never written down cannot be
reproduced or compared. It depends on Story 1 but adds value on its own, before any stage
consumes the result.

**Independent Test**: Resolve the pilot manifest, confirm every field is present with a value,
run it twice and confirm the two outputs are identical, then change one field and confirm the
difference between the two resolved files is exactly that field and whatever depends on it.

**Acceptance Scenarios**:

1. **Given** a minimal valid manifest, **When** the author resolves it, **Then** the written
   result contains every field of the schema with a concrete value and no placeholders.
2. **Given** the same manifest and the same tool version, **When** the author resolves it twice,
   **Then** the two results are identical.
3. **Given** a manifest, **When** it is resolved, **Then** the result is written beside a run
   report recording the tool version, the manifest identity, the declared and effective schema
   version and the date of the run.
4. **Given** a manifest, **When** it is checked or resolved, **Then** the author's own manifest
   file is left unchanged.

---

### User Story 3 - An archived manifest keeps working (Priority: P3)

A manifest that was written against an earlier schema version — for instance the one archived
with an already published model — is read by a later version of the tool. It loads: the tool
brings it up to the current schema as it reads it, leaves the file on disk untouched, and records
both the version the file declares and the version it was understood as.

**Why this priority**: The manifest is not only an input, it is the archival record of how a
published model was built. If a schema change turns that record into something the tool refuses,
every published model loses its build description. The value only becomes visible at the first
schema change, which is why it ranks below the first two — but the mechanism has to exist before
that change, not after.

**Independent Test**: Register a synthetic older schema version with one migration, feed a
manifest declaring that version, and confirm it loads with the migration applied, the file
unchanged on disk, and both versions recorded.

**Acceptance Scenarios**:

1. **Given** a manifest declaring a schema version older than the current one, **When** it is
   read, **Then** it is brought up to the current schema in memory and accepted.
2. **Given** that same manifest, **When** it has been read, **Then** the file on disk is
   byte-identical to before and the run report names both the declared and the effective version.
3. **Given** a manifest declaring a schema version the tool does not know, **When** it is read,
   **Then** it is refused, and the refusal names the versions the tool does implement.
4. **Given** a manifest that declares no schema version at all, **When** it is read, **Then** it
   is treated as the oldest version the tool knows and migrated from there.

---

### User Story 4 - Install the tool on a laptop in seconds (Priority: P3)

A contributor who wants to author or check a manifest installs the tool. They get a small, fast
installation that pulls no machine-learning framework, because checking and resolving a manifest
does not need one. Training support is something they install separately, when they need it.

**Why this priority**: It is the project's stated reason for existing in this shape — a narrow
tool that stays maintainable — and the point at which that promise is either kept or quietly
lost. It is independently testable and independently valuable: a reviewer, a CI job or a
contributor without a GPU can use the tool at all.

**Independent Test**: Install the default package into a clean environment with no
machine-learning framework present, confirm the installation stays within its budget, and confirm
that loading the tool does not pull a training framework in.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the default package is installed, **Then** the
   installation completes within its documented time and size budget.
2. **Given** the installed default package, **When** the tool is loaded, **Then** no training
   framework is loaded, and an automated check fails the build if one ever is.
3. **Given** a clean environment, **When** the default package is installed, **Then** checking
   and resolving a manifest both work without installing anything further.

---

### Edge Cases

- A field is spelled correctly but placed at the wrong level of the manifest: rejected naming
  both the path it was found at and where that field belongs.
- Two identical target boards are named in one manifest: rejected as a duplicate rather than
  silently de-duplicated.
- A model declares integer quantization but names no calibration sample count: rejected, because
  calibration data is what determines the quantized ranges, and the count has a documented
  minimum.
- A model declares that it processes personal data while also claiming the lowest risk class:
  rejected as a contradiction between two fields that are individually valid.
- A manifest declares publication but leaves a required compliance field empty: rejected before
  any network access is possible.
- The split ratios add up to one but one of them is zero: rejected. A part with no data cannot be
  trained on, tuned on or evaluated against, and a frozen test part is what every later result is
  measured against.
- A dataset reference is syntactically a path that does not exist on this machine: accepted at
  this stage, because resolving a dataset is a later stage's job, and the author is told that the
  reference was not resolved.
- A manifest is valid but its template parameters are not: rejected by the template itself, with
  the same quality of message as a schema error.
- The resolved output would overwrite an existing run artifact: never happens. Each invocation
  writes into its own new run directory, and an existing artifact is never overwritten or removed.
- A manifest file is empty, is not valid YAML, or contains a document that is not a mapping:
  each reported as what it is.
- The same manifest is checked on a machine with a different locale or line endings: the verdict
  and the resolved output do not change.

## Requirements *(mandatory)*

### Functional Requirements

**Checking a manifest**

- **FR-001**: The tool MUST provide a command that checks one manifest file and reports whether it
  is valid, exiting with a success status when it is and a distinct failure status when it is not.
- **FR-002**: Every rejection MUST name the path of the offending field, what was wrong with it,
  and what is accepted there.
- **FR-003**: The tool MUST reject unknown and misspelled fields rather than ignoring them, and
  MUST NOT reinterpret a manifest it does not fully understand.
- **FR-004**: The tool MUST distinguish, in its exit status, a manifest that failed a rule from an
  internal failure of the tool itself.
- **FR-005**: There MUST NOT be any option, flag or environment setting that skips checking.
- **FR-006**: Checking MUST NOT modify the author's manifest file, and MUST NOT require network
  access.

**Schema version and migration**

- **FR-007**: A manifest MUST declare the schema version it is written against; a manifest that
  declares none MUST be treated as the oldest version the tool knows.
- **FR-008**: The tool MUST hold one registered migration per schema version and MUST bring an
  older manifest up to the current version as it reads it, in memory only.
- **FR-009**: The tool MUST refuse a manifest whose declared version it does not know, and the
  refusal MUST name the versions it does implement.
- **FR-010**: Every run MUST record both the version the manifest declared and the version it was
  understood as after migration.

**Resolving a manifest**

- **FR-011**: The tool MUST provide a command that writes the fully resolved manifest: every
  default expanded, every value the pipeline will use made explicit, no field left implicit.
- **FR-012**: The resolved manifest MUST be written as an artifact of the run, beside a run report
  that records the provenance Principle III requires: the tool version, the manifest identity, the
  dataset identifier, the template identifier, the declared and effective schema version and the
  date. Converter and compiler versions are part of that record from the feature that first
  converts or compiles something; nothing here does. Each invocation MUST write into its own new run directory; an existing artifact
  MUST NOT be overwritten or removed.
- **FR-013**: Resolving the same manifest twice with the same tool version MUST produce a
  byte-identical **resolved manifest**. The run report is exempt and must be: it records the run's
  own identity and date, which is the provenance FR-012 requires. Two reports of the same input
  MUST differ only in those fields.
- **FR-014**: Defaults MUST resolve from the schema itself and the template named by the manifest,
  and from no other source. No board description contributes a default at this schema version; when
  one does, that is the only other source permitted. The schema MUST NOT accept a defaults section,
  an inheritance mechanism, or any other way for one part of a manifest to set values for another.

**What the schema requires**

- **FR-015**: The compliance block MUST be required for every manifest: risk class, privacy class,
  intended use and known limits. A manifest without it MUST be invalid, not merely incomplete.
- **FR-016**: A manifest that declares publication MUST be invalid when any required compliance
  field is missing or empty.
- **FR-017**: The schema MUST enforce rules that span fields: split ratios adding up to one with
  every part greater than zero; no duplicate target boards; no claim of the lowest risk class
  together with personal data; a calibration sample count at or above a documented minimum when
  integer quantization is declared; a dataset window present exactly when the named template
  declares that it consumes one; and no emulator named for verification when any target board
  states that none exists for it. The last two are how a template and a board state a requirement
  without the schema knowing anything about model architecture or hardware.
- **FR-018**: The dataset split MUST be expressed as named parts, not as a positional list.
- **FR-019**: Model identity fields (name, version) MUST follow one stated form, and the tool MUST
  state that form when rejecting a value.
- **FR-020**: A dataset reference MUST be required and checked for shape only at this stage;
  resolving it to a dataset declaration is out of scope, and the author MUST be told that the
  reference was not resolved.

**Templates and boards as data**

- **FR-021**: Templates MUST be a registry: each template registers itself under a stable
  identifier and validates its own parameters. Adding a template MUST NOT require editing a
  central list of templates.
- **FR-022**: A manifest naming an unregistered template MUST be rejected with the registered
  identifiers listed.
- **FR-023**: Board descriptions MUST be declarative data files, loadable and listable without
  code changes, and a manifest naming an unknown board MUST be rejected with the known boards
  listed.
- **FR-024**: A board description MUST carry the values Principle VII names — core, clock, memory,
  flash, accelerated kernels, interfaces, toolchain and emulator support — and MUST be checked for
  the types it declares and for the presence of a stated source for each value. Interpreting those
  values is out of scope here; carrying them is not, because the board files written here are the
  ones later stages will read.
- **FR-025**: A board description MUST be able to state that no emulator platform exists for it,
  and MUST NOT be accepted while naming an emulator platform that does not exist.

**The package itself**

- **FR-026**: The default installation MUST NOT require a training framework, and an automated
  check MUST fail the build if the core ever loads one.
- **FR-027**: A cold installation of the default package MUST stay within a documented time and
  size budget, checked automatically like any other budget.
- **FR-028**: The default installation MUST have at most six direct runtime dependencies, and the
  project at most four optional extras.
- **FR-029**: The published distribution MUST be named `caravan-ml` and the command MUST be named
  `caravan`.
- **FR-030**: The project MUST carry the Apache-2.0 licence text and MUST declare that licence in
  its package metadata.
- **FR-031**: The project MUST support the current and the previous stable Python minor version,
  and MUST NOT carry an upper version bound on a dependency without a documented incompatibility.

### Key Entities

- **Manifest**: one file describing one model version — its identity, template and parameters, its
  dataset, its training settings, its export targets, its compliance record and, optionally, its
  publication target. It is both the input to the pipeline and the archival record of a build.
- **Schema version**: the version of the manifest contract a file is written against, declared in
  the file itself.
- **Migration**: a named transformation from one schema version to the next, applied in memory
  when an older manifest is read.
- **Resolved manifest**: the same description with every default expanded and every implicit value
  made explicit; an artifact of a run, never a file the author maintains.
- **Run report**: the machine-readable record of one invocation — its inputs, the tool version, the
  declared and effective schema version, the date and the outcome of every rule checked.
- **Template**: a registered model architecture identified by a stable name, which validates its
  own parameters.
- **Board description**: a declarative description of one target board, including whether an
  emulator platform exists for it and where each of its values comes from.
- **Compliance record**: the required statement of risk class, privacy class, intended use and
  known limits that travels with the model.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author gets a verdict on a manifest in under two seconds on an ordinary laptop,
  with no network access and no dataset present.
- **SC-002**: Every one of the deliberately broken manifests in the test library is rejected for
  the stated reason, and each rejection names the offending field path — no generic failures.
- **SC-003**: A cold installation of the default package into a clean environment completes in
  under 30 seconds and downloads under 50 MB, on a machine with no machine-learning framework
  installed.
- **SC-004**: Every field the pilot model needs is expressible in the manifest without editing any
  framework code.
- **SC-005**: Resolving the same manifest twice produces byte-identical output.
- **SC-006**: A manifest written against an earlier schema version loads successfully, and its file
  on disk is byte-identical afterwards.
- **SC-007**: The resolved manifest contains no implicit values: every field of the schema appears
  with a concrete value.
- **SC-008**: Checking and resolving a manifest both succeed with no training framework installed,
  demonstrated on a clean environment in continuous integration.

## Constitution Alignment

The constitution requires every spec to name the principles it touches and state how it complies.

| Principle | How this feature complies |
|---|---|
| I. Declarative Manifest | The manifest is the only input; FR-014 forbids a defaults or inheritance mechanism; no stage of this feature reads code from a manifest. |
| III. Reproducible by Construction | FR-012 records the provenance of every run; FR-013 and SC-005 make resolution deterministic. |
| IV. Provenance Labels | No hardware number is produced by this feature, so no label is claimed. FR-020 requires that an unresolved dataset reference be reported as unresolved rather than assumed. |
| V. Budgets Are Gates | FR-005 forbids an option that skips checking; FR-027 makes the install budget a gate rather than a warning. |
| VI. Compliance Enforced by the Schema | FR-015 and FR-016 make the compliance block a schema requirement and refuse publication-bound manifests before any network access. |
| VII. Targets and Templates Are Data | FR-021 to FR-025 make templates a registry and boards data files, including honest emulator support. |
| VIII. No Lock-In | FR-006 requires that checking work without network access; no hosted service is involved. |
| IX. Stable Manifest Contract | FR-007 to FR-010 implement the declared version, the migration registry, in-memory upgrade and refusal only for an unknown version. |
| X. Built for Real Models | The pilot model's manifest is the acceptance fixture (SC-004); nothing is built that it does not need. |
| XI. No Claude in Model Learning | Nothing in this feature produces, labels or evaluates model data. |
| XII. Small Core, Few Dependencies | FR-026 to FR-031 are the dependency budget, the layering check, the install budget, the names and the Python policy. |

Deviations: none.

## Assumptions

- The pilot model's manifest is the reference fixture. The dataset it names is not needed for this
  feature, because a dataset reference is checked for shape only (FR-020).
- Board descriptions are introduced here as data with a schema, loadable and listable, so that a
  target name can be checked and a typo fails early. Interpreting board values — footprint
  analysis, requirement records, emulator invocation — is a later feature.
- The current schema version is the only one implemented when this feature is done, so the
  migration registry ships with no real migrations in it. It is exercised by a test that registers
  a synthetic older version, which is what keeps the mechanism honest before the first real
  schema change.
- The distribution name is `caravan-ml` and the command is `caravan` (owner decision of
  2026-10-22: the bare name on the package index is held by an unrelated project whose last
  release was in 2015).
- The split field is expressed as named parts. The positional-list form that appears in the design
  document's example manifest is not part of the schema and needs no migration, because no
  manifest has been published against it.
- The install and dependency budget numbers come from the constitution; changing them is an
  amendment, not a decision inside this feature.
- No hardware, emulator, accelerator or network access is needed to develop or test this feature.
