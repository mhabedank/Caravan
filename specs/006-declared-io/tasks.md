---

description: "Task list for feature 006: Declared Inputs and Outputs, and a Lean Manifest"
---

# Tasks: Declared Inputs and Outputs, and a Lean Manifest

**Input**: Design documents from `/specs/006-declared-io/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: requested. This project writes each test before the code it checks, and the suite is a
merge gate (constitution, Development Workflow). Test tasks are therefore not optional here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: may run in parallel with other [P] tasks — different files, no unfinished dependency.
- **[US1]** … **[US4]**: the user story the task serves. Setup, foundational and polish tasks carry
  none.

## Path Conventions

- Single Python package: source under `src/caravan/`, tests under `tests/`, feature documents under
  `specs/006-declared-io/`.
- Commands from `CONTRIBUTING.md`: `uv run pytest`, `uv run ruff check src tests`,
  `uv run ruff format src tests`.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 In `src/caravan/manifest/errors.py`, add the rule identifiers, each with its one-line
  reason in the existing style:
  - `CF-9`, declaration name: "`[a-z][a-z0-9_]{0,31}`, unique across inputs and outputs";
  - `CF-10`, one input and one output, and kinds implemented;
  - `CF-11`, a column both input and output;
  - `DS-11`, fewer than two classes;
  - `DS-12`, an input column the data does not have;
  - `X-6`, a declared name missing from the converted model's signature;
  - `F-1`, a floor exceeds a board, in a new `FIT_RULES` frozenset included in `ALL_RULES`.

  Put CF-9, CF-10 and CF-11 in `MANIFEST_REJECTION_RULES`. Remove `RULE_PERSONAL_DATA_RISK_CLASS`
  (CF-3), `RULE_PUBLISH_NEEDS_COMPLIANCE` (CF-5), `RULE_EMULATOR_EXISTS` (CF-7),
  `RULE_PUBLISH_BENCHMARK_ONLY` (CF-8) and `RULE_TRAINING_NOT_PERMITTED` (DS-9) from every group.
  Add `RETIRED_RULES = frozenset({"CF-3", "CF-5", "CF-7", "CF-8", "DS-9"})`.
- [X] T002 [P] Create `src/caravan/manifest/schema/removed.py`: one table, `REMOVED_FIELDS`, mapping
  each path to `(action, to, reason)`, with exactly the paths and messages of
  `specs/006-declared-io/contracts/manifest.md`, *Removed fields*:
  - dropped: `compliance`, `model.topic`, `model.task`, `dataset.license`,
    `dataset.permitted_use`, `verify`, `bench`, `publish`;
  - moved: `dataset.labels` → `outputs[0].labels`, `dataset.window` → `inputs[0].window`,
    `export.accuracy_drop_max` → `outputs[0].accuracy_drop_max`.

  Add `BENCHMARK_ONLY_PUBLISH_NOTICE` with the sentence from the migration contract, step 2. Pure
  data, no imports beyond the standard library.
- [X] T003 [P] Write `tests/unit/test_retired_rules.py`: no identifier in `RETIRED_RULES` appears in
  any rule group or in any `*.expected.json` under `tests/fixtures/`, and no module under
  `src/caravan/` raises one.
- [X] T004 [P] Write the new-form fixtures:
  - `tests/fixtures/manifests/valid/picket-mlp-v01.yaml`: exactly the pilot of
    `contracts/manifest.md`, with `dataset.source: ../../datasets/synthetic`.
  - `tests/fixtures/manifests/valid/picket-conv1d-v01.yaml`: `picket-conv1d-fixture.yaml` translated
    to the new form.
  - `tests/fixtures/manifests/valid/pilot-min-v01.yaml`: the smallest valid new-form manifest.

  Each starts with a comment naming the fixture it mirrors, as the existing fixtures do. Each
  states `accuracy_drop_max` on its output, which is required (FR-029).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Every user story depends on this phase.** It moves the whole pipeline to `caravan/v0.1`. At its
checkpoint, the migrated pilot fixture and the new-form fixture both run end to end, as the pilot
did before.

### Declarations and schema

- [X] T005 Write `tests/unit/test_io_declarations.py` first, covering `InputDeclaration` and
  `OutputDeclaration`:
  - `name` matches `[a-z][a-z0-9_]{0,31}` (rejects `Frames`, `can-id`, `1x` and 33 characters);
  - `kind` is `"series"` / `"class"` only;
  - `columns`: a list of distinct non-empty strings, at least one, optional;
  - `window`: an int > 0, optional;
  - `column` defaults to `"label"`;
  - `labels`: at least two distinct non-empty strings, optional;
  - `accuracy_drop_max`: a float in [0, 1], **required** on a `class` output, no default
    (Principle V; FR-029);
  - `extra="forbid"` on both.
- [X] T006 Implement `src/caravan/manifest/schema/io.py` to pass T005. The name pattern is one
  module constant with its form sentence, like `NAME_FORM` in `schema/model.py`.
- [X] T007 Write `tests/unit/test_migration_v01.py` first:
  - every step of the migration contract, on the committed `picket-mlp.yaml` and on a manifest
    carrying every removed field;
  - the notices: count, order, `path`, `action`, `to`, `reason`;
  - the benchmark-only-with-publish notice;
  - a previous form without `export.accuracy_drop_max` gets `0.02` written into the output with an
    `added` notice (FR-029);
  - a document with no `apiVersion` is migrated as `caravan/v0`;
  - the input mapping is not mutated;
  - the file's bytes are unchanged;
  - `MigrationResult` records the declared and effective versions.
- [X] T008 Implement the migration in `src/caravan/manifest/migrate.py`:
  - `CURRENT_SCHEMA_VERSION = "caravan/v0.1"`;
  - `default_registry()` knows `("caravan/v0", "caravan/v0.1")`;
  - a `Transform` returns `(mapping, notices)`;
  - add a `MigrationNotice` dataclass with `path`, `action` (`dropped`, `moved` or `added`), `to`,
    `reason`, and `MigrationResult.notices`;
  - add `migrate_v0_to_v01` driven by `REMOVED_FIELDS`.

  Adapt the synthetic-registry tests in `tests/unit/test_migration.py` to the new `Transform` shape
  without weakening them.
- [X] T009 Update the manifest schema:
  - remove `topic` and `task` in `src/caravan/manifest/schema/model.py`;
  - remove `labels`, `window`, `license` and `permitted_use`, and the module docstring about
    them, in `schema/dataset.py`;
  - remove `accuracy_drop_max` in `schema/export.py`;
  - remove `VerifySpec`, `BenchSpec` and `PublishSpec` in `schema/misc.py` (delete the module if
    it is empty);
  - delete `schema/compliance.py`.
- [X] T010 Rework `Manifest` in `src/caravan/manifest/schema/__init__.py`:
  - `apiVersion: Literal["caravan/v0.1"]`, `inputs: list[InputDeclaration]` and
    `outputs: list[OutputDeclaration]`;
  - remove `compliance`, `verify`, `bench`, `publish` and the CF-3, CF-7 and CF-8 validators;
  - CF-6 reads `inputs[0].window`, with the path `inputs[0].window`;
  - add CF-10: exactly one input and one output, message per `contracts/manifest.md`, naming
    `docs/research/2026-10-23-multi-io-on-mcu.md`;
  - add CF-9: names unique across inputs and outputs;
  - add CF-11: `outputs[0].column` not in `inputs[0].columns`;
  - CF-4 is unchanged.
- [X] T011 In `src/caravan/manifest/load.py`:
  - carry `MigrationResult.notices` into the load outcome;
  - in a `caravan/v0.1` document, report a path found in `REMOVED_FIELDS` with its own message at
    its own path, ahead of the generic unknown-field finding (FR-001).
- [X] T012 Write the resolver tests first in `tests/unit/test_resolve_v01.py`:
  - key order as in `data-model.md`;
  - `columns: derived` and `labels: derived` when not stated;
  - stated values kept as written;
  - `merge_derived(resolved, schema)` replaces exactly those two markers and nothing else;
  - byte-identical output across two calls.
- [X] T013 Implement `src/caravan/manifest/resolve.py`: the `caravan/v0.1` shape with no removed key,
  the `DERIVED = "derived"` marker, and `merge_derived`.
- [X] T014 Bring the remaining invalid fixtures under `tests/fixtures/manifests/invalid/` (B-1,
  CF-1, CF-2, CF-4, CF-6, T-1, T-2, V-1, unknown-field, unknown-field-misplaced) to the
  `caravan/v0.1` form, and update each `*.expected.json`; CF-6's path becomes `inputs[0].window`.
  Move the CF-3, CF-7 and CF-8 fixtures to `tests/fixtures/manifests/migration/`, each with a
  `*.notices.json` listing the notices it must produce. Add `v01-removed-compliance.yaml`,
  `v01-two-inputs.yaml` (CF-10), `v01-label-as-input.yaml` (CF-11) and `v01-name-with-hyphen.yaml`
  (CF-9), with expected files, so `tests/unit/test_fixture_coverage.py` holds.

### The data step and the stages

- [X] T015 Extend `project()` in `src/caravan/stages/base.py` to accept an index in a path:
  `outputs[0].labels`, `inputs[0].columns`. A missing index or key still raises
  `DeclarationError`, and the projection key is the path as written. Write
  `tests/unit/test_projection_index.py` first: indexed paths resolve, an out-of-range index raises,
  and two manifests that differ only in `outputs[0].accuracy_drop_max` give identical projections
  for every stage but `quantize` (FR-031).
- [X] T016 Write `tests/train/test_data_stage.py` first, on the synthetic fixture:
  - derived labels are `["dos", "fuzzy", "normal", "replay"]`;
  - stated labels keep their order;
  - a stated list missing a data value fails DS-5 at `outputs[0].labels`, naming it, and a stated
    list naming an absent value fails DS-5 likewise;
  - a one-class column fails DS-11;
  - a stated unknown column fails DS-12, naming the columns the data has;
  - stated columns are kept in stated order, and unread columns appear in `ignored_columns`;
  - `labels_source` and `columns_source` are correct;
  - a reused `data` stage reads no records (`context.records_if_read is None`).
- [X] T017 Change `src/caravan/data/reader.py`:
  - `read_records(dataset, *, input_columns, output_column)` replaces the fixed `LABEL_COLUMN`;
  - the header check requires exactly one `output_column`, and raises DS-12 for a stated input
    column the header lacks;
  - with no stated columns, the feature columns are every column but the output column, in file
    order;
  - with stated columns, they are used in stated order;
  - `RecordSchema` gains `ignored_names`;
  - move label validation out of the reader (`_check_labels` goes to the `data` stage).

  Update `src/caravan/data/reader_bridge.py` callers only as the signature requires.
- [X] T018 Create `src/caravan/stages/data.py`:
  - `SPEC = StageSpec(name="data", reads=("inputs[0].columns", "outputs[0].column",
    "outputs[0].labels"), reads_dataset=True, upstream=None, artifacts=("data/schema.json",))`;
  - the `DataSchema` of `data-model.md`;
  - derivation sorted with `sorted()` on `str`;
  - DS-5 in both directions, DS-11 and DS-12;
  - framework imports inside functions.
- [X] T019 Write `tests/train/test_rewire_names.py` first: for `mlp` and `conv1d` under one seed,
  the rewired model's weights equal the builder's array for array. The converted int8 operator list
  equals the unwired one. The SignatureDef carries the declared input and output names (research
  R4).
- [X] T020 Change `src/caravan/stages/build.py`:
  - reads `("model.template", "model.params", "train.seed", "inputs[0].name",
    "inputs[0].columns", "inputs[0].window", "outputs[0].name", "outputs[0].labels")`;
  - a `rewire(model, input_name, output_name)` helper builds an `Input` with the declared name,
    applies the builder's layers in order, and returns `keras.Model(inp, {output_name: x})`;
  - the window comes from `inputs[0].window`, the labels from `outputs[0].labels`;
  - `describe()` records `input_name` and `output_name`.
- [X] T021 Change `src/caravan/stages/train.py`:
  - reads `train.*`, `dataset.split`, `inputs[0].columns`, `inputs[0].window`,
    `outputs[0].name` and `outputs[0].labels`, and never `outputs[0].accuracy_drop_max` (FR-031);
  - delete `check_permitted`, `BENCHMARK_ONLY` and the DS-9 import;
  - compile with the loss keyed by the output name;
  - fit with targets as `{output_name: targets}`;
  - take `model.predict(...)[output_name]` before `argmax`;
  - in the module docstring, drop the Principle VI paragraph.
- [X] T022 Change `src/caravan/stages/quantize.py`:
  - reads `export.quantization`, `dataset.representative_samples`, `dataset.split`, `train.seed`,
    `inputs[0].columns`, `inputs[0].window`, `outputs[0].name`, `outputs[0].labels` and
    `outputs[0].accuracy_drop_max`. It is the only stage that reads the budget;
  - the accuracy-gate finding's path is `outputs[0].accuracy_drop_max`;
  - the float predictions are taken by output name.

  Check `src/caravan/convert/debugger.py` and `src/caravan/runtime/measure.py` for output-index
  assumptions that a dict output breaks, and fix only those.
- [X] T023 Change `src/caravan/stages/export.py` to read `("model.name", "model.version",
  "export.formats", "export.targets", "export.quantization", "inputs[0].name",
  "inputs[0].columns", "inputs[0].window", "outputs[0].name", "outputs[0].labels")`. No new
  artifact yet; US4 adds it.
- [X] T024 Change the pipeline in `src/caravan/cli/pipeline.py`:
  - every verb's stage list starts with `data`;
  - the `data` stage runs against the resolved manifest as declared, and every later stage against
    `merge_derived(resolved, schema)`;
  - `resolved.yaml` is written after the `data` stage, and with the markers if `data` fails;
  - `StageContext` no longer takes `labels`;
  - the run report's dataset section gains `input_columns`, `labels`, `labels_source` and
    `ignored_columns`.

  Update the stage lists in `src/caravan/cli/build.py`, `train.py`, `quantize.py` and `export.py`.
- [X] T025 [P] Update `tests/unit/test_cache_key_projection.py` for the new `reads` of every stage,
  including `data`. Add the re-run table of `data-model.md`, *Stages*, as cases (FR-031):
  - changing `outputs[0].accuracy_drop_max` leaves the keys of `data`, `build` and `train`
    unchanged and changes `quantize`'s;
  - changing `export.targets` leaves `data`, `build`, `train` and `quantize` unchanged;
  - changing `model.name` changes only `export`'s.
- [X] T026 [P] Update `tests/fixtures/models/make.py` to build its models through `rewire` with the
  names `frames` and `attack`, regenerate the committed `example-float.tflite` and
  `example-int8.tflite`, and keep `tests/train/test_fixture_models.py` asserting that regeneration
  is byte-identical.
- [X] T027 Adapt every existing test that reads a removed field or an old stage `reads` path, to the
  new form or to the migrated fixture, without weakening an assertion. The files to cover are
  those `grep -rln "dataset.labels\|dataset.window\|accuracy_drop_max\|topic\|permitted_use\|compliance" tests`
  lists: `tests/train/*`, `tests/contract/*`, `tests/integration/test_render.py`,
  `tests/unit/test_schema_requirements.py`, `tests/unit/test_errors.py` and the rest.

**Checkpoint**: `uv run pytest` is green. `caravan export` succeeds on both `picket-mlp-fixture.yaml`
(migrated) and `picket-mlp-v01.yaml`.

---

## Phase 3: User Story 1 — A manifest that asks only for what Caravan uses (Priority: P1) 🎯 MVP

**Goal**: an author writes no field that no stage reads. An old manifest still loads and says what
changed.

**Independent Test**: quickstart §1–§3. The new pilot validates with no removed field. The old pilot
validates with six `dropped` and three `moved` notices and an unchanged file. A removed field in the
new form is refused at its path with its own message.

### Tests for User Story 1

- [ ] T028 [P] [US1] Write `tests/integration/test_validate_migrated.py` (SC-002): every manifest in
  `tests/fixtures/manifests/valid/` and `tests/fixtures/manifests/migration/` loads, and each
  produces exactly the notices of its `*.notices.json`, or none for new-form files. No file changes
  on disk.
- [ ] T029 [P] [US1] Extend `tests/contract/test_cli_contract.py`:
  - `caravan validate` on an old-form manifest exits 0, prints "valid (migrated from caravan/v0 to
    caravan/v0.1)" and then the notices;
  - `--json` carries `migration_notices` as `path`, `action`, `to` and `reason`;
  - a removed field in a `caravan/v0.1` manifest exits 1 with the `REMOVED_FIELDS` message at its
    path;
  - `caravan render` writes notices to stderr only, so its stdout parses as YAML.
- [ ] T030 [P] [US1] Write `tests/contract/test_no_compliance_in_outputs.py` (SC-006): after
  `caravan export` on the migrated pilot fixture, no file in the run directory contains the keys
  `compliance`, `eu_ai_act_class`, `privacy`, `intended_use`, `known_limits`, `license` or
  `permitted_use`, nor the words "licence checked", "license verified" or "permitted".
- [ ] T031 [P] [US1] Write `tests/unit/test_every_field_is_read.py`:
  - every leaf path of the resolved `picket-mlp-v01.yaml` is in some `StageSpec.reads`, or is one
    of the two fields the constitution settles, each with its reason in a comment: `apiVersion`
    (Principle IX) and `dataset.source` (the data every `reads_dataset` stage reads);
  - SC-001: the new pilot has at most 34 non-blank, non-comment lines, against 43 in the old.

### Implementation for User Story 1

- [ ] T032 [US1] Print notices in `src/caravan/cli/validate.py`: after the verdict, one indented
  line each, as `dropped <path> — <reason>` or `moved <path> → <to>`. In the JSON document, add
  `migration_notices`.
- [ ] T033 [US1] In `src/caravan/cli/render.py`, send notices to stderr and the YAML to its usual
  destination unchanged.
- [ ] T034 [US1] In `src/caravan/run/report.py`, add `manifest.migration_notices`, and fill it in
  `src/caravan/cli/pipeline.py`, on both the success path and the failure path.
- [ ] T035 [US1] Remove what is left of the compliance layer from `src/`: references in
  `src/caravan/env.py`, `src/caravan/convert/__init__.py`, `src/caravan/manifest/_yaml.py`,
  `src/caravan/stages/cache.py` and `src/caravan/stages/base.py` docstrings, and anywhere else that
  `grep -rn "compliance\|permitted_use\|Principle VI" src` lists. No text may claim that a licence
  is checked or that data is permitted.
- [ ] T036 [P] [US1] Write `docs/migrations/caravan-v0.1.md`, the migration note Principle IX
  requires. It gives:
  - every affected field with the change required, from `REMOVED_FIELDS`;
  - the pilot before and after;
  - the one-time cache invalidation (research R9);
  - the label-order caveat of SC-003: derived labels sort, so pin them to keep an old order.
- [ ] T037 [P] [US1] Update `README.md`:
  - the manifest example becomes the new pilot;
  - remove the compliance block and its paragraph;
  - remove "model card" and "publication" from the stage list, which becomes the constitution 3.0.0
    preamble's;
  - link the migration note.

**Checkpoint**: US1 is independently demonstrable with no extra installed (quickstart §1–§3).

---

## Phase 4: User Story 2 — Declare what goes in and what comes out (Priority: P1)

**Goal**: an input and an output are declared. Labels and columns come from the data unless pinned.

**Independent Test**: quickstart §2 and §4, and §7 for SC-003. The new pilot trains with
`labels: [dos, fuzzy, normal, replay]` in its run's `resolved.yaml`, with the same windows and split
counts as the migrated pilot.

### Tests for User Story 2

- [ ] T038 [P] [US2] Write `tests/integration/test_render_derived.py`: `render` of the new pilot
  shows `columns: derived` and `labels: derived`. A run's `resolved.yaml` for the same file differs
  from `render`'s output in exactly those two values (FR-013).
- [ ] T039 [P] [US2] Write `tests/train/test_declared_io_end_to_end.py`:
  - `caravan train` on `picket-mlp-v01.yaml` succeeds, with `data/schema.json` and `resolved.yaml`
    holding the derived values;
  - `windows_kept`, `windows_discarded_mixed`, `records_dropped_remainder` and the split counts
    equal those of the migrated `picket-mlp-fixture.yaml` run;
  - the same holds for `picket-conv1d-v01.yaml` against `picket-conv1d-fixture.yaml`.
- [ ] T040 [P] [US2] Write `tests/train/test_migration_same_model.py` (SC-003): the migrated
  `picket-mlp-fixture.yaml`, and a new-form copy pinning `labels: [normal, dos, fuzzy, replay]` and
  naming the input `input` and the output `output`, train under the same seed to byte-identical
  weights (`get_weights()` compared array for array).
- [ ] T041 [P] [US2] Write `tests/unit/test_rules_coverage_v01.py`: CF-9, CF-10, CF-11, DS-11,
  DS-12, F-1 and X-6 are each raised somewhere in `src/` and each has a message naming what to do.
  This is the same shape as `tests/unit/test_run_rules_coverage.py`.

### Implementation for User Story 2

- [ ] T042 [US2] In `src/caravan/cli/pipeline.py`, print the derived labels and the number of input
  columns in the success summary of `train` and `export`, and the derived values in `--json`
  output, so an author sees the order without opening a file.
- [ ] T043 [US2] Run quickstart §2 and §4 (to the end of the `data/schema.json` and `resolved.yaml`
  checks), and record any deviation as a fix here before moving on.

**Checkpoint**: US1 and US2 together are the MVP: the new manifest form, end to end.

---

## Phase 5: User Story 3 — Learn before training that a model cannot fit (Priority: P2)

**Goal**: lower bounds against every target board, before training, failing only when a floor
exceeds a board.

**Independent Test**: quickstart §6 and §8. The pilot's `model/fit.json` shows `estimated` figures.
The too-big fixture fails F-1 with no trained model. A board change reruns only `fit` and `export`.

### Tests for User Story 3

- [ ] T044 [P] [US3] Write `tests/unit/test_fit_floors.py` first, on hand-built `LayerRecord`s:
  - kernel and bias byte sizes per quantization (int8 1/4, float16 2/2, none 4/4);
  - activation size per quantization (int8 1, float16 4, none 4);
  - excluded kinds (flatten, reshape, dropout, normalisation, activation) never contribute;
  - the RAM floor is the largest input + output over counted layers, naming the layer;
  - verdicts `below` / `exceeds` with the shortfall;
  - F-1 lists every failing board and resource;
  - a board without a figure fails rather than passes.
- [ ] T045 [P] [US3] Write `tests/train/test_fit_stage.py`:
  - the pilot writes `model/fit.json` with `provenance: estimated`, two floors, and `below` for
    every board and resource;
  - `tests/fixtures/manifests/gate/too-big-for-s32k144.yaml` exits 1 with F-1 naming `s32k144`
    flash, with no `model/trained.keras` and no `training-history.json` in the run;
  - removing `esp32` from the targets of a copy reuses `data`, `build` and `train`, and reruns `fit`.
- [ ] T046 [P] [US3] Write `tests/train/test_fit_floor_ordering.py`: for `picket-mlp-v01.yaml` and
  `picket-conv1d-v01.yaml`, the RAM floor in `model/fit.json` is at most `working_memory.floor_bytes`
  in `export.json` (feature 004).
- [ ] T047 [P] [US3] Write `tests/fixtures/manifests/gate/too-big-for-s32k144.yaml`: the new pilot
  with `params.hidden: [2048, 256]` and `export.targets: [s32k144]`. The first kernel alone is
  320 × 2048 = 655,360 bytes at int8, above the board's 524,288. Add a comment with that arithmetic.

### Implementation for User Story 3

- [ ] T048 [US3] Create `src/caravan/targets/fit.py` (core, no framework import):
  - `LayerRecord(kind, name, kernel_elements, bias_elements, input_elements, output_elements)`;
  - `COUNTED_KINDS`;
  - `floors(records, quantization) -> (FitFloor, FitFloor)`;
  - `verdicts(floors, boards) -> list[FitVerdict]`, with `board_source` taken from the board
    description's recorded source for `ram_kb` / `flash_kb`;
  - the method sentences and `NOT_A_FIT_CLAIM` from `contracts/fit-check.md`.
- [ ] T049 [US3] Create `src/caravan/stages/fit.py`:
  - `SPEC = StageSpec(name="fit", upstream="build", reads=("export.targets",
    "export.quantization"), reads_dataset=False, artifacts=("model/fit.json",))`;
  - read `model/built.keras` and map Keras layers to `LayerRecord`s: Dense, Conv1D, Conv2D,
    MaxPooling1D/2D, AveragePooling1D/2D, GlobalAveragePooling1D/2D and GlobalMaxPooling1D/2D are
    counted, everything else gets kind `excluded`; element counts at batch 1;
  - raise F-1 per `contracts/fit-check.md`, with the failing verdicts in `found`;
  - on a pass, write `model/fit.json`.
- [ ] T050 [US3] In `src/caravan/cli/pipeline.py` and the four verb modules, insert `fit` after
  `build`; `train` keeps `upstream="build"`. Add a `fit` section to the run report from
  `model/fit.json`, and print F-1 in the form of `contracts/fit-check.md`.
- [ ] T051 [US3] Extend `tests/contract/test_no_skip_option.py` so it covers the `fit` stage: no flag,
  environment variable or manifest field skips or relaxes it.

**Checkpoint**: quickstart §6 and §8 pass. The pilot's numbers fill the "to be measured" fit figures
in `quickstart.md`.

---

## Phase 6: User Story 4 — Everything a firmware author needs to feed the model (Priority: P2)

**Goal**: `model/interface.json` and the C additions, read from the converted file. The skeleton
binds by name.

**Independent Test**: quickstart §4 (the interface parts) and §5: a test that reads only the
contract and the header reproduces Caravan's predictions.

### Tests for User Story 4

- [ ] T052 [P] [US4] Write `tests/unit/test_interface_emit.py` first:
  - `interface.json` has sorted keys, two-space indentation, a trailing newline, `contract_version`
    1, `model: {name, version}`, `scaling: "none"`, `stride == window`, and `null` scale and zero
    point for float tensors;
  - the header constants are `g_model_data_model_name`, `g_model_data_model_version`,
    `g_model_data_input_<name>`, `g_model_data_output_<name>`, `…_label_count` and `…_labels`;
  - label escaping turns `a"b\c` and `aä` into `"a\x22" "b\x5c" "c"` and `"a\xc3" "\xa4"`;
  - two emissions are byte-identical;
  - the existing `tests/unit/test_c_array_compiles.py` still compiles the header with the additions.
- [ ] T053 [P] [US4] Write `tests/verify/test_interface_positions.py`: on the regenerated
  `tests/fixtures/models/example-int8.tflite`, `frames` and `attack` resolve to positions read from
  the signature, with shape, `int8`, scale and zero point equal to the tensor's in the file.
- [ ] T054 [P] [US4] Write `tests/train/test_interface_reordered_outputs.py`: convert a functional
  model with a dict of two outputs through `caravan.convert.tflite.convert`, and assert that the
  binding reader maps each name to the position the subgraph actually uses. This is the research R4
  reversal, kept as a test, because it is the case the whole contract exists for.
- [ ] T055 [P] [US4] Write `tests/verify/test_interface_contract_alone.py` (SC-005). It reads only
  `model/interface.json` and `model/model_data.h` from an export of the new pilot. For every test
  window of the fixture it builds the int8 input from the raw records, using `columns`, `window`,
  `scale` and `zero_point`, runs `model/model.tflite` in the desktop runtime at the contract's
  `position`, and maps the arg-max to a label from the header. The predictions must equal those in
  Caravan's quantized evaluation.
- [ ] T056 [P] [US4] Extend `tests/unit/test_skeleton.py`: no generated `main.cc` contains
  `input(0)` or `output(0)`; each uses the named constants.

### Implementation for User Story 4

- [ ] T057 [US4] In `src/caravan/runtime/flatbuffer.py` (`verify`), add `TensorBinding` and
  `read_bindings(path, names)`. For each declared name, take the SignatureDef tensor index, its
  position in subgraph 0's input or output list, the tensor name, the shape, the element type (from
  the schema's type table) and the scale and zero point (first quantization entry, or `None`). Raise
  X-6 for a declared name absent from the signature.
- [ ] T058 [US4] Create `src/caravan/export/interface.py` (core):
  - `interface_document(model, bindings, inputs, outputs) -> str`, per `contracts/interface.md`,
    where `model` is the name and version;
  - `c_label_literal(label) -> str` with the escaping rule;
  - `header_additions(array_name, model, bindings, outputs) -> str` and
    `source_additions(array_name, outputs) -> str`.
- [ ] T059 [US4] In `src/caravan/export/c_array.py`, `header()` and `source()` take optional
  additions text, placed before the include guard's end and after the array respectively. The
  default is empty, so feature 004's outputs and tests are unchanged without it.
- [ ] T060 [US4] In `src/caravan/export/skeleton.py`, `input(...)` and `output(...)` use the
  constants from the header; the input and output names are passed in.
- [ ] T061 [US4] In `src/caravan/stages/export.py`:
  - read the bindings;
  - write `model/interface.json` and the C additions, and pass the names to the skeleton;
  - add `model/interface.json` to `artifacts`, listed in `export.json` with size and digest.

  Add an `interface` section to the run report in `src/caravan/run/report.py` and
  `src/caravan/cli/pipeline.py`.

**Checkpoint**: quickstart §4 and §5 pass. Two exports of one quantized model give byte-identical
`interface.json`, `model_data.h` and `model_data.cc`.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T062 [P] Extend `tests/layering/test_no_framework_imported.py` and
  `tests/layering/test_hostile_import.py` to cover the new core modules: `manifest/schema/io.py`,
  `manifest/schema/removed.py`, `manifest/migrate.py`, `targets/fit.py` and `export/interface.py`.
- [ ] T063 [P] Update `docs/design/2026-10-23-owner-decisions.md`:
  - the status line: constitution amended to 3.0.0; D1, D2, D4 (as the declaration form) and R1,
    R2 implemented by feature 006;
  - P5 partly implemented: the interface contract, without input scaling.
- [ ] T064 Run every quickstart scenario §1–§8 in order. Fill in the figures marked *to be
  measured* in `specs/006-declared-io/quickstart.md` from the actual run, never from expectation.
- [ ] T065 Run `uv run ruff check src tests`, `uv run ruff format src tests` and `uv run pytest`,
  all green, and confirm that the install budget test still holds (no dependency was added).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: needs Phase 1, and blocks every story.
- **US1 (Phase 3)** and **US2 (Phase 4)**: need Phase 2. They are independent of each other and can
  run in parallel.
- **US3 (Phase 5)**: needs Phase 2 (the `build` stage reads the declarations). It is independent of
  US1, US2 and US4.
- **US4 (Phase 6)**: needs Phase 2 (names in the converted model, T020, T026). It is independent of
  US3.
- **Polish (Phase 7)**: after the stories it touches.

### Within each phase

- Tests come before their implementation: T005→T006, T007→T008, T012→T013, T016→T017/T018,
  T019→T020, T044→T048, T052→T058, T053/T054→T057.
- `schema/io.py` and the `Manifest` rework (T006, T010) come before the loader (T011), the resolver
  (T013) and the fixtures (T014).
- The indexed projection (T015) comes before every stage that reads a declaration field (T018,
  T020–T023).
- `reader.py` (T017) comes before the `data` stage (T018); the `data` stage before the pipeline
  (T024).
- T020 (`rewire`) comes before T026 (fixture models) and before every US4 verify test.

### Parallel opportunities

- Setup: T002, T003 and T004 together, after T001.
- Foundational: T025 and T026 together once T020 and T024 are done.
- US1: T028, T029, T030, T031, T036 and T037 together.
- US2: T038, T039, T040 and T041 together.
- US3: T044, T045, T046 and T047 together.
- US4: T052, T053, T054, T055 and T056 together.
- After Phase 2, the stories can proceed on separate branches: US1+US2, US3 and US4.

## Parallel Example: User Story 4

```bash
# Tests first, together:
T052 tests/unit/test_interface_emit.py
T053 tests/verify/test_interface_positions.py
T054 tests/train/test_interface_reordered_outputs.py
T055 tests/verify/test_interface_contract_alone.py
T056 tests/unit/test_skeleton.py
# Then the reader (T057) and the emitters (T058, T059, T060) in parallel; T061 wires them.
```

## Implementation Strategy

### MVP first

1. Phase 1 and Phase 2: the pipeline on `caravan/v0.1`, with the pilot green through migration.
2. Phase 3 (US1) and Phase 4 (US2): the new manifest form, with notices and derived labels. **Stop
   and validate**: quickstart §1–§4 and §7.
3. Phase 5 (US3): the fit check.
4. Phase 6 (US4): the interface contract.
5. Phase 7.

### Notes

- A [P] task touches no file another unfinished task touches.
- Commit after each task or each test-and-implementation pair.
- Numbers in documents come from runs, never from expectation (quickstart, T064).
- A failing test is fixed in the code, never skipped (constitution, Development Workflow).
