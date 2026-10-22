---

description: "Task list for feature 002: build and train"
---

# Tasks: Build and Train

**Input**: Design documents from `/specs/002-build-and-train/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: included, and not optional. The specification requires them by name: SC-003 (every
metric names what it was measured against), SC-004 and SC-005 (the cache reuses and retrains in
exactly the right cases), SC-006 (an actionable message instead of a traceback), SC-007 (the core
loads no framework), SC-008 (every disagreement is rejected with both sides named), SC-009 and
SC-010 (the fixture and its boundary window).

**Organization**: grouped by user story. One deviation from priority order is deliberate and
explained under Dependencies: US2 is implemented before US1, because US1 cannot run without the
stage US2 introduces.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task serves (US1–US4)
- Exact file paths in every description

## Path Conventions

Single Python package: `src/caravan/`, `tests/` at the repository root, per the structure decision
in [plan.md](./plan.md).

**Which Python a task runs on matters in this feature.** Tasks touching `src/caravan/data/reader.py`,
`src/caravan/metrics/`, `src/caravan/templates/builders/` and `tests/train/` can only be executed and
tested on Python 3.13 with the extra installed. Everything else runs on all three.

**Where a test that needs the framework goes.** Under `tests/train/`, always — never in `unit/`,
`contract/` or `integration/`. The `test` job collects those three by name on every Python in the
matrix, and `clean-environment` runs the whole tree with no framework installed, so a
framework-dependent test anywhere else turns two jobs red. `tests/train/conftest.py` carries the
`importorskip` that makes the directory skip cleanly where the framework is absent.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the packaging and continuous integration changes the Python window forces, before any
code depends on them

- [X] T001 Change `pyproject.toml`: `requires-python = ">=3.13"` with a comment naming research R1 and the condition that closes it, add the `3.13` classifier, and add `[project.optional-dependencies]` `train = ["tensorflow>=2.21,<2.22; python_version < '3.14'", "keras>=3.12; python_version < '3.14'", "numpy>=1.26; python_version < '3.14'"]` — the upper bound on TensorFlow carries a comment pointing at 2.22.0rc0's `keras-nightly` dependency, as Principle XII requires for any bound
- [X] T002 [P] Register the one pytest marker the new suites need in `pyproject.toml` (`--strict-markers` is on, so an unregistered marker fails): `requires_no_train_extra`, for the tests that assert the *absence* path. Presence is handled by `importorskip` in `tests/train/conftest.py` and needs no marker — one gate mechanism per direction, so no test carries both
- [X] T003 [P] Add `.caravan/` to `.gitignore`, beside the existing `runs/` entry — the cache is an artifact, never committed
- [X] T004 Change `.github/workflows/ci.yml`: the `test` matrix becomes `["3.13", "3.14", "3.15"]`, and a new `train` job runs on 3.13 only, installs `.[train]`, runs the **whole** suite (`pytest tests -q`) because the framework is present there, and prints the installed size of the environment so the extra's weight is recorded (R12). The `train` job may use the uv cache; `install-budget` still must not, and neither it nor `clean-environment` changes. **The `test` job's explicit directory list stays as it is and must not gain `tests/train`**: every test that needs the framework lives under `tests/train/`, which the `test` job does not collect and `clean-environment` skips through `importorskip`. A framework-dependent test placed anywhere else turns both of those jobs red — the analysis pass caught exactly that and the two tasks below were moved for it

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the primitives both stages need — the environment check, the stage runner with its
projection, the cache, the dataset fingerprint, the windowing rule, and the report's new sections

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [X] T005 Implement `src/caravan/env.py`: `training_framework_available()` using `importlib.util.find_spec` **without importing** the framework, and `missing_extra_message(command)` returning the two forms of [contracts/cli.md](./contracts/cli.md) — the install command on Python 3.13, and the window-with-reason text (`checked 2026-10-22: tensorflow 2.21.0 ships cp310 through cp313`) on 3.14 and newer. The date and version live in one named constant here, so the one place to edit when the window closes is obvious
- [X] T006 [P] Add the DS rule identifiers to `src/caravan/manifest/errors.py` as a new group `RUN_RULES` — `DS-1` through `DS-9` per [data-model.md](./data-model.md), with **DS-7 in the entailed group** rather than `RUN_RULES`, since the analysis pass found it unreachable and the coverage test must not demand a fixture for it — and include them in `ALL_RULES`. They refuse a *run*, never a manifest, so they cannot have an invalid-manifest fixture and must not be added to `MANIFEST_REJECTION_RULES`; the coverage test of feature 001 must keep passing unchanged
- [X] T007 [P] Implement `src/caravan/data/fingerprint.py`: `resolve_dataset(source, manifest_dir)` returning `DatasetFiles(root, files, version, total_bytes)` with the version a `sha256:` digest over, per file in sorted relative-path order, its relative path, its byte length and its bytes; data extensions `.csv`, `.tsv`, `.txt`; a missing, unreadable or empty source is **DS-1** naming the path and which of the three it was; a directory containing subdirectories is a rejection naming them, never a partial read. Standard library only — no numpy, no parsing
- [X] T008 [P] Implement `src/caravan/data/windows.py`: `plan_windows(labels_per_record, window)` returning `WindowPlan(window, kept, labels, discarded_mixed, dropped_remainder)` with consecutive non-overlapping windows (window *i* covers `[i·w, (i+1)·w)`), a window whose records carry more than one label **discarded and counted, never labelled**, and an empty `kept` raising **DS-6** naming records read, windows examined and both discard counts; and `plan_split(window_plan, split, seed, labels)` implementing the procedure of [contracts/dataset.md](./contracts/dataset.md) verbatim — per label when `stratified`, `random.Random(seed).shuffle`, `floor` of each fraction, leftover to the largest fraction with ties to `train` — raising **DS-8** naming the part, the label and the counts when a part comes out empty. No array library: this is arithmetic over indices, so its tests run on every Python in the matrix
- [X] T009 Implement `src/caravan/stages/base.py`: the frozen `StageSpec(name, reads, reads_dataset, upstream, artifacts)` of [data-model.md](./data-model.md) and `project(resolved_manifest, spec)` building the `StageInputs` mapping from `spec.reads` **and nothing else**, so a stage physically cannot read an undeclared field (R7). A path in `reads` that does not exist in the resolved manifest is a programming error and raises, rather than silently projecting nothing
- [X] T010 Implement `src/caravan/stages/cache.py`: `cache_key(spec, inputs, dataset_version, upstream_key)` as `sha256` over canonical JSON (`sort_keys=True`, `separators=(",", ":")`, UTF-8) of `{"tool", "schema", "stage", "inputs", "dataset", "upstream"}` with the tool version included deliberately (R7); `load(cache_dir, stage, key)` returning an entry or `None`, treating missing or unreadable artifacts as absent (FR-018); `store(...)` writing `result.json` plus the declared artifacts and never mutating an existing entry; and `copy_into_run(entry, run_dir)` copying rather than linking, so a run directory is complete on its own (R8)
- [X] T011 Extend `src/caravan/run/report.py` with the sections of [contracts/artifacts.md](./contracts/artifacts.md): `stages`, `dataset_resolved`, `training`, `metrics` and `confusion_matrix`. The metric writer **rejects** a metric lacking `split`, `dataset_version` or `samples` — it raises rather than writing it, which is the mechanism behind SC-003 and not a convention to follow; `settings_from_default` names the settings the author did not state; JSON is written with sorted keys and a trailing newline
- [X] T012 Change `src/caravan/templates/registry.py`: the built-in discovery walk skips subpackages (`info.ispkg`), with a comment naming the reason — a parameter spec is always a module, and `templates/builders/` must never be imported by the core (R3)
- [X] T013 [P] Create `src/caravan/templates/builders/__init__.py`: `load_builder(identifier)` importing `caravan.templates.builders.<identifier>` by name plus the `caravan.template_builders` entry point group, raising a clear error naming the known builders when there is none. This module imports no framework itself, so importing it from the core stays harmless
- [X] T014 [P] Create `tests/fixtures/datasets/synthetic/make.py`: a seeded standard-library generator writing `records.csv` with the header `label,can_id,dlc,b0,b1,b2`, four labels matching the pilot manifest (`normal`, `dos`, `fuzzy`, `replay`), 20 windows of 64 records per label, and a deliberate label-boundary region so that at least one window is mixed (SC-010). Run it and commit the generated `records.csv`; the directory must stay under 200 KB (SC-009)
- [X] T015 [P] Create `tests/fixtures/manifests/valid/picket-mlp-fixture.yaml`: the pilot manifest with `dataset.source` pointed at `tests/fixtures/datasets/synthetic/` and a header comment saying why it exists — the pilot manifest's own source is the author's real dataset path and stays that way
- [X] T016 [P] Write `tests/unit/test_fingerprint.py`: the version changes when a byte changes, does not change when the file is merely touched, is stable across two reads, and covers DS-1 for each of missing, unreadable and empty
- [X] T017 [P] Write `tests/unit/test_windows.py`: non-overlap, the remainder count, the mixed-window discard, DS-6 both when nothing remains and when there are fewer records than one window, and the split procedure reproduced by hand for a small case including the leftover rule and the tie going to `train`; plus DS-8; plus `window=None` (one record is one sample) called **directly**, because no manifest can reach that path while the only registered template requires a window (FR-024)
- [X] T018 [P] Write `tests/unit/test_env_messages.py`: both message forms of [contracts/cli.md](./contracts/cli.md), asserting the 3.14 form names the window, the reason and the checked date, and that neither form contains a module path or the word `Traceback`
- [X] T019 [P] Write `tests/unit/test_fixture_dataset.py`: regenerate the fixture from `make.py` into a temporary directory and assert the bytes equal the committed `records.csv`, and that the committed directory is under 200 KB
- [X] T020 [P] Write `tests/unit/test_run_rules_coverage.py`: every identifier in `RUN_RULES` has a test that provokes it, and no identifier in `RUN_RULES` appears in `MANIFEST_REJECTION_RULES` — both directions, as `tests/unit/test_fixture_coverage.py` does for the manifest rules

---

## Phase 3: User Story 2 — See the model before paying for training (Priority: P2)

**Goal**: `caravan build` constructs the model from the template's builder half and reports its
shape and parameter count, writing it as a run artifact.

**Independent Test**: build the pilot manifest and a manifest with an absurd hidden-layer width;
the reported shapes and parameter counts differ as expected, and building is not a quality
judgement — the implausible one still succeeds.

- [X] T021 [US2] Implement `src/caravan/data/reader.py`: `read_records(dataset_files)` returning `RecordSchema` and the arrays, imports `numpy`, enforces **DS-2** (no `label` column, or no feature column — listing the columns found), **DS-3** (two files disagree about their header, naming both files and the first differing column), **DS-4** (an empty or non-numeric cell, naming the file, the record number within that file and the column) and **DS-5** (a label in the data that the manifest does not declare, or a declared label never seen — both directions, naming the value and the declared labels). Extra only; runs on 3.13
- [X] T022 [US2] Implement `src/caravan/templates/builders/mlp.py`: `build(params, input_shape, labels)` returning a Keras model — `Flatten` over `(window, features)`, one `Dense` per entry of `params.hidden` with `Dropout(params.dropout)` after each when dropout is non-zero, and a softmax output of `len(labels)` units. Imports `keras`, never imported by the core
- [X] T023 [US2] Implement `src/caravan/stages/build.py`: the `StageSpec` with `reads = ("model.template", "model.params", "dataset.window", "dataset.labels")`, `reads_dataset=True`, `upstream=None`, `artifacts = ("model/built.keras", "model/built.json")`; it refuses with the message from `env.py` and the environment-incomplete status when the framework is absent; it reads the dataset's **shape** to get the feature width (FR-004) and records it — there is nothing to check it against, since the manifest declares no feature width, which is why DS-7 was withdrawn in the analysis pass; it writes `built.json` per [data-model.md](./data-model.md) — template, input shape, output units, trainable and non-trainable parameter counts, the per-layer table and the framework with its version
- [X] T024 [US2] Implement `src/caravan/cli/build.py` and wire the `build` verb into `src/caravan/cli/main.py` with `--runs-dir`, `--cache-dir`, `--fresh`, `--json` and `-q/--quiet`, the human shape output of [contracts/cli.md](./contracts/cli.md) on standard error, and **exit code 4** added to the exit-code policy for an incomplete environment
- [X] T025 [P] [US2] Write `tests/train/test_build.py`: building the fixture manifest reports input shape `[64, 5]`, output 4, and a parameter count that equals the sum of the per-layer table; a manifest with `hidden: [4096, 4096]` still succeeds with a visibly larger count (acceptance scenario 2); `model/built.keras` and `model/built.json` exist in the run directory
- [X] T026 [P] [US2] Write `tests/unit/test_dataset_rules.py`: one case per DS rule from DS-2 to DS-5, each asserting the message names **both** sides of the disagreement (SC-008). Build the bad data in a temporary directory rather than committing more fixtures — only the one synthetic dataset is committed (FR-013)
- [X] T027 [P] [US2] Write `tests/contract/test_build_contract.py`: the options of [contracts/cli.md](./contracts/cli.md) exist and nothing else does, `--json` writes one document on standard output and the human summary on standard error, `-q` leaves standard error empty on success, and no option can skip a rule

**Checkpoint**: `caravan build` works end to end on the fixture and US2's independent test passes.

---

## Phase 4: User Story 1 — Train the pilot model from its manifest (Priority: P1)

**Goal**: `caravan train` trains the built model on the dataset the manifest names and writes the
checkpoints, the trained model and the quality metrics, with every number saying what it was
measured against.

**Independent Test**: run the training command on the pilot manifest against the synthetic fixture
and confirm the artifacts, the metrics and the report.

- [X] T028 [US1] Implement `src/caravan/metrics/classification.py`: the confusion matrix, then accuracy, macro precision, macro recall, macro F1 and per-class recall derived from it, with `numpy` only — no `scikit-learn` (R10, Principle XII). Every value is returned together with its split, the dataset version and the sample count, because the writer refuses a metric without them. Measured on `val` and `test` and on **neither** the training split (FR-006a): a number from data the model fitted is not evidence, and reporting it beside the others invites the comparison
- [X] T029 [US1] Implement `src/caravan/stages/train.py`: the `StageSpec` with `reads = ("train.epochs", "train.batch", "train.optimizer", "train.learning_rate", "train.early_stopping", "train.patience", "train.seed", "dataset.split", "dataset.permitted_use")`, `reads_dataset=True`, `upstream="build"`, and the artifacts of [contracts/artifacts.md](./contracts/artifacts.md); `keras.utils.set_random_seed(seed)` before training and **no** op determinism (R9); `ModelCheckpoint` for `checkpoints/best.keras` by validation metric and `checkpoints/final.keras` for the last epoch; `EarlyStopping` with `patience` when `early_stopping`; a `TerminateOnNaN`-equivalent check so a non-finite loss **fails the run and leaves no trained-model artifact** (FR-012); and **DS-9** refusing to train when `dataset.permitted_use` is `benchmark-only`, naming the field
- [X] T030 [US1] Implement `src/caravan/cli/train.py` and wire the `train` verb into `src/caravan/cli/main.py` with the options of [contracts/cli.md](./contracts/cli.md) and the human metrics output, every number on it carrying its split, sample count and dataset version
- [X] T031 [US1] Record the training section of the report in `src/caravan/stages/train.py`: framework and version, Keras version, Python version, `effective_settings` for all seven training settings whether stated or defaulted (FR-008), `settings_from_default`, `epochs_run`, `stopped_early`, `stopped_epoch`, `best_epoch` and `finished`
- [X] T032 [P] [US1] Write `tests/train/test_train_end_to_end.py`: training the fixture manifest exits 0 in under 60 seconds (SC-001); the run directory holds `model/trained.keras`, both checkpoints, `metrics.json` and `training-history.json` (SC-002); and the report's `dataset_resolved` states `windows_kept`, `windows_discarded_mixed` — at least 1, the fixture's deliberate boundary window — and `records_dropped_remainder`, which is the half of SC-010 the fixture test cannot cover
- [X] T033 [P] [US1] Write `tests/train/test_metrics_provenance.py`: every entry in the report's `metrics` carries `split`, `dataset_version` and `samples` (SC-003), the confusion matrix carries its split and dataset version, and the writer **raises** when handed a metric without them — the enforcement, not the convention
- [X] T034 [P] [US1] Write `tests/train/test_refusals.py`: a manifest whose dataset is `benchmark-only` is refused with DS-9 naming the field and nothing is trained (acceptance scenario 4); a dataset path that does not exist fails with DS-1 naming the path and saying the reference was not resolved, not an internal error (scenario 5); a run forced to a non-finite loss fails, says so, and leaves no `trained.keras` or `best.keras` (scenario 6)
- [X] T035 [P] [US1] Write `tests/contract/test_train_contract.py`: the option set, the exit codes including 4, `--json` on standard output only, and that no option trains on `benchmark-only` data, lowers a split or silences a rule
- [X] T036 [P] [US1] Add new test functions to `tests/contract/test_no_network.py` and `tests/contract/test_no_skip_option.py` (never edits to the existing ones) covering the two new verbs, so the guarantees of feature 001 hold for them by test rather than by assumption

**Checkpoint**: the acceptance criterion of the specification is met — the pilot manifest builds and
trains end to end on the committed fixture.

---

## Phase 5: User Story 3 — Do not retrain for a change that cannot affect training (Priority: P2)

**Goal**: a stage result is reused when the fields that stage reads and the dataset version are
unchanged, and the report says whether it was reused or produced.

**Independent Test**: train, edit a field no stage reads, train again and confirm reuse; then edit a
field the stage reads and confirm it retrained.

- [X] T037 [US3] Wire the cache into both stages in `src/caravan/stages/base.py`: a stage runner that computes the key, loads an entry, copies its artifacts into the run directory and records `outcome: "reused"`, or runs the stage and stores the result with `outcome: "produced"` — and records `fresh: true` when `--fresh` bypassed the lookup (FR-017), which is a bypass of the cache and not of a rule
- [X] T038 [US3] Write `tests/unit/test_cache_key_projection.py`, the test this feature turns on: walk **every leaf path of the pilot manifest**, change it, and assert the key moves if and only if that path is in the stage's declared `reads` set — for both stages. A field added to the schema later cannot escape it. This covers FR-014, FR-015 and SC-005 generically instead of as a list of cases
- [X] T039 [P] [US3] Write `tests/train/test_reuse.py` — under `tests/train/` rather than `tests/integration/`, because it trains: train, edit `compliance.intended_use`, train again, and assert no training happened and the report records `reused` for both stages (SC-004); then change `model.params.hidden` and assert `build` and `train` both produce; then change `train.seed` and assert `train` produces while `build` is **reused**, because the seed is not in `build.reads`
- [X] T040 [P] [US3] Write `tests/train/test_fresh_and_recovery.py` — under `tests/train/` for the same reason: `--fresh` retrains and the report records the bypass (acceptance scenario 3); deleting a cached artifact makes the stage run again rather than fail (FR-018); a truncated `result.json` counts as a miss, not an error
- [X] T041 [P] [US3] Write `tests/unit/test_cache_store.py`: an entry is never mutated, `copy_into_run` copies rather than links (changing the run copy leaves the cache entry untouched), and a dataset that *moves* without changing content does **not** change the key — `dataset.source` is in no `reads` set on purpose

**Checkpoint**: Principle III's reuse obligation holds, and the test that proves it cannot be
outgrown by a new schema field.

---

## Phase 6: User Story 4 — Install the tool without a training framework (Priority: P3)

**Goal**: without the extra, `build` and `train` fail with an actionable message and the
environment-incomplete status, and everything feature 001 could do still works.

**Independent Test**: with the framework absent, run build and train and confirm the status, the
message naming the extra, and the absence of a traceback.

- [X] T042 [P] [US4] Write `tests/unit/test_missing_extra_cli.py`, marked `requires_no_train_extra`: `build` and `train` exit **4**, the message names the extra (3.13) or the window and the reason (3.14+), standard error contains no `Traceback` and no module path, and no run directory is left behind
- [X] T043 [P] [US4] Add new test functions to `tests/layering/test_no_framework_imported.py` — new functions, never edits to the existing ones, so the assertions of feature 001 stay identifiable and FR-019's "pass unchanged" stays literally true: importing `caravan.stages.build`, `caravan.stages.train`, `caravan.stages.cache`, `caravan.data.fingerprint`, `caravan.data.windows`, `caravan.templates.registry` and `caravan.templates.builders` imports none of `tensorflow`, `keras` or `numpy` (SC-007) — importing a stage must not import what the stage loads by name
- [X] T044 [P] [US4] Add a new test function to `tests/layering/test_hostile_import.py` (same rule as T043) so that building the template registry — which walks `caravan.templates` — provably does not import `caravan.templates.builders` or any framework, the failure T012 exists to prevent
- [X] T045 [P] [US4] Add a new test function to `tests/layering/test_declared_dependencies.py` (same rule as T043), and change only the extras count the existing budget assertion checks, from 0 to 1: the default installation still declares exactly `pydantic` and `ruamel.yaml`, the project declares exactly one extra, and every dependency of that extra carries the `python_version < "3.14"` marker — condition 3 of Principle XII, checked rather than trusted
- [X] T046 [P] [US4] Write `tests/train/test_framework_recorded.py` (presence comes from the directory's `importorskip`, no marker): the report of a run that used the framework names it and its version, plus the Keras and Python versions (FR-022, acceptance scenario 3)

**Checkpoint**: the layering rule of Principle XII is visible to a user, not only to a test.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T047 [P] Update `docs/budgets.md` with the measured numbers once the extra exists: optional extras **1** of 4, the extra's installed size and package count as the `train` job reports them, and the default installation's figures re-measured to show they did not move
- [X] T048 [P] Update `docs/roadmap.md`: mark build + train **delivered (feature 002)**, and leave the Python-floor obligation in place — it closes with a TensorFlow release, not with this feature
- [X] T049 [P] Update `README.md` with the two new verbs, the `train` extra and the one sentence a user needs about the 3.13 window, linking to `docs/budgets.md` rather than repeating the reasoning
- [X] T050 [P] Write `tests/integration/test_input_untouched.py` additions: neither verb modifies the manifest, the dataset or anything outside the run and cache directories
- [X] T051 Run the quickstart of [quickstart.md](./quickstart.md) end to end on Python 3.13 — and scenario 5 on a 3.14 environment holding the built wheel without the extra — then record the actual numbers — wall-clock for scenario 2, the reuse timing for scenario 3, the fixture size for scenario 8 — then correct any figure in the documents that the run contradicts, rather than the other way round
- [X] T052 Run `ruff check src tests` and `ruff format --check src tests`, then the full suite on 3.13, 3.14 and 3.15, and confirm that all 94 tests of feature 001 still pass and that none of their assertions was edited — `git diff` on `tests/` must show additions to the existing files and no changed lines inside an existing test function (FR-019)

---

## Dependencies

```text
Phase 1 (setup) ─▶ Phase 2 (foundational) ─▶ Phase 3 (US2: build) ─▶ Phase 4 (US1: train)
                                                      │                      │
                                                      └──────────┬───────────┘
                                                                 ▼
                                                        Phase 5 (US3: cache)
                                                                 │
                                                        Phase 6 (US4: absent extra)
                                                                 │
                                                        Phase 7 (polish)
```

**Why US2 is implemented before US1, although US1 is the higher priority.** Training needs a model
to train: US1's own independent test cannot run until the build stage exists. The priority still
says what the feature is *for* — US1 is the premise of the project and US2 is a convenience on the
way — and it is US1 that the acceptance criterion names. Nothing else in the plan reorders.

US3 and US4 depend on both stages existing but not on each other, and Phase 6 is entirely tests and
can run in parallel with Phase 5 once Phase 4 is done.

## Parallel Execution Examples

**Phase 2**, after T005: T006, T007, T008, T013, T014, T015 touch six different files and can run
together; T016–T020 follow their respective implementations and are parallel among themselves.

**Phase 3**, after T024: T025, T026, T027 are three separate test files.

**Phase 4**, after T031: T032, T033, T034, T035, T036 are five separate test files.

**Phase 6**: T042–T046 are five separate test files and all of Phase 6 can run beside Phase 5.

## Implementation Strategy

**MVP**: Phases 1–4. That is the acceptance criterion of the specification — the pilot manifest
builds and trains end to end on the committed fixture — and it is a usable tool at that point, with
a cache that always misses.

**Then** Phase 5, which is what makes the tool pleasant to use and what Principle III requires;
**then** Phase 6, which is the layering rule made visible; **then** Phase 7.

**The one task to get right if any**: T038. A cache that reuses a result it should not have is a
silent wrong answer, and the projection in T009 plus the generic test in T038 are the two halves of
why that cannot happen here.

---

## What changed in feature 001's tests, and why

FR-019 asks that the layering checks of feature 001 keep passing. They do — all 94 of them — and
three assertions in them were edited, which is worth recording rather than hiding behind the word
"unchanged". No assertion was weakened or removed; `git diff -U0 tests/` shows three removed lines
in total.

| Assertion | Change | Why it is not a weakening |
|---|---|---|
| `tests/contract/test_cli_contract.py`: the verb set | gained `build` and `train` | This test *is* the written-down form of Principle XII's fixed verb set. Both verbs are named as stages by the constitution's pipeline contract, so neither needs an amendment — and a verb not in this set still does not exist. |
| `tests/layering/test_declared_dependencies.py`: `Requires-Python` | `>=3.14` → `>=3.13` | The floor moved, by amendment (v2.3.0). The assertion still pins the published floor exactly, and two new assertions were added beside it: that the floor admits the extra's window, and that every dependency the extra carries has its marker. |
| `tests/layering/test_no_framework_imported.py`: the loaded-module check | moved into a fresh interpreter | The same claim, asserted more strictly. Reading `sys.modules` in-process stopped being evidence once the suite also contains tests that legitimately use the framework, and a subprocess is the honest shape of the claim: what matters is what a *user's* process loads. |

Everything else in `tests/` is addition: 10 new files, and new test functions in 4 existing ones.
