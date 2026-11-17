# Implementation Plan: A Guided Way to Write the Manifest

**Branch**: `013-guided-manifest-setup` (work happens on `claude/optimistic-sagan-tve9tc`) |
**Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-guided-manifest-setup/spec.md`

## Summary

Add `caravan init`, admitted by the constitution's amendment v4.3.0: a line-by-line dialogue that
reads the author's data, proposes a type for every column with the reason, asks only for what
Caravan cannot know — the output, the template, the boards, the int8 budget — and writes a short,
commented manifest that `caravan validate` accepts unchanged.

The approach (research.md): read the tables with the standard library so `init` runs in the default
installation (R2, R3); propose types by eight rules a reader can check against the reason shown
(R4, R5); take template parameters and the window from an optional `starter` on each template's
registration, so `init` holds no list of template names (R7); fill one answer set from options,
proposals or the dialogue, so the scripted and the interactive paths write the same bytes (R6);
serialise with comments through the YAML module that already exists, validate the exact bytes with
`load_manifest`, and move the file into place only when it is valid (R9).

## Technical Context

**Language/Version**: Python, supporting 3.13, 3.14 and 3.15 like the core (`requires-python`).

**Primary Dependencies**: `pydantic` and `ruamel.yaml`, both already direct dependencies. No
dependency is added (FR-024, Principle XII). `ruamel.yaml`'s round-trip mode, for comments, is used
only inside `caravan/manifest/_yaml.py`.

**Storage**: files — the data the author points at (read only) and the one manifest written.

**Testing**: pytest. Contract tests for the verb (exit codes, streams, options, no-skip walk);
unit tests for the profiler's rules and the writer; integration tests for every offered combination
(SC-002) and for byte-identity between the piped dialogue and `--no-input` (FR-020). All run in the
default installation, so they run in the core matrix.

**Target Platform**: any terminal, or none — standard input and error only (FR-022).

**Project Type**: CLI tool (a new verb in an existing command line).

**Performance Goals**: proposals for a million-row dataset within 5 seconds (SC-005), by reading a
bounded sample of 50,000 rows (R3).

**Constraints**: no training framework imported (layering tests); no network; no run directory,
cache or report written; no option whose name contains a forbidden word (`force`, `skip`, …);
nothing written on abort or on a validation failure; byte-identical output for identical answers.

**Scale/Scope**: one new verb with 13 options; about 12 questions; 4 built-in template starters;
one new optional field on `TemplateParameterSpec`; one new function in `_yaml.py`; one public
helper split out of `fingerprint.py`; CLI reference, README command list, tutorial part 1 and the
roadmap updated.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution v4.3.0.

| Principle | How the design complies | Status |
|---|---|---|
| I. Declarative manifest | `init` writes an ordinary manifest: template plus parameters, no code, no defaults section. Values that follow from the data (labels) are not asked (FR-015). Template starters are proposals in a dialogue, not defaults a manifest resolves (R7). | Pass |
| II. Embedded targets only | Offers only registered boards. | Pass |
| III. Reproducible | `init` is not a stage and writes no artifact; its own output is deterministic (FR-020): no date, no version stamp (contracts/manifest-output.md). | Pass |
| IV. Labelled numbers | `init` reports no figure about a model on hardware. Board RAM and flash are shown as the board description states them. | Pass |
| V. Budgets are gates | Every required budget is asked and confirmed (FR-011); no option skips a check; `--overwrite` confirms a write and is named so the no-skip test passes (R6). | Pass |
| VI. Asks only what it uses | Questions limited to fields a stage reads (FR-007); no description, unit or licence. Data is read locally and never copied. | Pass |
| VII. Targets and templates are data | Templates and boards come from the registries; starters are an optional field of the template's own registration, so a new template appears without changing `init` (SC-006). A test checks every registered starter. | Pass |
| VIII. No lock-in, local | Offline; the result is a plain YAML file. | Pass |
| IX. Manifest contract | Writes the current schema version; never rewrites an existing file, and replaces one only on the author's explicit confirmation (amendment v4.3.0). | Pass |
| X. Built for real models | No template or type is added. | N/A |
| XI. No Claude in model learning | Not touched. | N/A |
| XII. Small core | `init` admitted by v4.3.0 within its bounds: one new manifest, validated before success, default installation, offline, no runtime dependency, usable without a terminal, never editing. YAML stays behind `_yaml.py`; the profiler imports only the standard library and `fingerprint`. | Pass |
| Resources & cost | New tests run in the existing core matrix; no new CI job. | Pass |
| Workflow | One pull request for the feature ([mhabedank/Caravan#26](https://github.com/mhabedank/Caravan/pull/26)); pushes in validated batches. | Pass |

**Post-design re-check (after Phase 1)**: unchanged. The design adds one optional field to
`TemplateParameterSpec`, which Principle VII allows as data on the template; it adds no field to the
manifest schema, so Principle I's "every field is read by a stage" is not engaged. No deviation, so
Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/013-guided-manifest-setup/
├── plan.md               # This file
├── research.md           # Phase 0: R1–R10
├── data-model.md         # Phase 1: profiles, starter, answer set, session states
├── quickstart.md         # Phase 1: runnable validation
├── contracts/
│   ├── cli-init.md       # the verb: options, streams, exit codes
│   └── manifest-output.md# the file it writes
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/caravan/
├── cli/
│   ├── main.py               # + the `init` subparser and handler (13 options)
│   └── init.py               # NEW: argument handling, exit codes, streams; drives the session
├── init/                     # NEW package: the guided setup, no framework, no YAML import
│   ├── __init__.py
│   ├── profile.py            # column profiling with csv, the R4 rules, R5 output proposal
│   ├── answers.py            # the answer set, per-answer validation, proposals (R7, R8)
│   ├── session.py            # question order, back, summary, given-by-option, modes (R6, R10)
│   └── write.py              # answer set → commented mapping; temp file, validate, os.replace (R9)
├── manifest/_yaml.py         # + dump_commented(): round-trip serialisation with comments
├── data/fingerprint.py       # + data_files(): the public listing split out of _files_in
└── templates/
    ├── registry.py           # + TemplateStarter, + optional `starter` on TemplateParameterSpec
    ├── mlp.py                # + starter
    ├── conv1d.py             # + starter
    ├── conv2d.py             # + starter
    └── autoencoder.py        # + starter

tests/
├── contract/
│   ├── test_init_contract.py          # NEW: exit codes, streams, --no-input, --overwrite, abort
│   └── test_no_skip_option.py         # unchanged; walks `init` automatically
├── integration/
│   ├── test_init_combinations.py      # NEW: every offered combination validates (SC-002, SC-006)
│   └── test_init_byte_identical.py    # NEW: piped dialogue == --no-input (FR-020)
├── unit/
│   ├── test_init_profile.py           # NEW: R4 rules on the fixtures and on edge cases
│   ├── test_init_write.py             # NEW: no defaults written, comments, relative dataset path
│   └── test_template_starters.py      # NEW: every registered starter validates and fits its window
└── layering/                          # unchanged; must still pass

docs/
├── ref/cli.md                # + caravan init (test_docs_reference requires every verb)
├── intro/tutorial01.md       # + "or let caravan init write it"
└── roadmap.md                # + init (013); later: full-screen extra, editing a manifest
README.md                     # + init in the command list
```

**Structure Decision**: a new `caravan/init/` package beside `cli/`, because the session, the
profiler and the writer are testable without argument parsing, and because the later full-screen
extra (owner, 2026-11-16) will drive the same session object from a different front end. The CLI
module stays thin, like the other verbs in `cli/`. Nothing in `caravan/init/` imports the YAML
library directly (only through `_yaml.py`) or anything behind an extra.

## Complexity Tracking

No constitution violations. Nothing to justify.
