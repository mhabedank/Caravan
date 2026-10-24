# Tasks: Typed Features, Ludwig-Style

**Input**: `/specs/008-typed-features/` (spec, plan, research, data-model, contracts, quickstart)

**Tests**: requested by the constitution's workflow gates. Tests come before their implementation.

**Cost rule (constitution 4.1.0)**: commit and push to `008-typed-features` without a PR. One PR when
every task is done and the local validation (T050) is green.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Set `SCHEMA_VERSION = "caravan/v0.2"` in `src/caravan/manifest/version.py` and the
  schema's `apiVersion` literal in `src/caravan/manifest/schema/__init__.py`. Add rule constants to
  `src/caravan/manifest/errors.py`:
  - `RULE_FEATURE_TYPE = "CF-14"`;
  - `RULE_STRATIFY_COLUMN = "CF-15"`;
  - `RULE_BUDGET_FOR_TYPE = "CF-16"`;
  - `RULE_ONE_OUTPUT = "CF-17"` (all in `MANIFEST_REJECTION_RULES`);
  - `RULE_CLASS_OUTSIDE_TRAIN = "DS-14"`;
  - `RULE_BINARY_SPELLINGS = "DS-15"` (both in `RUN_RULES`).

  Move CF-10 to `RETIRED_RULES` and update `tests/unit/test_retired_rules.py` (seven identifiers).
  Add the new identifiers to `tests/unit/test_rules_coverage_v01.py` `NEW_RULES`.

---

## Phase 2: User Story 1 — name the columns and their types, as in Ludwig (P1)

**Goal**: `caravan/v0.2` validates, resolves and renders; every fixture is in the new form.

**Independent test**: quickstart §1–§2.

### Tests

- [ ] T002 [P] [US1] Write `tests/unit/test_features_schema.py`:
  - every key and default of `contracts/manifest.md` (input features, output feature, global
    preprocessing, trainer, `random_seed`, export);
  - `type` outside `number|binary|category` → CF-14, naming the implemented types;
  - not exactly one output → CF-17;
  - `stratify` on a non-output column → CF-15;
  - `mae_increase_max` on `category` or `accuracy_drop_max` on `number` → CF-16;
  - `probabilities` with `fixed` → CF-12;
  - the split column as a feature or as the output → CF-13;
  - a feature naming the output column → CF-11;
  - names against CF-9;
  - window vs template → CF-6.
- [ ] T003 [P] [US1] Write `tests/contract/test_manifest_v02.py`. Each `v0.1` key of the "Removed"
  table in `contracts/manifest.md`, written in a `v0.2` manifest, is refused at its path with the
  new key named. A `v0.1` manifest as a whole is refused with V-1.
- [ ] T004 [P] [US1] Write one invalid fixture per new rule under
  `tests/fixtures/manifests/invalid/`, each with an `.expected.json`:
  - `cf-14-text-feature.yaml`;
  - `cf-15-stratify-other-column.yaml`;
  - `cf-16-budget-for-type.yaml`;
  - `cf-17-two-outputs.yaml`.

### Implementation

- [ ] T005 [US1] Write `src/caravan/manifest/schema/features.py`, which replaces `io.py`. It holds
  `InputFeature` and `OutputFeature`, each with typed `preprocessing`, `encoder`, `loss`,
  `threshold`, `clip`, `accuracy_drop_max` and `mae_increase_max`, as `contracts/manifest.md` lists
  them with defaults:
  - `normalization` ∈ {`zscore`, `minmax`, `iq`, `null`};
  - `missing_value_strategy` ∈ {`fill_with_const`, `fill_with_mean`};
  - `most_common` default 32;
  - `encoder.type` ∈ {`dense`, `onehot`}, default `dense`;
  - `embedding_size` default `min(vocab, 4)`, resolved after fitting;
  - `threshold` default 0.5;
  - `loss.type` ∈ {`mean_squared_error`, `mean_absolute_error`, `huber`}.
- [ ] T006 [US1] Write `src/caravan/manifest/schema/preprocessing.py`:
  - `window_size` (int > 0, optional);
  - `split: {type: random|stratify|fixed (default random), probabilities (default [0.7, 0.15, 0.15];
    > 0 each, sum 1), column}`.

  Rename `schema/train.py` to `schema/trainer.py` with `epochs` (50), `batch_size` (256),
  `learning_rate` (0.001), `optimizer: {type: adam|sgd|adamw}` and `early_stop` (int ≥ −1,
  default 5). Reduce `schema/dataset.py` to a path, so `dataset` is a string. Add
  `representative_samples` to `schema/export.py`.
- [ ] T007 [US1] Rebuild `Manifest` in `src/caravan/manifest/schema/__init__.py` with
  `input_features`, `output_features`, `preprocessing`, `defaults`, `dataset`, `trainer`,
  `random_seed` (default 42) and `export`, and the validators of T002. Put the `v0.1` keys into
  `src/caravan/manifest/schema/removed.py` with messages naming the `v0.2` key.
- [ ] T008 [US1] Rewrite `src/caravan/manifest/resolve.py`:
  - apply `defaults` per type (feature value, then `defaults`, then type default);
  - emit every feature fully resolved, with the `derived` marker where fitting will decide (vocab,
    shift and scale, `embedding_size`);
  - replace `merge_derived` with `merge_fitted(resolved, fitted)`, which writes each feature's
    fitted values under `preprocessing.fitted`.
- [ ] T009 [US1] Rewrite every manifest fixture to `caravan/v0.2` as in `contracts/manifest.md`:
  - under `tests/fixtures/manifests/{valid,invalid,gate}/`;
  - `examples/picket-mlp.yaml`;
  - `ports/pace-cnn/pace-cnn.yaml`;
  - `can_id` is `category`, every other CSV column `number`;
  - the fixed-split fixture uses `preprocessing.split: {type: fixed, column: split}`;
  - keep `tests/fixtures/manifests/invalid/v-1-previous-version.yaml` as a `v0.1` manifest.

  Update `tests/support.py` constants and `tests/contract/test_example_matches_fixture.py`.
- [ ] T010 [US1] Bring the core tests built on the `v0.1` declaration form to `v0.2`:
  - **Delete** `tests/unit/test_io_declarations.py`, which T002 replaces.
  - **Rewrite to `v0.2` paths:**
    - `tests/unit/test_resolve_v01.py` (renamed `test_resolve_v02.py`, `merge_fitted` instead of
      `merge_derived`);
    - `tests/unit/test_projection_index.py`, `tests/unit/test_cache_key_projection.py`,
      `tests/unit/test_every_field_is_read.py`, `tests/unit/test_errors.py`,
      `tests/unit/test_windows.py`, `tests/unit/test_fixed_split.py`;
    - `tests/contract/test_conv1d_manifest.py`, `tests/integration/test_validate.py`,
      `tests/layering/test_hostile_import.py`.

  Then run `pytest tests/unit tests/contract tests/integration tests/layering` green. The train
  tests built on the `v0.1` form are rewritten where their stage changes: T018, T021 and T023.

**Checkpoint**: the core suites green on 3.13 and 3.15 without extras.

---

## Phase 3: User Story 4 — defaults per type (P3; small, done with the schema)

- [ ] T011 [P] [US4] In `tests/unit/test_features_schema.py`:
  - `defaults: {number: {preprocessing: {normalization: minmax}}}` gives minmax on every number
    feature without its own value, and a feature's own value wins;
  - a `defaults` entry for an absent type is accepted and rendered.

  T008 implements it.

---

## Phase 4: User Story 2 — each type brings its preprocessing (P1)

**Goal**: fitted on the training part, built into the model, raw values in; the typed pilot passes
int8 with derived labels.

**Independent test**: quickstart §3–§5.

### Tests

- [ ] T012 [P] [US2] Write `tests/unit/test_fit_preprocessing.py` for `src/caravan/data/fit.py`
  (pure Python):
  - zscore, minmax and iq shift/scale;
  - scale 0 → 1, with a note;
  - vocabulary by frequency, descending, ties by text, capped by `most_common`, `cut` counted, with
    "unknown" at index 0;
  - pinned `vocab` kept;
  - text categories get codes 1..V in vocabulary order;
  - binary spellings per Ludwig, `fallback_true_label`, DS-15;
  - output labels with no unknown, DS-14;
  - fill values;
  - fitting reads only the given training rows.
- [ ] T013 [P] [US2] Write `tests/train/test_preprocessing_layers.py`:
  - **`Standardize`, `VocabularyOneHot` and `AsChannel` in isolation:**
    - each, converted under Caravan's settings, has only operators in
      `{QUANTIZE, DEQUANTIZE, SUB, MUL, ADD, EQUAL, CAST, SUM, CONCATENATION, RESHAPE,
      FULLY_CONNECTED, STRIDED_SLICE}`;
    - the one-hot is exact for every vocabulary code;
    - an unseen code lands in slot 0;
    - `Standardize` matches `(x − shift) / scale` within the int8 step.
  - **Serialisation:** all three survive `keras.models.load_model` and `fix_batch` (registered,
    constructor arguments, no `Lambda`). Extend `tests/train/test_batch_fix.py` for a five-input
  model with mixed dtypes.
- [ ] T014 [P] [US2] Extend `tests/unit/test_cache_key_projection.py` (FR-019, Principle III):
  - a change of the fitted values merged into the resolved manifest (a vocabulary entry, a shift)
    changes the keys of `build`, `train` and `quantize`, but not of `data`;
  - a change of `output_features[0].accuracy_drop_max` or `mae_increase_max` changes only
    `quantize` and `export`, never `build` or `train`;
  - a change of `random_seed` re-runs `data`, because the split moves.
- [ ] T015 [P] [US2] Write `tests/train/test_typed_pilot.py` for `examples/picket-mlp.yaml`, with
  labels derived and nothing pinned:
  - **SC-003:** `caravan export` passes the int8 gate;
  - **SC-004:** feeding the exported model the raw CSV values of each test window by input name
    gives the same class as the trained model on at least (1 − `accuracy_drop_max`) of the windows;
  - the report lists `data.features` with fitted values and an empty `ignored_columns`.

### Implementation

- [ ] T016 [US2] Write `src/caravan/data/fit.py` (core, standard library) per `data-model.md`,
  *Fitted preprocessing*. Make T012 pass.
- [ ] T017 [US2] Rewrite `src/caravan/data/reader.py` to read typed columns:
  - `number` as float32, with missing cells filled per strategy;
  - `category` and `binary` as the raw value, kept as text until mapped by the fitted tables;
  - the output column per its type;
  - the split column as today, accepting `0/1/2` and `train/validation/test` (research R8);
  - columns no feature reads are returned as `ignored`;
  - DS-12 for a named column the data lacks.
- [ ] T018 [US2] Rewrite `src/caravan/stages/data.py`:
  - reads `input_features`, `output_features[0].name`, `output_features[0].type`,
    `output_features[0].preprocessing`, `preprocessing.window_size`, `preprocessing.split` and
    `random_seed`;
  - cuts windows, splits, and fits on the training windows only;
  - writes `data/schema.json` and `data/preprocessing.json`.

  Make `src/caravan/cli/pipeline.py` call `merge_fitted`, so every later stage's key includes the
  fitted values. Rewrite `tests/train/test_data_stage.py` and `tests/train/test_declared_io_end_to_end.py`
  for the typed form; the latter is renamed `test_typed_end_to_end.py`, with the same assertion that
  derived and pinned vocabularies give the same samples and split.
- [ ] T019 [US2] Write `src/caravan/templates/builders/preprocessing.py` (train extra) with
  registered layers:
  - `Standardize(shift, scale)`;
  - `VocabularyOneHot(vocab)`: int32 compare, unknown slot at index 0;
  - `AsChannel()`;
  - `DenseEncoder(embedding_size)`: `Dense` without bias on the last axis.

  Add the module to the layering tests' extra-only list. Make T013 pass.
- [ ] T020 [US2] Write `src/caravan/templates/builders/frontend.py`. It builds one `keras.Input` per
  input feature, with shape `(window_size,)` and dtype float32 for `number` and int32 otherwise,
  named after the feature. Then the layer of T019 and the encoder, concatenated to
  `(window_size, channels)` and fed to the template body. Rewrite `rewire` and `construct` in
  `src/caravan/stages/build.py` to use it, with the head per output type (`data-model.md`, *Model
  inputs and outputs*). The `build` reads become `input_features`, `output_features[0].name`,
  `output_features[0].type`, `output_features[0].preprocessing`, `preprocessing.window_size`,
  `model.*` and `random_seed`. Rewrite `tests/train/test_rewire_names.py` and
  `tests/train/test_conv1d_build.py` for several named inputs.
- [ ] T021 [US2] Rewrite `src/caravan/data/reader_bridge.py` `assemble_samples` to return a dict of
  per-feature window arrays keyed by feature name (codes mapped by the fitted tables), plus the
  targets. Update `src/caravan/stages/train.py` to train on the dict with the `category` loss. Its
  reads become `trainer.*`, `random_seed`, `preprocessing.*`, `input_features` and the output's
  name/type/preprocessing/loss. Update `tests/train/conftest.py` (its manifest template) and
  `tests/train/test_gate_failure.py` to `v0.2`.
- [ ] T022 [US2] Update `src/caravan/convert/batch.py` `fix_batch`: every input is rebuilt at batch
  1 with its own dtype and name, and a model containing a `Lambda` is refused. Update
  `src/caravan/convert/tflite.py`:
  - the representative dataset yields dicts keyed by input name;
  - `inference_input_type` is unset;
  - outputs are float32.
- [ ] T023 [US2] Update `src/caravan/stages/quantize.py` and `src/caravan/runtime/inspect.py`:
  - **"fully quantized" means** every tensor int8 or int32 except the model's float32/int32 inputs
    (each followed by QUANTIZE for float) and its float32 outputs (after DEQUANTIZE) (research R5);
  - **measurement:** LiteRT is fed by input name;
  - **calibration:** a dict per window;
  - **the gate for `category`:** as today, read from `output_features[0].accuracy_drop_max`.

  Make T015 pass.

**Checkpoint**: quickstart §3 and §4 hold. The full suite with the train extra is green, except the
tests still written for the `v0.1` export (fixed in Phase 5).

---

## Phase 5: User Story 3 — the firmware binds every input by name (P2)

**Goal**: per-input binding in the contract, header and runner; the input order never matters.

**Independent test**: quickstart §5.

### Tests

- [ ] T024 [P] [US3] Write `tests/train/test_input_order.py`. Export the five-input pilot and
  assert:
  - the converted file's input order differs from the manifest's (as measured), and the test says
    so if it ever stops differing;
  - `model/interface.json` gives each input's name, position, dtype (`float32` or `int32`), shape
    `[1, window_size]` and type;
  - feeding inputs by the contract's positions reproduces the trained model's classes on the test
    windows.
- [ ] T025 [P] [US3] Extend `tests/unit/test_interface_emit.py`:
  - the header has one `#define <MODEL>_INPUT_<NAME> <position>` per input, with the element type
    in a comment;
  - every input carries `fitted`: shift and scale for `number`; `vocab` and `cut` for `category`;
    the spelling table for `binary` (FR-012);
  - text categories carry their `text_codes` table;
  - binary features carry their spelling table;
  - number features carry `missing`;
  - the output gives `decision`;
  - the JSON is deterministic.
- [ ] T026 [P] [US3] Extend `tests/unit/test_skeleton.py`: the runner fills each input by its
  constant with raw values (`fill_int32` / `fill_float`) and contains no scale, zero point, mean or
  vocabulary.

### Implementation

- [ ] T027 [US3] Update `src/caravan/runtime/flatbuffer.py` `read_bindings` to return every input's
  name, position, dtype and shape from the signature.
  - **New fixture model:** add a five-input, mixed-dtype model to `tests/fixtures/models/make.py`
    (float32 and int32 inputs, float32 output) and regenerate the committed fixture models.
  - **Verify suite:** update it for several inputs: `tests/verify/test_flatbuffer_reading.py`,
    `tests/verify/test_inspect.py`, `tests/verify/test_interface_positions.py` and
    `tests/verify/test_measure.py`.
  - **Check:** the `verify` suite runs on 3.14 with only the runtime extra (CI job `measure`).
- [ ] T028 [US3] Rewrite `src/caravan/export/interface.py` (`interface_document`,
  `header_additions`, `source_additions`) to `contracts/interface.md`. A `category` input's header
  comment says the code is an integer, never a rounded number. Update
  `src/caravan/export/skeleton.py` and `src/caravan/export/c_array.py`. The `export` reads become
  `model.name`, `model.version`, `export.*`, `input_features`, the output's
  name/type/preprocessing/threshold, and `preprocessing.window_size`.
- [ ] T029 [US3] Update the fit floors (`src/caravan/stages/fit.py` `layer_records`,
  `src/caravan/targets/fit.py`): flash counts the preprocessing constants and the embedding; RAM
  counts every input tensor at 4 bytes × window_size and the concatenated features (research R11).
  Update `tests/unit/test_fit_floors.py` with the arithmetic for a five-input model.

**Checkpoint**: T024–T026 green; quickstart §5.

---

## Phase 6: User Story 1, continued — `binary` and `number` outputs (P1, scenario 6)

**Goal**: both output types train, pass their own int8 budget and export their decision (SC-007).

**Independent test**: quickstart §6.

### Tests

- [ ] T030 [P] [US1] Write `tests/unit/test_regression_metrics.py` for
  `src/caravan/metrics/regression.py` (core): MAE, MSE, RMSE and R² on hand-computed cases,
  including a constant target, where R² is undefined and reported as such.
- [ ] T031 [P] [US1] Add `tests/support.py` helpers that derive test-time datasets from the
  committed fixture, so that no new dataset is committed:
  - **`write_binary_dataset(dest)`**: the output `is_attack` is `no` for normal records and `yes`
    for the rest;
  - **`write_number_dataset(dest)`**: the output `payload_mean` is the mean of `b0..b2` over each
    window's records, written per record, so a window's records agree.
- [ ] T032 [P] [US1] Write `tests/train/test_output_types.py`:
  - **binary:** trains, its gate uses accuracy, the export's contract says `threshold: 0.5`, and
    the header has the threshold;
  - **number:** trains with `mean_squared_error`, its gate uses the MAE increase in the column's
    unit, the exported model's output is float32 in that unit, and `clip` bounds it;
  - a gate failure for `number` writes the per-layer error table as for `category`.

### Implementation

- [ ] T033 [US1] Write `src/caravan/metrics/regression.py` (standard library). Make T030 pass.
- [ ] T034 [US1] Add the `binary` and `number` heads to `src/caravan/templates/builders/frontend.py`:
  - `binary`: sigmoid unit;
  - `number`: linear unit, then `Standardize`'s inverse when the output `normalization` is set, then
    MAXIMUM/MINIMUM for `clip`.

  In `src/caravan/stages/train.py`, add each type's loss (`binary_crossentropy` with
  `positive_class_weight`; MSE, MAE or Huber) and metrics.
- [ ] T035 [US1] Add the gate per type in `src/caravan/stages/quantize.py`:
  - `binary`: accuracy at `threshold`;
  - `number`: MAE trained against quantized, with `mae_increase_max`;
  - the report's `quantization.gate` gives `metric`, `trained`, `quantized`, `change`, `budget` and
    `verdict`.

  Make T032 pass.

**Checkpoint**: quickstart §6.

---

## Phase 7: The port and the documents

- [ ] T036 [P] Change `ports/pace-cnn/convert.py`:
  - it writes raw values (no standardisation) and the split as `train`/`validation`/`test`;
  - it keeps every hash check;
  - it detects the repository by a `pyproject.toml` naming `caravan-ml` above the script, not by
    `parents[2]`, so a copy outside the checkout works (the defect found on 2026-10-24).

  Add `tests/unit/test_port_convert.py` for that check; it needs no archive.
- [ ] T037 [P] Rewrite `ports/pace-cnn/pace-cnn.yaml` in `v0.2`:
  - nine `number` input features;
  - `activity` as a `category` output with `accuracy_drop_max: 0.03`;
  - `preprocessing: {window_size: 128, split: {type: fixed, column: split}}`;
  - `trainer` per R1;
  - `random_seed: 0`.

  Update `ports/pace-cnn/README.md`: the standardisation now happens in the model, and that row is
  removed from the difference table.
- [ ] T038 Run the port with the working tree on the UCI HAR archive (as feature 007 R10). The
  archive lives only in a session's scratch directory. If it is gone, download it again from
  <https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones>; the
  converter checks its hash. Record
  int8 and float accuracy on the 2,947 test windows, model size and operators in
  `specs/008-typed-features/research.md` as R16. Check SC-006 (≥ 0.918).
- [ ] T039 [P] Add a `caravan/v0.1 → caravan/v0.2` section to `docs/manifest-changes.md`: the table
  of research R1, the by-hand edit of the pilot, and every exception to Ludwig's naming with its
  reason (SC-002). Also say that derived labels are now ordered by frequency in the training part
  (Ludwig's order), no longer alphabetically, so a model that relied on the old order pins
  `preprocessing.vocab`.
- [ ] T040 [P] Rewrite `docs/try-it.md` "Your own data" and "Run" for `v0.2`:
  - how columns become features;
  - what each type does;
  - what is ignored;
  - the fixed split's values.

  Rewrite the README's manifest example and status. `tests/train/test_try_it_guide.py` and
  `tests/integration/test_readme.py` keep passing.
- [ ] T041 [P] Update `docs/releases/0.1.0.md`:
  - the known limits lose "unscaled inputs" and "one input" and gain the model size of the typed
    pilot;
  - the change notes name `v0.2`.

  Update `docs/roadmap.md`: feature 008 under v0.1.
- [ ] T042 [P] Mark the retired feature-006 terms in `specs/006-declared-io/` with one line at the
  top of `spec.md`: superseded by feature 008 for the declaration form.

---

## Phase 8: Validation

- [ ] T043 Run `ruff check` and `ruff format --check`.
- [ ] T044 Run the full suite on 3.13 with both extras.
- [ ] T045 Run the core suites on 3.15 without extras.
- [ ] T046 Run `tests/verify tests/unit tests/contract` on 3.14 with `verify`.
- [ ] T047 Run the whole tree from a clean wheel on 3.14.
- [ ] T048 Run `actionlint` on the workflows (unchanged, a guard).
- [ ] T049 Run quickstart §1–§7 by hand and fill the figures marked *to be measured* in
  `quickstart.md`.
- [ ] T050 Push `008-typed-features`, open one PR (constitution 4.1.0), see CI green and report to
  the owner. Merging and the release of `v0.1.0` (feature 007, T038–T043) follow on the owner's
  go-ahead.

---

## Dependencies & Execution Order

- **Setup:** T001 first.
- **US1, Phase 2:**
  - T002–T004 before T005–T010;
  - T005 → T006 → T007 → T008 → T009 → T010.
- **US4, Phase 3:** T011 with T008.
- **US2, Phase 4:**
  - needs Phase 2;
  - T012–T015 before T016–T023;
  - T016 → T017 → T018; T019 → T020 → T021 → T022 → T023.
- **US3, Phase 5:**
  - needs T022, T023;
  - T024–T026 before T027–T029.
- **Output types, Phase 6:**
  - needs T020–T023;
  - T030–T032 before T033–T035.
- **Phase 7:**
  - T036, T037 and T039–T042 can start after Phase 2;
  - T038 needs Phases 4–6.
- **Phase 8:** last.

## Parallel opportunities

- T002, T003, T004.
- T012, T013, T014, T015.
- T024, T025, T026.
- T030, T031, T032.
- T036, T037, T039, T040, T041, T042.

## Implementation Strategy

1. **MVP:** Phases 1–4. The typed pilot passes int8 with derived labels from raw values. Stop and
   check SC-003 and SC-004.
2. **Binding by name and the fit floors:** Phase 5.
3. **`binary` and `number` outputs:** Phase 6.
4. **The port, the documents and validation;** then one PR.
