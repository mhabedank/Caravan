# Feature Specification: `caravan init` Proposes the Whole Manifest at Once

**Feature Branch**: `015-init-one-proposal`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description (German, in full):

> Umbau von `caravan init`: ein Gesamtvorschlag statt Frage für Frage. Grundlage ist
> specs/013-guided-manifest-setup/ux-research-2026-11.md (bitte zuerst lesen, besonders "Ist-Stand
> im Code vs. Ziel"). Kernthese: nicht ein besserer Fragebogen, sondern weniger Fragen.
>
> Ziel: init liest die Daten und leitet einen vollständigen Manifest-Vorschlag ab (Zielspalte,
> Typen, Template, Board, Budget), zeigt ihn kompakt und fragt nur "übernehmen / anpassen".
> Einzelfragen erscheinen nur bei "anpassen" oder bei unsicheren Vorschlägen. Jeder Vorschlag
> bekommt eine Sicherheit; nachgefragt wird gezielt nur, wo sie niedrig ist. `--yes`; ohne Terminal
> wird nie gefragt; jede Fehlermeldung bei fehlenden Angaben nennt ein konkretes Flag mit Beispiel.
> Der Zeilen- bzw. Ein-Schritt-Modus ist der Standard, die Textual-Vollbildoberfläche startet nur
> auf ausdrücklichen Wunsch (`--tui`). `init --json` gibt den geschriebenen Pfad, die übernommenen
> Vorschläge mit Sicherheit und die Befunde aus. init erzeugt optional eine AGENTS.md neben dem
> Manifest.
>
> Nicht in diesem Feature: MCP-Server, llms.txt, Fleet- bzw. Monetarisierungsthemen, ein
> einheitliches Fehlerformat über alle Verben (eigenes Feature).
>
> Offen und in der Spec zu klären: ob die Vollbildoberfläche bleibt; ob der Vorschlag die
> Speicherkosten pro Board zeigt; ob die Verfassung angepasst werden muss (Principle XII).

*In short: rebuild `caravan init` around one complete proposal instead of one question after
another — not a better questionnaire, fewer questions.*

## Context

Feature 013 built `caravan init`. It reads the data, proposes a type for each column with its
reason, and then asks up to thirteen questions in a fixed order (data → boards → quantization →
output → … → file → review). Accepting every proposal on the synthetic data takes twelve answers
(013, SC-003). With the `authoring` extra installed, a full-screen interface starts by default.

The UX research of November 2026 (`specs/013-guided-manifest-setup/ux-research-2026-11.md`)
concludes that the obstacle is the number of questions, not their quality:

- Comparable tools ask one question after deriving everything they can: accept the recommended
  setup, or customize it. The detail questions appear only on "customize" (create-next-app).
- Work on column type detection recommends showing a person only the columns the detector is
  unsure of, not all of them (SortingHat, ArcheType).
- A command asks only when a person can answer; without a terminal it never waits for input, and
  a missing answer is named together with the option that gives it (clig.dev).
- Agents are a user group of their own: they need a machine-readable result more than a dialogue,
  and an `AGENTS.md` beside the project is a common way to tell them how to work in it.

### What the data settles and what it does not

A first measurement, taken on 2026-11-24 with `init` as it is on `main`, on the four tabular
datasets shipped with the tests, compared with the manifests written by hand for them (or, for
`soc`, with the output the dataset is made for):

| Dataset | Item | Proposed today | Intended | Why the data allows both |
|---|---|---|---|---|
| synthetic | `dlc` | category | number | 8 distinct integers: a code or a count |
| anomaly | output type of `condition` | binary | anomaly | two values: a class pair, or normal against fault |
| recordings | `c` | category | number | 3 distinct integers |
| recordings | output type of `label` | binary | category | two values |
| soc | output column | `temp` | `soc` | no column named like an answer; the fallback took the last category-like column |
| soc | `current` | category | number | 7 distinct integers |
| soc | `temp` | category | number | 11 distinct integers |

Every one of the seven differences comes from one of three rules: *few distinct integers make a
category*, *two values make a binary output*, and *with no column named like an answer, take the
last category-like column*. In each case the data genuinely allows more than one answer. None of
the differences comes from a rule the data settles — text values, many distinct numbers, a single
value in every row, a column named `label`. That is the case for certainty: ask about exactly the
first kind, and stop asking about the second.

Two things `init` cannot know at all: the boards (a hardware decision made before any machine
learning; the joint review of 2026-11-16, A10, ruled out proposing one) and, where the data is
ambiguous, the author's intent.

### Relation to feature 013

This feature changes how `init` asks, not what it writes. It **replaces** in feature 013: FR-025
(the full-screen interface starts by default; `--plain`), FR-027 (the fixed question order) and
User Story 4, scenario 1. It **sharpens** FR-021 (a missing answer names the option *with an
example value*) and the contract's meaning of `--no-input` (FR-017 below). Every other requirement
of feature 013 stays in force — in particular what the written file must be (FR-003, FR-004,
FR-016 to FR-020), what may be asked (FR-007, FR-010, FR-015), and the guided choices behind each
question (FR-028 to FR-035), which are now reached through "adjust".

## Clarifications

### Session 2026-11-24

*(Open: whether the full-screen interface stays; whether the proposal shows the memory per board.
Answered here once the owner decides.)*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One proposal, then one decision (Priority: P1)

An author points `init` at their data. `init` reads it and shows, on one screen, the manifest it
would write: the output column and its type, every input column with its type or "left out", the
template and its size, the window where the template reads one, the quantization, the budget, the
model's name and the file. Each line says how sure `init` is and why. The boards line says that the
author chooses. `init` then asks only what it cannot settle — the boards, and the items it is
unsure of, with all unsure columns in a single step — and finally: accept, or adjust.

**Why this priority**: This is the core thesis of the research and the owner's request: fewer
questions. It delivers the whole value on its own; everything else in this feature is a way to
reach the same proposal without a person.

**Independent Test**: In an empty directory beside the synthetic dataset, run `caravan init`, give
the data, accept every proposal, choose the board `s32k144`. Count the answers: at most four. Run
`caravan validate` on the written file: it exits 0. Run `init` again with `--yes` and the same
answers given as options: the file is byte-identical.

**Acceptance Scenarios**:

1. **Given** a directory of CSV files, **When** `init` has read it, **Then** it shows the complete
   proposal before it asks anything else, and every line carries a certainty and a one-line
   reason (for example "number — certain: 254 distinct numeric values").
2. **Given** a proposal whose items are all certain or conventions, **When** it is shown, **Then**
   `init` asks for the boards and then for the decision, and for nothing else.
3. **Given** uncertain input columns (for example `dlc` on the synthetic data),
   **When** the proposal is shown, **Then** `init` asks about those columns only, in one step, each
   with its proposal and the types its values allow; one keystroke accepts them all as proposed.
4. **Given** an uncertain output column or output type, **When** the proposal is shown, **Then**
   `init` asks for that item, offering only the answers the data allows.
5. **Given** the decision, **When** the author accepts, **Then** the manifest is written, validated
   as `caravan validate` would, and `init` reports the path and the next command.
6. **Given** the decision, **When** the author chooses to adjust, **Then** `init` lists the items of
   the proposal; the author picks one, answers its question (with the lists, forms, window table
   and drawing of feature 013), and returns to the updated proposal. Items that depend on the
   changed one and were not answered are proposed again; items that were answered are kept and
   marked to be checked again.
7. **Given** the board question, **When** the boards are listed, **Then** each shows its memory and
   flash as in feature 013; what the proposal itself shows about the model's memory per board is
   FR-006.

---

### User Story 2 - No question without a person; every missing answer names its option (Priority: P1)

A script, a continuous-integration job or a coding agent runs `init` without a terminal. `init`
never asks and never waits. With `--yes` it takes every proposal, writes the manifest, and says
which proposals it took while unsure. Without `--yes` it writes nothing, shows the proposal and says
how to accept it. Where an answer has no proposal — the boards always — it names the option that
gives it, with an example value that works for this data.

**Why this priority**: The research names the machine-readable path as the product and `init` as
the comfort layer over it. Today, without a terminal and without `--no-input`, `init` reads answers
from standard input, so a script that forgets the option hangs or answers questions by accident.

**Independent Test**: Run `init` with standard input closed and no terminal, once with `--yes` and
every open answer given, once without `--yes`, once without `--board`. The first writes a valid
manifest; the second and third write nothing, exit with the usage code within seconds, and their
messages name the options; adding exactly the options and values they name makes the run succeed.

**Acceptance Scenarios**:

1. **Given** no terminal, `--yes` and `--board s32k144`, **When** `init` runs on the synthetic data,
   **Then** it writes the manifest, asks nothing, exits 0, and lists the proposals it took while
   uncertain, each with the option that sets it.
2. **Given** no terminal and no `--yes`, **When** `init` runs, **Then** nothing is written, the
   proposal is shown, and the message names `--yes` and the command that would accept the
   proposal; the exit code is the usage code.
3. **Given** `--yes` and no `--board`, **When** `init` runs, **Then** it exits with the usage code and
   says that Caravan does not choose the hardware, how to give it — for example `--board s32k144`
   — and which boards are registered.
4. **Given** data with no column `init` can propose as the output, **When** `init` runs with `--yes`,
   **Then** the message names `--output` with a column of this data as the example.
5. **Given** a terminal and `--yes`, **When** `init` runs, **Then** it asks nothing.
6. **Given** an existing file at the target path, `--yes` and no `--overwrite`, **When** `init` runs,
   **Then** it refuses, writes nothing, and names `--overwrite`.

---

### User Story 3 - The result as one JSON document (Priority: P2)

An agent runs `init --json` and reads one JSON document on standard output: the paths written, or
none; every item of the proposal with its value, where it came from, its certainty and reason, and
the option that sets it; and the findings. From a run that wrote nothing, it can build the command
that will.

**Why this priority**: JSON output is the first step the research recommends for agents and for
continuous integration alike, and `validate`, `render` and the pipeline verbs already offer it;
`init` does not.

**Independent Test**: Run `init --json` without `--yes` on the synthetic data. Parse standard output:
one document, no written path, every item listed with certainty. Build a command from the document
alone — the options it names for the open items, plus the accepting option — run it with `--json`,
and parse the result: the manifest path, and the manifest validates.

**Acceptance Scenarios**:

1. **Given** `--json`, `--yes` and every open answer, **When** `init` runs, **Then** standard output
   holds exactly one JSON document — the written path, the items, the findings — and nothing else;
   the exit code is the one the run would have without `--json`.
2. **Given** `--json` without `--yes`, **When** `init` runs, **Then** the document lists every item
   with its certainty, names the option and an example for each open item, has no written path, and
   nothing is written.
3. **Given** answers that produce a manifest `validate` refuses, **When** `init --json --yes` runs,
   **Then** the findings appear in the same form `validate --json` uses, and nothing is written.
4. **Given** `--json` in a terminal, **When** `init` runs, **Then** it asks nothing.

---

### User Story 4 - An `AGENTS.md` beside the manifest (Priority: P3)

On request, `init` also writes an `AGENTS.md` next to the manifest: a short guide for a coding agent
that works in the author's project — which file describes the model, how to check and build it
with Caravan, what the exit codes mean, and which decisions belong to the author and not to the
agent.

**Why this priority**: The research ranks it after JSON output: common practice, but its effect is
not shown. It is cheap once the proposal and the JSON result exist.

**Independent Test**: Run `init --yes --agents-md` with every open answer in an empty directory.
Both files exist; the guide names the manifest's file and commands that succeed on it. Run it again
in a directory that already holds an `AGENTS.md`: that file is unchanged, the manifest is written,
and `init` says it left the guide alone.

**Acceptance Scenarios**:

1. **Given** `--agents-md` and no `AGENTS.md` in the manifest's directory, **When** the manifest has
   been written and validated, **Then** `AGENTS.md` is written beside it.
2. **Given** an existing `AGENTS.md`, **When** `init` runs with `--agents-md` — with or without
   `--overwrite` — **Then** that file is left unchanged, `init` says so, and the manifest is still
   written.
3. **Given** no `--agents-md` and no choice of it under "adjust", **When** `init` writes, **Then** it
   writes only the manifest.
4. **Given** the same answers twice, **When** `init` writes the guide twice, **Then** both are
   byte-identical.

---

### User Story 5 - The full-screen interface only on request (Priority: P3)

`caravan init` starts the line mode, also when the `authoring` extra is installed. `--tui` starts the
full-screen interface, which opens on the same proposal and offers the same decision. Whether the
interface stays at all is FR-019.

**Why this priority**: Starting a full-screen interface uninvited is the opposite of what the
research recommends, so the default changes in any case. Whether the interface is worth keeping is
a separate decision.

**Independent Test**: With the extra installed and a terminal, `caravan init` starts the line mode.
`caravan init --tui` starts the full-screen interface; driven with keystrokes to accept the
proposal, it writes the file the line mode writes with the same answers.

**Acceptance Scenarios**:

1. **Given** the extra and a terminal, **When** the author runs `caravan init`, **Then** the line mode
   starts.
2. **Given** the extra and a terminal, **When** the author runs `caravan init --tui`, **Then** the
   full-screen interface starts on the proposal, and writes the same file for the same answers.
3. **Given** no extra, **When** the author runs `caravan init --tui`, **Then** `init` exits with the
   code for something that installs separately and names the install command.
4. **Given** `--tui` together with `--yes`, `--json` or `--no-input`, or without a terminal, **When**
   `init` runs, **Then** it exits with the usage code and says why.

---

### Edge Cases

- **No data given**: in a terminal, the data is the one question before the proposal; data
  directories or tables in the current directory are offered as choices when there are any.
  Without a person, the message names `--dataset` with an example taken from the current directory
  when one exists.
- **Every column is uncertain**: still one step for all of them, not one question per column.
- **Many columns** (say 200): the proposal groups the input columns by proposed type and names the
  uncertain ones one by one; it still fits one screen.
- **An option is given for an item `init` is unsure of**: the option wins and the item is not asked;
  the result marks it as given.
- **An option's value the data does not allow** (for example `--output-type binary` for a column of
  four values): usage error naming the values that are allowed (as in feature 013).
- **Uncertain proposals taken under `--yes`**: never silent — listed on standard error and in the
  JSON document as taken while uncertain.
- **An adjustment invalidates a later item** (for example a new output type no template serves):
  the item is proposed again where it was not answered, otherwise marked to be checked; "accept" is
  not offered while an item is invalid, and the proposal says which one and why.
- **A large dataset**: the proposal says it was made from a sample; a proposal the sample cannot
  settle is uncertain, not certain.
- **No template serves the output and inputs**: as in feature 013, `init` says so and names what
  would make one fit; under `--yes` this is a rule failure, not a usage error.
- **Aborted anywhere** (interrupt, end of input): nothing is written, no traceback.
- **The manifest can be written but the `AGENTS.md` cannot** (for example, no permission): neither is
  left behind; `init` writes all it was asked to write or nothing (an existing `AGENTS.md` excepted,
  which is left as it is).
- **Narrow terminal, no colour**: the proposal stays readable; certainty is said in words, not only
  in colour.
- **Image data**: as in feature 013, recognised and pointed to the manifest reference.

## Requirements *(mandatory)*

### Functional Requirements

**The proposal**

- **FR-001**: Before asking anything but the data, `init` MUST derive a complete proposal from the
  data and the registries: the output column, its type (and, for an anomaly output, the value that
  means normal), every input column's type or its omission, the template, its parameters, the
  window where the template reads one, the quantization, the budget, the model's name and the file.
  The boards are an item of the proposal without a proposed value.
- **FR-002**: Every item MUST carry exactly one certainty and a one-line reason:
  - **certain** — derived from the data by a rule that settles it (FR-003);
  - **uncertain** — derived from the data by a rule that does not settle it: the data allows
    another answer that is also in use, as with the three rules of the Context;
  - **convention** — not derived from the data: a documented starting value, such as `int8`, the
    budget the shipped examples use (labelled as not a recommendation), the template's starting
    parameters, a name from the data directory;
  - **open** — no proposal: the boards always, and the output column when no column qualifies.
- **FR-003**: A rule MAY mark its proposal certain only if its proposals agree with the intended
  manifest on every tabular dataset shipped with Caravan; a rule MAY be stricter than that. Each of
  the seven differences measured on 2026-11-24 (Context) MUST come out uncertain or open.
- **FR-004**: No board MUST be proposed (feature 013, FR-034; review A10).
- **FR-005**: The proposal MUST be compact: one line per item, input columns grouped by proposed
  type, uncertain columns named one by one, the certainty said in words.
- **FR-006**: [NEEDS CLARIFICATION: does the proposal show the model's memory cost per board — one
  line per chosen board with the flash and RAM lower bounds, only a mark where a bound already
  exceeds a board, or nothing until "adjust"?]

**Asking**

- **FR-007**: In a terminal, `init` MUST ask, after the proposal, only for: the data when not given;
  the boards when not given; and each uncertain item not given, with all uncertain input columns in
  one step. It MUST NOT ask about a certain item or a convention.
- **FR-008**: Each of these questions MUST show its proposal and the answers the data allows, and
  accepting the proposal — for all uncertain columns at once — MUST take one keystroke.
- **FR-009**: Then `init` MUST show the updated proposal and offer exactly three things: accept (one
  keystroke), adjust, stop.
- **FR-010**: "Adjust" MUST offer the items of the proposal as a list; the chosen item is asked with
  its question from feature 013, after which `init` returns to the proposal. Dependent items follow
  feature 013, FR-035: re-proposed where not answered, marked to be checked where answered.
- **FR-011**: `init` MUST NOT write unless the author accepted in a terminal or `--yes` was given.

**Without a person**

- **FR-012**: `init` MUST ask only when a person can answer: its input comes from a terminal and its
  questions reach one. Otherwise, and whenever `--no-input`, `--yes` or `--json` is given, it MUST
  NOT ask and MUST NOT wait for input.
- **FR-013**: `--yes` MUST accept every proposal not given as an option, in a terminal or not. It
  MUST NOT answer an open item, MUST NOT confirm overwriting an existing file (`--overwrite` stays
  the only confirmation), and MUST NOT skip validation or any other check (Principle V).
- **FR-014**: Without a person and without `--yes`, `init` MUST write nothing, MUST show the proposal,
  and MUST exit with the usage code, naming `--yes` and the command that would accept the proposal.
- **FR-015**: Every message about a missing or open answer MUST name, for each such answer, exactly
  one option and an example value that is valid here — a column of this data, a registered board, a
  type this column allows — so that adding the option with that value gets past the message.
- **FR-016**: Under `--yes`, the proposals taken while uncertain MUST be listed in the output, each
  with the option that sets it.
- **FR-017**: `--no-input` MUST keep its general meaning — never ask — and MUST no longer accept the
  proposals; that is `--yes`. The change MUST be recorded in a change note (Principle IX).

**Interfaces**

- **FR-018**: The line mode MUST be the default in every case, also with the `authoring` extra
  installed. `--plain` is removed.
- **FR-019**: [NEEDS CLARIFICATION: does the full-screen interface stay — kept behind `--tui` and
  opening on the proposal, removed together with the `authoring` extra, or kept unchanged behind
  `--tui` until its use is measured?] Whatever is decided, it MUST NOT start without `--tui`.
- **FR-020**: `--tui` without the extra MUST exit with the code for something that installs
  separately and name the install command; `--tui` without a terminal, or with `--yes`, `--json` or
  `--no-input`, MUST be a usage error.

**The JSON result**

- **FR-021**: With `--json`, `init` MUST write exactly one JSON document to standard output and
  nothing else there; everything for people stays on standard error.
- **FR-022**: The document MUST contain: the paths written (the manifest, and the `AGENTS.md` when
  written), as given on the command line or relative to the current directory, or none; every item
  with its manifest field, its value, its source (given as an option, answered, or proposed), and,
  for a proposal, its certainty and reason; for every item, the option that sets it with an example;
  the findings — validation findings in the form `validate --json` uses, and `init`'s own notes
  (sampled data, proposals taken while uncertain, an `AGENTS.md` left unchanged); and the next
  command.
- **FR-023**: The document MUST have the same shape whether the run wrote, refused or only showed the
  proposal; a part that does not apply is present and empty. The shape MUST be documented as part of
  the `init` contract.
- **FR-024**: The exit codes MUST be the same with and without `--json`: those of feature 013
  (FR-006), and the code for something that installs separately for `--tui` without its extra.

**The `AGENTS.md`**

- **FR-025**: With `--agents-md`, or when chosen under "adjust", `init` MUST write `AGENTS.md` in the
  manifest's directory, after the manifest has validated and only then.
- **FR-026**: `init` MUST NOT overwrite or edit an existing `AGENTS.md`, also not with `--overwrite`;
  it says that it left the file unchanged, and the manifest is still written.
- **FR-027**: The guide MUST name the manifest's file; give the commands to validate, render and build
  it, with their `--json` form; say what the exit codes mean; say that the manifest is the one place
  to change the model and that it is validated after every edit; say that the budgets are gates and
  that loosening one is the author's decision, not a fix (Principle V); say that data and
  credentials stay out of the repository (Principle VI); and point to the manifest reference.
- **FR-028**: The guide MUST NOT repeat the manifest's values beyond its file name (Principle I: one
  description of the model), MUST NOT claim that a licence, permission or use was checked
  (Principle VI), and MUST NOT describe a workflow in which an agent produces training data, labels,
  evaluation judgments, or signals for model selection, threshold tuning or architecture search
  (Principle XI); it says that these come from the author.
- **FR-029**: The guide MUST be in English and byte-identical for the same answers.

**Kept and bounded**

- **FR-030**: Everything feature 013 guarantees about the written manifest MUST still hold, in every
  mode — line mode, `--yes`, and the full-screen interface where it exists: validation before
  success, no overwrite without confirmation, nothing written on abort, byte-identical files for the
  same answers and data, only registered templates and boards, nothing asked that no stage reads.
- **FR-031**: Every item of the proposal MUST be settable by an option (feature 013 has one for each;
  `--agents-md` is added). No option skips or silences a check.
- **FR-032**: Principle XII MUST be amended to admit the `AGENTS.md` before the feature is released
  (see Constitution).
- **FR-033**: Out of scope: an MCP server, an `llms.txt`, fleet and monetisation topics, one error
  format across all verbs, publishing a JSON schema of the manifest, editing an existing manifest,
  and type detection by a learned model.

### Key Entities

- **Proposal**: the complete set of items one manifest is written from, derived from the data and the
  registries before anything is asked. It is the same in every mode and is what the decision
  accepts.
- **Item**: one entry of the proposal — the manifest field it fills, its value, its source (given,
  answered, proposed), its certainty and reason, and the option that sets it.
- **Certainty**: one of `certain`, `uncertain`, `convention`, `open` (FR-002). Only `uncertain` and
  `open` items are asked.
- **Finding**: a validation finding, in the form `validate` reports it, or a note of `init`'s own.
- **Result document**: the JSON document of FR-022.
- **Agent guide**: the optional `AGENTS.md` of FR-025 to FR-029, written beside the manifest.

## Constitution

The principles this feature touches, and how it complies (Development Workflow & Quality Gates).

- **XII. Small Core, Few Dependencies** — *must the constitution be amended?* **Yes, for the
  `AGENTS.md`, and for nothing else.**
  - Principle XII fixes the set of **verbs**, not their options. `--yes`, `--json`, `--tui` and
    `--agents-md` add no verb and need no amendment. The research's question about `--json` and
    `--yes` for *all* verbs belongs to the separate feature on one error format; it needs no
    amendment either for the same reason.
  - The bounds of `init` say it "writes one new manifest and nothing else". An `AGENTS.md` is
    something else, so a MINOR amendment must admit it: one optional `AGENTS.md` beside the
    manifest, written only after the manifest validates, never over an existing file, with its
    content bounded as in FR-027 and FR-028.
  - "Never over an existing file without the author's explicit confirmation": `--yes` is not that
    confirmation (FR-013); `--overwrite` remains it.
  - The full-screen interface "MUST ask the same questions and write the same file": kept behind
    `--tui` and opening on the same proposal, it does. Removed, the `authoring` slot is unused — no
    violation (the benchmarking-or-publication slot is unused today), but the slot's description in
    XII should then be updated.
  - No runtime dependency is added; `init` stays offline and in the default installation.
- **I. Declarative Manifest** — `init` still writes an ordinary manifest; the guide does not restate
  it (FR-028).
- **IV. Measured, Emulated or Estimated** — memory figures stay labelled as lower bounds estimated
  before building. Certainty is the same honesty applied to proposals: nothing is shown as known
  that is guessed (FR-002, FR-003).
- **V. Budgets Are Gates** — `--yes` skips no check (FR-013); the guide says a budget is the
  author's (FR-027).
- **VI. The Data Is the Author's** — nothing is asked that no stage reads; the guide claims no check
  of rights (FR-028).
- **VII. Targets and Templates Are Data** — every choice still comes from the registries.
- **IX. Manifest Contract** — the changed command line (`--no-input`, `--plain`) is allowed before
  1.0.0 and gets a change note (FR-017).
- **XI. No Claude in Model Learning** — the guide describes no workflow in which an agent produces
  data, labels or selection signals (FR-028); proposals come from rules, not from a language model.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the synthetic dataset with `label` as the output, going from `caravan init` to a
  written, valid manifest takes at most 4 answers, the data included (feature 013: 12).
- **SC-002**: On every tabular dataset shipped with Caravan, 100% of the proposals marked certain
  match the intended manifest, and all 7 differences measured on 2026-11-24 are marked uncertain or
  open.
- **SC-003**: 100% of the manifests `init` writes pass `caravan validate` unchanged, in every mode
  (feature 013, SC-002, kept).
- **SC-004**: Without a terminal, 100% of runs end without waiting for input, each within 5 seconds
  on the shipped datasets.
- **SC-005**: For every message about a missing answer, adding the option and the example value it
  names gets the run past that message — checked for every item that can be missing.
- **SC-006**: A script that reads only the JSON document of a run that wrote nothing can build the
  command that writes the manifest, and that command succeeds.
- **SC-007**: The proposal for the synthetic dataset, and for a dataset of 200 columns, fits in 24
  lines of 80 characters.
- **SC-008**: An author new to Caravan gets from a data directory to a valid manifest in under 2
  minutes without opening the documentation (feature 013: under 5).
- **SC-009**: The same answers and data produce byte-identical manifests — and guides — in every mode.

## Assumptions

- **Certainty is a category, not a percentage.** The proposals come from rules, not from a learned
  model; a number such as "87 %" would claim a precision the rules do not have. A learned detector
  is a possible later step, judged against measured data (the research's open question 1).
- **Template and parameters are conventions.** `init` does not infer an architecture from the data;
  it proposes the first registered template that answers the output, with the template's starting
  values, shows them, and lets the author change them under "adjust".
- **The `AGENTS.md` is opt-in**, as the request says "optional": Principle XII lets `init` write one
  file, and many projects already have an `AGENTS.md`. It is not proposed by default.
- **The baseline of FR-003** is the four tabular fixture datasets measured on 2026-11-24; a dataset
  shipped later joins the check, and a rule that then disagrees loses its certainty.
- **Output stays English**, like the rest of Caravan.
- **Before 1.0.0**, the command line may change without compatibility (Principle IX); scripts that
  use `--no-input` to accept proposals switch to `--yes`, as the change note says.
- **No new dependency**: the feature reuses the question engine, the profile and the memory estimate
  of feature 013.
