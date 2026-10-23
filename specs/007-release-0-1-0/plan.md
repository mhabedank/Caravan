# Implementation Plan: Release 0.1.0

**Branch**: `007-release-0-1-0` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-release-0-1-0/spec.md`

## Summary

The work turns the v0.1 framework into a version someone can install by tag, try in minutes and
trust:

- **Console output.** The training framework's output moves into `framework.log` in the run
  directory. That also repairs `--json` on the stage verbs, which Keras currently corrupts.
- **The guide.** One guide leads from an empty environment to an exported model and is tested as
  written.
- **Truthful documents.** The README, roadmap and a release note describe the release as it is.
- **Release workflow.** A workflow builds from the tag, checks the build and publishes a GitHub
  release with the wheel attached.

One functional change rides along because the release waits for it. **A fixed split** lets the data
say which records are training, validation and test. Without it, the `pace-cnn` port would leak
overlapping windows across the split, and its test score would mean nothing (research R8, R9).

The release itself is two steps:
1. `v0.1.0rc1` is tagged as soon as the work is merged. It is the version to try by hand and the
   version the port pins.
2. `v0.1.0` is tagged once the port has run on UCI HAR as an internal test and every Caravan defect
   it found is fixed.

## Technical Context

**Language/Version**: Python ≥ 3.13; training half on 3.13 (TensorFlow 2.21.0), runtime extra on
3.13–3.14, core on 3.13–3.15. Unchanged.

**Primary Dependencies**: none added. The redirection uses `os.dup`/`os.dup2`; the release workflow
uses `uv build` and the GitHub CLI already present on hosted runners.

**Storage**: files: the run directory gains `framework.log`; the repository gains `examples/`,
`ports/pace-cnn/`, `docs/try-it.md`, `docs/releases/0.1.0.md`.

**Testing**: pytest. A new guide test executes the guide's `run` blocks (in `tests/train`). Unit and
contract tests cover the fixed split, the redirection and the version check. The release workflow
runs the guide literally against the published release.

**Target Platform**: Linux and macOS for the guide (`curl`, `tar`); Windows is not a stated
platform of 0.1.0.

**Project Type**: CLI and library (single project).

**Performance Goals**: SC-001: from an empty environment to an exported model in under 10 minutes,
most of it the install of the training extra. SC-002: the export step prints at most 25 lines.

**Constraints**:
- The core still imports no framework; the redirection lives in the pipeline runner, which already
  runs only where an extra is installed.
- No credential exists anywhere: the release uses the workflow's own token, and nothing goes to the
  package index.
- No data enters the repository. The port's archive is read from wherever the author keeps it and
  verified by hash.

**Scale/Scope**: about ten source files touched, three new rules, one workflow, four documents, one
port directory.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I — declarative manifest, every field read | `dataset.split.column` is read by the data stage (which windows go where) and by `train`/`quantize` through the split plan; the fractions keep being read when used | pass |
| II — scope by target | the port is a microcontroller model; nothing widens scope | pass |
| III — reproducible | the version in every record is the tag's (R3); a fixed split is part of the data stage's key, so changing the column or its values re-runs `data`; the release is built from the tag | pass |
| IV — provenance | the port's numbers carry their labels and the run they came from; the published `pace-cnn` card figures are not claimed | pass |
| V — budgets before training | unchanged; the port states `accuracy_drop_max` | pass |
| VI — the data is the author's | Caravan does not judge the dataset's licence; the owner decided the port is internal; the contradiction is recorded for the zoo | pass |
| VII — registries, recorded sources | no board or template added | pass |
| VIII — export contract | `interface.json` unchanged; the port's record states that its input is standardised by the converter | pass |
| IX — variable until 1.0.0 | the fixed split is additive: an existing manifest keeps validating, so no new schema version is needed; the release note links the one change note since development began | pass |
| X — a named model drives it | `pace-cnn` drives the fixed split | pass |
| XI — no Claude in learning | the converter and the port train nothing with Claude, label nothing, evaluate nothing with Claude | pass |
| XII — small core, few dependencies | no dependency; no verb (`--framework-output` is an option on existing verbs); install budget unchanged | pass |
| Workflow — framework release gate | semver, change note, pilot green: recorded in the release note, enforced by the release workflow (R6, R7) | pass |
| Resources & cost | no cash cost: CI on the existing hosted runners, no paid service, no key | pass |

No violations, so no complexity tracking.

*Re-checked after Phase 1:* the design adds no dependency, no verb and no data. Every new manifest
field (`dataset.split.column`) has a reader. The constitution still passes.

## Project Structure

### Documentation (this feature)

```text
specs/007-release-0-1-0/
├── plan.md              # this file
├── research.md          # R1 console output … R9 fixed split
├── data-model.md        # split forms, framework log, release record
├── quickstart.md        # validation scenarios
├── contracts/
│   ├── manifest.md      # dataset.split.column, CF-12, CF-13, DS-13
│   ├── cli.md           # --framework-output, framework.log, --json repaired
│   └── release.md       # the release procedure and workflow
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/caravan/
├── __init__.py                     # __version__ = "0.1.0rc1", then "0.1.0"
├── manifest/schema/dataset.py      # Split gains `column`; CF-12
├── manifest/schema/__init__.py     # CF-13 (split column vs declarations)
├── manifest/errors.py              # CF-12, CF-13, DS-13
├── data/reader.py                  # read the split column; exclude it from derived inputs
├── data/windows.py                 # plan_split by column; mixed-split windows discarded and counted
├── stages/data.py                  # schema.json records the split column and its counts
├── cli/main.py                     # --framework-output on build, train, quantize, export
├── cli/pipeline.py                 # redirect fds 1 and 2 to framework.log around the stage loop
└── run/report.py                   # artifacts: framework_log; dataset_resolved: split source

examples/picket-mlp.yaml            # the guide's manifest; source → ../tests/fixtures/datasets/synthetic
ports/pace-cnn/
├── README.md                       # what the port is, its differences, its licence status
├── convert.py                      # UCI HAR archive (hash-checked) → CSV with label and split columns
└── pace-cnn.yaml                   # the Caravan manifest
docs/try-it.md                      # the guide, blocks marked fetch / install / run
docs/releases/0.1.0.md              # release note: what, where, limits, gate, port result
docs/roadmap.md                     # feature 006 and 007 under v0.1; v0.1 released
README.md                           # install by tag, status, quick start
pyproject.toml                      # version
.github/workflows/release.yml       # on tag v*: check, build, release, verify

tests/
├── unit/test_version.py            # __version__ equals the distribution's metadata
├── unit/test_fixed_split.py        # split by column: windows, mixed-split discard, empty part
├── unit/test_framework_log.py      # fd redirection keeps Caravan's lines, captures C-level output
├── contract/test_cli_contract.py   # --framework-output; --json parses after a stage run
├── contract/test_example_matches_fixture.py
├── integration/test_readme.py      # README quick start runs; install lines match the guide
├── train/test_try_it_guide.py      # the guide's run blocks, SC-002
├── train/test_fixed_split_run.py   # a run with a fixed split; DS-13
└── fixtures/
    ├── datasets/split/             # tiny synthetic data with a split column (generated, seeded)
    └── manifests/invalid/cf-12-*, cf-13-*
```

**Structure Decision**: a single project, as in every earlier feature. `ports/` is new: a port is
a record of Caravan meeting a real model, kept so it can be repeated. It holds no data and is not
part of the package.

## Phase order

1. **Fixed split** (FR-017–019), test-first. The port depends on it.
2. **Console output** (FR-008–010), test-first. The guide's SC-002 depends on it.
3. **Example, guide and guide test** (FR-005–007).
4. **Version check, release workflow, README, roadmap and release-note draft** (FR-001–004,
   FR-011–013).
5. **Merge, then tag `v0.1.0rc1`.** Tagging is an outward step: done after the owner's go-ahead in
   the conversation.
6. **The port** (FR-014–016, FR-020): converter, manifest, run with the candidate, record. Every
   Caravan defect found is fixed with a test, followed by `rc2` if needed.
7. **`v0.1.0`**, after the owner's go-ahead: version bump, release note completed with the port's
   result, tag.

## Complexity Tracking

No violations.
