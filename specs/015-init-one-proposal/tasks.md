# Tasks: `caravan init` Proposes the Whole Manifest at Once

**Input**: Design documents from `/specs/015-init-one-proposal/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included. The plan names the test files, and most success criteria (SC-001 to SC-007,
SC-009, SC-010) can only be shown by tests. Each story's tests are written first and fail before its
implementation. Every test runs in the default installation, so in the existing core matrix.

**Organization**: by user story — US1 (P1) one proposal, one decision; US2 (P1) no question without
a person; US3 (P2) the JSON result; US4 (P3) the `AGENTS.md`; US5 (P3) one interface. The *removal*
of the full-screen interface's code is in Phase 2, not in US5: every change to the question engine in
Phases 2 and 3 would otherwise have to keep the Textual front end and its tests working, only for
them to be deleted later. US5 keeps the checks that prove the story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 … US5

## Path Conventions

Single project: `src/caravan/`, `tests/` at the repository root. Code paths follow plan.md.

---

## Phase 1: Setup

- [X] T001 Amend the constitution to v4.5.0 (MINOR) in `.specify/memory/constitution.md` through
  `/speckit-constitution`, with the substance of research R10: (1) Principle XII's `init` bound
  becomes "one new manifest and, when asked, one `AGENTS.md` beside it, and nothing else", the guide
  written only after the manifest validates, never over or into an existing `AGENTS.md`, repeating no
  value of the manifest, claiming no check of rights (VI) and describing no workflow Principle XI
  forbids; (2) "the authoring extra of the budget below" becomes "an optional extra within the budget
  below", still asking the same questions and writing the same file; (3) the extras budget names
  training, verification, benchmarking and publication — four, as before v4.4.0. The Sync Impact
  Report names feature 015 and the owner's answers of 2026-11-26 as the source. **Precedes every
  task of Phase 6 (US4).** Done 2026-11-27: constitution v4.5.0.
- [X] T002 [P] Add fixtures for the rules research R1 adds or changes to
  `tests/fixtures/datasets/init/`, each a small hand-written or arithmetic CSV, and record what each is
  for in `tests/fixtures/datasets/init/README.md`:
  `time-column.csv` (a column `t` of integers that never decrease, more than 16 distinct, beside a
  numeric `x` and a text `label` of three values); `many-text.csv` (a text column `station` with 300
  distinct values beside a text `label` of three values); `no-output.csv` (three float columns `a`,
  `b`, `c`, no column named like an answer and none category-like); `ok-fault.csv` (a text column
  `state` with the values `ok` and `fault` beside two float columns, for an anomaly output whose
  normal value is not `normal`).

---

## Phase 2: Foundational (blocking all stories)

**Purpose**: remove the second front end, then give every proposal its certainty and build the
proposal object both the line mode and `--yes` read.

### Removing the full-screen interface (research R9)

- [X] T003 Delete `src/caravan/tui/` and `tests/tui/`. In `src/caravan/cli/init.py` remove
  `INSTALL_HINT`, the `--plain` option and the `run_app` branch, so the line dialogue is the only
  front end. In `tests/contract/test_init_contract.py` drop `"--plain"` from the three tests that pass
  it (they run the line dialogue on piped input, as before). Reword the docstrings of
  `src/caravan/init/__init__.py`, `src/caravan/init/session.py` and `src/caravan/cli/init.py` so none
  names a second front end, Textual or the `authoring` extra.
- [X] T004 [P] Remove the `authoring` extra and its comment from `pyproject.toml`; regenerate
  `uv.lock` with `uv lock` and confirm `textual` no longer appears in it.
- [X] T005 [P] Remove the `authoring` job from `.github/workflows/ci.yml`.
- [X] T006 [P] In `tests/layering/test_declared_dependencies.py` expect the extras `["train",
  "verify"]` (update the comment that names feature 013); in
  `tests/layering/test_no_framework_imported.py` remove `AUTHORING_ONLY_MODULES` and
  `test_only_the_authoring_modules_import_textual_and_no_core_module_imports_them`.
- [X] T007 [P] In `docs/ref/cli.md` remove the `--plain` bullet and the full-screen half of "How it
  looks" (one sentence remains: the questions line by line, an empty line takes the proposal, `<`
  goes back); in `docs/intro/install.md` remove the section "The full-screen setup, optionally".

### Tests for certainty and the proposal (write first, they fail)

- [X] T008 [P] Write `tests/unit/test_init_certainty.py` (FR-003, SC-002). A table in the test states
  the intended answer per shipped tabular dataset — `synthetic` from `examples/picket-mlp.yaml`,
  `anomaly` from `examples/anomaly-autoencoder.yaml`, `recordings` from
  `tests/fixtures/manifests/valid/recordings-conv1d.yaml`, `frames` from `examples/frames-conv2d.yaml`,
  `soc` (output `soc`, every column `number`) from its `make.py` docstring, and `bursts` (output
  `label`; `can_id` category, `dlc` and `b0` number — the CAN shape of `synthetic`) from its
  `make.py` docstring. The edge-case tables under `tests/fixtures/datasets/init/` have no intended
  manifest and are not part of this table (spec FR-003). Assert: every proposal whose certainty is `certain` equals the intended answer; the seven
  differences of the spec's Context (`dlc`, output type of `condition`, `c`, output type of
  `label` in recordings, output column of `soc`, `current`, `temp`) are `uncertain` or `open`; a
  window is `certain` only when its size meets the table's criteria (`windows.MAX_LOST`,
  `windows.MIN_TEST_PER_CLASS`) and `uncertain` when it comes from the fallback (research R1.3,
  checked with each manifest's own template). Write the module docstring so that adding a shipped
  dataset means adding a row.
- [X] T009 [P] Extend `tests/unit/test_init_profile.py` with one case per rule of research R1's table:
  the certainty and alternatives of empty, constant, bad-name and image columns (`certain`, left out);
  two values (`uncertain`, binary); integers named like an identifier (`uncertain`, category); text
  with at most 256 distinct values (`certain`) and `many-text.csv`'s `station` (`uncertain`); at most
  16 distinct integers (`uncertain`); many distinct numbers (`certain`); `time-column.csv`'s `t`
  (`uncertain`, proposed left out, reason naming a time or a counter); and the fallback output on
  `tests/fixtures/datasets/soc` carrying its own reason, not "a column named like an answer".
- [X] T010 [P] Write `tests/unit/test_init_proposal.py` (FR-005, FR-006, SC-007): for
  `tests/fixtures/datasets/synthetic` and for a 200-column table generated in `tmp_path`, the proposal
  lines are at most 24, each at most 80 characters (`len(line)` in characters); the certainty is a
  word on every item line (`certain`, `uncertain`, `convention`, `open`); input columns are grouped by
  type, up to four uncertain columns named one per line and beyond four grouped; with board `s32k144`
  one memory line per board follows the boards line, and the label line reads "lower bounds,
  estimated before building; build checks again"; with the parameters `{hidden: [4096, 4096]}` the board
  is marked `✗` and an `exceeds-board` note is in `Proposal.notes` (FR-006); the session for this
  case is built with `given={"params": {"hidden": [4096, 4096]}, …}`, not through the CLI.

### Implementation

- [X] T011 In `src/caravan/init/profile.py` add to `ColumnProfile` the fields `certainty` (one of
  `certain`, `uncertain`, `convention`, `open`), `alternatives` (what else the values allow) and
  `never_decreasing` ("numeric, and no value below the one before it within any file"), tracked while
  sampling. Set certainty in `_propose` per research R1's table, including the two stricter rules
  (identifier names; text with `distinct_capped`) and the new rule: a numeric column that never
  decreases within any file and has more than `SMALL_CODES` distinct values is proposed left out,
  `uncertain`, reason "only grows within each file: a time or a counter? usually left out". Change
  `proposed_output` to return the name, its certainty and its reason — `certain` with "a column named
  like an answer" for `OUTPUT_NAMES`, `uncertain` with "no column named like an answer: the last
  column with few values" for the fallback, `open` when none. Make `output_types` callers able to
  tell whether more than one type is offered. Depends on T002, T009.
- [X] T012 [P] In `src/caravan/init/windows.py` give `WindowTable` a field `path` — `criteria` when
  a size met the criteria, `fallback` when the fewest-lost size was taken, `none` when no size yields
  windows — and extend `tests/unit/test_init_windows.py` to check it on `synthetic` (criteria),
  `anomaly` with `autoencoder` (fallback) and `recordings` with `conv1d` (fallback).
- [X] T013 [P] In `src/caravan/init/memory.py` add a `BoardMemory` record — `board`, `flash_bytes`,
  `ram_bytes`, `board_flash_bytes` and `board_ram_bytes` ("none when it states none"), a verdict per
  resource ("`below`, `exceeds`, `unknown` … anything but `below` is marked and becomes a note"),
  `peak_layer`, and `label` = `LABEL` — built from an `Estimate`, and a function that renders one line
  per board as in contracts/cli-init.md (`s32k144  flash ≥ 9.8 of 512 KB · RAM ≥ 2.6 of 64 KB  ✓`).
  Keep `panel()` for the adjust path.
- [X] T014 In `src/caravan/init/session.py` add (research R1, R5; data-model "Item"):
  `certainty(key, column=None) -> (certainty, reason)` for every key — output and output type from
  T011; inputs per column; window from `WindowTable.path` (`criteria` → `certain`, `fallback` →
  `uncertain`); template `certain` when exactly one registered template answers the output, else
  `convention`; params, quantization, name, file `convention`; budget `convention` for
  `accuracy_drop_max` and `auc_drop_max` and `open` for a `number` output; boards always `open`;
  normal label `open`. Add `to_ask()` ("open or uncertain, not given, not yet answered; uncertain
  inputs as one entry"), `ready` ("nothing open, nothing stale, every check passes"),
  `candidates()` (readable data directories and tables directly in `cwd`), and `example(key,
  column=None)` per research R5's table (a value from the question's own valid choices; the
  placeholder `<directory of CSV files>` only for data with no candidate; for a `number` budget one
  percent of the sampled range, rounded). A window with path `none` makes the data `unusable` (a rule
  failure, research R1), not a missing answer. Depends on T011, T012.
- [X] T015 Create `src/caravan/init/proposal.py` with `Item` (fields of data-model "Item": `key`,
  `column`, `field`, `value`, `source` one of `given`, `answered`, `proposed`, `certainty` "none for
  `given` and `answered`", `reason`, `alternatives`, `option`, `example`, `stale`), `Proposal`
  (`dataset`, `items` "in the order of feature 013's `ORDER`, inputs in column order", `memory`,
  `to_ask`, `ready`, `notes` — "`init`'s own notes so far", kinds `sampled` and `exceeds-board` at
  this stage), `build(session) -> Proposal` and `lines(proposal, width=80) -> list[str]` in the
  layout of contracts/cli-init.md ("The proposal, as shown"): `  <label, 10>  <value, 26>  <certainty>:
  <reason>` cut with `…`, grouping and the memory lines from T013, the label once. Depends on T013,
  T014. Makes T008–T010 pass.

**Checkpoint**: `uv run pytest tests/unit tests/contract tests/layering -q` is green; no front end
uses the proposal yet.

---

## Phase 3: User Story 1 — One proposal, then one decision (Priority: P1) 🎯 MVP

**Goal**: in a terminal, `init` shows the whole proposal, asks the boards and only the uncertain or
open items (uncertain columns in one step), then accept / adjust / stop.

**Independent Test**: on `synthetic`, with a person present, four answers (data, board, columns step,
accept) write a manifest that validates (spec US1).

### Tests for User Story 1 (write first, they fail)

- [X] T016 [P] [US1] Write `tests/contract/test_init_line.py`. Its helper runs `main(["init", …])` in
  `tmp_path` with `caravan.cli.init._terminal` replaced to return `True` (the check `_person` builds on) and standard input a counting
  reader. Tests: four answers on `synthetic` (`<data>`, the number of `s32k144`, Enter, Enter) write a
  valid `synthetic-mlp.yaml` (SC-001); the proposal is on standard error before the board question;
  the columns step lists exactly `can_id` and `dlc`; every board in the board question shows the
  model's lower bounds and the list ends with the label line; the second proposal has the memory
  line and its label; `a`, then the window,
  shows the window table and strip, and after choosing 8 the window line reads `8 rows` with
  `answered`; `q` and end of input write nothing and exit 2; `<` in the asking step goes back one
  question; with data directories in `cwd` and no `--dataset`, they are offered as numbered choices;
  after adjusting the output to a column that makes the template stale, Enter at the decision is
  refused with the item named.

### Implementation for User Story 1

- [X] T017 [US1] In `src/caravan/init/session.py` make the board choices show, per registered board,
  its RAM and flash and the model's lower bounds against them once the estimate can be made, and the
  label line "lower bounds, estimated before building; build checks again" below the list (US1
  scenario 7, Principle IV); let the dataset question offer `candidates()`; turn the `review` question into the
  decision (choices: write — only when `ready` —, adjust, stop) while keeping its key so later
  answers are still marked stale through `ORDER`.
- [X] T018 [US1] Rewrite the top-level `run()` of `src/caravan/init/line.py` as research R2's flow:
  data (when not given) → `proposal.lines()` → boards (when not given) → each entry of
  `session.to_ask()`, the uncertain inputs through a new `ask_uncertain_columns()` that shows only
  those columns with their proposal, reason and alternatives and accepts edits like `dlc=number,
  can_id=-` → `proposal.lines()` again → the decision line `Enter: write <file> · a: adjust · q:
  stop` → on `a`, the items numbered; the chosen one asked with the existing `show_question` /
  `ASK` functions and the session's `explain()` panels; back to the proposal. Recompute `to_ask()`
  after every answer. Keep `<`, end of input and interrupt as today.
- [X] T019 [US1] In `src/caravan/cli/init.py` add `_person()` — standard input and standard error are
  terminals (research R3) — and run `line.run()` when it is true. Until T024 replaces it, the path
  without a person and without `--no-input` also runs `line.run()` on piped standard input, as
  feature 013 did, so the suite stays green between the two stories; `--no-input` keeps feature 013's
  meaning until T024. A validation finding after writing still sends the person back to the item that
  owns it (feature 013, research R10).
- [X] T020 [US1] Move the three line-dialogue tests of `tests/contract/test_init_contract.py`
  (`test_the_dialogue_accepts_every_proposal_with_enter`, `test_going_back_keeps_the_answers`,
  `test_end_of_input_writes_nothing`) into `tests/contract/test_init_line.py`, rewritten for the new
  flow with the person helper; update the dialogue side of
  `test_the_dialogue_and_no_input_write_the_same_bytes` in
  `tests/integration/test_init_combinations.py` to the new flow's answers, driven with `_terminal`
  returning `True` so it keeps working after T024.

**Checkpoint**: US1 works on its own; T016 passes; the default-install suite is green.

---

## Phase 4: User Story 2 — No question without a person; every missing answer names its option (Priority: P1)

**Goal**: without a person `init` never reads standard input; `--yes` accepts; otherwise nothing is
written and every missing answer comes with an option and a value that works.

**Independent Test**: with standard input closed and no terminal: `--yes --board s32k144` writes;
without `--yes` and without `--board`, exit 2 within seconds, and adding exactly the named options
writes (spec US2).

### Tests for User Story 2 (write first, they fail)

- [X] T021 [P] [US2] Write `tests/contract/test_init_no_person.py` with `_terminal` returning `False`
  and a standard input that fails the test if read: without `--yes`, exit 2, nothing written, the
  proposal and `nothing written: no one to ask, and --yes was not given` on standard error, and the
  accepting command naming `--board esp32 --yes`; `--yes --board s32k144` writes, exits 0, and lists
  `can_id` and `dlc` as uncertain proposals taken, each with `--input <column>=number` (FR-016);
  `--yes` without `--board` exits 2 naming `--board` with an example and the registered boards;
  `--yes` with an existing file and no `--overwrite` exits 2 naming `--overwrite` and leaves the file;
  `--no-input` and `--yes` with `_terminal` returning `True` never read; `--yes` with `--params
  '{hidden: [4096, 4096]}'` prints the `exceeds-board` note and still writes (FR-006); every shipped
  tabular dataset ends within 5 seconds (SC-004).
- [X] T022 [P] [US2] Write `tests/contract/test_init_examples.py` (FR-015, SC-005): for every item that
  can be missing — data (with and without a candidate in `cwd`), boards, output (`no-output.csv`),
  normal value (`ok-fault.csv` with `--output state --output-type anomaly`), budget (`soc` with
  `--output soc`) — run `--yes` without it, take the option and value from the message, add exactly
  those, and assert that message is gone; except the placeholder data example, the run then writes.

### Implementation for User Story 2

- [X] T023 [US2] Create `src/caravan/init/result.py` with `accepting_command(argv, examples)`: the
  command as given, plus each open item's example, plus `--yes`, quoted with `shlex.join`
  (contracts/cli-init.md, "Without a person").
- [X] T024 [US2] In `src/caravan/cli/init.py` add `-y`/`--yes` ("accept every proposal not given as
  an option; ask nothing") and give `--no-input` its new meaning ("ask nothing; without `--yes`, write
  nothing"); `_person()` is false whenever `--yes` or `--no-input` is given (T030 adds `--json`).
  Without a person:
  with `--yes`, take every proposal not given (`session.fill()`), print the uncertain ones taken, write;
  open items → one line each in the contract's format with `session.example()`, exit 2; without `--yes`
  → the proposal lines, the missing lines and `accepting_command()`, exit 2, nothing written. A window
  with path `none`, image inputs or no usable input → exit 1. `--yes` never implies `--overwrite`.
  Depends on T014, T023.
- [X] T025 [US2] In `tests/contract/test_init_contract.py` replace `--no-input` by `--yes` wherever a
  test meant "accept the proposals", add `test_no_input_alone_writes_nothing`, and keep the remaining
  feature-013 cases (template refusal, input edits, window too short, quantization `none`, params as
  a flow mapping, unreadable data, only `int8` and `none`, exit 1 reserved for a refused manifest).
- [X] T026 [US2] In `tests/integration/test_init_combinations.py` switch the scripted side to `--yes`
  and assert the line mode (from T020) and `--yes` write byte-identical files for `synthetic`,
  `anomaly` and `recordings` (SC-009).
- [X] T027 [P] [US2] In `docs/ref/cli.md` document `-y`/`--yes` and the new meaning of `--no-input`
  (`tests/contract/test_docs_reference.py` requires every option).

**Checkpoint**: US1 and US2 both work; `init` never blocks without a terminal.

---

## Phase 5: User Story 3 — The result as one JSON document (Priority: P2)

**Goal**: `init --json` prints one document per run with the written paths, every item with its
certainty, the memory per board, findings and notes, and the next command.

**Independent Test**: a preview document without `--yes` names a `next` command that, run as is,
returns a `written` document and a valid manifest (spec US3, SC-006).

### Tests for User Story 3 (write first, they fail)

- [X] T028 [P] [US3] Write `tests/contract/test_init_json.py`: for each outcome — `written`, `invalid`
  (every offered choice validates, so produce it by monkeypatching `Session.document` to append an
  unknown top-level field, which validation refuses),
  `unusable`, `proposed`, `incomplete`, `refused` — standard output parses as exactly one JSON object
  with the keys of contracts/init-result.md in order (`outcome`, `written`, `dataset`, `items`,
  `memory`, `findings`, `notes`, `next`), all present; the exit code matches the outcome; standard
  error is empty; with `_terminal` returning `True`, `--json` never reads; findings equal
  `Finding.as_dict()`; every `Item` has `source` in `given`, `answered`, `proposed` and `certainty`
  `null` unless `proposed`; every item has a non-empty `option` and `example` (FR-031); memory
  entries carry the label "lower bounds, estimated before building;
  caravan build checks them again"; the same command twice prints the same bytes; and the round trip
  of SC-006 — run the `proposed` document's `next` with `shlex.split` and get `written`.

### Implementation for User Story 3

- [X] T029 [US3] In `src/caravan/init/result.py` build the document from a `Proposal`, the outcome
  (`written` 0, `invalid` and `unusable` 1, `proposed`, `incomplete` and `refused` 2), the validation
  findings (`Finding.as_dict()`), the notes (kinds `sampled`, `uncertain-taken`, `exceeds-board`,
  `agents-md-kept`, `missing`, each with `key`, `column`, `message`, `example`) and `next`
  (`caravan build <file>` after writing; the accepting command with `--json` for `proposed` and
  `incomplete`; otherwise `null`). Serialise with `json.dumps(..., indent=2, ensure_ascii=False)` and a
  trailing newline, like `validate --json`. Depends on T015, T023.
- [X] T030 [US3] In `src/caravan/cli/init.py` add `--json` and route every outcome reached after
  argument parsing through `result.py`: the document on standard output and nothing for people on
  standard error (a defect still prints its trace). Depends on T024, T029.
- [X] T031 [P] [US3] In `docs/ref/cli.md` document `--json` and the outcomes with their exit codes.

**Checkpoint**: US3 works on its own on top of US2's non-interactive path.

---

## Phase 6: User Story 4 — An `AGENTS.md` beside the manifest (Priority: P3)

**Goal**: on request `init` writes the guide of contracts/agents-md.md beside the manifest, never over
an existing one, all or nothing with the manifest.

**Independent Test**: `--yes --agents-md` in an empty directory writes both files; with an existing
`AGENTS.md` it stays unchanged, the manifest is written, and `init` says so (spec US4).

**Precondition**: T001 (constitution v4.5.0) — done.

### Tests for User Story 4 (write first, they fail)

- [ ] T032 [P] [US4] Write `tests/contract/test_init_agents_md.py`: `--yes --agents-md` writes
  `AGENTS.md` beside the manifest, also when the manifest goes to a subdirectory, with exactly the text
  of contracts/agents-md.md and the manifest's file name; an existing `AGENTS.md` is unchanged with and
  without `--overwrite`, the manifest is written, and `kept AGENTS.md: it exists, and init never
  changes it` is printed (and an `agents-md-kept` note with `--json`); without `--agents-md` no guide;
  two runs give byte-identical guides; two manifests that differ in everything but their name give the
  same guide; when moving the manifest into place fails (monkeypatched `os.replace`), neither file is
  left; every command line in the guide's table parses with `build_parser()`; in the line mode the
  adjust list offers `AGENTS.md` and choosing it writes the guide.

### Implementation for User Story 4

- [ ] T033 [P] [US4] Create `src/caravan/init/guide.py` with the guide's text as one constant, exactly
  contracts/agents-md.md, and `render(manifest_name) -> str` — the only variable is the manifest's file
  name: no date, no version, no other value (FR-028, FR-029).
- [ ] T034 [US4] In `src/caravan/init/guide.py` add the all-or-nothing write of research R8 and call it
  from `Session.write()` in `src/caravan/init/session.py`: both files prepared as temporary files in
  the manifest's directory; the manifest validated; the guide linked into place exclusively; the
  manifest moved into place; on failure the guide just created is removed. An existing `AGENTS.md` is
  never opened for writing. Depends on T033.
- [ ] T035 [US4] Add the `agents_md` item (`convention`, "not written", option `--agents-md`) to
  `src/caravan/init/session.py` and `src/caravan/init/proposal.py`, the `--agents-md` option and the
  final lines `wrote AGENTS.md` / `kept AGENTS.md: it exists, and init never changes it` to
  `src/caravan/cli/init.py`, and the `agents-md-kept` note to `src/caravan/init/result.py`. Depends on
  T034.
- [ ] T036 [P] [US4] In `docs/ref/cli.md` document `--agents-md` and add the guide to **Writes**.

**Checkpoint**: US4 works with `--yes` and in the line mode.

---

## Phase 7: User Story 5 — One interface (Priority: P3)

**Goal**: the line mode is the only interface; what the full-screen interface showed is reachable under
"adjust"; nothing outside the change note mentions it (the code went in Phase 2).

**Independent Test**: `--plain` and `--tui` are usage errors; no `authoring` extra; under "adjust" the
window table, the drawing, the parameter form and the memory panel appear (spec US5).

- [ ] T037 [P] [US5] Write `tests/contract/test_init_one_interface.py`: `--plain` and `--tui` exit 2;
  under "adjust" in the line mode (person helper of T016) the template shows the drawing, the
  parameters show the presets and the per-value form, and the quantization shows the memory panel
  (FR-020); and the SC-010 search — the case-insensitive regular expressions `` `?authoring`?
  extra``, `\[authoring`, `authoring =`, `textual`, `full[- ]screen` and `--plain` over `src/`,
  `docs/`, `README.md`, `pyproject.toml` and `.github/` — finds only `docs/releases/0.1.0.md`. Before
  T038, check the test against today's `docs/roadmap.md` ("full screen with the `authoring` extra") to
  see it catches the backticked and the spaced spelling.
- [ ] T038 [US5] Reword the feature-013 row of `docs/roadmap.md` so it no longer names the removed
  interface ("`caravan init`: a first manifest from the data, with the window table, a drawing of the
  network and memory per board"), and fix anything else T037's search finds.

**Checkpoint**: all five stories work; the search is clean.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T039 [P] Rewrite the prose of the `caravan init` entry in `docs/ref/cli.md` to
  contracts/cli-init.md: one proposal with a certainty per line, the boards and the uncertain items
  asked, accept / adjust / stop, the memory line per board, behaviour without a person, outcomes and
  exit codes.
- [ ] T040 [P] Update the `caravan init` tip in `docs/intro/tutorial02.md` (one proposal, only the
  boards and what it is unsure of are asked) and the command list line in `README.md` (`caravan init
  # propose a first manifest from your data`).
- [ ] T041 [P] Add the change note of contracts/cli-init.md to the "Change notes" section of
  `docs/releases/0.1.0.md`.
- [ ] T042 [P] Add a row for feature 015 to `docs/roadmap.md` (one proposal instead of question by
  question; `--yes`, `--json`, `--agents-md`; the line mode the only interface), after T038.
- [ ] T043 Run quickstart.md §1–§8 and record the outcome of each section, including the SC-008 check
  with a reader new to Caravan, in the Notes below.
- [ ] T044 Local validation before the pull request (constitution, Resources & Cost Discipline):
  `uv run ruff check .`, `uv run ruff format --check .`, and the whole suite on Python 3.13, 3.14 and
  3.15 in the default installation, plus the `verify` and `train` jobs' commands from
  `.github/workflows/ci.yml` where their window allows.
- [ ] T045 Mark the tasks done here, set the spec's status, push in one validated batch, and open the
  feature's one pull request as a draft with spec, plan and tasks on the branch.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1**: T001 (done) precedes Phase 6; T002 before T011.
- **Phase 2**: T003–T007 first (they remove what later tasks would otherwise have to keep working);
  T008–T010 before T011–T015; T011 → T014 → T015; T012 and T013 in parallel with T011.
- **Phase 3 (US1)**: after Phase 2.
- **Phase 4 (US2)**: after Phase 2; T026 needs T020 (US1) for the line side of the byte-identity
  test — the only cross-story link.
- **Phase 5 (US3)**: after T023 and T024 (US2), which give it the non-interactive path.
- **Phase 6 (US4)**: after Phase 2 and T001.
- **Phase 7 (US5)**: after Phase 2; T037's adjust checks use US1's person helper (T016).
- **Phase 8**: after the stories it documents.

### Story order

US1 → US2 → US3 → US4 → US5 by priority. US4 and US5 can run beside US2 and US3.

### Within a story

Tests first, failing; then session and proposal changes; then the line front end or the CLI; then the
reference documentation for any new option, so `test_docs_reference.py` stays green at every
checkpoint.

## Parallel Examples

```text
Phase 2, after T003:  T004 · T005 · T006 · T007        (four different files)
Phase 2 tests:        T008 · T009 · T010
Phase 2 code:         T011 ‖ T012 ‖ T013, then T014, then T015
US2 tests:            T021 · T022
US4:                  T032 (tests) ‖ T033 (guide text)
Polish:               T039 · T040 · T041 · T042
```

## Implementation Strategy

### MVP

Phases 1–3: the one-proposal flow in a terminal (US1) on the certainty engine. Stop and run
quickstart.md §1–§2.

### Releasable

US1 and US2 together — both P1: the flow with a person and the guarantee that nothing waits for one.
Then US3 (JSON), US4 (guide, after the amendment) and US5 (the clean search), each its own
checkpoint.

### One pull request

Per the constitution: spec, plan and these tasks are pushed to the branch without a pull request; the
one pull request opens when T044 has passed (T045).

## Notes

- `[P]` tasks touch different files and depend on nothing unfinished.
- No test is skipped, quarantined or weakened to get green.
- Feature 013's spec, plan and tasks stay as written; this feature records what it replaces.
