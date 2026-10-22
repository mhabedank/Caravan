---

description: "Task list for feature 003: quantize"
---

# Tasks: Quantize

**Input**: Design documents from `/specs/003-quantize/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: included, and not optional. The specification requires them by name: SC-003 (every number
names what it was measured against), SC-004 (the report's claim matches an independent reading of
the file), SC-005 (a failing gate leaves nothing and explains itself), SC-006 (nothing can silence
the gate), SC-007 (seven reuse cases), SC-008 (measurement works with no training framework),
SC-009 (a missing part is answered, not crashed), SC-010 (the budgets hold).

**Organization**: grouped by user story, in priority order. Both P1 stories are needed for the MVP
and neither is useful without the other: a quantized model nobody verified is not a deliverable,
and a verification with nothing to verify is not a feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story the task serves (US1–US4)
- Exact file paths in every description

## Path Conventions

Single Python package: `src/caravan/`, `tests/` at the repository root.

**Which extra a file needs decides where it lives, and which Python can run its tests.** This is now
a three-way split and getting it wrong turns CI red, as it did in feature 002:

| Directory | Needs | Tested on |
|---|---|---|
| everything else under `src/caravan/` | nothing | 3.13, 3.14, 3.15 |
| `src/caravan/runtime/` | the `verify` extra | 3.13, 3.14, 3.15 |
| `src/caravan/convert/` | the `train` extra | 3.13 only |
| `tests/unit`, `tests/contract`, `tests/integration`, `tests/layering` | nothing | all three |
| `tests/verify/` | the `verify` extra | all three |
| `tests/train/` | both | 3.13 only |

A test that needs the training framework goes in `tests/train/` and nowhere else. A test that needs
only the runtime goes in `tests/verify/`. Neither rule has an exception.

---

## Phase 1: Setup

**Purpose**: the second extra, and the continuous integration that proves its claim

- [ ] T001 Add `verify = ["ai-edge-litert>=2.3"]` to `[project.optional-dependencies]` in `pyproject.toml`, with **no** Python marker and a comment saying why there is none: it installs on every Python the project supports (3.13, 3.14 and 3.15, verified 2026-10-22), which is the whole reason it exists as a second extra. No upper bound, per Principle XII
- [ ] T002 [P] Register the pytest marker `requires_no_verify_extra` in `pyproject.toml` for the tests that assert the absence path, matching the `requires_no_train_extra` convention of feature 002 — presence stays handled by `importorskip`, one mechanism per direction
- [ ] T003 Change `.github/workflows/ci.yml`: the `test` matrix jobs install `.[verify]` and add `tests/verify` to their directory list, so FR-023's claim that measurement works on every supported Python is actually run on every supported Python; the `train` job installs `.[train,verify]`; `clean-environment` and `install-budget` are **untouched** and keep proving the default installation needs neither extra

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the primitives both P1 stories need — reading a model, measuring one, the rules, and
the report's new sections

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [ ] T004 Extend `src/caravan/env.py`: `REQUIRED_RUNTIME_MODULES = ("ai_edge_litert",)`, a presence check using the same `_importable` helper (which already swallows what `find_spec` can raise), and `missing_part_message(command, part)` rendering the two forms of [contracts/cli.md](./contracts/cli.md) — the conversion part with its Python window on 3.14 and newer, the runtime part with the sentence that it installs on every Python. Neither message may contain a module path or the word `Traceback`
- [ ] T005 [P] Add the Q rule identifiers to `src/caravan/manifest/errors.py` as a new group `QUANTIZE_RULES` — `Q-1` through `Q-5` per [data-model.md](./data-model.md) — included in `ALL_RULES` and kept out of `MANIFEST_REJECTION_RULES`, so the fixture coverage test of feature 001 keeps passing
- [ ] T006 [P] Implement `src/caravan/runtime/inspect.py` (extra `verify`): `inspect_model(path)` returning the `ModelInspection` of [data-model.md](./data-model.md) — size from the filesystem, one `TensorRecord` per tensor with dtype, shape, scale and zero point, `dtype_counts`, and `fully_integer` computed **from the tensor records**. Nothing in this module may consult a converter, a log or the requested setting: the whole point is that the file is the only source (research R2)
- [ ] T007 [P] Implement `src/caravan/runtime/measure.py` (extra `verify`): `measure(path, features, targets, labels)` returning the `SplitMeasurement` of [data-model.md](./data-model.md). An integer input tensor **must** be fed data quantised with the model's own scale and zero point — `clip(round(x / scale) + zero_point, -128, 127)` as int8 — because handing float data to an int8 tensor is a silent reinterpretation of bytes and the accuracy would be nonsense shaped like a measurement (research R4). The class decision is the arg-max of the output as stored; no dequantisation, no probability reported
- [ ] T008 Implement `src/caravan/convert/tflite.py` (extra `train`): `convert(model, setting, representative)` returning the serialised model for each of the three settings — int8 full-integer with the representative dataset and int8 input and output, float16, and no quantisation — via `from_keras_model`, the path research R1 found byte-identical to the longer one. `representative` is `None` for `float16` and `none`, which is **valid input and not an error**: the schema makes `representative_samples` optional and rule CF-4 demands it only for int8. A conversion failure raises **Q-2** carrying what the converter reported
- [ ] T009 [P] Implement `src/caravan/convert/debugger.py` (extra `train`): `layer_errors(model, representative)` returning `LayerErrorRow`s from `tf.lite.experimental.QuantizationDebugger`, with `rmse = sqrt(mean_squared_error)` and `rmse_over_scale = rmse / scale` where the scale is non-zero, ordered by `rmse_over_scale` descending. Called **only** on a failed gate (research R6): it costs a second instrumented conversion and one inference per calibration sample
- [ ] T010 Extend `src/caravan/run/report.py` with the `quantization` section of [contracts/quantized-model.md](./contracts/quantized-model.md) and the gate's entry in the existing `gates` list. The accuracy figures are written as the `QualityMetric` of feature 002, which cannot be constructed without its split, dataset version and sample count — so SC-003 holds here by the same mechanism rather than a new one
- [ ] T011 [P] Write `tests/verify/conftest.py`: `collect_ignore_glob` when `ai_edge_litert` is absent, mirroring `tests/train/conftest.py`, plus a fixture giving the path of a committed example model
- [ ] T012 [P] Write `tests/unit/test_quantize_rules_coverage.py`: every identifier in `QUANTIZE_RULES` is provoked by some test, and none of them appears in `MANIFEST_REJECTION_RULES` — both directions, as feature 002 does for its DS rules

---

## Phase 3: User Story 2 — Trust that it is really int8 (Priority: P1)

**Goal**: what the produced model contains is established by reading the file, and recorded.

**Independent Test**: inspect a produced model independently of the converter and confirm the
report's claim matches the file.

*Implemented before user story 1 although both are P1: the gate cannot be judged on a model nobody
has established the shape of, and this is the smaller half.*

- [ ] T013 [US2] Implement the inspection half of `src/caravan/stages/quantize.py`: convert, write the model into the stage's private directory, inspect the written file, and raise **Q-3** when the setting was int8 and `fully_integer` is false, naming the tensors that are not integers
- [ ] T014 [P] [US2] Write `tests/verify/test_inspect.py`: an int8 model reports every tensor int8 or int32, an input and output with a scale and a zero point, and `fully_integer` true; a float model reports float tensors and `fully_integer` false; the size matches `stat`. Runs on every Python in the matrix, because inspection needs no training framework
- [ ] T015 [P] [US2] Write `tests/train/test_quantize_int8.py`: quantising the fixture manifest produces a model whose **file** reports the dtype counts the report claims — read with the runtime, not from `quantization.json` — which is SC-004 and the reason this story exists. Include the explicit assertion that no `float32` tensor remains
- [ ] T016 [P] [US2] Write `tests/train/test_quantize_settings.py`: `float16` and `none` both convert, are measured, and are **not** described as int8; `int8` is. One case per setting, so a schema value no model uses still has behaviour
- [ ] T017 [P] [US2] Write `tests/verify/test_inspect_rejects_a_float_model_declared_int8.py`: `Q-3` fires with the offending tensor names, provoked by inspecting a float model against an int8 expectation — the failure mode a converter silently producing a partly quantised model would cause

**Checkpoint**: what is in the file is known, and the claim about it is the file's, not a tool's.

---

## Phase 4: User Story 1 — Get a deployable model, or a reason why not (Priority: P1)

**Goal**: three accuracies, one gate, an artifact or a reason.

**Independent Test**: quantize the pilot manifest and confirm the model, the three figures, the
verdict; then force a failure and confirm the table and the absent artifact.

- [ ] T018 [US1] Implement the calibration draw in `src/caravan/stages/quantize.py`: the `CalibrationPlan` of [data-model.md](./data-model.md) — `random.Random(train.seed).sample` over the **training** split's indices, capped at what the split holds, with requested, available and used all recorded. There must be no code path that draws from the test split. **`requested` may legitimately be `None`**: the schema's `representative_samples` is optional and only int8 requires it, so a `float16` or `none` manifest yields `requested=None`, `used=0` and no indices — `min(None, available)` would raise on correct input, which the analysis pass caught before it was written
- [ ] T019 [US1] Implement the three measurements: the trained model with the training framework, the converted model and the quantized model with the runtime, all on the test split against the same dataset version (research R7). The converted model is a second conversion with no quantisation, so that the gated difference is the quantisation and nothing else
- [ ] T020 [US1] Implement the gate per [contracts/gate.md](./contracts/gate.md): `quantization_drop = converted - quantized` against `export.accuracy_drop_max`, `<=` passes, a negative drop passes and is recorded as negative rather than clamped, `resolution = 1 / samples` recorded beside the verdict, **Q-4** on failure and **Q-5** when the comparison cannot be measured at all — unknown is not within budget
- [ ] T021 [US1] Wire the stage's `StageSpec` with the seven declared reads of [data-model.md](./data-model.md), `upstream="train"`, and the two declared artifacts; write `quantization.json` as the record the report is built from, so a reused result reports the same numbers as the run that produced it. It must carry the whole record of [contracts/quantized-model.md](./contracts/quantized-model.md), including the two pieces no other task owned: the **`tools` block** — the converter and the runtime each with its version, and the Python version they ran on (FR-018) — and **`trained_size_bytes`**, measured with `stat` on the trained model, since the inspection only ever sees the quantized file (FR-019)
- [ ] T022 [US1] On a failed gate, write `quantization-error.csv` **straight into `context.run_dir`**, not into the stage's working directory, and the table into the report, with the 0.289 reference stated. The directory matters: a stage that raises has its working directory deleted by the runner of feature 002 — that is how a failed gate leaves no model behind — so a table written there would be destroyed by the same mechanism that protects the artifact. It is deliberately not a declared artifact either: the cache would then demand it on every run, and a failed run never reaches the cache
- [ ] T023 [US1] Implement `src/caravan/cli/quantize.py` and wire the `quantize` verb into `src/caravan/cli/main.py` with the options of [contracts/cli.md](./contracts/cli.md) and both human summaries — including the line that says when the split cannot resolve the threshold, which is the difference between a verdict the author can act on and a number that looks authoritative
- [ ] T024 [P] [US1] Write `tests/unit/test_gate_arithmetic.py`: the `<=` boundary passes, a negative drop passes and stays negative, a drop one step over fails, the resolution is `1 / samples`, and the threshold is read as an absolute difference and never as a percentage. Pure arithmetic, so every resolution can be constructed here rather than hoped for on the fixture
- [ ] T025 [P] [US1] Write `tests/unit/test_calibration_draw.py`: the same seed draws the same samples, a different seed draws different ones, the draw is capped at what the split holds with all three counts recorded, and the indices are always within the training split
- [ ] T026 [P] [US1] Write `tests/train/test_quantize_end_to_end.py`: the fixture quantizes inside the 60-second budget (SC-001); the run directory holds `model/quantized.tflite` and `quantization.json` (SC-002); the report carries all three accuracies, both differences, the threshold, the verdict and the resolution; and every accuracy names its split, dataset version and sample count (SC-003)
- [ ] T027 [P] [US1] Write `tests/train/test_gate_failure.py`: a manifest with `accuracy_drop_max: 0.0` fails with exit 1 and a `Q-4` finding; **no** `model/quantized.tflite` exists in that run directory; `quantization-error.csv` does; the report's `gates` list carries a failed `accuracy` entry with both numbers; and the per-layer table is ordered worst first with rows naming layers of the built model (SC-005)
- [ ] T028 [P] [US1] Write `tests/train/test_quantize_refusals.py`: `Q-1` when the trained model is missing or unreadable, naming the stage that should have produced it; `Q-2` when the conversion fails; and `Q-5` when the comparison cannot be measured
- [ ] T029 [P] [US1] Write `tests/contract/test_quantize_contract.py`: the option set is exactly the documented one, the manifest is a required positional, `--json` goes to standard output with the summary on standard error, an invalid manifest is exit 1 before anything is converted, and no option name contains a word that could silence a gate (SC-006)

- [ ] T029a [P] [US1] Write `tests/train/test_quantize_reuse.py`, the coverage the analysis pass found missing: the seven cases of [quickstart.md](./quickstart.md) scenario 5, each asserting the outcome of all three stages. Editing `compliance.intended_use` reuses everything; **editing `export.targets` also reuses everything**, because this stage does not read it and adding a board must not re-quantize; `export.accuracy_drop_max`, `export.quantization` and `dataset.representative_samples` each re-quantize while build and train are reused; `train.seed` and a changed dataset byte produce all three. This is FR-020 to FR-022 and SC-007, which had no task until now
- [ ] T029b [US1] Register the quantize stage with the generic projection test of feature 002 in `tests/unit/test_cache_key_projection.py` by adding it to that file's `STAGES` tuple — one line, and it then walks every leaf of the pilot manifest for this stage too, asserting the key moves if and only if the leaf is in the declared read set. The seven cases above are the lived version; this is the one a new schema field cannot escape

**Checkpoint**: the acceptance criterion is met — the pilot manifest quantizes end to end on the
committed fixture, a failing gate explains itself and leaves nothing behind, and what re-quantizes
is settled by a test rather than by reading the read set.

---

## Phase 5: User Story 3 — See what the quantization cost, per layer (Priority: P2)

**Goal**: a failed gate emits an ordered, meaningful table rather than only a verdict.

**Independent Test**: force a failure and read the table.

- [ ] T030 [P] [US3] Write `tests/unit/test_layer_error_ranking.py`: rows order by `rmse_over_scale` descending, a zero scale yields `None` and sorts last rather than raising, `rmse` is the square root of the mean squared error, and the 0.289 reference travels with the table rather than being left for the reader to remember
- [ ] T031 [P] [US3] Write `tests/train/test_layer_error_table.py`: the table is absent on a passing run and present on a failing one — the asymmetry the constitution asks for, since a passing run has nothing to act on — and its rows name operators that exist in the model
- [ ] T032 [US3] Add the reference line and the guide's 0.7 flag level to the human output and to the report, so neither number ever appears without what it means. **Neither becomes a gate**: a project that invented its own per-layer cutoff would be gating on a heuristic nobody wrote in the manifest

---

## Phase 6: User Story 4 — Read and run a model without a training framework (Priority: P2)

**Goal**: the measurement half runs on every supported Python, and a missing part is answered.

**Independent Test**: run the measurement tests on 3.15, where the training framework cannot be
installed at all.

- [ ] T033 [P] [US4] Write `tests/verify/test_measure.py`: measuring a committed example int8 model against a committed example input gives the accuracy and confusion matrix expected, and feeding **float** data where the input is int8 is proven to give a different, wrong answer — so the quantisation step in T007 is load-bearing rather than decorative
- [ ] T034 [P] [US4] Add new test functions to `tests/layering/test_no_framework_imported.py`: `caravan.runtime.inspect` and `caravan.runtime.measure` import no `tensorflow` and no `keras`; `caravan.convert.*` is declared extra-only; `caravan.stages.quantize` imports none of them. The AST check of feature 002 extends to the new directories without changing its existing assertions
- [ ] T035 [P] [US4] Add a new test function to `tests/layering/test_declared_dependencies.py`: exactly two extras, `train` and `verify`; every `train` dependency still carries its `python_version` marker; and **no** `verify` dependency carries one, because a marker there would silently narrow the claim FR-023 makes
- [ ] T036 [P] [US4] Write `tests/unit/test_missing_part_cli.py`, marked `requires_no_verify_extra` where it asserts the runtime's absence: `quantize` exits 4 naming the missing part, no traceback, no run directory left behind — for each of the two parts
- [ ] T037 [P] [US4] Add a new test function to `tests/layering/test_hostile_import.py`: with every framework unimportable, `caravan.stages.quantize` still imports and `caravan quantize` still answers with exit 4 rather than an `ImportError`

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T038 Commit a small example int8 model and its input under `tests/fixtures/models/`, generated by a committed script as the dataset fixture was, so `tests/verify` has something to read on a Python where no converter can run. It must be kilobytes. The regeneration test asserts **functional equivalence** — same tensor dtypes, shapes, input and output quantisation parameters, and the same predictions on the committed input — and **not** byte-identity: a flatbuffer carries a converter's own version and layout choices, and nothing promises two runs of a converter produce identical bytes. Promising it would buy an intermittent failure. The test lives in `tests/train/`, because regenerating needs the converter
- [ ] T039 [P] Update `docs/budgets.md`: two extras of four, the `verify` extra's measured size and package count, and the contrast with the `train` extra — the number that justifies the split
- [ ] T040 [P] Update `docs/roadmap.md`: quantize **delivered (feature 003)**, export **next**. Leave the Python-floor obligation exactly as it is and add one line recording that feature 003 answered the question the Technical Baseline reopened: there is no framework-free conversion path, so the floor stays until a stable TensorFlow ships for the current Python
- [ ] T041 [P] Update the Technical Baseline in `.specify/memory/constitution.md` to record that answer, as a PATCH amendment: the quantize stage was built, the alternative was checked, and the conclusion is that conversion keeps the framework while reading and running a model no longer does
- [ ] T042 [P] Update `README.md` with the `quantize` verb, the two extras and which Python each needs, linking to `docs/budgets.md` rather than restating the reasoning
- [ ] T043 Run the quickstart of [quickstart.md](./quickstart.md) end to end on 3.13, and scenario 6 on 3.15, then replace every illustrative figure in the contracts and the quickstart with the measured one — including the example outputs in `contracts/cli.md`, which are currently written from one real run and must be re-checked against the implemented command
- [ ] T044 Run `ruff check src tests` and `ruff format --check src tests`, then the full suite on 3.13 with both extras, on 3.14 and 3.15 with the verify extra, and in a clean environment with neither; confirm no assertion of features 001 and 002 was weakened and record any that changed, as `tasks.md` of feature 002 does

---

## Dependencies

```text
Phase 1 (setup) ─▶ Phase 2 (foundational) ─▶ Phase 3 (US2: what is in the file)
                                                        │
                                                        ▼
                                              Phase 4 (US1: the gate)
                                                        │
                                        ┌───────────────┴───────────────┐
                                        ▼                               ▼
                              Phase 5 (US3: the table)      Phase 6 (US4: no framework)
                                        └───────────────┬───────────────┘
                                                        ▼
                                              Phase 7 (polish)
```

**Both P1 stories are in the MVP** and the order between them is not a priority call: the gate
(US1) judges a model whose shape US2 establishes, so US2 lands first because it is the smaller half
and the other depends on it.

US3 and US4 depend on US1 but not on each other, and Phase 6 is entirely tests, so it can run
beside Phase 5.

## Parallel Execution Examples

**Phase 2**, after T004: T005, T006, T007, T009, T011, T012 touch six different files.

**Phase 3**, after T013: T014, T015, T016, T017 are four separate test files.

**Phase 4**, after T023: T024 through T029 and T029a are seven separate test files; T029b is one
line in an existing one and must follow T021, which declares the read set it checks.

**Phases 5 and 6** can run concurrently once Phase 4 is done; within them, every task but T032 is
independent.

## Implementation Strategy

**MVP**: Phases 1–4. That is the acceptance criterion: the pilot manifest quantizes end to end, the
model is proven int8 by reading it, and the gate decides on a stated threshold.

**Then** Phase 5, which is what makes a failure actionable; **then** Phase 6, which is what makes
the next four stages cheap; **then** Phase 7.

**The two tasks to get right if any**: T006, because a report that describes the model from
anything but the file is the one failure this feature was designed around; and T020, because a gate
with the wrong comparison, the wrong boundary or a clamped negative is a gate that lies in a
direction nobody checks.

**And the cheapest task with the most reach is T029b**: one line adds this stage to the projection
test feature 002 wrote, and from then on no schema field can quietly enter or leave what
re-quantizes.
