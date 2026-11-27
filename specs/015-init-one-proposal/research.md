# Research: `caravan init` Proposes the Whole Manifest at Once

**Feature**: 015-init-one-proposal | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

The UX research behind the feature is `specs/013-guided-manifest-setup/ux-research-2026-11.md`. This
note records what planning had to decide on top of it, from the code as it is on `main` (feature 013
merged) and from measurements on the shipped data.

## R1 — How sure is each proposal? A rule per item, measured

**Decision**: certainty is decided per *rule*, not per value. Every rule that makes a proposal is
classified once, against the shipped tabular datasets (FR-003), and the classification travels with
its proposal and reason.

**Measurements.**

1. *Types and outputs* (2026-11-24, in the spec's Context): seven differences between today's
   proposals and the intended manifests, all from three rules — few distinct integers make a
   category, two values make a binary output, and the fallback output column.
2. *Everything else* (2026-11-27, `Session.fill()` on the six tabular fixtures `synthetic`,
   `anomaly`, `recordings`, `soc`, `bursts` and `frames`, with board `s32k144`):

   | Dataset | Output | Window proposed | Template | Budget |
   |---|---|---|---|---|
   | synthetic | `label` (named) | 16 | mlp | 0.02 |
   | anomaly | `condition` (named) | 4 (fallback) | mlp | 0.02 |
   | recordings | `label` (named) | 8 | mlp | 0.02 |
   | soc | `temp` (**fallback**, reason text wrong) | 32 | mlp | **none** |
   | bursts | `label` (named) | 8 | mlp | 0.02 |
   | frames | `label` (named) | 4 | mlp | 0.02 |

   Two findings. The fallback output carries the reason of the named rule ("a column named like an
   answer") — a defect in today's reason text, fixed here because the reason is now what decides
   whether a person is asked. And a `number` output has no budget proposal at all
   (`BUDGET_PROPOSALS` has no `mae_increase_max`): it is *open* (spec FR-002, amended).
3. *Windows against the hand-written sizes* (2026-11-27, with each manifest's own template). The
   table's criteria are at most 5% of windows lost to mixed labels and at least 5 test windows per
   class (`windows.MAX_LOST`, `MIN_TEST_PER_CLASS`):

   | Dataset (template) | Hand-written | Its test windows / lost | Proposal | Proposal's path |
   |---|---|---|---|---|
   | synthetic (mlp) | 64 | 2 per class / 1% — **fails** | 16: ≥7 per class, 0% | criteria met |
   | anomaly (autoencoder) | 5 | fault 0 / 0% — fails | 5 | fallback ("loses the fewest") |
   | recordings (conv1d) | 32 | idle 4, move 6 / 21% — **fails** | 16: 8 and 14 / 10% | fallback |

   Wherever a hand-written size differs from the proposal, the hand-written size fails the table's
   criteria; the shipped manifests chose their windows before feature 014 made the table. So for the
   window, the reference FR-003 compares against is the table's criteria, not the shipped size
   (spec FR-003, amended). A proposal from the table's fallback path is uncertain.

**The classification** (the rule names are those of `profile.py` and `windows.py`):

| Item | Rule | Certainty | Why |
|---|---|---|---|
| column | every sampled cell empty | certain (left out) | nothing to read |
| column | one value in every row | certain (left out) | carries no information |
| column | name cannot name a feature | certain (left out) | the manifest cannot use it; the reason says how to rename |
| column | file names of images | certain (left out) | out of scope for `init` (feature 013) |
| column | two distinct values → binary | **uncertain** | differs on recordings/anomaly as outputs; as an input 0/1 could be a number |
| column | integers named like an identifier → category | **uncertain** | agrees on the shipped data, but a name is weaker evidence than values, and feature 013's assumptions name this exact case as the one to confirm (stricter, as FR-003 allows) |
| column | text, at most 256 distinct → category | certain | agrees everywhere |
| column | text, 257 or more distinct → category | **uncertain** (new) | nearly every row distinct reads as an identifier or a time stamp, not a category; stricter, no shipped counter-example |
| column | ≤16 distinct integers → category | **uncertain** | the source of four of the seven differences |
| column | numeric, many distinct → number | certain | agrees everywhere |
| column | numeric, never decreasing within any file, more than 16 distinct → left out | **uncertain** (new rule) | a time or a counter: a model that reads it learns the clock. No shipped dataset has one, so it cannot be certain |
| output | named like an answer (`label`, `target`, …) | certain | five of five named cases agree |
| output | last category-like column (fallback) | **uncertain** | wrong on `soc` |
| output | none | open | — |
| output type | the column allows only one type | certain | nothing to choose |
| output type | text, more than two values → category | certain | agrees (synthetic, frames) |
| output type | two values → binary | **uncertain** | differs on anomaly and recordings |
| output type | few distinct integers → number, category offered too | **uncertain** | same ambiguity as for inputs |
| normal value | — (only asked when no value is `normal`) | open | the data cannot say which value is normal |
| window | a size meets the table's criteria → the largest such | certain | R1.3 |
| window | fallback: the size that loses the fewest | **uncertain** | no size meets the criteria |
| window | no size yields windows | — | a rule failure (exit 1), not a missing answer: no option value would help |
| template | the only registered template that answers the output | certain | nothing to choose |
| template | the first of several, by starter rank | convention | an architecture is not in the data |
| parameters | the template's starter | convention | ditto |
| budget | the shipped examples' value (category, binary, anomaly) | convention | labelled "not a recommendation" (feature 013) |
| budget | `number` output | open | unit of the column; no value carries over |
| quantization | `int8` | convention | |
| name, file | from the data directory and template | convention | |
| `AGENTS.md` | not written | convention | opt-in (spec, Assumptions) |
| boards | — | open | review A10 |

On the synthetic data this asks for the boards and for one step of two uncertain columns (`can_id`,
`dlc`); output, type and window are certain. With the data and the decision that makes four answers
(SC-001).

**Rationale**: a rule-level class is checkable (a test runs every rule over every shipped dataset),
explains itself (the reason names the rule), and cannot claim more precision than rules have
(spec, Assumptions: no percentages).

**Alternatives considered**: a score per value from the counts (rejected: a number with no
calibration behind it); a language model or learned detector (out of scope, FR-033; Principle XI
would not forbid a non-Claude detector, but nothing measures one here); marking only the seven
measured cases uncertain (rejected: it would leave the identifier and high-cardinality cases certain
on the strength of a name or of no evidence).

**Known limit**: FR-003 is only as good as the shipped data. A dataset added later joins the test
that enforces it; a rule that disagrees with it loses its certainty there and then.

## R2 — The flow on top of the existing session

**Decision**: keep the question engine of feature 013 (`caravan/init/session.py`) — its proposals,
choices, checks, stale marking and writer — and add three things to it: a certainty per item, the
list of items still to ask, and the proposal as one object. The line front end
(`caravan/init/line.py`) gets a new top-level flow; its per-question functions stay and serve
"adjust".

```text
data ─▶ proposal shown ─▶ boards (unless given) ─▶ each uncertain or open item (unless given),
        uncertain columns as one step ─▶ proposal shown again ─▶ decision
decision: Enter ─▶ write ─▶ validate ─▶ done
          a     ─▶ list of items ─▶ that item's question (feature 013) ─▶ proposal ─▶ decision
          q / end of input / interrupt ─▶ stopped, nothing written
```

After every answer the items to ask are recomputed: an answer can turn a later certain item
uncertain (a new output column) or settle one. `<` goes back one question inside the asking step, as
today.

**Rationale**: the review question of feature 013 already lists every answer and jumps to it — that
*is* "adjust". Re-ordering the flow around it costs little and keeps one engine.

**Alternatives considered**: a new engine (rejected: the checks and stale marking would be written
twice); walking all questions on "adjust" as create-next-app does (rejected: picking the one item is
fewer questions, the thesis of the feature).

## R3 — When is there a person?

**Decision**: `init` asks only when standard input **and standard error** are terminals, and none
of `--yes`, `--no-input`, `--json` is given. Questions go to standard error, so that is the stream
that must reach a person; standard output may be captured (`path=$(caravan init …)`), which today's
check (stdin and *stdout*) wrongly treats as "no person".

Tests drive the line mode by replacing the one detection function (`caravan.cli.init._person`) and
feeding standard input, which is what feature 013's `--plain` tests did implicitly.

**Alternatives considered**: checking standard input only (clig.dev's minimum; rejected because a
question written to a redirected stderr reaches no one).

## R4 — Options

**Decision**:

| Option | Change |
|---|---|
| `--yes`, `-y` | new: accept every proposal not given; never ask |
| `--no-input` | now only "never ask"; without `--yes` nothing is written (FR-017) |
| `--json` | new: one result document on standard output; never ask |
| `--agents-md` | new: also write `AGENTS.md` beside the manifest |
| `--plain` | removed (FR-018) |
| everything else | unchanged from feature 013 |

`--yes` does not imply `--overwrite` (FR-013). None of the new names contains a word the no-skip
test forbids (`tests/contract/test_no_skip_option.py`). `--tui` is not added (spec, Clarifications).

## R5 — A message for a missing answer names one option and a value that works

**Decision**: the session gets one function, `example(key)`, that returns an option with a value
valid *here*, from the same choices the question would offer:

| Item | Example taken from |
|---|---|
| data | a directory or table in the current directory that `init` can read; otherwise the placeholder `<directory of CSV files>` (the one case where no valid value exists to name) |
| boards | the first registered board, with the full list |
| output | the first column offered as an output |
| output type | the type the column's values make first; the others listed |
| normal value | the column's first value; the others listed |
| budget (`number`) | one percent of the range seen in the sample, rounded, "in the column's unit" |
| any other | its proposal |

Format, one line per missing answer, on standard error (and as `example` in the JSON document):

```text
caravan init: no board: Caravan does not choose the hardware; give it with --board, for example
  --board esp32 (registered: esp32, s32k144, stm32h743)
```

A test runs every item that can be missing, adds exactly the named option and value, and checks the
run gets past that message (SC-005).

## R6 — The JSON result

**Decision**: one document per run on standard output, the shape fixed in
[contracts/init-result.md](./contracts/init-result.md). It reuses `Finding.as_dict()` for validation
findings, so they are in the form `validate --json` prints (FR-022). With `--json`, nothing for people
is written to standard error (as `validate --json` does); a defect still prints its trace there.

`outcome` names how the run ended, one-to-one with an exit code: `written` 0, `invalid` 1,
`unusable` 1 (the data cannot be set up, no template or window fits), `proposed` 2 (not accepted),
`incomplete` 2 (open items), `refused` 2 (an option value the data does not allow, an existing file
without `--overwrite`). A command line the parser rejects (unknown option) never reaches `init` and
produces no document; the contract says so.

**Alternatives considered**: JSON Lines with one event per step (rejected: one run, one answer); a new
error format (out of scope, FR-033: that is the separate feature on one error format across verbs).

## R7 — The memory line per board

**Decision**: computed by `memory.estimate()` from feature 013, which calls the same floor functions
`build`'s fit check uses (`caravan.targets.fit`), so the proposal and the fit check cannot disagree on
method. One line per chosen board, flash and RAM together:

```text
  memory   s32k144  flash ≥ 9.8 KB of 512 KB · RAM ≥ 2.6 KB of 64 KB  (lower bounds, est.)
```

A verdict other than `below` — `exceeds`, or `unknown` when the board states no figure — is marked
`✗` and becomes a finding before the decision (FR-006). The board question lists every registered
board with the same figures, since the rest of the proposal is known by then. When the estimate
cannot be made yet (no inputs), the line says so instead of showing a number.

## R8 — The `AGENTS.md`

**Decision**: the guide's text is a fixed template in a new module `caravan/init/guide.py`, filled
only with the manifest's file name — no other value (FR-028), no date, no version (FR-029). The exact
text is [contracts/agents-md.md](./contracts/agents-md.md).

**Writing, all or nothing** (spec, Edge Cases): both files are prepared as temporary files in the
manifest's directory; the manifest is validated (feature 013, as today); then the guide is linked into
place *exclusively* (it is always a new file, so a race with a file created meanwhile fails rather
than overwrites); then the manifest is moved into place; if that fails, the guide just created is
removed. An existing `AGENTS.md` is never touched — not with `--overwrite` either — and is reported as
a note.

**Alternatives considered**: appending a Caravan section to an existing `AGENTS.md` (rejected:
editing an author's file is what Principle XII keeps from `init`); writing the guide to standard
output (rejected: standard output belongs to the path or the JSON document).

## R9 — Removing the full-screen interface

**Decision** (spec, Clarifications 2026-11-26): remove, in one change —

| Where | What goes |
|---|---|
| `src/caravan/tui/` | the package (`__init__.py`, `app.py`) |
| `tests/tui/` | the pilot tests |
| `pyproject.toml` | the `authoring` extra and its comment; `uv.lock` regenerated |
| `.github/workflows/ci.yml` | the `authoring` job |
| `tests/layering/test_declared_dependencies.py` | `authoring` from the expected extras |
| `tests/layering/test_no_framework_imported.py` | the authoring-only module list and its test |
| `src/caravan/cli/init.py` | `INSTALL_HINT`, `--plain`, the app branch |
| `src/caravan/init/__init__.py`, `session.py` | docstrings naming the second front end |
| `docs/intro/install.md` | the section "The full-screen setup, optionally" |
| `docs/ref/cli.md` | "How it looks", `--plain` |
| `docs/roadmap.md` | the row of feature 013 updated; a row for this feature |

What the interface alone offered is already in the line mode: the window table and strip, the drawing,
the memory panel and the parameter form are produced by the session's `explain()` and `line.ask_form`
(FR-020). A search for the removed interface — the case-insensitive patterns `` `?authoring`?
extra``, `\[authoring`, `authoring =`, `textual`, `full[- ]screen` and `--plain` — over `src/`,
`docs/`, `README.md`, `pyproject.toml` and `.github/` must find only the change note in
`docs/releases/0.1.0.md` (SC-010; the command is in quickstart.md §7). The patterns allow for the
backticks and the spelling "full screen" that today's pages use. The roadmap's row for feature 013 is reworded rather
than annotated, so it does not name the removed interface either. "An authoring aid" — the
constitution's description of `init`, quoted in `tests/contract/test_cli_contract.py` — stays.

## R10 — The amendment of Principle XII (v4.4.0 → v4.5.0, MINOR)

**Decision**: one amendment, made as the first task through `/speckit-constitution`, with this
substance (the wording is the amendment's):

1. The `init` bound "it writes one new manifest and nothing else" becomes: it writes one new manifest
   and, when asked, one `AGENTS.md` beside it, and nothing else; never over an existing file without
   the author's explicit confirmation — and never over or into an existing `AGENTS.md` at all; the
   guide is written only once the manifest has validated, repeats none of its values, claims no check
   of rights (VI) and describes no workflow Principle XI forbids.
2. "a richer interface MAY come only as an optional extra — the authoring extra of the budget below —"
   loses the reference to a named slot: a richer interface MAY come only as an optional extra within
   the budget below, asking the same questions and writing the same file.
3. The extras budget returns to the slots before v4.4.0: training, verification, benchmarking,
   publication. Still four.

MINOR, because a bound is materially changed (a second file admitted) and a slot re-named; no
principle is removed and no gate loosened. The Sync Impact Report names this feature as the source.

## R11 — Tests

| Spec | Test |
|---|---|
| FR-003, SC-002 | every rule over every shipped tabular dataset against a table of intended answers in the test; the seven 2026-11-24 differences are uncertain or open |
| SC-001 | the line mode, with a fake terminal, on synthetic: four answers |
| FR-012, SC-004 | closed standard input, no terminal: no read is attempted, exit within 5 s |
| FR-014, FR-015, SC-005 | every missing item: add the named option and value, the message goes away |
| FR-016 | `--yes` lists the uncertain proposals taken |
| FR-021 to FR-024, SC-006 | the document parses for every outcome; a script builds the writing command from a `proposed` document alone and runs it |
| FR-006 | the memory line equals `build`'s floors (the existing `tests/train/test_init_memory_matches_build.py` covers the method) and marks an exceeded board |
| FR-025 to FR-029 | guide written, existing guide untouched with and without `--overwrite`, byte-identical, nothing left behind when the manifest move fails |
| FR-018 to FR-020, SC-010 | `--plain` and `--tui` are usage errors; no `authoring` extra; the search of R9 |
| SC-007 | the proposal for synthetic and for a generated 200-column table fits 24 × 80 |
| SC-009 | line mode and `--yes` write byte-identical files |
| FR-030 | feature 013's combination and byte-identity tests, moved from `--no-input` to `--yes` |

All run in the default installation, so in the existing core matrix; the `authoring` job goes. SC-008
(a new author in under 2 minutes) is a manual check in the quickstart.
