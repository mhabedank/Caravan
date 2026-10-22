---

description: "Task list for feature 004: Export"
---

# Tasks: Export

**Input**: Design documents from `/specs/004-export/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: requested. This project writes the test before the code it checks, and the suite is a
merge gate (constitution, Development Workflow). Test tasks are therefore not optional here.

## Format: `[ID] [P?] [Story] Description`

- **[P]** — may run in parallel with other [P] tasks: different files, no unfinished dependency
- **[US1]** … **[US5]** — the user story the task serves; setup, foundational and polish carry none

## Path Conventions

Single Python package. Source under `src/caravan/`, tests under `tests/`, feature documents under
`specs/004-export/`. Generated C-family output is written into the run directory, never into the
repository.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Add rule identifiers `X-1` … `X-5` with their one-line reasons and an `EXPORT_RULES`
  frozenset in `src/caravan/manifest/errors.py`, included in `ALL_RULES`
- [X] T002 Amend the constitution to v2.4.0 (MINOR) in `.specify/memory/constitution.md`:
  Principle VIII's export clause becomes "documents the runtime, the operator set and a computed
  floor on the working memory with its method named; the figure a target requires is documented by
  the stage that can measure it", with a Sync Impact Report carrying the rationale from
  `plan.md` and the two measured figures from `research.md`
- [X] T003 [P] Write the kernel coverage data file `src/caravan/targets/kernels/cmsis-nn.yaml` with
  the 11 mapped operators, the four unmapped source files, the source statement
  `tensorflow/lite/micro/kernels/cmsis_nn/ in tensorflow/tflite-micro` and `read_on: 2026-10-22`
- [X] T004 [P] Write `src/caravan/targets/kernels/esp-nn.yaml` the same way, from
  `tensorflow/lite/micro/kernels/esp_nn/ in espressif/esp-tflite-micro`, 7 source files
- [X] T005 [P] Write the resolver method table `src/caravan/export/methods.py`: builtin operator
  name → public resolver method, with the source `tensorflow/lite/micro/micro_mutable_op_resolver.h`
  and the date, covering at least every operator the implemented templates can emit plus the
  irregular names research R4 names (`AddConv2D`, `AddMaxPool2D`, `AddAveragePool2D`, `AddSvdf`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Everything in Phase 3 and later depends on this phase.**

- [X] T006 Write `tests/unit/test_working_memory_floor.py` first: the lifetime arithmetic on
  hand-built graphs — a chain where reuse is possible, a graph where two large tensors are live at
  once, a graph input live from the start, a graph output live to the end — asserting the peak and
  that the peak is never greater than the read-write sum
- [X] T007 Write `tests/verify/test_flatbuffer_reading.py` first: on the committed quantized
  fixture model, the operator records carry name, builtin code, version and node count; the
  subgraph count is 1; both memory figures are present and the floor is the smaller
- [X] T008 Implement `src/caravan/runtime/flatbuffer.py` (`verify` extra): `OperatorRecord`,
  `TensorLifetime`, `GraphInspection`, `inspect_graph(path)` reading through
  `ai_edge_litert.schema_py_generated`, with the tensor-type byte widths taken from the schema's own
  type table rather than hard-coded by name
- [X] T009 Implement the floor in the same module: first and last use per non-constant tensor,
  graph inputs live from `-1`, graph outputs live to the node count, the peak as `max` over nodes
- [X] T010 Write `tests/train/test_batch_fix.py` first: cloning a trained model onto a batch of one
  is faithful — predictions equal element by element, on an `mlp` and on a `conv1d` model — and the
  cloned model's input shape has a leading 1
- [X] T011 Implement `src/caravan/convert/batch.py` (`train` extra): `fix_batch(model)` via
  `keras.models.clone_model(model, input_tensors=Input(batch_shape=(1, *shape[1:])))` plus
  `set_weights`, refusing a model whose input shape is already fixed to something other than 1
- [X] T012 Write `tests/unit/test_export_rules_coverage.py` first: every identifier in
  `EXPORT_RULES` is raised somewhere in the stage and carries a message naming what to do, the same
  shape of test the `DS` and `Q` rules have
- [X] T013 Declare the stage in `src/caravan/stages/export.py`: `StageSpec(name="export",
  upstream="quantize", reads=("export.formats", "export.targets", "export.quantization"),
  reads_dataset=False, artifacts=(…))`, and extend the generic cache-key projection test of
  feature 002 with the new stage in one line

---

## Phase 3: User Story 1 — Get the set of artifacts a firmware author can use (Priority: P1) 🎯 MVP

**Goal**: one command turns a gated model into the deliverable files, or refuses by name.

**Independent Test**: run `caravan export` on the pilot fixture after `quantize`; the run directory
holds the model, the array, the header and the report, and the artifacts outlive the tool.

### Tests for User Story 1

- [X] T014 [P] [US1] `tests/unit/test_c_array.py`: the generated source round-trips to the model's
  exact bytes; the header declares the same length; `alignas(16)` is present; two generations of the
  same model are byte-identical; no timestamp, path or host name appears in either file
- [X] T014b [P] [US1] `tests/unit/test_c_array_compiles.py`: compile the generated `.cc` and `.h`
  with the host C++ compiler and assert it succeeds, skipping when no compiler is on the path. This
  is what turns SC-004 from a claim into a check: the pair needs only `<cstdint>`, so a host
  compiler settles it, while the resolver cannot be compiled here because it includes the runtime's
  headers — which the test states as its reason for not trying
- [X] T015 [P] [US1] `tests/contract/test_export_contract.py`: exit 0 writes every artifact the
  manifest's formats imply; exit 1 for `X-1` with the format named and **no** artifact of any
  format; exit 1 for `X-2` naming the stage to run first; exit 2 for an unreadable manifest path;
  the absence of `--format`, `--target` and any skip option asserted over the whole parser
- [X] T016 [P] [US1] `tests/contract/test_export_report.py`: the report names every artifact with
  its size and its `sha256:` digest, the digest matches the file on disk, and the re-written model
  and the quantize stage's model are recorded as two paths sharing one digest
- [X] T016b [P] [US1] `tests/unit/test_subgraph_refusal.py`: the stage refuses `X-3` for a graph
  record carrying two subgraphs. The check is tested against the record rather than against a file,
  because producing a genuine two-subgraph int8 model needs control flow in the template and is a
  feature of its own; the test states that reason, so the next reader knows it is a deliberate seam
  and not a shortcut

### Implementation for User Story 1

- [X] T017 [US1] Implement `src/caravan/export/c_array.py`: the `.cc` and `.h` text exactly as
  research R3 records the runtime's generator writing it, from bytes plus an artifact name
- [X] T018 [US1] Implement `src/caravan/export/artifacts.py`: `Artifact`, `ExportSet`,
  `RunnerRequirements`, and the digest-and-size recording used for every written file
- [X] T019 [US1] Implement the stage body in `src/caravan/stages/export.py`: read the upstream
  quantized model, refuse `X-2` when it is absent, refuse `X-1` for an unimplemented format before
  writing anything, refuse `X-3` for more than one subgraph, write the model and the array into the
  stage's private work directory
- [X] T020 [US1] Implement `src/caravan/cli/export.py` and register the `export` subcommand in
  `src/caravan/cli/main.py`, with the stage options the other verbs share and no option of its own
- [X] T021 [US1] Implement the human summary of `contracts/cli.md`, including the two lines about
  the working-memory floor and what it omits
- [X] T021b [US1] Record in `docs/roadmap.md` the obligation the contract names: the environment
  check asks for every part the plan could need rather than every part it will need, so an author
  on a Python the conversion half does not reach cannot export a model they already have. Name the
  two feature-002 invariants a fix has to preserve, so the next person does not rediscover them
- [X] T022 [US1] Write `export.json` through the run report machinery of feature 002, carrying the
  artifact list, the graph record, the cache verdict and the provenance of every number
- [X] T022b [US1] `tests/contract/test_export_cache.py`: a second export of an unchanged run reuses
  the stored result and records that it did; `--fresh` produces it again and records that too;
  editing a manifest field the stage does not read changes nothing (FR-029, FR-030) — the same pair
  of assertions feature 003 carries for quantize

**Checkpoint**: `caravan export` produces the model, the array, the header and the report, and
refuses `X-1`, `X-2` and `X-3` by name.

---

## Phase 4: User Story 2 — Know what the model really needs (Priority: P1)

**Goal**: the operator set comes from the file, and the resolver holds exactly it.

**Independent Test**: read the operator set with no training framework installed and compare it
with the desktop interpreter's node list; they differ, and the export agrees with the file.

### Tests for User Story 2

- [X] T023 [P] [US2] `tests/verify/test_interpreter_differs.py`: the interpreter's node list for the
  fixture model contains `DELEGATE` and the file's operator set does not — the finding of research
  R1 asserted rather than trusted, so that a future runtime version cannot quietly make the stage
  wrong
- [X] T024 [P] [US2] `tests/unit/test_resolver_methods.py`: every operator the implemented templates
  can emit has a method in the table; the table's names match the source research R4 cites;
  `AddConv2D` is spelled with a capital D; an operator absent from the table raises `X-4`
- [X] T025 [P] [US2] `tests/unit/test_resolver.py`: the generated resolver names each distinct
  operator exactly once, carries the operator count as the template argument, comments each line
  with the version and the node count, and emits `AddCustom` with its name for a custom operator

### Implementation for User Story 2

- [X] T026 [US2] Implement `src/caravan/export/resolver.py`: the header text of
  `contracts/artifacts.md`, from the operator records and the method table, refusing `X-4` for an
  operator with no public method
- [X] T027 [US2] Record the operator set in the report: name, builtin code, version, node count,
  custom name where there is one, plus the node total beside the distinct count
- [X] T028 [US2] Write the resolver as a run artifact from the stage body, after the array

**Checkpoint**: the resolver is generated from the file's operator set and nothing else, and an
operator the runtime cannot resolve refuses the run instead of producing code that fails to compile.

---

## Phase 5: User Story 3 — Ship the graph that was measured (Priority: P1)

**Goal**: the conversion fixes the batch, so the gate's numbers describe the exported artifact.

**Independent Test**: the exported model and the model the gate measured are the same bytes, and the
operator set is the three-operator one.

### Tests for User Story 3

- [X] T029 [P] [US3] `tests/train/test_quantize_fixed_batch.py`: the quantized fixture model has a
  leading input dimension of 1, three distinct operators and four nodes, and contains none of
  `SHAPE`, `STRIDED_SLICE`, `PACK`
- [X] T030 [P] [US3] `tests/train/test_export_end_to_end.py`: quantize then export the pilot
  fixture; the exported model's bytes equal the quantized model's; the report's operator set equals
  an independent reading of the file; the whole run completes under the 30-second budget

### Implementation for User Story 3

- [X] T031 [US3] Call `fix_batch` in `src/caravan/convert/tflite.py` before conversion, inside the
  existing `Q-2` guard so a failure there is still a conversion failure and not a trace
- [X] T032 [US3] Record in the quantize report that the conversion fixed the batch, and what the
  input shape became, so the change is visible in the artefact rather than only in a commit message
- [X] T033 [US3] Update the quantize stage's recorded figures and any test that asserted the old
  operator count or model size, with the reason named in the test rather than only in the diff
- [X] T034 [US3] Update `specs/003-quantize/quickstart.md` and the feature-003 numbers that this
  change makes stale, marking them as superseded by 004 rather than silently editing them

**Checkpoint**: one conversion, one model, one set of numbers, and they describe what ships.

---

## Phase 6: User Story 4 — See where the accelerated kernels apply (Priority: P2)

**Goal**: a sourced, dated verdict per operator per target, and a refusal where there is no source.

**Independent Test**: export for the three built-in boards; every operator has a verdict for every
board, each carrying its source and date.

### Tests for User Story 4

- [X] T035 [P] [US4] `tests/unit/test_kernel_coverage.py`: the three outcomes of
  `contracts/coverage.md` — accelerated with its evidence file, falling back, and a board declaring
  no library — plus `X-5` for a board naming a library with no data file
- [X] T036 [P] [US4] `tests/unit/test_kernel_data_files.py`: both data files parse, every mapped
  operator name is one the schema knows, `read_on` is a date, `source` is non-empty, and every
  listed source file appears in either `operators` or `unmapped` so nothing is silently dropped
- [~] T037 [P] [US4] **Superseded**: the fixture was for `X-5`, and `X-5` was withdrawn during
  implementation. The board schema admits `accel` only from a closed list and every board file is
  validated when loaded, so a board naming an unknown accelerated library cannot exist — the
  fixture would have been a file no code path could reach. The protection moved earlier instead:
  `test_every_library_the_schema_admits_has_sourced_data` pairs the schema's list with the data
  files, so widening the list without reading a source fails in continuous integration rather than
  in somebody's run. Same reasoning as DS-7 in feature 003

### Implementation for User Story 4

- [X] T038 [US4] Implement `src/caravan/targets/kernels.py`: `KernelLibrary` loading from the data
  files, `CoverageVerdict`, and `coverage(operators, board)` returning one verdict per operator
- [~] T039 [US4] **Superseded** with T037, for the same reason: there is no reachable state to
  refuse. `X-5` lives in `ENTAILED_RULES`, with the explanation beside it, and a test asserts it is
  the one `X` identifier deliberately outside `EXPORT_RULES`
- [X] T040 [US4] Record the verdicts in the report, grouped by target, each with its evidence,
  source and date, and summarise them in the human output as "n of m accelerated"
- [~] T041 [US4] **Reduced, with the reason recorded.** The intent was that a board whose `accel`
  changed produces new coverage rather than a reused verdict. Board descriptions are not in the
  resolved manifest, so putting them in the key means either adding them to feature 001's resolve
  output — which also changes the `resolved-manifest.yaml` artifact — or giving the stage machinery
  a second data fingerprint beside `dataset_version`. Both are changes to another feature's
  contract, decided in a feature about exporting, which is how contracts get bent.
  What holds today: the key already carries the tool version, so every board or kernel-data change
  a *user* can see — they come with an upgrade — produces a new key. What does not hold: a
  contributor editing a board file in place, same version, gets a reused result until they pass
  `--fresh`. Asserted by a test so the limit is stated rather than assumed, and recorded in
  `data-model.md` as the obligation it is

**Checkpoint**: coverage is a sourced claim per operator per board, and a new accelerated library
costs a data file rather than a code change.

---

## Phase 7: User Story 5 — Find out what is still the author's job (Priority: P2)

**Goal**: a runner skeleton and an honest requirements record.

**Independent Test**: read the skeleton and the record; every value the author must supply is named,
and no computed figure is presented as measured.

### Tests for User Story 5

- [X] T042 [P] [US5] `tests/unit/test_skeleton.py`: the skeleton names the runtime the board
  declares, references both generated headers, carries the arena as a named constant with the floor
  in its comment, and is deterministic
- [X] T043 [P] [US5] `tests/contract/test_no_unverified_claims.py`: no artifact and no report field
  claims the skeleton was compiled, linked or run; the working-memory figure always travels with its
  method and with the sentence saying what it omits; no latency, flash or memory figure for a target
  appears anywhere in the report; and no coverage verdict is phrased as a statement about speed
  (FR-023) — the field names and the human summary are asserted, not just the prose

### Implementation for User Story 5

- [X] T044 [US5] Implement `src/caravan/export/skeleton.py`: the per-target skeleton of
  `contracts/artifacts.md`, with the runtime and the accelerated library from the board description
- [X] T045 [US5] Implement `RunnerRequirements` in the report: runtime, operator set, floor,
  `floor_method`, and `floor_is_not_the_requirement` as the full sentence
- [X] T046 [US5] Write the skeleton per target from the stage body, under `runner/<target>/`

**Checkpoint**: an author can see what to supply, and nothing claims more than was done.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T047 [P] Extend the layering test `tests/layering/test_no_framework_imported.py`:
  `convert.batch` joins the framework-importing modules, `runtime.flatbuffer` is extra-only, and
  the `export/` package and `targets/kernels.py` must import no framework at all
- [X] T048 [P] Add the export verb to `tests/contract/test_no_network.py` and
  `tests/contract/test_no_skip_option.py`
- [X] T048b [P] Confirm the continuous integration images carry a host C++ compiler so T014b runs
  rather than skips there, and record in `.github/workflows/ci.yml` which job owns that check — a
  test that skips everywhere proves nothing
- [X] T049 [P] Update `README.md` with the `export` verb and what it produces
- [X] T050 [P] Update `docs/roadmap.md`: export delivered, and `conv1d` with the `pace-cnn` port is
  the last item of v0.1
- [X] T051 [P] Record in `docs/budgets.md` that this feature adds no dependency and no extra, with
  the measured install unchanged
- [X] T052 Run the full suite in all four environments of the continuous integration matrix and the
  quickstart end to end, then record the measured figures in the feature documents where the
  documents currently say the figure is not predicted

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (setup) has no dependency; T003, T004 and T005 are parallel
- Phase 2 (foundational) depends on Phase 1 and blocks everything after it
- Phase 3 (US1) depends on Phase 2
- Phase 4 (US2) depends on Phase 2 and on T019 for the place to write the resolver
- Phase 5 (US3) depends on Phase 2 (T011) and reaches into feature 003's conversion
- Phase 6 (US4) depends on Phase 1 (T003, T004) and Phase 2
- Phase 7 (US5) depends on Phase 6 for the board's library and on Phase 4 for the operator set
- Phase 8 depends on everything it tests

### Within Each User Story

Test first, then the implementation it checks. A test that passes when first written is reported,
not quietly kept: it means it was not testing what it claimed.

### Parallel Opportunities

- T003, T004, T005 — three independent data files
- T014, T014b, T015, T016, T016b, T022b — the independent test modules for US1
- T023, T024, T025 — three independent test modules for US2
- T035, T036, T037 — coverage tests and the fixture
- T047, T048, T048b, T049, T050, T051 — independent documents and tests

---

## Implementation Strategy

### MVP first

Phases 1–3 give a working `caravan export` that writes the model, the C array and the header, and
refuses by name. That alone is deployable: an author can flash the model and compile the array.

### Incremental delivery

US2 adds the resolver, which is what makes the firmware build minimal rather than guessing. US3
makes the exported graph the measured one — the correctness of every number upstream. US4 and US5
add the two records that tell an author what they are getting and what they still owe.

### What to do when a measurement contradicts a document

Record the correction in the document and name it, the way `docs/budgets.md` names the ones before
it. A document about measured things that quietly changes its numbers is worth less than no
document.
