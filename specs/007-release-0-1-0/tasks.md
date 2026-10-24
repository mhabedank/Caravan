# Tasks: Release 0.1.0

**Input**: Design documents from `/specs/007-release-0-1-0/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: requested. The constitution's workflow gates require tests for changed behaviour, and the
spec asks for the documents to be checked by tests (SC-003). Tests come before their implementation.

**Organization**: by user story. The story phases are not in priority order:
- US2, the console output, comes before US1, because the guide's acceptance (SC-002) depends on it.
- The fixed split, which only US4 needs, comes before the candidate tag, because the port pins that
  candidate.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Setup

- [X] T001 Add `tests/unit/test_version.py`: assert `caravan.__version__ ==
  importlib.metadata.version("caravan-ml")` (research R3), and assert that the version parses as
  PEP 440 with `packaging.version.Version`. It must pass on the current `0.1.0.dev1`.

---

## Phase 2: Foundational

- [X] T002 Make `.github/workflows/ci.yml` skip documentation-only changes (constitution 4.1.0,
  Resources & Cost Discipline). Add `paths-ignore: ['specs/**', 'docs/**', '**/*.md', '.specify/**']`
  to both the `push` and `pull_request` triggers. A change that also touches code still runs
  everything.

---

## Phase 3: User Story 2 — the console shows Caravan, not the framework (P2, done first)

**Goal**: framework output goes to `framework.log`; `--framework-output` brings it back; `--json`
on stage verbs is clean JSON.

**Independent test**: quickstart §1 and §2.

### Tests for User Story 2

- [X] T003 [P] [US2] Write `tests/unit/test_framework_log.py` for a context manager
  `caravan.run.framework_log.captured(path)`:
  - output written with `os.write(1, …)` and `os.write(2, …)` inside it lands in the file, as do
    `print` and `warnings.warn`;
  - output written after it reaches the original descriptors;
  - the descriptors are restored when the body raises;
  - an empty capture leaves no file behind;
  - `captured(None)` redirects nothing.

  Use `capfd` to observe the real descriptors.
- [X] T004 [P] [US2] Extend `tests/contract/test_cli_contract.py`: the stage verbs accept
  `--framework-output`, and `validate` and `render` do not (Principle XII: an option, not a verb).
- [X] T005 [P] [US2] Write `tests/train/test_console_output.py`. Run `caravan export` on
  `tests/fixtures/manifests/valid/picket-mlp-fixture.yaml` with `capfd` and assert:
  - stdout plus stderr is at most 25 lines;
  - no line matches `^(I|W|E)0000 |Saved artifact|TensorSpec\(|fully_quantize|oneDNN`;
  - the run directory holds a non-empty `framework.log` that contains `fully_quantize`;
  - `report.json` lists it under `artifacts.framework_log`.

  Second case: with `--json`, stdout parses with `json.loads`. Third case: with
  `--framework-output`, the framework lines reach the console and no `framework.log` exists.
- [X] T006 [P] [US2] In `tests/train/test_console_output.py`, add a failure case. Make a stage fail
  inside the framework, by monkeypatching the converter to write to descriptor 2 and then raise.
  Assert that the console's last lines name the failing stage and print
  `framework output: <run dir>/framework.log` (contracts/cli.md), and that the log holds the
  framework's line.

### Implementation for User Story 2

- [X] T007 [US2] Implement `src/caravan/run/framework_log.py`:
  - `captured(path: Path | None)` flushes `sys.stdout` and `sys.stderr`, then saves descriptors 1
    and 2 with `os.dup`;
  - it opens `path` for appending and `os.dup2`s it onto 1 and 2;
  - in `finally`, it flushes and restores both descriptors, closes the saved copies, and removes the
    file if it is empty;
  - standard library only (core layer, no framework import).

  Add the module to the layering tests' list of core modules in
  `tests/layering/test_no_framework_imported.py`.
- [X] T008 [US2] Add `--framework-output` to `build`, `train`, `quantize` and `export` in
  `src/caravan/cli/main.py`, with help text "show the training framework's own output instead of
  writing it to framework.log".
- [X] T009 [US2] In `src/caravan/cli/pipeline.py`:
  - wrap the stage loop, from `resolve_dataset` to the last `run_stage`, in
    `captured(None if args.framework_output else run_dir / "framework.log")`;
  - after it, add `framework_log` to `report.artifacts` when the file exists;
  - on every failure path (rule, environment, internal error), restore the descriptors first, then
    name the stage that was running (`<manifest>: stage <name> failed`) and print
    `    framework output: <path>` after the existing lines when the file is not empty. Keep the
    running stage's name in a variable set before each `run_stage` call, so an internal error (exit
    3) reports it too (FR-009).
- [X] T010 [US2] Add `FRAMEWORK_LOG_NAME = "framework.log"` to `src/caravan/run/paths.py`, and
  check that `tests/train/test_writes_nothing_else.py` still holds. Update its list of what a run
  may write if it enumerates files.

**Checkpoint**: T003–T006 green; quickstart §1 and §2 hold by hand.

---

## Phase 4: User Story 1 — install a named version and try it in minutes (P1)

**Goal**: an example and a guide that work from an installed package. The guide is tested as
written.

**Independent test**: quickstart §4.

### Tests for User Story 1

- [X] T011 [P] [US1] Write `tests/contract/test_example_matches_fixture.py`. Load
  `examples/picket-mlp.yaml` and `tests/fixtures/manifests/valid/picket-mlp-fixture.yaml` with
  `read_mapping`, and assert they are equal once `dataset.source` is removed from both. Also assert
  that the example's source resolves to `tests/fixtures/datasets/synthetic` relative to the
  example's directory.
- [X] T012 [US1] Write `tests/train/test_try_it_guide.py`:
  - **parse** `docs/try-it.md`: blocks open with a fence line ```` ```bash ```` and are followed by
    a comment line `# step: fetch|install|run`;
  - **prepare** a temporary directory the way the fetch block would: copy `examples/` and
    `tests/fixtures/datasets/synthetic` to the same relative paths;
  - **run** every `run` block unchanged with `bash -euo pipefail`, with the test interpreter's
    `bin` directory on `PATH`;
  - **assert** exit 0, the files the guide lists under "What you get" exist in the newest run
    directory, and the `export` command's output holds to SC-002 (at most 25 lines, none of T005's
    patterns).

  Also assert that the guide's install block names the wheel URL form of research R2 with
  `{version}` equal to `caravan.__version__`.

### Implementation for User Story 1

- [X] T013 [P] [US1] Create `examples/picket-mlp.yaml`. Copy
  `tests/fixtures/manifests/valid/picket-mlp-fixture.yaml` with
  `source: ../tests/fixtures/datasets/synthetic` and a header comment. The comment explains:
  - the synthetic data;
  - why the labels are pinned (research R11 of feature 006, in one sentence);
  - how to point `source` at one's own data.
- [X] T014 [US1] Write `docs/try-it.md`. It holds:
  1. **Requirements**: Python 3.13, `curl`, `tar`.
  2. **Install** (`# step: install`), the wheel URL of research R2 for the current version, with
     extras `train,verify`, inside a fresh virtual environment.
  3. **Fetch the example** (`# step: fetch`), research R4's command.
  4. **Run** (`# step: run`): `caravan validate examples/picket-mlp.yaml`,
     `caravan render examples/picket-mlp.yaml --stdout`, then
     `caravan export examples/picket-mlp.yaml`.
  5. **"What you get"**: each file of the run directory in one line. The run's own files are
     `report.json`, `resolved-manifest.yaml`, `data/schema.json`, `metrics.json`,
     `quantization.json`, `export.json` and `framework.log`. The model files are
     `model/model.tflite`, `model/model_data.h`, `model/model_data.cc`, `model/resolver.h`,
     `model/interface.json`, `model/fit.json` and `runner/<board>/main.cc`.
  6. **"Your own data"**:
     - the CSV layout with a header and a `label` column;
     - that every other column becomes an input;
     - labels derived and sorted unless pinned;
     - windows of `inputs[0].window` records, which never overlap;
     - the fixed split (`dataset.split.column`), once Phase 6 is done.
  7. **"On Python 3.14 or 3.15"**: install without extras; `validate` and `render` work; a training
     verb exits 4 and names the extra and Python 3.13.

  Every number in it must come from a run (T041).

**Checkpoint**: T011 and T012 green.

---

## Phase 5: User Story 3 — the release says truthfully what it is (P2)

**Goal**: README, roadmap, release note and release workflow.

**Independent test**: quickstart §5 and §7; `tests/integration/test_readme.py`.

### Tests for User Story 3

- [X] T015 [P] [US3] Write `tests/integration/test_readme.py`:
  - every `caravan …` line in the README's quick-start block runs, from the repository root, with
    exit 0, against `examples/picket-mlp.yaml`. These are `validate` and `render` only, so the test
    runs without extras;
  - the README contains no `pip install caravan-ml` line without a URL;
  - its install lines name the same URL form as `docs/try-it.md`.
- [X] T016 [P] [US3] Write `tests/unit/test_release_note.py`. `docs/releases/0.1.0.md` exists and
  has the sections:
  - "What it does";
  - "Where it runs";
  - "Known limits", with at least four bullet points (spec US3 scenario 3);
  - "Change notes", linking `docs/manifest-changes.md`;
  - "Release gate";
  - "The pace-cnn port".

### Implementation for User Story 3

- [X] T017 [P] [US3] Rewrite the README's "Status", "Install" and quick-start sections in
  `README.md`:
  - **Status**: every verb (`validate`, `render`, `build`, `train`, `quantize`, `export`,
    `templates`, `boards`) and both templates;
  - **Install**: the wheel URL form and the `git+https://github.com/mhabedank/Caravan@v<version>`
    form, with the Python window per extra, and a link to `docs/try-it.md`;
  - remove every claim of a package-index install.
- [X] T018 [P] [US3] Update `docs/roadmap.md`:
  - add feature 006 (declared inputs and outputs, fit check, interface contract), the fixed split
    and the console output to the v0.1 table, marked delivered;
  - state the release as "candidate `v0.1.0rc1`; `v0.1.0` after the `pace-cnn` port";
  - keep the Python floor obligation with its closing condition, updated to "2.22.0rc0 still a
    candidate, checked 2026-10-23";
  - record the runtime-only export as deferred by the owner, with its date.
- [X] T019 [P] [US3] Draft `docs/releases/0.1.0.md` with the sections of T016. Known limits:
  - the training half needs Python 3.13;
  - export needs the training extra even when training and quantization are cached;
  - unscaled inputs, with derived labels failing the int8 gate on the synthetic example (R11);
  - footprint figures are lower bounds, not measurements;
  - only one input and one output.

  Leave the port section as "pending".
- [X] T020 [US3] Move the guide-block parser from T012 into `tests/support_docs.py` and use it in
  `tests/train/test_try_it_guide.py`, `tests/integration/test_readme.py` and
  `.github/workflows/release.yml` (T021, via `python -m tests.support_docs <file> <step>`, printing the
  blocks of that step).
- [X] T021 [US3] Write `.github/workflows/release.yml` (research R6, contracts/release.md):
  - **trigger and permissions**: on `push` of tags `v*`; `permissions: contents: write`;
  - **check**: the tag without `v` equals the version in `pyproject.toml` and
    `caravan.__version__`; then the full suite on 3.13 with both extras;
  - **build**: `uv build`; install the wheel in a fresh 3.13 environment with `[train,verify]` and
    in a fresh 3.14 environment without extras; `caravan --version` equals `caravan-ml <version>`
    in both; upload `dist/` as a workflow artifact;
  - **release**: `gh release create "$TAG" dist/* --notes-file docs/releases/0.1.0.md`, with
    `--prerelease` when the version contains `rc`;
  - **verify**: on a fresh runner, run the guide's fetch, install and run blocks, extracted with
    `tests/support_docs.py` (T020), with `{version}` substituted. Measure the wall time from the
    first install command to the end of `export`, write it to the job summary, and fail above 10
    minutes (SC-001). Also run the README's install line for the same version (SC-003).

  No secret beyond `GITHUB_TOKEN`.

**Checkpoint**: T015 and T016 green; `release.yml` passes `actionlint` if available. Otherwise read
it against contracts/release.md.

---

## Phase 6: User Story 4, part 1 — a fixed split (P2)

**Goal**: `dataset.split.column` (FR-017–019). The port cannot be honest without it.

**Independent test**: quickstart §3.

### Tests for the fixed split

- [X] T022 [P] [US4] Write `tests/unit/test_fixed_split.py` for `src/caravan/data/windows.py`:
  - `plan_windows(labels, window, parts=…)` keeps a window whose records all name one part and
    records that part;
  - it discards a window whose records name two parts, counting it in `discarded_mixed_split`;
  - a window mixed by label and by part counts as mixed by label only;
  - `plan_split(plan, column="split")` returns exactly the windows of each part, with
    `stratified=False`, `seed=None` and `source="column:split"`;
  - a part with no window raises DS-8 naming the column.

  Pure Python, no extra.
- [X] T023 [P] [US4] Add invalid fixtures, each with an `.expected.json`:
  - `tests/fixtures/manifests/invalid/cf-12-split-column-with-fractions.yaml`, expecting CF-12 at
    `dataset.split`;
  - `tests/fixtures/manifests/invalid/cf-13-split-column-as-input.yaml`, expecting CF-13 at
    `dataset.split.column`.

  Also add a valid fixture, `tests/fixtures/manifests/valid/picket-mlp-fixed-split.yaml`, which uses
  `split: {column: split}` and `source: ../../datasets/split`.
- [X] T024 [P] [US4] ~~Generate a second committed dataset under `tests/fixtures/datasets/split/`~~.
  **Changed during implementation:** feature 002's FR-013 allows exactly one committed dataset, and
  `tests/unit/test_fixture_dataset.py` says so. So `tests/support.py` gains
  `write_split_dataset(dest)`, which derives the fixed-split data at test time from the committed
  synthetic records:
  - it adds a `split` column: per label, windows 0–11 `train`, 12–15 `val`, 16–19 `test`;
  - the last `normal` window names two parts and is discarded;
  - the counts are `SPLIT_COUNTS = {train: 48, val: 16, test: 15}`.

  The valid fixture `picket-mlp-fixed-split.yaml` reads `source: data/`, which the tests write.
- [X] T025 [P] [US4] Write `tests/train/test_fixed_split_run.py`:
  - `caravan train` on the fixed-split fixture: the report's `dataset_resolved` has
    `split_source: column:split`, `windows_discarded_mixed_split: 1`, and split counts 48/16/15;
  - `data/schema.json` lists the derived input columns without `split`;
  - a copy of the data with one value set to `holdout` stops with DS-13, naming file, line and
    value.

### Implementation of the fixed split

- [X] T026 [US4] Add `RULE_SPLIT_COLUMN_WITH_FRACTIONS = "CF-12"`,
  `RULE_SPLIT_COLUMN_DECLARED = "CF-13"` and `RULE_SPLIT_VALUE = "DS-13"` to
  `src/caravan/manifest/errors.py`. CF-12 and CF-13 go in `MANIFEST_REJECTION_RULES`, DS-13 in the
  dataset run rules. Update `tests/unit/test_rules_coverage_v01.py` or the coverage test that
  enumerates new rules.
- [X] T027 [US4] In `src/caravan/manifest/schema/dataset.py`, give `Split` the field `column: str |
  None = Field(default=None, min_length=1)`.
  - A `model_validator(mode="before")` raises CF-12 when `column` is set together with any of
    `train`, `val`, `test` or `stratified` in the raw input. Message from contracts/manifest.md.
  - Skip CF-1 when `column` is set.
  - Add CF-13 to the cross-field validator in `src/caravan/manifest/schema/__init__.py`: the column
    equals `outputs[0].column` or is in `inputs[0].columns`.
- [X] T028 [US4] In `src/caravan/data/reader.py`:
  - `read_records` takes `split_column: str | None` and returns each record's part;
  - a missing column or a value outside `train`, `val`, `test` raises DS-13 with file, line and
    value;
  - derived input columns exclude the split column.
- [X] T029 [US4] In `src/caravan/data/windows.py`:
  - `plan_windows` takes optional per-record parts and returns per-window parts plus
    `discarded_mixed_split`;
  - `plan_split` takes `column=` and returns the fixed `SplitPlan` (data-model.md) instead of
    drawing by seed;
  - `SplitPlan` gains `source`.
- [X] T030 [US4] Thread the split column through the stages:
  - `src/caravan/stages/data.py` writes `split_column` to `data/schema.json`;
  - `src/caravan/stages/train.py` and `src/caravan/stages/quantize.py` pass
    `dataset.split.column` to the reader and to `plan_split`;
  - the report's `dataset_resolved` gains `split_source` and `windows_discarded_mixed_split`
    (`src/caravan/stages/train.py` where it builds that record).

  **Cache keys (Principle III).** `train` and `quantize` already read `dataset.split` and
  follow automatically. The `data` stage does not: add `dataset.split.column` to its `reads` in
  `src/caravan/stages/data.py`, because it now excludes that column from the derived inputs. Add a
  case to `tests/unit/test_cache_key_projection.py`: changing `dataset.split.column` changes the
  `data` key, and changing a fraction does not.
- [X] T031 [US4] Document the fixed split:
  - a section in `docs/try-it.md`, "Your own data";
  - the README's manifest example comment;
  - the manifest contract of feature 006 is historical, so it is not touched.

**Checkpoint**: T022–T025 green, the whole suite green.

---

## Phase 7: The candidate

- [X] T032 Set the version to `0.1.0rc1` in `pyproject.toml` and `src/caravan/__init__.py`. Run
  ruff and the whole suite on 3.13 with both extras, on 3.15 without extras, on 3.14 with `verify`,
  and from a clean wheel (as in feature 006, T075). Commit and push, and see PR #12 green.
- [ ] T033 Ask the owner to merge PR #12 (merged 2026-10-24 as `be3c44a`). The tag push from the session
  was refused by its proxy (HTTP 403), so `release.yml` gained a manual start that tags itself
  (owner's choice). After the merge, and only on the owner's go-ahead in the
  conversation, tag `v0.1.0rc1` on `main` and push the tag. See `release.yml` green through
  **verify**. If any job fails, follow contracts/release.md: fix on `main`, then tag `rc2`; never
  move a tag.

---

## Phase 8: User Story 4, part 2 — the `pace-cnn` port (P2)

**Goal**: `pace-cnn` rebuilt with the candidate on UCI HAR, as an internal test (FR-014–016,
FR-020).

**Independent test**: quickstart §6.

- [X] T034 [P] [US4] Write `ports/pace-cnn/convert.py`. Standard library plus numpy, which the
  train extra already brings. It takes `<archive.zip> <out dir>`.
  1. **Verify** the archive's SHA-256 against
     `c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031` (the zoo's
     `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`, `archive_sha256`), and
     refuse otherwise.
  2. **Read** the 9 `Inertial Signals` files, `y_*.txt` and `subject_*.txt`, for train and test.
  3. **Assign validation subjects** exactly as the zoo's `split_subjects` in
     `src/mobility_model_zoo/condition_monitoring/benchmark.py`:
     - take the sorted distinct training subjects;
     - draw `len // 7` (= 3) of them with
       `numpy.random.default_rng(2026).choice(subs, size=3, replace=False)`.

     Check the result against the benchmark manifest: 6,288 training and 1,064 validation windows.
     The subject lists hash to its `subjects_sha256`, computed the way the zoo's `subjects_sha256`
     computes it.
  4. **Standardise** each channel with the mean and standard deviation (+1e-6) of the training
     subjects without the validation subjects.
  5. **Write** `records.csv`: one row per time step, 128 rows per window, columns `label` (the six
     names, from `activity_labels.txt`), `split` (`train`, `val`, `test`), then the nine channels.
  6. **Write** `stats.json` with the mean, std and the validation subjects.

  The output directory must be outside the repository; refuse a path inside it.
- [X] T035 [P] [US4] Write `ports/pace-cnn/pace-cnn.yaml`:
  - **input and output**: one `series` input `imu` with window 128, and a `class` output
    `activity`, labels pinned in the dataset's order, `accuracy_drop_max: 0.03` (the zoo's K2);
  - **template**: `conv1d` with three blocks (16/5/pool 2, 32/5/pool 2, 32/3), all with
    `padding: same` and `normalise: true`, head `average`, and `dropout: 0.3` on the third block
    only, the nearest the template comes to the zoo's dropout before the dense layer;
  - **training**: `epochs: 20`, `batch: 128`, `learning_rate: 0.002`, `early_stopping: false`,
    `seed: 0`;
  - **data and export**: `representative_samples: 500`, `split: {column: split}`,
    `targets: [esp32]`. The zoo also measured an ESP8266, for which Caravan has no board
    description;
  - **`dataset.source`**: a placeholder the README tells the author to replace.
- [X] T036 [US4] Write `ports/pace-cnn/README.md`:
  - what the port is: an internal test of Caravan on a real model, not a zoo release, nothing
    published;
  - the steps, using the candidate's install line;
  - every difference from the zoo's recipe (research R8 table);
  - the licence contradiction, word for word from both sources, as an open item for the zoo.
- [ ] T037 [US4] Run the port with the candidate in a fresh 3.13 environment, installed from the
  release's wheel URL, on the archive in the session's scratch directory or a fresh download from
  archive.ics.uci.edu. Record from the run report: float and int8 accuracy on the 2,947 test
  windows, the gate verdict, model size, operators, fit floors, and the wall time. Compare with
  `zoo/models/pace-cnn/results/0.1.0/quality.json` and `releases/0.1.0.yaml`.
- [ ] T038 [US4] For every Caravan defect the port shows: write a failing test, fix on a branch, PR,
  CI green, merge. Then repeat T032–T033 with `rc2` and T037. Findings that are the model's, not
  Caravan's, go to the release note only (FR-015).

---

## Phase 9: The release

- [ ] T039 Complete `docs/releases/0.1.0.md`:
  - the port's result from T037, with numbers and provenance labels, and the comparison with the
    published `pace-cnn` stated as a comparison;
  - the gate checklist with links to the green `release.yml` runs (R7).

  Mark v0.1 released in `docs/roadmap.md` with the date.
- [ ] T040 Set the version to `0.1.0`. Rerun T032's validation and open a PR. After the owner's merge
  and go-ahead, tag `v0.1.0` and see `release.yml` green through **verify** (a full release, not a
  pre-release).

---

## Phase 10: Polish

- [ ] T041 [P] Run quickstart §1–§5 by hand on the candidate and fill every figure in
  `docs/try-it.md` and `docs/releases/0.1.0.md` from those runs. That includes the export summary
  lines, the time to an exported model and the file sizes.
- [ ] T042 [P] Update `specs/007-release-0-1-0/quickstart.md` §6 with the measured port figures.
- [ ] T043 Run `ruff check`, `ruff format --check` and the full suite; confirm the install budget
  job still holds (no dependency was added).

---

## Dependencies & Execution Order

- **Setup**: T001 first, independent.
- **US2 (Phase 3)** has no dependency. T003–T006 come before T007–T010.
- **US1 (Phase 4)** needs US2 (SC-002 in T012). T011–T012 come before T013–T014.
- **US3 (Phase 5)**:
  - T015–T016 come before T017–T019;
  - T020 moves T012's parser into `tests/support_docs.py`, so it comes before the workflow, T021;
  - T017 needs T014 for the shared URL form.
- **Fixed split (Phase 6)** is independent of Phases 3–5. T022–T025 come before T026–T030, in the
  order T026 → T027 → T028 → T029 → T030; T031 needs T014.
- **Candidate (Phase 7)** needs Phases 1–6.
- **Port (Phase 8)** needs the candidate's tag. T034 and T035 can be written earlier, in parallel
  with anything; T037 cannot.
- **Release (Phase 9)** needs T037 and T038 complete with no open Caravan defect.
- **Polish**: T041 after T033; T042 after T037; T043 last.

## Parallel opportunities

- T003, T004, T005 and T006 (different test files).
- T011 and T013; T015, T016, T017, T018 and T019.
- T022, T023, T024 and T025.
- T034 and T035, at any time.
- Phases 3–5 and Phase 6 can proceed side by side.

## Parallel Example: the fixed split

```bash
# Tests first, together:
T022 tests/unit/test_fixed_split.py
T023 tests/fixtures/manifests/{invalid,valid}/…
T024 tests/fixtures/datasets/split/make.py
T025 tests/train/test_fixed_split_run.py
# Then T026 → T030 in order (rules, schema, reader, windows, stages).
```

## Implementation Strategy

### MVP first

1. **US2 then US1.** A clean console and a tested guide make the candidate worth trying by hand:
   the owner's first request.
2. **US3 and the fixed split.** Then tag `v0.1.0rc1`.

### Then

3. **The port** with the candidate; fixes and `rc2` if it finds defects.
4. **`v0.1.0`.**

### Notes

- Tags and merges happen only on the owner's go-ahead in the conversation (T033, T040).
- Nothing the port produces is published, and no data enters the repository (FR-016, FR-020).
- Numbers in documents come from runs, never from expectation (T041).
- A failing test is fixed in the code, never skipped (constitution, Development Workflow).
