# Implementation Plan: Windows That Know Their Recordings

**Branch**: `014-recording-aware-windows` (work happens on `claude/optimistic-sagan-tve9tc`) |
**Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-recording-aware-windows/spec.md`

## Summary

Make the windowing aware of recordings and the default split leak-free, and let every output type get
windows. The reader keeps concatenating files but returns their row ranges (cut further by an
optional `recording_column`); `plan_windows` cuts inside each range, at a `window_stride` that may be
smaller than the window, and labels each window by a `window_label` rule (`all_equal`, `last`,
`majority`, `mean`, `{any: v}`); `plan_split` gains `recording`, `group` and `blocked` splits that
assign whole groups, retry seeds for class coverage, and purge windows that would touch another part.
With a window and no stated split, the run derives `recording` or `blocked` from the data. The schema
moves to `caravan/v0.3` with a change note; the interface contract to version 4 with
`training_stride` and `window_label`. (research.md R1–R10.)

## Technical Context

**Language/Version**: Python 3.13–3.15 (core); the training path 3.13 as today.

**Primary Dependencies**: none new. Windowing and splitting stay standard-library only
(`data/windows.py`); the reader keeps numpy behind the `train` extra.

**Storage**: files — CSV data in; `data/schema.json`, the run report, `model/interface.json` out.

**Testing**: pytest. Unit tests on the pure functions (windows, labels, splits, purge) run in the
core matrix on every Python; contract tests for the manifest rules and the report shape; one
end-to-end export on the `train` extra; three new generated fixtures (R10).

**Target Platform**: unchanged (developer machine, CI).

**Project Type**: CLI tool / library (the pipeline's data stage and schema).

**Performance Goals**: windowing stays linear in rows; with a quarter-window stride, planning a
million rows stays under 2 seconds in pure Python (four million candidate windows checked by label
runs, not row by row — label runs are precomputed per recording).

**Constraints**: no window across recordings; no row shared across parts; every drop counted by
reason; reproducible from the report (seed, retries, assignment); a changed default only with a new
schema version and change note (Principle IX); no framework imported by the core (Principle XII).

**Scale/Scope**: 3 new manifest fields, 3 new split types, 7 new rule identifiers; ~6 source modules
touched; 39 manifests rewritten to `caravan/v0.3`; 3 new fixtures; reference docs for the new fields,
the change note, glossary entries for recording and window.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Against v4.3.0.

| Principle | How the design complies | Status |
|---|---|---|
| I. Declarative manifest | Three optional fields, each with a documented default and each read by the data stage; the split type a run derives from the data is shown as `derived` by `render` and recorded with its effective value by the run. No defaults section is added. | Pass |
| II. Embedded only | Serves the application classes already in scope (state estimation, intrusion and fault detection). | Pass |
| III. Reproducible | Seeds from the manifest; retries and assignments recorded; the stage cache key gains the new fields (they are read by the data, train, quantize and export stages). | Pass |
| IV. Labelled numbers | No hardware figures. | N/A |
| V. Gates | No gate is loosened; the neighbouring-windows notice accompanies a choice the author made explicitly, it does not replace a gate. Refusals (DS-18, DS-19, DS-20) fail the stage. | Pass |
| VI. Asks only what it uses | `recording_column` is optional and read by windowing and the split; nothing descriptive is asked. | Pass |
| VII. Data, not forks | No board or template change. | N/A |
| VIII. Portable artifacts | The interface contract states how training windows were cut and labelled (contract v4). | Pass |
| IX. Manifest contract | A changed meaning → `caravan/v0.3` and a change note with the restoring edit; v0.2 refused with V-1. | Pass |
| X. Real models | Justified by documented application classes (battery state of charge, CAN intrusion) that the current code cannot serve. | Pass |
| XI. No Claude in learning | Untouched. | N/A |
| XII. Small core | Standard library only in the core; no new dependency; no new verb. | Pass |
| Workflow (Resources & Cost Discipline) | The rule: "one pull request per feature, opened when its implementation is built and the local validation … has passed. Spec, plan, tasks and analysis are committed and pushed to the feature branch without a pull request"; specs "ride with the feature they belong to, or several are merged in one pull request". [mhabedank/Caravan#26](https://github.com/mhabedank/Caravan/pull/26) was opened as a draft at the spec stage of 013. Resolution (owner's delegation, 2026-11-17): #26 stays a draft and becomes the pull request of 014's implementation; 013's spec, plan, tasks and the joint review ride with it. It holds documentation only until then, so it starts no CI job, which is what the rule protects. It is marked ready for review only once 014 is built and validated locally. | Deviation, recorded below |

**Post-design re-check**: unchanged. The only recorded deviation is the timing of the pull request,
which is a matter of process, not of the design.

## Project Structure

### Documentation (this feature)

```text
specs/014-recording-aware-windows/
├── plan.md               # this file
├── research.md           # R1–R10
├── data-model.md         # Recording, WindowPlan, SplitPlan, Group
├── quickstart.md
├── contracts/
│   ├── manifest-fields.md  # caravan/v0.3 fields, defaults, rules, change note
│   └── reports.md          # data/schema.json, console summary, interface.json v4
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
src/caravan/
├── manifest/
│   ├── version.py                 # SCHEMA_VERSION = "caravan/v0.3"
│   ├── schema/__init__.py         # apiVersion literal; CF-20..CF-23 cross-field rules
│   ├── schema/preprocessing.py    # window_stride, window_label, recording_column; Split types
│   ├── resolve.py                 # defaults: stride, label rule by output type, split "derived"
│   └── errors.py                  # rule identifiers CF-20..23, DS-18..20; the notice
├── data/
│   ├── reader.py                  # recordings (file ranges, recording column), group column
│   ├── windows.py                 # per-recording windows, stride, label rules, split types, purge
│   └── test_part.py               # passes recordings and the group column through
├── stages/
│   ├── data.py                    # report additions; derived split recorded
│   └── train.py                   # passes the new plan inputs (no logic change)
├── export/interface.py            # contract v4: training_stride, window_label
└── cli/                           # console data summary; notice printed by validate
tests/
├── fixtures/datasets/{recordings,soc,bursts}/   # generated, with make.py
├── fixtures/manifests/**          # rewritten to caravan/v0.3; new valid/invalid fixtures
├── unit/test_windows_recordings.py, test_window_label.py, test_window_stride.py, test_split_groups.py
└── contract/test_manifest_v03.py, test_split_refusals.py, test_interface_v4.py
docs/
├── ref/manifest/preprocessing.md  # new fields; the random-split warning replaced
├── ref/manifest-changes.md        # the v0.3 change note
├── ref/rules.md                   # seven new rules
├── glossary.md                    # recording; window (updated: stride, label rule)
└── topics/pipeline.md             # how rows become examples, updated
```

**Structure Decision**: the change is concentrated where the rule already lives — `data/windows.py`
for the arithmetic (core, tested everywhere) and `manifest/schema/preprocessing.py` for the fields —
with the reader only reporting boundaries. No module moves.

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|---|---|---|
| #26 opened before the implementation was built | this session's tooling opens a draft pull request on the first push; the session may push only to its assigned branch | closing #26 and reopening later would leave the specs without a pull request while the tooling requires one; a draft with documentation only costs no CI minutes. #26 becomes 014's implementation PR (013's documents ride with it, which the rule allows) and leaves draft only after local validation |
