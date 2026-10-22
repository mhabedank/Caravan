---

description: "Task list for feature 001: manifest schema and package skeleton"
---

# Tasks: Manifest Schema and Package Skeleton

**Input**: Design documents from `/specs/001-manifest-schema/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: included. The specification requires them explicitly — FR-026 ("an automated check MUST
fail the build"), FR-027 ("checked automatically"), SC-002 (a library of broken manifests) and
SC-008 (demonstrated on a clean environment). They are not optional here.

**Organization**: grouped by user story, so each story can be implemented, tested and demonstrated
on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task serves (US1–US4)
- Exact file paths in every description

## Path Conventions

Single Python package: `src/caravan/`, `tests/` at the repository root, per the structure decision
in [plan.md](./plan.md).

**One refinement of the plan's tree**: `manifest/schema.py` becomes a package,
`src/caravan/manifest/schema/`, split by manifest section. The schema is the largest single piece
of this feature; splitting it by section lets six tasks run in parallel instead of one task
blocking the story, and keeps each file small enough to read in one go. Nothing else about the
structure changes.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: a package that installs, with the identity and the budgets the constitution fixes

- [X] T001 Create `pyproject.toml`: distribution name `caravan-ml`, command `caravan`, `requires-python = ">=3.14"` (research R4), build backend `hatchling`, `src` layout, Apache-2.0 declared in metadata, runtime dependencies exactly `pydantic` and `ruamel.yaml` with **no upper version bounds** (Principle XII, FR-031)
- [X] T002 [P] Add the full Apache-2.0 licence text as `LICENSE` and a `NOTICE` file naming the project and copyright holder (FR-030)
- [X] T003 [P] Add `.gitignore` covering Python build and cache artifacts, `.venv/`, `dist/`, and `runs/` — run directories are artifacts, never committed
- [X] T004 [P] Add a `dev` dependency group in `pyproject.toml` with `pytest` and `ruff` only, and configure both there: `testpaths`, strict markers, and a line length of 100 to match the documents
- [X] T005 Create the package and test directory skeleton per [plan.md](./plan.md) — `src/caravan/{cli,manifest,templates,targets,run}/` and `tests/{unit,contract,integration,layering,fixtures}/` — with `src/caravan/__init__.py` containing the version string and nothing else, so importing the package stays free of side effects
- [X] T006 [P] Create `uv.lock` at the repository root by locking the project, matching the sibling project's setup (research R14)
- [X] T007 Add `.github/workflows/ci.yml` running lint and the unit, contract and integration suites on Python 3.14 and 3.15 — the two versions the Python policy covers, no more

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the primitives every story needs — reading YAML, reporting a finding, writing a run, and the command line's own contract

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [X] T008 Implement `src/caravan/manifest/_yaml.py` as the **only** module that imports `ruamel.yaml` (research R2): safe mode, returns plain Python structures, and reports an empty file, invalid YAML, or a document that is not a mapping each as what it is, naming the file and the position
- [X] T009 [P] Implement `src/caravan/manifest/errors.py`: the `Finding` type carrying `path`, `problem`, `found`, `accepted` and `rule`; the rule identifier constants from [data-model.md](./data-model.md), in two groups that must stay distinguishable in code: **rejection rules**, which refuse a manifest (`V-1`, `T-1`, `T-2`, `B-1`, `CF-1`…`CF-7`), and **non-rejection identifiers**, which never do (`V-2` accepts a manifest without a version, `D-1` records an unresolved reference, `E-1` and `S-1` govern board files rather than manifests). The distinction is what T019 and T061 check against; and the renderer producing the three-part text form of [contracts/cli.md](./contracts/cli.md) — field path first, then what was wrong, then what is accepted, with a nearest-name suggestion at small edit distance, and never a pydantic type name, module path or traceback
- [X] T010 [P] Implement `src/caravan/run/paths.py`: the run directory `runs/<UTC basic ISO timestamp>-<first 8 hex of the manifest SHA-256>/`, created fresh; an existing directory makes the run **fail rather than overwrite**; `--runs-dir` relocates the parent and may not point inside an existing run directory ([contracts/run-report.md](./contracts/run-report.md))
- [X] T011 Implement `src/caravan/run/report.py` writing `report.json` with exactly the field set of [contracts/run-report.md](./contracts/run-report.md): `dataset` and `template` as provenance fields in their own right, because Principle III names both in the record every artifact must carry and a reader must not have to parse a gate's `detail` string for them; `schema_version_declared` and `schema_version_effective` both always present even when equal (FR-010), `migrations_applied` as an ordered list, `outcome` one of `valid`, `invalid`, `error`, `gates` listing only the groups actually reached, `unresolved`, `artifacts` as paths relative to the run directory, and `seed`
- [X] T012 Implement `src/caravan/manifest/migrate.py` as an **instance-based** registry, not a module-level singleton (research R6): schema version identifiers with the transform that brings each up to the next, `caravan/v0` registered with no transform, rule V-1 refusing an unknown declared version while naming the implemented ones, and rule V-2 treating an absent `apiVersion` as the oldest known version
- [X] T013 Implement `src/caravan/cli/main.py`: `argparse` subcommands (research R1), the exit-code policy 0 valid / 1 rule said no / 2 usage / 3 internal defect, the stream policy from [contracts/cli.md](./contracts/cli.md) (answers on standard output, messages for people on standard error), and the global `--version`, `-q/--quiet` and `--json` options
- [X] T014 [P] Add `tests/contract/test_cli_contract.py` asserting the exit-code policy and the stream separation, including that `--quiet` leaves standard error empty on success and that `--json` puts nothing but the JSON document on standard output
- [X] T015 [P] Add `tests/contract/test_no_network.py` making socket creation raise for the duration and asserting every command still behaves as specified (quickstart scenario 9, Principle VIII)

**Checkpoint**: the package installs, the command runs, a finding can be reported and a run can be recorded

---

## Phase 3: User Story 1 — Check a manifest before anything expensive runs (Priority: P1) 🎯 MVP

**Goal**: an author gets a verdict on a manifest, and every rejection names the field, what was wrong and what is accepted.

**Independent Test**: the pilot manifest validates; every manifest in the invalid fixture library is rejected for its own rule; the listings the error messages promise exist.

### Tests for User Story 1

> Write these first. The fixtures *are* the acceptance criteria of SC-002 and SC-004, so they come before the schema they test.

- [X] T016 [P] [US1] Add `tests/fixtures/manifests/valid/picket-mlp.yaml`, the pilot manifest exactly as given in [contracts/manifest-v0.md](./contracts/manifest-v0.md) — including `split` as named parts, `formats: [flatbuffer, c_array]`, `verify.emulator: none` and `representative_samples: 500`
- [X] T017 [P] [US1] Add `tests/fixtures/manifests/valid/pilot-min.yaml`, the minimal manifest from the same contract, which must validate with everything optional left out
- [X] T018 [P] [US1] Add the invalid fixture library under `tests/fixtures/manifests/invalid/`, one file per **rejection rule** (T009), named `<rule>-<slug>.yaml` with a sibling `<rule>-<slug>.expected.json` holding the expected `path`, `problem`, `accepted` and `rule` — covering V-1, T-1, T-2, B-1 and CF-1 through CF-8 — the CF-8 fixture being `cf-8-benchmark-only-publish.yaml`, whose author marked the dataset `benchmark-only` while also declaring publication. Two further fixtures cover errors that are not rule-numbered and therefore use a bare slug: `unknown-field.yaml` and `unknown-field-misplaced.yaml`. **No V-2 fixture here** — V-2 accepts a manifest that declares no version, so its fixture is a valid one (T047)
- [X] T019 [US1] Add `tests/unit/test_fixture_coverage.py` failing if any **rejection rule** declared in `src/caravan/manifest/errors.py` has no invalid fixture, and failing if a non-rejection identifier has one — this is what keeps SC-002 true as rules are added, rather than true only today. The non-rejection identifiers are covered instead by T047 (V-2) and T061 (E-1, S-1); D-1 is asserted by T020, which checks that the dataset reference is reported as unresolved
- [X] T020 [P] [US1] Add `tests/integration/test_validate.py` covering quickstart scenarios 1 and 2: the pilot manifest exits 0 with `"outcome": "valid"`, the report carrying `dataset` and `template` as provenance and the dataset reference listed under `unresolved` (rule D-1); every invalid fixture exits 1 with the expected rule in `findings[0].rule`; and the same manifest with CRLF line endings, a trailing newline difference and a non-UTF-8 locale set produces the identical verdict and the identical findings (spec edge case)
- [X] T021 [P] [US1] Add `tests/unit/test_errors.py` asserting the message form of [contracts/cli.md](./contracts/cli.md): the field path immediately after the file name, the accepted list for an unknown field, the did-you-mean suggestion, both locations for a misplaced field, every related field named for a cross-field rule, the **stated form** quoted back when a `model.name` or `model.version` is rejected (FR-019), and no pydantic type, module path or traceback anywhere

### Implementation for User Story 1

- [X] T022 [P] [US1] Implement `src/caravan/manifest/schema/model.py`: `name` lower-case letters, digits and hyphens starting alphanumeric and at least 3 characters; `version` three dot-separated non-negative integers; `topic` and `task` non-empty strings; `template` a template identifier; `params` a template-defined object. `extra="forbid"`
- [X] T023 [P] [US1] Implement `src/caravan/manifest/schema/dataset.py`: `source` required non-empty; `split` as the named-part object with defaults 0.7 / 0.15 / 0.15 and `stratified` default true; `window` optional integer greater than zero when present; `labels` at least 2, unique, each non-empty; `representative_samples` optional integer; `license` optional free-text string; `permitted_use` one of `training`, `benchmark-only`, `unknown` with default `unknown` (FR-032). **Never a positional list for `split`** (FR-018). `extra="forbid"`
- [X] T024 [P] [US1] Implement `src/caravan/manifest/schema/train.py` with the defaults of [data-model.md](./data-model.md): `epochs` 50 greater than zero, `batch` 256 greater than zero, `optimizer` one of `adam`/`sgd`/`adamw` default `adam`, `learning_rate` 0.001 greater than zero, `early_stopping` true, `patience` 5 zero or more, `seed` 42. `extra="forbid"`
- [X] T025 [P] [US1] Implement `src/caravan/manifest/schema/export.py`: `quantization` one of `int8`/`float16`/`none` default `int8`; `formats` from `flatbuffer`/`c_array`/`onnx` default `[flatbuffer, c_array]`, non-empty and unique — **not `tflite` or `model_cc`** (research R8); `targets` at least one board identifier, unique; `accuracy_drop_max` between 0 and 1 inclusive, default 0.02. `extra="forbid"`
- [X] T026 [P] [US1] Implement `src/caravan/manifest/schema/compliance.py`: `eu_ai_act_class` one of `minimal-risk`/`limited-risk`/`high-risk`; `privacy` one of `no-personal-data`/`anonymized`/`personal-data`; `intended_use` at least 20 characters and not whitespace only; `known_limits` at least one entry, each non-empty. All four required (FR-015). `extra="forbid"`
- [X] T027 [P] [US1] Implement `src/caravan/manifest/schema/misc.py`: `VerifySpec` with `emulator` one of `renode`/`none` **default `none`** (see [data-model.md](./data-model.md) for why the design document's `renode` default was not kept); `BenchSpec` with `metrics` from `latency_p50`/`latency_p99`/`ram_peak`/`flash` default `[latency_p50, ram_peak, flash]`, non-empty and unique; `PublishSpec` with `hf_repo` non-empty in `owner/name` shape and `license` one of `apache-2.0`/`mit`/`cc-by-4.0` default `apache-2.0`. `extra="forbid"`
- [X] T028 [US1] Implement `src/caravan/manifest/schema/__init__.py`: the `Manifest` root with `apiVersion`, `model`, `dataset`, `export` and `compliance` required and `train`, `verify`, `bench`, `publish` optional, plus cross-field rules CF-1 through CF-8 verbatim from [data-model.md](./data-model.md) — split parts summing to 1 within 1e-6 with every part strictly greater than zero, no duplicate targets, `personal-data` incompatible with `minimal-risk`, int8 requiring `representative_samples` of at least 100, `publish` requiring every compliance field non-empty, the template's `consumes_window` deciding whether `window` must be present or absent, `verify.emulator: renode` rejected when any target board states no emulator platform, and `publish` rejected together with a dataset the author marked `benchmark-only` (CF-8). No `defaults` key accepted at any level (FR-014). Depends on T022–T027
- [X] T029 [P] [US1] Implement `src/caravan/templates/registry.py`: the `TemplateParameterSpec` with `identifier`, `parameters`, `consumes_window` and `summary`, and a registry populated by the modules of the package and extensible from outside it without editing a central list (FR-021). **Parameter half only — no training framework** (research R7)
- [X] T030 [P] [US1] Implement `src/caravan/templates/mlp.py`: identifier `mlp`, parameters `hidden` (list of integers, at least one entry, each greater than zero) and `dropout` (number from 0 up to but excluding 1, default 0.0), `consumes_window` true, and a one-line summary. The only template registered in this feature (Principle X)
- [X] T031 [P] [US1] Implement `src/caravan/targets/schema.py`: the board description model per [data-model.md](./data-model.md), with `emulator` **required and nullable** so that "no emulator" is stated rather than omitted (rule E-1), the `toolchain` block (`compiler`, `optimization`, `runtime`) that Principle VII requires even though no stage here reads it, and `sources` required to carry an entry for each of `clock_mhz`, `ram_kb`, `flash_kb`, `accel`, `toolchain` and `emulator` (rule S-1)
- [X] T032 [US1] Implement `src/caravan/targets/registry.py` loading and listing board descriptions from package data, validating each against the model, and asserting that `board` equals the file stem. Depends on T031
- [X] T033 [P] [US1] Add `src/caravan/targets/boards/stm32h743.yaml` exactly as in [contracts/manifest-v0.md](./contracts/manifest-v0.md), with the Renode platform `stm32h743`, the `toolchain` block, and a source for every value including the toolchain's citation that it is a project decision rather than a vendor default
- [X] T034 [P] [US1] Add `src/caravan/targets/boards/s32k144.yaml` with `emulator: null`, the `toolchain` block, and the source recording the evidence and the date: Renode models `nxp-s32k388`, `nxp-s32k388evb` and `s32k118`, not the S32K144 (research R13)
- [X] T035 [P] [US1] Add `src/caravan/targets/boards/esp32.yaml` with `accel: esp-nn`, `emulator: null`, a `toolchain` block naming the Xtensa cross compiler, and the source recording that Renode has no ESP32 platform
- [X] T036 [US1] Implement `src/caravan/manifest/load.py` as the one entry point for the load sequence of [data-model.md](./data-model.md): read, version check, migrate, schema validation collecting **all** field errors of one pass before reporting, template resolution and parameter validation, board resolution, then the cross-field rules. The author's file is never written (FR-006). Depends on T008, T012, T028, T029, T032
- [X] T037 [US1] Implement `src/caravan/cli/validate.py`: the `validate` command with `--runs-dir`, `--no-report`, `--json` and `--quiet`, recording the dataset reference as unresolved with its reason (rule D-1) so a valid manifest is never mistaken for a resolved dataset, and recording the dataset's terms as unverified whenever `permitted_use` is `unknown` so that silence about a licence is visible as silence (FR-032). Depends on T011, T036
- [X] T038 [P] [US1] Implement `src/caravan/cli/listing.py`: `caravan templates` and `caravan boards`, each one identifier per line with its summary, reading from the same registries the error messages cite — a test asserts the two agree (quickstart scenario 8)
- [X] T039 [US1] Wire `validate`, `templates` and `boards` into `src/caravan/cli/main.py` and confirm the whole invalid fixture library produces its expected rule. Depends on T013, T037, T038

### Added after the consistency analysis (US1)

> These four tasks close gaps the cross-artifact analysis of 2026-10-22 found. Their numbers follow
> the existing ones rather than renumbering sixty tasks; their position in the phase is their
> position in the order.

- [X] T061 [P] [US1] Add `tests/fixtures/boards/` with one invalid board description per board-file rule — `e-1-emulator-omitted.yaml` (the field missing rather than `null`), `e-1-platform-that-does-not-exist.yaml`, `s-1-source-missing.yaml` (a value with no citation) — and `tests/unit/test_board_schema.py` asserting each is rejected with its rule, plus that the three shipped board files all validate. Rules E-1 and S-1 govern board files, not manifests, so they cannot appear in the manifest fixture library (T018) and would otherwise go untested (FR-024, FR-025)
- [X] T062 [P] [US1] Add `tests/contract/test_no_skip_option.py` asserting that no subcommand exposes an option that skips, forces, ignores or downgrades a check — walk every registered parser's option strings and fail on `--force`, `--skip*`, `--ignore*`, `--no-validate` and the like. FR-005 is the executable form of Principle V, and an absent flag is exactly what gets added back by accident
- [X] T063 [US1] Add a timing assertion to `tests/integration/test_validate.py`: a verdict on the pilot manifest in under two seconds, with no network and no dataset present (SC-001). The plan states both performance goals are measured rather than estimated, so this is what makes that true. Depends on T020

**Checkpoint**: User Story 1 is complete — a manifest can be authored and checked, with actionable errors, and nothing heavier than two dependencies is installed

---

## Phase 4: User Story 2 — See exactly what the pipeline will use (Priority: P2)

**Goal**: the resolved manifest, with every default expanded, written as an artifact beside the run report.

**Independent Test**: resolving the minimal manifest yields a complete manifest with no implicit value; resolving twice is byte-identical; the input file is untouched.

### Tests for User Story 2

- [X] T040 [P] [US2] Add `tests/integration/test_render.py` covering quickstart scenario 3: every schema field present with a concrete value in the resolved output, and two runs byte-identical
- [X] T041 [P] [US2] Add `tests/contract/test_run_report.py` asserting the report shape of [contracts/run-report.md](./contracts/run-report.md) and the determinism rule of research R9 — two reports identical once `started_at` and the run directory name are removed
- [X] T042 [P] [US2] Add `tests/integration/test_input_untouched.py` covering quickstart scenario 4: the manifest's hash is unchanged after both `validate` and `render`

### Implementation for User Story 2

- [X] T043 [US2] Implement `src/caravan/manifest/resolve.py`: expand every default, expand `model.params` with the template's parameter defaults, set `apiVersion` to the effective version, fix key order by the schema rather than by input order, and emit no timestamp, absolute path or machine-specific value (research R9). Depends on T028, T029
- [X] T044 [US2] Implement `src/caravan/cli/render.py`: the `render` command writing `resolved-manifest.yaml` and `report.json` into a new run directory, plus `--stdout` which writes the resolved manifest to standard output, creates no run directory and produces output byte-identical to the file form. Depends on T010, T011, T043
- [X] T045 [US2] Wire `render` into `src/caravan/cli/main.py` and confirm `validate` and `render` agree on the same manifest — same findings, same unresolved references, same effective schema version. Depends on T039, T044

### Added after the consistency analysis (US2)

- [X] T064 [P] [US2] Add `tests/contract/test_run_directory.py` asserting the collision rule of [contracts/run-report.md](./contracts/run-report.md): a second run into an existing run directory fails rather than overwriting, nothing outside the run directory is created or removed, and `--runs-dir` pointing inside an existing run directory is refused

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 — An archived manifest keeps working (Priority: P3)

**Goal**: a manifest written against an older schema version loads, migrated in memory, with the file on disk untouched and both versions recorded.

**Independent Test**: a synthetic older version with one transform loads and is migrated; the file is byte-identical afterwards; an unknown version is refused with the implemented versions listed.

### Tests for User Story 3

- [X] T046 [P] [US3] Add `tests/unit/test_migration.py` building a registry that contains a synthetic older version with one transform (possible because the registry is an instance, not a singleton — research R6) and asserting: the manifest loads migrated, the file on disk is byte-identical afterwards, the report names both the declared and the effective version, and `migrations_applied` lists the transform
- [X] T047 [P] [US3] Add the fixture `tests/fixtures/manifests/valid/v-2-no-version.yaml` with its expected result: accepted as the oldest known version, with the report naming the effective version. The V-1 refusal fixture belongs to T018, because the unknown-version refusal is already reachable in User Story 1 through the Foundational version registry — keeping it there stops T019 from failing while User Story 3 is still unbuilt

### Implementation for User Story 3

- [X] T048 [US3] Extend `src/caravan/manifest/migrate.py` to apply a chain of transforms on a copy in order, never touching the input, and to record each applied transform for `migrations_applied` in the report. Depends on T012, T011
- [X] T049 [P] [US3] Write `docs/manifest-migrations.md`: how to add a schema version — register the version, write the transform, add a fixture declaring the old version, and write the migration note Principle IX requires. The procedure exists before it is first needed, which is the point of the mechanism

**Checkpoint**: the archival promise of Principle IX is executable, with nothing yet to migrate

---

## Phase 6: User Story 4 — Install the tool on a laptop in seconds (Priority: P3)

**Goal**: the default installation is small, fast and free of any training framework, and the build fails if that ever stops being true.

**Independent Test**: a clean environment with no machine-learning framework installs the default package within budget and runs the integration suite.

### Tests for User Story 4

- [X] T050 [P] [US4] Add `tests/layering/test_no_framework_imported.py`: after importing every core module, no training framework appears in the loaded module table (level 1 of research R11)
- [X] T051 [P] [US4] Add `tests/layering/test_hostile_import.py`: an import hook makes importing a training framework raise, and the end-to-end `validate` and `render` runs must still pass — this catches a lazy import inside a function, which level 1 cannot (level 2 of research R11)
- [X] T052 [P] [US4] Add `tests/layering/test_declared_dependencies.py` reading the built distribution's metadata and failing when the runtime dependency set exceeds six, **the optional extras exceed four**, the set contains a training framework, or any requirement carries an upper version bound without a documented incompatibility (FR-028, FR-031, level 4 of research R11). The extras limit binds before the first extra exists, which is the only time it is free

### Implementation for User Story 4

- [X] T053 [US4] Add a `clean-environment` job to `.github/workflows/ci.yml` installing only the built wheel into a fresh environment with no machine-learning framework present and running the integration suite there (level 3 of research R11, SC-008). Depends on T007, T045
- [X] T054 [US4] Add an `install-budget` job to `.github/workflows/ci.yml` measuring wall-clock time and total bytes downloaded for a cache-disabled install of the built wheel, failing over 30 seconds or 50 MB (FR-027, SC-003). It measures and fails; it does not warn (Principle V)
- [X] T055 [P] [US4] Write `docs/budgets.md` recording the dependency, install and Python-version budgets, where each is measured, and that the headroom between the expected ~4 MB and the 50 MB limit is reserved for the analysis feature rather than available for convenience

**Checkpoint**: all four user stories are independently functional, and the two budgets of Principle XII are measured rather than asserted

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T056 [P] Write `README.md`: what Caravan is, its scope boundary (embedded targets only), the install line for `caravan-ml`, and a short worked example taken from [quickstart.md](./quickstart.md)
- [X] T057 [P] Write `CONTRIBUTING.md` including the dependency gate as a checklist a contributor can self-apply before proposing one — what it replaces, why it cannot be owned in a few hundred lines, which extra it belongs to, whether the budget still holds, and whether it constrains the Python policy
- [X] T058 Run every scenario of [quickstart.md](./quickstart.md) on a clean environment and record the measured install time and size in `docs/budgets.md`, replacing the estimate with a measurement
- [X] T059 [P] Run `ruff` over `src/caravan/` and `tests/` and fix what it reports; confirm no file exceeds the line length configured in `pyproject.toml`
- [X] T060 Walk the 32 functional requirements of [spec.md](./spec.md) and confirm each is covered by a named test or carries an explicit note saying why not; record the mapping at the end of `specs/001-manifest-schema/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: needs Setup — **blocks every user story**
- **US1 (Phase 3)**: needs Foundational. No dependency on another story
- **US2 (Phase 4)**: needs Foundational; T045 touches the same file as T039, so it follows US1's wiring task; T064 needs only T010 and T044
- **US3 (Phase 5)**: needs Foundational only. Independent of US1 and US2
- **US4 (Phase 6)**: the three layering tests need Foundational only; the two CI jobs need a working end-to-end run, so T053 follows T045
- **Polish (Phase 7)**: needs the stories that are being shipped

### Within each user story

- Tests before implementation. For US1 the fixtures are the acceptance criteria themselves, so they are genuinely first
- Schema sections (T022–T027) before the root with its cross-field rules (T028)
- Registries (T029, T031, T032) before the load sequence (T036)
- Load sequence before the commands (T037, T044)
- Commands before their wiring into `main.py` (T039, T045) — one file, therefore never parallel

### Parallel Opportunities

- Setup: T002, T003, T004, T006 together
- Foundational: T009, T010 together; T014, T015 together
- US1 tests: T016, T017, T018, T020, T021, T061, T062 together
- US1 schema: T022–T027 all together — six files, no shared state
- US1 board files: T033, T034, T035 together
- US2 tests: T040, T041, T042 together
- US4 layering tests: T050, T051, T052 together
- Whole stories: US3 can be built alongside US1, since it touches only `migrate.py`, its own test and its own fixtures

---

## Parallel Example: User Story 1

```bash
# The fixtures and tests first, all at once:
Task: "Add tests/fixtures/manifests/valid/picket-mlp.yaml"
Task: "Add tests/fixtures/manifests/valid/pilot-min.yaml"
Task: "Add the invalid fixture library under tests/fixtures/manifests/invalid/"
Task: "Add tests/integration/test_validate.py"
Task: "Add tests/unit/test_errors.py"

# Then the six schema sections, all at once:
Task: "Implement src/caravan/manifest/schema/model.py"
Task: "Implement src/caravan/manifest/schema/dataset.py"
Task: "Implement src/caravan/manifest/schema/train.py"
Task: "Implement src/caravan/manifest/schema/export.py"
Task: "Implement src/caravan/manifest/schema/compliance.py"
Task: "Implement src/caravan/manifest/schema/misc.py"

# Then the board data, all at once:
Task: "Add src/caravan/targets/boards/stm32h743.yaml"
Task: "Add src/caravan/targets/boards/s32k144.yaml"
Task: "Add src/caravan/targets/boards/esp32.yaml"
```

---

## Implementation Strategy

### MVP: Setup + Foundational + User Story 1

T001 through T039, plus T061 to T063. That delivers a tool an author can actually use: write a manifest, get a verdict,
get an actionable message when it is wrong. It is also the point at which the feature's central
claim is testable — that checking a manifest needs no machine-learning framework at all.

**Stop and validate here.** Run quickstart scenarios 1, 2 and 8 before going further.

### Incremental delivery

1. Setup + Foundational → the command runs and can report
2. **US1 → the MVP.** Validate, with the fixture library and the listings
3. US2 → the resolved manifest and the run report, which makes runs comparable
4. US3 → the archival promise, provable before it is needed
5. US4 → the budgets enforced in continuous integration rather than in intent
6. Polish → README, contributing, the measured budget numbers, the requirement-coverage map

### If time is short

US3 and US4 are both P3 but they are not equal in risk. US4 should not slip: it is cheap, and
without it the layering rule is a document rather than a property — which is the exact failure the
constitution's Principle XII was written against. US3's mechanism must exist before the first
schema change, but that change is not in this feature, so T049's written procedure plus T046's test
is the minimum that keeps the promise honest.

---

## Notes

- 64 tasks: 7 setup, 8 foundational, 27 for US1, 7 for US2, 4 for US3, 6 for US4, 5 polish.
  T061 to T064 were added by the cross-artifact analysis of 2026-10-22; they carry the next free
  numbers rather than renumbering everything after them, so read the order from the position, not
  from the number
- Every schema task quotes its constraints verbatim from [data-model.md](./data-model.md), so no
  limit, enum or default is decided at implementation time
- Rule identifiers (`CF-1`, `B-1`, …) are carried into the code, the findings and the fixture file
  names, so a test asserts which rule fired rather than matching prose
- Three tasks are deliberately about absence: T051 proves the core works while a framework is
  *unimportable*, T062 proves no option exists to skip a check, and T034/T035 record that no
  emulator exists for two boards, with the evidence
- Commit after each task or logical group; stop at any checkpoint to validate a story on its own
