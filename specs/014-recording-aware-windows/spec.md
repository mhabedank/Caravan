# Feature Specification: Windows That Know Their Recordings

**Feature Branch**: `014-recording-aware-windows`

**Created**: 2026-11-16

**Status**: Draft

**Input**: Package P1 of the joint review of 2026-11-16
(`specs/013-guided-manifest-setup/review-2026-11-16.md`), started by the owner with `/speckit-specify`
right after the review: "a data model that knows recordings" — windows restart per recording, a rule
for the label of a window, a split by recording or block, and training with overlapping windows
behind that split. The review's three reviewers agreed this must come before `caravan init` ships.

## Context

Caravan turns rows into training examples by cutting them into windows. Today it does that in a way
that is correct for one kind of data — long, clean stretches of one label in one file — and silently
wrong for the others the documentation says it serves. The review measured each of these on the
current code:

- **A continuous number as the output yields no examples.** A window whose rows disagree about the
  output is dropped, and for a `number` output the rows almost always disagree. A state of charge
  falling 0.01 per row, cut into windows of 32: 156 of 156 windows dropped. The documentation lists
  battery state of charge as a served application.
- **Short events of a rare class vanish.** Twenty-row bursts every 200 rows, cut into windows of 64:
  no window of the burst class survives. Real CAN intrusion data has exactly this shape. The shipped
  fixture does not, because its stretches are aligned with the window.
- **Two recordings become one window.** All files are joined into one sequence and cut on one grid,
  so a window can hold the end of one recording and the start of the next — a jump the device never
  sees — and one file's leftover rows shift the grid of every later file.
- **The default split leaks.** Windows are shuffled into training, validation and test one by one.
  Neighbouring windows of the same recording are near-copies, so the test part measures memory,
  not generalisation: in a two-class example, 13 of 15 test windows had a training window directly
  beside them. The reference documentation already says this inflates the score and "has no symptom
  inside Caravan".

The owner decided on 2026-11-16 (clarifications below) how the defaults change and that training
with overlapping windows belongs in this feature.

## Clarifications

### Session 2026-11-16

- Q: Which split applies to windowed data when the manifest names none? → A: By recording: with
  several recordings, whole recordings go to one part; with one recording, contiguous blocks of it
  do. A change of the default before 1.0, with a change note.
- Q: Does training with overlapping windows belong in this feature? → A: Yes, and only together
  with a split by recording or block.
- Q: Which label rule applies when the manifest names none? → A: By output type: classes and
  anomaly keep today's rule (a window whose label changes is dropped); a number takes the value of
  the window's newest row. Other rules can be chosen.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A window never mixes two recordings (Priority: P1)

An author has one CSV file per recording session. Caravan treats each file as its own recording:
windows start at each file's first row and never reach into the next file, and the run report says
how many rows of each recording did not fill a last window. An author with all sessions in one file
names the column that says which session a row belongs to, and gets the same behaviour.

**Why this priority**: every other part of this feature — the split, the overlap, honest test
scores — depends on knowing where a recording starts and ends.

**Independent Test**: take two files of 1,000 rows each, window 64. Every window lies inside one
file, the report lists 1,000 − 15 × 64 = 40 leftover rows per file, and the second file's first
window starts at its first row.

**Acceptance Scenarios**:

1. **Given** a dataset of several files, **When** windows are cut, **Then** no window contains rows
   from two files, and each file's windows start at its first row.
2. **Given** a single file with a recording column, **When** windows are cut, **Then** a change of
   that column's value starts a new recording, and no window contains two values of it.
3. **Given** a recording shorter than one window, **When** windows are cut, **Then** it yields no
   window, and the report names it with its row count.
4. **Given** a recording column, **When** the manifest also lists it as an input or as the output,
   **Then** validation refuses the manifest and says the column marks recordings and is not read by
   the model.

---

### User Story 2 - A test score that measures the model, not its memory (Priority: P1)

An author who does not think about splits gets one that does not leak. With several recordings,
whole recordings go to training, validation or test. With a single recording, contiguous blocks go
to the parts, and windows at a block's edge that would share rows or neighbours with another part are
left out and counted. An author who wants a random or stratified split over windows can still name
it, and is told what it costs.

**Why this priority**: an inflated test score is the most expensive failure in the pipeline — it
passes every gate and fails on the board — and today it is the default.

**Independent Test**: the review's two-class example (contiguous blocks of 3,200 rows, window 64,
seed 42) under the new default: the share of test windows with a training window directly beside
them falls from 13 of 15 to at most 1 in 10.

**Acceptance Scenarios**:

1. **Given** a windowed manifest with several recordings and no split, **When** the run splits,
   **Then** every recording's windows are in exactly one part, and the report lists which
   recordings went where.
2. **Given** a windowed manifest with one recording and no split, **When** the run splits, **Then**
   the parts are contiguous blocks, and the report states how many windows were left out at block
   edges.
3. **Given** too few recordings to give every part one (for example two files and three parts),
   **When** the run splits, **Then** it refuses, says how many recordings there are and how many the
   parts need, and names the blocked split as the alternative.
4. **Given** a manifest that names a random or stratified split with a window, **When** it is
   validated, **Then** it is accepted with a notice that neighbouring windows can fall into
   different parts and inflate the test score.
5. **Given** a split by a named column (for example a subject or vehicle id), **When** the run
   splits, **Then** all rows with the same value land in one part.
6. **Given** a classification output, **When** a split by recording or block is made, **Then** the
   report gives the windows per class in every part, and refuses, as today, when a class has none in
   a part.

---

### User Story 3 - Every kind of output gets windows (Priority: P2)

An author chooses what a window's label means. For a number, the default takes the newest row's
value, so a continuous target yields windows. For a short, rare event, the author chooses "this
value anywhere in the window", so the event's windows are kept. Whatever rule applies is written into
the run's resolved manifest and into the export, so the firmware knows what a prediction means.

**Why this priority**: it makes two documented application classes work at all (state estimation,
intrusion detection), but it builds on the windows of User Story 1.

**Independent Test**: a fixture with a state of charge falling 0.01 per row yields windows under the
default; a fixture with 20-row bursts every 200 rows keeps windows of the burst class with the
"anywhere" rule.

**Acceptance Scenarios**:

1. **Given** a `number` output and no rule, **When** windows are cut, **Then** each window's label
   is the value of its newest row, and no window is dropped for disagreeing values.
2. **Given** a classification output and no rule, **When** windows are cut, **Then** a window
   whose label changes is dropped and counted, as today.
3. **Given** the rule "newest row", **When** windows are cut, **Then** each window takes its newest
   row's label.
4. **Given** the rule "majority", **When** a window's labels are tied, **Then** the window is dropped
   and counted as tied.
5. **Given** the rule "this value anywhere" with a named value, **When** a window contains that value
   in any row, **Then** the window takes that value; otherwise it is treated as by the default rule.
6. **Given** a named value the output column never contains, **When** the run reads the data,
   **Then** it refuses and lists the values the column does contain.
7. **Given** any rule, **When** the export is written, **Then** the interface contract states the
   rule.

---

### User Story 4 - More examples from the same data, safely (Priority: P2)

An author with little data lets windows overlap during training — for example a new window every
16 rows for windows of 64 — and gets about four times as many examples. Caravan allows this only
with a split by recording, by column or by block, and makes sure no window in one part shares a row
with a window in another.

**Why this priority**: overlap is standard practice for sensor and audio models and makes a model
robust to windows that start mid-event, as a streaming device feeds it; but it is only safe on top of
User Story 2.

**Independent Test**: one recording, window 64, training step 16, the default blocked split: about
four times as many windows as with step 64, and no row is shared between windows of different parts.

**Acceptance Scenarios**:

1. **Given** a training step smaller than the window and a split by recording, column or block,
   **When** windows are cut, **Then** a new window starts every step rows within each recording.
2. **Given** a training step smaller than the window and a random or stratified split, **When** the
   manifest is validated, **Then** it is refused, naming the splits that allow overlap.
3. **Given** overlapping windows and a blocked split, **When** the run splits, **Then** every window
   that would share a row with a window of another part is left out and counted.
4. **Given** a training step larger than the window, **When** the manifest is validated, **Then** it
   is refused: rows between windows would be read by nothing.
5. **Given** a training step, **When** the export is written, **Then** the interface contract
   records it as how the training data was cut, not as how the device must read.

---

### Edge Cases

- **A recording column whose value returns later** (session A, then B, then A again): each
  contiguous run is a recording for windowing; a split by that column keeps all rows of A together.
- **Every recording shorter than one window**: no sample at all; the refusal names the longest
  recording and the window.
- **Files of very different lengths**: a split by recording assigns recordings, not rows, so the
  parts' shares of windows can differ from the stated probabilities; the report states the shares
  actually reached.
- **One recording and a class that occurs in only one block**: stratification cannot hold; the
  refusal names the class and says it occurs in one stretch of the data only.
- **A fixed split column together with a recording column**: the fixed column decides the parts; a
  window must not cross either boundary.
- **The "anywhere" rule on a binary or anomaly output**: allowed; for anomaly, a window containing
  the abnormal value anywhere counts as abnormal and is excluded from training on normal windows.
- **Overlap with a fixed split**: allowed, and windows sharing rows across parts are left out as for
  a blocked split.
- **Images** (one row per sample, no window): nothing in this feature applies; the existing split
  rules hold.

## Requirements *(mandatory)*

### Functional Requirements

**Recordings**

- **FR-001**: Every data file MUST be a recording of its own. Windows MUST start at a recording's
  first row and MUST NOT contain rows from two recordings.
- **FR-002**: A manifest MAY name one column that marks recordings within files. A change of its value
  between consecutive rows MUST start a new recording.
- **FR-003**: The recording column MUST NOT be an input or the output, and MUST NOT be read by the
  model; a manifest that declares it as either MUST be refused with the reason.
- **FR-004**: The run report MUST list, per recording, its rows, its windows and its leftover rows,
  and MUST name recordings too short for one window.

**The label of a window**

- **FR-005**: A manifest MAY state a window label rule: *all equal* (a window whose label changes is
  dropped), *newest row*, *majority* (a tie is dropped), *this value anywhere* (with the value
  named), and, for a number output, *mean*.
- **FR-006**: Without a stated rule, a category, binary or anomaly output MUST use *all equal* and a
  number output MUST use *newest row*.
- **FR-007**: A rule MUST be refused where it does not apply to the output type (for example *mean*
  on a category), and a named value the output column does not contain MUST be refused at run time
  with the values it does contain.
- **FR-008**: Every dropped window MUST be counted by reason (label changed, tie, crossed a part)
  in the run report.

**Splits**

- **FR-009**: A split *by recording* MUST place every recording's windows in exactly one part; a
  split *by column* MUST place all rows sharing the column's value in one part.
- **FR-010**: A *blocked* split MUST place contiguous stretches of windows in the parts and MUST
  leave out windows that touch or overlap a window of another part, counting them.
- **FR-011**: For a manifest with a window and no stated split, the split MUST be *by recording* when
  the data has at least as many recordings as parts, and *blocked* otherwise.
- **FR-012**: A random or stratified split over windows MUST remain available when named, and
  validation MUST then report a notice that neighbouring windows can fall into different parts.
- **FR-013**: A split by recording or column MUST, for a classification output, try to give every
  part windows of every class, and MUST refuse with per-class counts when it cannot.
- **FR-014**: The run report and the resolved manifest MUST record the effective split, which
  recordings or groups went to which part, and the share of windows each part actually received.
- **FR-015**: The existing fixed split by a column of part names MUST keep working unchanged, now
  with windows that also respect recording boundaries.

**Overlapping windows**

- **FR-016**: A manifest MAY state a training step between 1 and the window size; without one, the
  step MUST equal the window (no overlap).
- **FR-017**: A step smaller than the window MUST be refused with a random or stratified split.
- **FR-018**: No window in one part MAY share a row with a window in another part; windows that would
  MUST be left out and counted.

**Contract and compatibility**

- **FR-019**: The exported interface contract MUST state the window label rule and the training step,
  and MUST describe the step as how the training data was cut.
- **FR-020**: Windowing and splitting MUST run without the training framework, as today, so they are
  tested on every supported Python.
- **FR-021**: Because the default split of windowed data changes meaning, the schema version MUST
  change and a change note MUST name the affected fields and the edit that restores the old behaviour
  (Principle IX).
- **FR-022**: The reference documentation's warning about random splits MUST be replaced by the new
  defaults and their reasons, and the shipped examples and fixtures MUST include data with several
  recordings, a continuous target and short bursts.

### Key Entities

- **Recording**: a stretch of rows taken in one go — a file, or a run of equal values of the
  recording column. Windows never cross one.
- **Window**: consecutive rows of one recording, as many as the window size says, starting every
  training step rows.
- **Window label rule**: how a window's rows' labels become the window's label, or why the window is
  dropped.
- **Group**: the unit a split assigns to a part — a recording, a value of a named column, or a block.
- **Part**: training, validation or test.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A dataset with a continuous number output yields at least 90% of its possible windows
  under the default rule (today: 0%).
- **SC-002**: A dataset with 20-row bursts every 200 rows keeps at least one window of the burst class
  per burst with the "anywhere" rule and a window of 64 (today: none).
- **SC-003**: Across the shipped multi-file fixture, 0 windows contain rows of two files.
- **SC-004**: Under the new default split, at most 1 in 10 test windows has a training window of the
  same recording directly beside it (today, in the review's example: 13 in 15).
- **SC-005**: With a training step of a quarter window, a dataset yields at least 3.5 times the
  windows it yields without overlap, and 0 rows are shared between parts.
- **SC-006**: Every manifest in the repository that the change of defaults affects carries the edit
  named in the change note, and every one of them still validates.
- **SC-007**: An author reading the run report can say, without opening any other file, how many
  windows were dropped and why, and which recordings went to which part.

## Assumptions

- **A file is a recording.** Data that puts several recordings in one file names a recording column;
  data that splits one recording across files is out of scope (it is rare and can be joined).
- **Order within a recording is time order**, oldest first, as the reference already states for
  records; this feature does not sort rows.
- **Blocks for a single recording** are long enough to hold several windows each; their size is a
  documented default derived from the number of windows and the parts, not an input the author must
  give.
- **The sample period and the inference step on the device** belong to package P3 of the review
  (the time and window contract) and are out of scope here; this feature only stops the contract
  from implying that training's step is the device's.
- **Streaming evaluation** (event-level recall, false alarms per hour) is a later feature.
- **Before 1.0** (Principle IX), changing a default is allowed with a new schema version and a change
  note; no migration is owed.
- **`caravan init` (feature 013)** will build on these rules: it will propose the split and the label
  rule instead of asking, and ask only where the data makes them matter.
