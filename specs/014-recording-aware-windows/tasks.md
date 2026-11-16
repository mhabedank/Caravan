# Tasks: Windows That Know Their Recordings

**Input**: Design documents from `/specs/014-recording-aware-windows/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included. The plan and quickstart name the test files, and every success criterion
(SC-001–SC-005) is a measured property only a test can hold. Each story's tests come first and fail
before its implementation.

**Organization**: US1 (P1) no window crosses a recording · US2 (P1) a split that does not leak ·
US3 (P2) every output gets windows · US4 (P2) overlapping windows, safely.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4

## Path Conventions

`src/caravan/`, `tests/`, `docs/` at the repository root. Unit tests of `data/windows.py` run in the
core matrix (no framework); the end-to-end export needs the `train` extra.

---

## Phase 1: Setup

- [ ] T001 [P] Generate `tests/fixtures/datasets/recordings/` with a `make.py` like the existing
  fixtures': six CSV files `r1.csv`…`r6.csv` with columns `label, a, b, c`, two classes `idle` and
  `move`, file lengths 450, 517, 600, 389, 702, 498 rows (none a multiple of 64), each file holding
  stretches of both classes; commit the generated files and record the shape in
  `tests/fixtures/datasets/recordings/README.md`.
- [ ] T002 [P] Generate `tests/fixtures/datasets/soc/` with `make.py`: two files of 1,000 rows,
  columns `soc, current, voltage, temp`, `soc` falling 0.01 per row from 1.0 (continuous, never
  repeating within a file) — the review's failing case (spec Context).
- [ ] T003 [P] Generate `tests/fixtures/datasets/bursts/` with `make.py`: one file of 4,000 rows,
  columns `label, can_id, dlc, b0`, `label` `normal` with 20-row `dos` bursts every 200 rows starting
  at row 100 — the review's CAN-like case.
- [ ] T004 [P] Add `tests/support.py` constants for the three fixtures (`RECORDINGS_DATASET`,
  `SOC_DATASET`, `BURSTS_DATASET`) and a helper `leakage_example()` that builds the review's labels:
  one recording, two classes in contiguous 3,200-row blocks.

---

## Phase 2: Foundational (blocking all stories)

- [ ] T005 Change the schema version to `caravan/v0.3`: `SCHEMA_VERSION` in
  `src/caravan/manifest/version.py` and the `apiVersion` literal in
  `src/caravan/manifest/schema/__init__.py`; rewrite every `apiVersion: caravan/v0.2` in the
  repository (39 files: `examples/`, `tests/fixtures/manifests/**`, documentation code blocks) to
  `caravan/v0.3`; confirm a `caravan/v0.2` manifest is refused with V-1 (research R9). Manifests that
  a test expects to split at random get `split: {type: random}` stated explicitly.
- [ ] T006 Add the fields to `src/caravan/manifest/schema/preprocessing.py` exactly as in
  [contracts/manifest-fields.md](./contracts/manifest-fields.md): `window_stride: int | None`
  ("1 … window_size; default window_size"), `window_label`
  (`"all_equal" | "last" | "majority" | "mean"` or a one-key mapping `{any: <value>}`),
  `recording_column: str | None`; extend `Split.type` with `recording`, `group`, `blocked`, and make
  the type optional so "unset" can resolve to `derived` (keep `random` as the resolved default when
  there is no window). `group` requires `column`; `fixed` keeps its rules.
- [ ] T007 Add rule identifiers CF-20, CF-21, CF-22, CF-23, DS-18, DS-19, DS-20 to
  `src/caravan/manifest/errors.py` with the meanings of research R7, and a `Notice` type (not a
  finding; does not change the exit code) for the neighbouring-windows notice.
- [ ] T008 Implement CF-20–CF-23 as cross-field validators in
  `src/caravan/manifest/schema/__init__.py`: CF-20 "`window_stride` outside 1 … `window_size`, or set
  without a window"; CF-21 "`window_stride` < `window_size` with `random` or `stratify`"; CF-22
  "`window_label` not applicable to the output type (`mean` only for `number`; `majority` and `{any}`
  not for `number`), or `window_label`/`recording_column` without a window"; CF-23
  "`recording_column` equals an input, the output or `split.column`; `group` without `split.column`".
  Add one invalid fixture per rule under `tests/fixtures/manifests/invalid/` with its
  `.expected.json`, following the existing `<rule>-<case>.yaml` pattern.
- [ ] T009 Resolve the defaults in `src/caravan/manifest/resolve.py`: `window_stride` →
  `window_size`; `window_label` → `last` for `number`, `all_equal` otherwise; `split.type` unset with
  a window → `derived` (`DERIVED`), without a window → `random`; `recording_column` → `None`. Add
  `preprocessing.window_stride`, `preprocessing.window_label` and `preprocessing.recording_column` to
  the read lists of the data, train, quantize and export stages (`src/caravan/stages/data.py:40`,
  `train.py:50`, `quantize.py:66`, `export.py:99`) so the stage cache key covers them (Principle III).
- [ ] T010 Print the neighbouring-windows notice from `caravan validate` and record it in the run
  report when `split.type` is `random` or `stratify` and a window is set (FR-012), in
  `src/caravan/cli/validate.py` and `src/caravan/run/report.py`; text as in
  [contracts/manifest-fields.md](./contracts/manifest-fields.md).
- [ ] T011 Write `tests/contract/test_manifest_v03.py`: every example and valid fixture validates
  under `caravan/v0.3`; each new invalid fixture fails with exactly its rule; `render` shows
  `type: derived` for a windowed manifest without a split; the notice appears for `random` with a
  window and the exit code stays 0.

**Checkpoint**: the schema accepts and rejects the new fields; nothing reads them yet; `pytest -q` is
green in the default installation.

---

## Phase 3: User Story 1 — No window crosses a recording (P1) 🎯 MVP

**Goal**: windows are cut inside recordings (files, or runs of the recording column), with leftovers
and too-short recordings reported.

**Independent test**: quickstart step 1.

### Tests for US1

- [ ] T012 [P] [US1] Write `tests/unit/test_windows_recordings.py`: on the `recordings/` fixture
  with window 64, no window spans two files; each file's first kept window starts at its first row;
  per-recording leftovers equal `rows mod 64` (`r1`: 450 − 7 × 64 = 2); a recording shorter than the
  window appears in `too_short`; with a single file and a `recording_column` whose value changes, no
  window holds two values, and a value that returns later starts a new recording; DS-20 when the
  recording column is missing from a file.

### Implementation for US1

- [ ] T013 [US1] In `src/caravan/data/reader.py`, return `recordings` on `RecordSet` — one
  `(file, key, start, end)` per file, each cut where `recording_column` changes value between
  consecutive rows (read as text, like the fixed split's column in `_parts`); refuse with DS-20 when
  the column is missing from a file. Keep the concatenated arrays unchanged (research R1).
- [ ] T014 [US1] In `src/caravan/data/windows.py`, make `plan_windows` take `recordings` and cut
  windows inside each `[start, end)` only; add `recording_of`, `per_recording` (`file`, `key`,
  `rows`, `windows`, `leftover_rows`), `too_short` and a `dropped` dict to `WindowPlan`, keeping
  `discarded_mixed`, `discarded_mixed_split` and `dropped_remainder` as derived values with their
  current meanings (data-model.md). DS-6, when nothing is kept, names the longest recording.
- [ ] T015 [US1] Pass `records.recordings` to `plan_windows` in every caller:
  `src/caravan/stages/data.py:157`, `src/caravan/stages/train.py:167`,
  `src/caravan/data/test_part.py:54`; images (no window) keep one record per sample.
- [ ] T016 [US1] Add `window`, `recordings`, `recordings_too_short` and `windows_dropped` to
  `data/schema.json` in `src/caravan/stages/data.py` and the first line of the console data block
  ([contracts/reports.md](./contracts/reports.md)) to the stage summary.

**Checkpoint**: T012 green; the existing suite still green.

---

## Phase 4: User Story 2 — A test score that measures the model (P1)

**Goal**: `recording`, `group` and `blocked` splits; the derived default; purge at part boundaries;
refusals that name counts.

**Independent test**: quickstart steps 2 and 3.

### Tests for US2

- [ ] T017 [P] [US2] Write `tests/unit/test_split_groups.py`: on `recordings/`, `recording` puts every
  file's windows in one part and the assignment is identical for the same seed; `group` by a column
  keeps all rows of a value together, also when the value returns later; `blocked` on
  `leakage_example()` with window 64 and seed 42 leaves **no** test window directly beside a training
  window (SC-004; today 13 of 15) and every class in every part; the derived default is `recording`
  with ≥ 3 recordings and `blocked` otherwise; the reported `shares` sum to 1 and `seed` is the seed
  actually used after retries; no row index belongs to windows of two parts.
- [ ] T018 [P] [US2] Write `tests/contract/test_split_refusals.py`: two files with
  `split: {type: recording}` → DS-18 naming "2 recordings", "3 parts" and `blocked`; a class present in
  only one group → DS-19 with per-class window counts per group; the fixed split by column still works
  and its windows respect recordings (FR-015).

### Implementation for US2

- [ ] T019 [US2] In `src/caravan/data/windows.py`, implement the group split of research R4: groups
  ordered by first row, shuffled with `random.Random(seed)`, assigned greedily to the part furthest
  below its target share (ties: train, val, test); for a classification output retry seeds
  `seed+1 … seed+99` until every part has every class, else DS-19; fewer groups than parts → DS-18.
  Record `type`, `seed`, `assignment` and `shares` on `SplitPlan`.
- [ ] T020 [US2] In `src/caravan/data/windows.py`, implement `blocked` (research R5): blocks of
  `max(1, round(windows_in_stretch / 10))` windows formed within each stretch of one label of each
  recording, assigned per class by the same deficit walk; then the purge — walking each recording in
  row order, drop a window whose rows touch or overlap the previous kept window of a different part,
  counting it as `purged`. Apply the purge after every split type.
- [ ] T021 [US2] Resolve `derived` in `split_for` (`src/caravan/data/windows.py:335`): `recording`
  with ≥ 3 recordings, else `blocked`; set `derived: true`; read the `group` column through the reader
  (`RecordSet.groups`, like `parts`).
- [ ] T022 [US2] Record the effective split in `data/schema.json` and in the run's resolved manifest
  (`split.type` effective, `derived`, `seed`, `assignment`, `shares`), and print the console `split:`
  line of [contracts/reports.md](./contracts/reports.md), in `src/caravan/stages/data.py` and
  `src/caravan/manifest/resolve.py`.

**Checkpoint**: T017–T018 green; quickstart steps 2–3 pass.

---

## Phase 5: User Story 3 — Every output gets windows (P2)

**Goal**: the window label rules, with drops counted by reason and the rule in the contract.

**Independent test**: quickstart step 4.

### Tests for US3

- [ ] T023 [P] [US3] Write `tests/unit/test_window_label.py`: `soc/` with the default (`last`) keeps
  ≥ 90% of possible windows (SC-001) and `mean` keeps 100%; `all_equal` on `soc/` keeps none and
  says so; `bursts/` with `{any: dos}` and window 64 keeps ≥ 1 `dos` window per burst (SC-002);
  `majority` drops ties and counts them as `tied`; `{any: v}` falls back to `all_equal` for windows
  without `v`; `{any: nope}` → DS-20 listing the values present; on an `anomaly` output, `{any: <abnormal>}`
  makes a window with one abnormal row abnormal.

### Implementation for US3

- [ ] T024 [US3] In `src/caravan/data/windows.py`, apply the rule of research R3 per window:
  `all_equal` (drop `mixed`), `last`, `majority` (drop `tied`), `mean` (number outputs; written as the
  reader writes numbers), `{any: v}` (else `all_equal`); count drops in `WindowPlan.dropped`.
- [ ] T025 [US3] Check `{any: v}` against the output column at run time (DS-20) in
  `src/caravan/stages/data.py`, before fitting.
- [ ] T026 [US3] Write the rule into the export: `window_label` in `model/interface.json`
  (`src/caravan/export/interface.py`), and add a test in `tests/contract/test_interface_v4.py`.

**Checkpoint**: T023 green; quickstart step 4 passes.

---

## Phase 6: User Story 4 — Overlapping windows, safely (P2)

**Goal**: `window_stride` below the window, allowed only with a group, blocked or fixed split, with no
row shared across parts.

**Independent test**: quickstart step 5.

### Tests for US4

- [ ] T027 [P] [US4] Write `tests/unit/test_window_stride.py`: stride 16 on window 64 gives ≥ 3.5×
  the windows of stride 64 on `recordings/` (SC-005); windows start every 16 rows within each
  recording and never cross one; under `blocked` and `recording`, no row index belongs to windows of
  two parts; the purge count is reported.

### Implementation for US4

- [ ] T028 [US4] In `src/caravan/data/windows.py`, cut windows at `r_start + k * stride` within each
  recording (research R6); make the label-run lookup per recording so a quarter-window stride on a
  million rows plans in under 2 seconds (plan, Performance Goals), and add that timing to
  `tests/unit/test_window_stride.py`.
- [ ] T029 [US4] Rename the contract's `"stride"` to `"training_stride"` carrying `window_stride`,
  add `"training_stride_note"`, and raise `CONTRACT_VERSION` to 4 in
  `src/caravan/export/interface.py` ([contracts/reports.md](./contracts/reports.md)); update every
  reader of `"stride"` in `src/caravan/runtime/`, `examples/esp32/`, `examples/lora32/` and the tests;
  extend `tests/contract/test_interface_v4.py`.

**Checkpoint**: T027 green; quickstart step 5 passes.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T030 [P] Document the fields in `docs/ref/manifest/preprocessing.md` (Does / Default / Change it /
  Extremes for `window_stride`, `window_label`, `recording_column`, and the split types `recording`,
  `group`, `blocked`), replacing the warning about random splits with the new default and its
  reason (FR-022).
- [ ] T031 [P] Add the v0.3 section to `docs/ref/manifest-changes.md` with the text of
  [contracts/manifest-fields.md](./contracts/manifest-fields.md), and the seven rules to
  `docs/ref/rules.md`.
- [ ] T032 [P] Update `docs/glossary.md` (new entry *recording*; *window* now with stride and label
  rule — "Windows never overlap" is no longer true) and `docs/topics/pipeline.md` (how rows become
  examples); fix every other page that says windows never overlap
  (`docs/intro/overview.md:119`, `docs/intro/tutorial02.md:112`, `docs/releases/0.1.0.md` stays as a
  historical record).
- [ ] T033 Add a valid fixture manifest `tests/fixtures/manifests/valid/recordings-conv1d.yaml` on
  `recordings/` (window 64, stride 16, derived split) and run quickstart step 7 end to end on the
  `train` extra; record the console block and the contract in "Status at close" below.
- [ ] T034 Run `pytest -q` and `pytest tests/layering -q` on Python 3.13 and 3.15 in a default
  installation, and the full suite with the `train` extra on 3.13; record the results and the
  measured SC-001–SC-005 figures below.

---

## Dependencies

- Phase 1 and Phase 2 before any story; T005 first in Phase 2 (every later fixture is `caravan/v0.3`).
- US1 before US2 (splits assign recordings) and before US4 (stride works within recordings).
- US3 depends only on Phase 2 and T014 (the per-window loop); it can run beside US2.
- US4 after US2 (overlap is only allowed with a group, blocked or fixed split, and the purge lives in
  T020).
- T029 after T026 (both edit `interface.py`).

## Parallel opportunities

- Phase 1: T001–T004 together.
- Phase 2: T006 and T007 together, then T008–T010.
- Tests of a story (T012; T017–T018; T023; T027) can be written together once Phase 2 is done.
- Polish: T030–T032 together.

## Implementation strategy

**MVP is US1 + US2** (both P1): windows inside recordings and a split that does not leak remove the
two failures that make today's test scores untrustworthy. US3 then makes the number and burst
applications work; US4 adds overlap on the safe footing of US2. Push in validated batches: after
Phase 2, after US2, after US4, after Polish.
