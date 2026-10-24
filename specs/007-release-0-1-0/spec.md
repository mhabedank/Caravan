# Feature Specification: Release 0.1.0 — a version you can install, try and trust

**Feature Branch**: `007-release-0-1-0`

**Created**: 2026-10-23

**Status**: Draft. **Updated 2026-10-24**: `v0.1.0rc1` was released and the `pace-cnn` port ran
with it (research R10 and the official run). The owner then decided that `v0.1.0` waits for typed,
Ludwig-style columns with their preprocessing (decision D7 in
`docs/design/2026-10-23-owner-decisions.md`); that is the next feature, and the remaining tasks of
this one (T038–T043) resume after it.

**Input**: User description: "lass uns 0.1.0 abschließen" — after the owner asked whether there is a
version to test and try by hand. There is not: the package says `0.1.0.dev1`, nothing is tagged,
and the README promises an install that does not work.

## Context

The roadmap calls v0.1 "complete as a framework": every stage from manifest to C array exists, both
templates exist, and the pilot fixture runs end to end. A manual run on 2026-10-23 confirmed it:
one command turned the pilot fixture into an int8 model of 14,856 bytes, a C array, the interface
contract and a runner skeleton per board, in about 16 seconds.

What stands between that and a release someone else can use, found on the same day:

- **The install the README promises does not exist.** `pip install caravan-ml` fails: the name is
  not on the package index (checked 2026-10-23). The owner decided to install from the tagged
  source on GitHub; the package index can follow in a later release.
- **The README describes an older state.** It says five verbs exist; export, the `conv1d` template,
  the declared inputs and outputs and the fit check are not mentioned in its status.
- **A run prints framework noise.** `caravan export` prints a long list of the training framework's
  internal variables to the console before Caravan's own summary.
- **The roadmap does not know feature 006**, and still lists the release obligations of v0.1 as
  open.
- **Export asks for more than it needs.** An author with a model already trained and quantized
  cannot export on a Python without the training framework, although exporting needs only the
  model runtime (roadmap, the obligation feature 004 recorded). The owner deferred it: a known
  limit of 0.1.0, not a fix in it.
- **The Python floor stays at 3.13.** It returns to 3.14 when a stable training framework ships for
  it; on 2026-10-23 the newest is a release candidate (2.22.0rc0). This is a condition to wait for,
  not work, and the published metadata is true as it stands.

- **The roadmap names one more condition for the release:** the port of the zoo's `pace-cnn`
  through Caravan, with the zoo's data and recipe. The owner decided that 0.1.0 waits for it.

There is no guide for trying Caravan by hand: what to install, which data to use, which command
to run, and what to look at in the result.

**The shape that follows from the owner's three decisions (2026-10-23):** a release candidate
`v0.1.0rc1` is tagged as soon as this feature's work is done. The owner tries it by hand, and the zoo
pins it to port `pace-cnn`. Whatever the port finds in Caravan is fixed, and a further candidate is
tagged if needed. `v0.1.0` is tagged when the port has succeeded, from a commit that passed the same
checks as the candidate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install a named version and try it in a few minutes (Priority: P1)

The owner, or anyone the owner sends the link to, installs a tagged Caravan version (the
candidate first, then 0.1.0) from GitHub, follows one short guide, and has a quantized model with its C array and interface contract in front of them,
having typed only the commands the guide shows.

**Why this priority**: It is what the owner asked for: a version to test and try by hand. Without
it every other improvement is invisible.

**Independent Test**: On a machine that has never seen the repository, follow the guide from the
first line to the last on Python 3.13 and check that every step does what the guide says it does.

**Acceptance Scenarios**:

1. **Given** a fresh environment on Python 3.13, **When** the author installs the tagged version
   with the training and runtime extras as the guide says, **Then** the install succeeds and
   `caravan --version` reports exactly that version (`0.1.0rc1`, later `0.1.0`).
2. **Given** that installation, **When** the author runs the guide's commands on the example data,
   **Then** `validate`, `render`, `build`, `train`, `quantize` and `export` each succeed, and the
   run directory holds the files the guide lists.
3. **Given** a fresh environment on Python 3.14 or 3.15 without extras, **When** the author
   installs the tagged version, **Then** `validate` and `render` work on the example manifest, and a
   training command says which extra and which Python it needs, rather than failing obscurely.
4. **Given** the guide, **When** the author reaches its end, **Then** it shows how to point the
   same manifest at their own data: the expected file layout, the label column, and what Caravan
   derives.

---

### User Story 2 - A run's console output is Caravan's, not the framework's (Priority: P2)

Every command prints Caravan's own summary and findings. Messages of the training framework or the
converter are not shown by default; they are available when the author asks for them.

**Why this priority**: The first manual try is where an author decides whether the tool is
trustworthy. A screen of internal variable dumps before the result hides the result and looks
like an error.

**Independent Test**: Run `caravan export` on the pilot fixture and compare the console output to
the summary the guide shows.

**Acceptance Scenarios**:

1. **Given** the pilot fixture, **When** `caravan export` runs, **Then** the console shows only
   Caravan's lines: no framework variable listings, no framework logging.
2. **Given** a failure inside the training framework, **When** it happens, **Then** its cause still
   reaches the author: the summary names the stage that failed and where the full framework output
   was kept.
3. **Given** an author who wants the framework's output, **When** they ask for it with the
   documented switch, **Then** it is shown.

---

### User Story 3 - The release says truthfully what it is (Priority: P2)

The README, the roadmap and a release note describe 0.1.0 as it is: what it does, what it does not
do yet, on which Python versions each part runs, and the known limits found so far.

**Why this priority**: Principle IV (provenance) applies to the project's own claims. A release
whose documents promise an install that fails, or omit a known limit, is not trustworthy, however
good the code is.

**Independent Test**: Read the README, the roadmap and the release note and check each claim
against the released package: every command shown runs, every number is from a run, every listed
limit is real.

**Acceptance Scenarios**:

1. **Given** the README, **When** a reader follows its install and status sections, **Then** every
   command works as written and the status lists every verb and template that exists.
2. **Given** the roadmap, **When** a reader looks up v0.1, **Then** it lists feature 006, marks
   v0.1 as released with its date, and lists what stays open and why.
3. **Given** the release note, **When** a reader looks for known limits, **Then** it names at
   least: the Python floor of the training half, derived labels failing the int8 gate on the
   synthetic example because inputs are not scaled (research R11 of feature 006), that footprint
   figures are lower bounds, not measurements, and that export needs the training extra even when
   training and quantization are cached.

---

### User Story 4 - `pace-cnn` is rebuilt with the candidate before 0.1.0 (Priority: P2)

A release candidate is pinned and the zoo's published IMU activity model `pace-cnn` is rebuilt
through Caravan on its real data, with the zoo's split by subject (FR-017), as an internal test
(FR-020). 0.1.0 is released only when that run succeeds,
so the first release has been used for a real model, not only for the synthetic fixture.

**Why this priority**: It is the owner's decision (2026-10-23) and the roadmap's last condition for
the release. A framework whose first release has only ever seen synthetic data has not met a real
model's columns, sizes and label sets.

**Independent Test**: With the candidate installed, run the port's manifest
(`ports/pace-cnn/pace-cnn.yaml` in this repository) through `caravan export` on the zoo's dataset and compare the result with the published 0.1.0 of `pace-cnn`:
same task, same boards, accuracy and size recorded with their provenance.

**Acceptance Scenarios**:

1. **Given** a tagged candidate, **When** the port pins it, **Then** exactly that candidate is
   installed and every run report records its version.
2. **Given** the port's manifest and the zoo's dataset, converted outside both repositories,
   **When** the port runs, **Then** it
   reaches an exported model, or stops at a gate with a finding that names its cause.
3. **Given** a finding that is a defect in Caravan, **When** it is fixed, **Then** a further
   candidate is tagged and the port is repeated with it; `v0.1.0` is never tagged over a known open
   defect from the port.
4. **Given** the port's result, **When** 0.1.0 is released, **Then** the release note states what
   the port showed, with numbers from its run report and their provenance label, and does not claim
   the hand-made card figures of the published `pace-cnn` (footprint and latency come from v0.2 and
   v1.0).

---

### Edge Cases

- The release is tagged but the published package differs from the tagged source: the release
  procedure builds the package from the tag and checks the built package, not the working tree.
- An author installs 0.1.0 with a manifest written for an earlier development state
  (`caravan/v0`): refused with V-1 and the change note, as constitution 4.0.0 requires.
- The guide's example data: the only committed dataset is the synthetic fixture inside the test
  tree. The guide must reach it from an installed package, or the release must ship an example the
  guide can use; a guide that only works from a repository checkout does not satisfy User Story 1.
- The example with derived labels fails the int8 gate (research R11): the guide uses the manifest
  that pins the labels, and says why in one sentence, instead of hiding the failure.
- Framework output suppressed and the framework crashes: the cause must not be lost (User Story 2,
  scenario 2).

## Requirements *(mandatory)*

### Functional Requirements

**Version and distribution**

- **FR-001**: The package version MUST be the tagged one (`0.1.0rc1` for the candidate, `0.1.0` for
  the release), and every run report and provenance record made with it MUST carry that version.
- **FR-002**: Each tagged version MUST be installable from GitHub by its tag, with and without
  extras, exactly as the README and the guide show. Nothing is published to the public package
  index in this feature; the README MUST NOT claim that it is.
- **FR-003**: A release candidate MUST be tagged `v0.1.0rc1` (and `rc2`, … for later candidates)
  and the release `v0.1.0`. The version the package reports MUST equal the tag, and each tag's
  package MUST be checked as built from that tag, not from a working tree.
- **FR-004**: The constitution's release gate MUST hold and be recorded for the candidate and for
  0.1.0: semantic versioning, a
  change note for every breaking schema change since the last release (`caravan/v0` →
  `caravan/v0.1`, in `docs/manifest-changes.md`), and the pilot manifest green end to end.

**Trying it by hand**

- **FR-005**: A guide MUST lead from an empty environment to an exported model in one sequence of
  commands, list the files the run produces and say what each one is for.
- **FR-006**: The guide MUST work from an installed package, without a checkout of the repository.
  The example data it uses MUST be synthetic, small and generated or shipped without any
  third-party data (constitution: no datasets in the repository beyond the synthetic fixture).
- **FR-007**: The guide MUST show how to use one's own data: the file layout the data stage reads,
  the output column, and which values Caravan derives.

**Console output**

- **FR-008**: By default, commands MUST NOT print the training framework's or the converter's own
  output to the console. Caravan's summary, findings and refusals MUST be unaffected.
- **FR-009**: When a stage fails inside the framework, the summary MUST name the stage and point to
  the place where the framework's full output was kept for that run.
- **FR-010**: One documented switch MUST show the framework's output again. It MUST NOT add a verb
  (Principle XII fixes the verb set).

**Truthful documents**

- **FR-011**: The README's install, status and quick-start sections MUST match the released package:
  every command shown MUST run, and the status MUST list every implemented verb and template.
- **FR-012**: The roadmap MUST list feature 006 under v0.1, mark v0.1 released with its date, and
  keep the open conditions (the Python floor) with their closing condition.
- **FR-013**: A release note MUST state what 0.1.0 does, on which Python versions each part runs,
  and its known limits, at least those named in User Story 3, scenario 3.

**A fixed split** (owner decision 2026-10-23, after research R8)

- **FR-017**: A manifest MUST be able to let the data decide the split: `dataset.split.column` names
  a column whose value in every record is `train`, `val` or `test`. A window takes the part its
  records name; a window whose records name different parts MUST be discarded and counted in the
  run report, like a window whose records disagree on the label.
- **FR-018**: With a fixed split, the fractions and `stratified` MUST NOT be stated, the split column
  MUST NOT be an input or output column, and it MUST be left out when the input columns are
  derived. Each violation is refused with its own rule at validation.
- **FR-019**: A split column missing from the data, a value other than the three names, or a part
  that receives no window MUST stop the run with a finding naming the column and the value.

**The port before the release**

- **FR-014**: `v0.1.0` MUST NOT be tagged before the `pace-cnn` port has run with a
  candidate and either reached an exported model or stopped at a gate whose finding is the model's
  and not a Caravan defect.
- **FR-015**: Every Caravan defect the port finds MUST be fixed in Caravan, with a test, before
  `v0.1.0`; a finding that is not a Caravan defect MUST be recorded in the release note as what the
  port showed.
- **FR-016**: The port's data, raw source data and any credential MUST NOT enter either repository
  (constitution). The converter and the manifest of the port are kept in this repository, so the
  port can be repeated; the data is read from wherever the author keeps the archive, verified by
  its hash.
- **FR-020**: The port is an internal test of Caravan (owner decision 2026-10-23): nothing it
  produces is published, and the zoo is not changed by it. The contradiction between the dataset's
  own licence text ("Any commercial use is prohibited") and the zoo's registration of it for
  commercial use is recorded as an open item for the zoo.

### Key Entities

- **Release candidate**: a tag the owner tries and the zoo pins; it may be followed by another.
- **Release**: a version number, a tag, a built package, a release note.
- **Release note**: what the version does, where each part runs, known limits, and the change notes
  it carries.
- **Try-it guide**: the commands from an empty environment to an exported model, with the example
  data and the result explained.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Someone who has never seen the repository goes from an empty Python 3.13 environment
  to an exported model in under 10 minutes of wall time, typing only commands from the guide.
- **SC-002**: The console output of the guide's `export` step fits on one screen (at most 25
  lines) and contains no line from the training framework.
- **SC-003**: Every command in the README and the guide runs as written against the released
  package, checked by a test that executes them, not by reading.
- **SC-004**: The release note names at least four known limits (those of User Story 3,
  scenario 3), each of which a reader can
  reproduce from the guide or the cited research.
- **SC-005**: Installed from a tag, `caravan --version` reports that tag's version and a run report
  records it.
- **SC-006**: `pace-cnn` has been rebuilt through a Caravan candidate, with the zoo's data and
  split, before `v0.1.0` is tagged, and the release note reports the result with its numbers' provenance.

## Assumptions

- **Not waiting for the Python floor.** Releasing at `>=3.13` is honest because 3.13, 3.14 and 3.15
  are all tested; the floor rises in a later release when a stable training framework ships for
  3.14.
- **Waiting for the `pace-cnn` port** (owner decision, 2026-10-23). The port pins a Caravan
  candidate and runs on the zoo's dataset; it is an internal test, not a zoo release (FR-020).
  It reproduces the task, not the exact recipe: the differences Caravan cannot express in 0.1.0
  (dropout placement, a learning-rate schedule, calibration order) are accepted and recorded
  (research R8). Its data must be
  obtainable by the zoo's author; if it is not available in a session, the port waits for the
  author, and so does `v0.1.0`, while the candidate stays usable for trying by hand.
- **Export without the training framework is deferred** (owner decision, 2026-10-23) and is a
  known limit in the release note.
- **No package-index publication** (owner decision, 2026-10-23): install from the GitHub tag.
- **Owner decisions D3 and D6** (render and validate writing only to the shell; findable run
  directory names) are not part of this release. Before 1.0.0 they may change the output layout
  without compatibility (constitution 4.0.0).
- **Input scaling (P5)** is not part of this release; its absence is a known limit in the release
  note.
- Nothing in this feature trains with a Claude model, labels data or evaluates with one
  (Principle XI). No credential is stored anywhere; if the package is published, the credential
  comes from the environment of that one step only, with a spending limit of zero (publishing costs
  nothing). Publication to the package index is not part of this feature, so no credential is
  needed at all.

## Constitution Check

| Principle | How this feature complies |
|---|---|
| III — reproducible | the version in every provenance record is the tagged one (FR-001); the package is checked as built from the tag (FR-003) |
| VI — the data is the author's | Caravan does not judge the dataset's licence; the owner decided the port is internal only, and the contradiction is handed to the zoo (FR-020) |
| X — a named model drives it | the first release is exercised on the named model `pace-cnn` before it ships (FR-014) |
| IV — provenance | every number in the guide and release note comes from a run (SC-003); limits stated (FR-013) |
| IX — manifest contract | change note for `caravan/v0` → `caravan/v0.1` is part of the gate (FR-004); no migration before 1.0.0 |
| XI — no Claude in learning | nothing in scope trains, labels or evaluates |
| XII — small core | no verb added (FR-010); no dependency added; install budget unchanged |
| Development Workflow | the framework-release gate is the acceptance of this feature (FR-004) |
