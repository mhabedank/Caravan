# Implementation Plan: `caravan init` Proposes the Whole Manifest at Once

**Branch**: `015-init-one-proposal` (work happens on `claude/caravan-init-proposal-redesign-aolf81`) |
**Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-init-one-proposal/spec.md`

## Summary

Rebuild the flow of `caravan init` around one proposal: read the data, derive every item of the
manifest with a certainty (`certain`, `uncertain`, `convention`, `open`) and a reason, show it in at
most 24 lines, ask only the boards and the uncertain or open items — the uncertain columns in one step
— and then accept, adjust or stop. Without a person `init` never asks: `--yes` accepts, anything else
writes nothing and names the option and a working example for every missing answer. `--json` prints
one result document; `--agents-md` writes a guide for coding agents beside the manifest. The
full-screen interface and the `authoring` extra are removed (spec, Clarifications 2026-11-26).

The approach (research.md): certainty is a property of the *rule* that made a proposal, classified
once against the shipped tabular data and enforced by a test (R1); the question engine of feature 013
stays and gains certainty, the items to ask and the proposal as one object, while the line front end
gets a new top-level flow and keeps its per-question functions for "adjust" (R2); a person is present
only when standard input and standard error are terminals (R3); every missing answer has one example
taken from the question's own valid choices (R5); the JSON document reuses `Finding.as_dict()` (R6);
the memory line reuses the estimate that shares `build`'s floor functions (R7); the guide is a fixed
text with one variable, written all-or-nothing with the manifest (R8). Planning measured the windows
too and amended the spec where the measurement showed the hand-written sizes fail the window table's
own criteria (R1.3, FR-003) and where a `number` output has no budget to propose (FR-002).

## Technical Context

**Language/Version**: Python, 3.13, 3.14 and 3.15, like the core (`requires-python`).

**Primary Dependencies**: `pydantic`, `ruamel.yaml` (already direct). No runtime dependency added;
the `authoring` extra and its `textual` are removed (Principle XII).

**Storage**: files — the data (read only), the manifest, and on request `AGENTS.md`.

**Testing**: pytest in the default installation. Contract tests for the verb (modes, streams, exit
codes, outcomes, the JSON document, the guide); unit tests for the certainty of every rule against
every shipped tabular dataset (FR-003) and for the proposal layout (24 × 80); integration tests for
byte-identity between the line mode and `--yes`, for the JSON round trip and for the example-option
round trip. The line mode is driven by replacing the person-detection function and feeding standard
input (R3).

**Target Platform**: any terminal, or none.

**Project Type**: CLI tool (a reworked verb).

**Performance Goals**: without a person, every run on the shipped datasets ends within 5 seconds
(SC-004); the proposal reads the 50,000-row sample of feature 013 plus the output column for the
window table, as today.

**Constraints**: never read standard input without a person; nothing written unless accepted or
`--yes`; `AGENTS.md` never overwritten or edited; no option that skips a check; byte-identical output
for identical answers; no training framework imported; offline.

**Scale/Scope**: one verb reworked (4 options added or changed, 1 removed); about 30 rules
classified; one new module each for the proposal, the result document and the guide; one package
(`caravan/tui`), one test directory, one extra and one CI job removed; the constitution amended
(v4.5.0); CLI reference, install page, roadmap, tutorial part 2 and release notes updated.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution v4.4.0.

| Principle | How the design complies | Status |
|---|---|---|
| I. Declarative manifest | The written manifest is unchanged in kind and content (feature 013's writer). The guide repeats no value of it (FR-028). No schema field is added. | Pass |
| II. Embedded targets only | Boards still only from the registry; none proposed. | Pass |
| III. Reproducible | `init` writes no artifact of a run; its two files are deterministic (FR-029, SC-009). | Pass |
| IV. Labelled numbers | The memory line carries "lower bounds, estimated before building" wherever it appears, the JSON document included (R7). Certainty labels proposals honestly: a rule is `certain` only where the shipped data confirms it (R1). | Pass |
| V. Budgets are gates | `--yes` skips no check; a bound that exceeds a board is a note, the gate stays `build`'s fit check (FR-006). No new option contains a forbidden word (R4). The guide says a failed budget is the author's to loosen. | Pass |
| VI. Asks only what it uses | Fewer questions than feature 013, none new; the guide claims no check of rights. | Pass |
| VII. Targets and templates are data | Choices and examples come from the registries (R5); a new template or board appears without a change to `init`. | Pass |
| VIII. No lock-in, local | Offline; plain files. | Pass |
| IX. Manifest contract | The command line changes before 1.0.0 (`--no-input`, `--plain`, the extra) with a change note (contracts/cli-init.md). The schema does not change. | Pass |
| X. Built for real models | No template, type, board or field is added. | N/A |
| XI. No Claude in model learning | Proposals come from rules, not from a model. The guide describes no workflow in which an agent produces data, labels or selection signals, and tells it not to iterate parameters or budgets until a gate passes (contracts/agents-md.md). | Pass |
| XII. Small core | **Needs amendment v4.5.0 before release** (FR-032, R10): `init`'s bound "one new manifest and nothing else" must admit the optional `AGENTS.md`, and the extras budget loses the `authoring` slot. The amendment is the first task; nothing that writes a guide merges before it. Flags add no verb. One optional dependency goes, none is added. | Pass, conditional on the first task |
| Resources & cost | The `authoring` CI job is removed; new tests run in the existing core matrix. Spec, plan and tasks are pushed without a pull request; one pull request when built. | Pass |
| Workflow | Principles touched are listed in the spec and here. | Pass |

**Post-design re-check (after Phase 1)**: unchanged. The design adds no manifest field, no
dependency and no verb. Two rules are stricter than FR-003 requires (identifier names, text with 257+
values) and one rule is new (columns that never decrease); all three only make `init` ask more, never
less, so no principle is loosened. The amendment of XII remains the one precondition. No deviation, so
Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/015-init-one-proposal/
├── plan.md               # This file
├── research.md           # Phase 0: R1–R11
├── data-model.md         # Phase 1: certainty, item, proposal, board memory, notes, result, states
├── quickstart.md         # Phase 1: runnable validation
├── contracts/
│   ├── cli-init.md       # the verb: options, flow, layout, streams, exit codes, change note
│   ├── init-result.md    # the JSON document
│   └── agents-md.md      # the guide's text
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.specify/memory/constitution.md   # amendment v4.5.0 (R10) — first task

src/caravan/
├── cli/
│   └── init.py               # options (--yes, --json, --agents-md; --no-input changed; --plain and
│                             #   INSTALL_HINT gone), person detection, outcomes → exit codes
├── init/
│   ├── profile.py            # certainty and alternatives per rule; never-decreasing columns;
│   │                         #   the fallback output's own reason
│   ├── session.py            # certainty(key), items, to_ask(), example(key), ready; budget of a
│   │                         #   number output open; no reference to a second front end
│   ├── proposal.py           # NEW: the proposal object and its 24 × 80 layout, memory lines
│   ├── result.py             # NEW: the JSON result document, notes, the accepting command
│   ├── guide.py              # NEW: the AGENTS.md text and the all-or-nothing write
│   ├── line.py               # the new flow: data → proposal → boards → uncertain/open → decision
│   │                         #   ↔ adjust; the uncertain-columns step; per-question asks kept
│   ├── windows.py            # which path made the proposal (criteria met / fallback / none)
│   ├── memory.py             # one line per board, verdicts exposed for the document
│   ├── drawing.py, form.py   # unchanged
│   └── __init__.py           # docstring
└── tui/                      # REMOVED

tests/
├── contract/
│   ├── test_init_contract.py       # feature 013's cases, --no-input → --yes where it meant "accept"
│   ├── test_init_line.py           # NEW: the flow with a person (US1)
│   ├── test_init_no_person.py      # NEW: no person, --yes, --no-input, notes, timing (US2)
│   ├── test_init_one_interface.py  # NEW: --plain/--tui refused, adjust panels, the search (US5)
│   ├── test_init_json.py           # NEW: the document for every outcome; the round trip (SC-006)
│   ├── test_init_examples.py       # NEW: every missing item's example gets past it (SC-005)
│   └── test_init_agents_md.py      # NEW: written, kept, byte-identical, nothing left on failure
├── unit/
│   ├── test_init_certainty.py      # NEW: every rule × every shipped tabular dataset (FR-003, SC-002)
│   ├── test_init_proposal.py       # NEW: layout ≤ 24 × 80, synthetic and 200 columns (SC-007)
│   ├── test_init_profile.py        # + never-decreasing, high-cardinality text, fallback reason
│   └── test_init_windows.py        # + the path that made the proposal
├── integration/
│   └── test_init_combinations.py   # --no-input → --yes; + line mode == --yes (SC-009)
├── layering/
│   ├── test_declared_dependencies.py   # extras: train, verify
│   └── test_no_framework_imported.py   # authoring module list and its test removed
└── tui/                              # REMOVED

pyproject.toml, uv.lock               # the authoring extra removed
.github/workflows/ci.yml              # the authoring job removed

docs/
├── ref/cli.md                # caravan init: the proposal, the options, outcomes (test_docs_reference)
├── intro/install.md          # "The full-screen setup, optionally" removed
├── intro/tutorial02.md       # the init paragraph: one proposal
├── releases/0.1.0.md         # the change note (contracts/cli-init.md)
└── roadmap.md                # feature 013's row amended; a row for feature 015
```

**Structure Decision**: the feature stays inside the `caravan/init/` package and the thin CLI module
of feature 013. Three new modules keep three new responsibilities out of the session, which is
already the largest file in the package: the proposal and its layout (`proposal.py`), the
machine-readable result (`result.py`) and the guide (`guide.py`). The session remains the one place
that knows proposals, checks and certainty, so the line mode and `--yes` cannot drift apart.

## Complexity Tracking

No constitution violations. The amendment of Principle XII is the owner's decision recorded in the
spec and is made before release as the first task; it is not a deviation to justify here.
