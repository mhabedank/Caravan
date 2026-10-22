---

description: "Task list for feature 005: the conv1d template"
---

# Tasks: The conv1d Template

**Input**: Design documents from `/specs/005-conv1d-template/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: requested. This project writes the test before the code it checks, and the suite is a
merge gate (constitution, Development Workflow). Test tasks are therefore not optional here.

## Format: `[ID] [P?] [Story] Description`

- **[P]** — may run in parallel with other [P] tasks: different files, no unfinished dependency
- **[US1]** … **[US4]** — the user story the task serves; setup and polish carry none

## Path Conventions

Single Python package. Source under `src/caravan/`, tests under `tests/`, feature documents under
`specs/005-conv1d-template/`. No dataset is added: the acceptance path uses the committed synthetic
fixture (Principle IX).

---

## Phase 1: Foundational (Blocking Prerequisites)

**Everything after this depends on the arithmetic and on the registry field.**

- [ ] T001 Write `tests/unit/test_sequence_length.py` first, from the 14 cases research R5 verified
  against the framework: `same` padding never shortens below the stride; `valid` padding refuses
  when the window is shorter than the kernel; pooling refuses when it would leave nothing; and the
  two cases the framework itself refuses (`n=4, k=5, valid` and `n=2, k=3, valid`) are refused here
  too. The test states that these numbers came from Keras, so a later "simplification" of the
  formulas has something to fail against
- [ ] T002 Implement `src/caravan/templates/sequence.py`: `length_after(n, kernel, stride, padding)`
  and `length_after_pool(n, pool)`, each returning `None` for "does not fit", and a `walk` that
  runs a sequence of blocks and reports where it stopped
- [ ] T003 Add the optional `window_fit` field to `TemplateParameterSpec` in
  `src/caravan/templates/registry.py`: `Callable[[BaseModel, int], str | None] | None`, defaulting
  to `None` so the dense template and any third-party template are unaffected. Document in the
  docstring that it returns the *sentence*, not a boolean, and why: the core does not know what a
  kernel is and cannot compose the message

---

## Phase 2: User Story 1 — Describe a convolutional model in a manifest (Priority: P1) 🎯 MVP

**Goal**: a manifest naming the template validates, builds, trains, quantizes and exports.

**Independent Test**: run the pipeline on the committed fixture and get a quantized, exported model.

### Tests for User Story 1

- [ ] T004 [P] [US1] `tests/unit/test_conv1d_parameters.py`: every field of `ConvBlock` and
  `Conv1dParameters` rejected at its bounds — `filters: 0`, `kernel: 0`, `stride: 0`, `pool: 0`,
  `dropout: 1.0`, an unknown `padding`, an unknown `head`, an empty `blocks` list, an unknown field
  (`extra="forbid"`) — each asserting the error names *which block* and which field, per FR-011
- [ ] T005 [P] [US1] `tests/contract/test_conv1d_manifest.py`: a conv1d manifest validates and
  renders with defaults filled in; a bad parameter is rejected as `T-2` with the path
  `model.params.blocks.0.<field>`; a manifest without `dataset.window` is rejected as `CF-6`
- [ ] T006 [P] [US1] `tests/fixtures/manifests/valid/picket-conv1d-fixture.yaml`: the fixture
  manifest of `contracts/template.md`, pointing at the committed synthetic dataset, with two blocks
  and the `average` head
- [ ] T007 [US1] `tests/train/test_conv1d_pipeline.py`: build, train, quantize and export the
  fixture manifest end to end; the gate passes; every stage's artifacts are written; and no stage
  needed a special case

### Implementation for User Story 1

- [ ] T008 [US1] Implement `src/caravan/templates/conv1d.py`: `ConvBlock` and `Conv1dParameters`
  with the fields, bounds and defaults of `data-model.md`, `extra="forbid"`, and the `SPEC` with
  `consumes_window=True` and a one-line summary for the listing
- [ ] T009 [US1] Implement `src/caravan/templates/builders/conv1d.py`: blocks to a model, with the
  layer order `convolution → (normalisation) → activation → (pooling) → (dropout)`. Normalisation
  before the activation, because that is the order it folds into the convolution in — the fold is
  the reason it is offered (research R4), and a comment says so
- [ ] T010 [US1] Verify the fixture manifest runs: `caravan validate`, `build`, `train`, `quantize`
  and `export`, and record the measured figures in `quickstart.md` where it says the byte count is
  not predicted

**Checkpoint**: the template exists, the pipeline runs it, and a bad parameter is refused by path.

---

## Phase 3: User Story 2 — Know what the architecture costs on the target (Priority: P1)

**Goal**: the head's cost and the operator consequences are visible in the artifacts.

**Independent Test**: export both heads and compare the recorded operator sets and coverage.

### Tests for User Story 2

- [ ] T011 [P] [US2] `tests/unit/test_conv1d_operators_are_mapped.py`: every operator this template
  can produce — `RESHAPE`, `CONV_2D`, `MAX_POOL_2D`, `MEAN`, `FULLY_CONNECTED`, `SOFTMAX`, and
  `DEPTHWISE_CONV_2D` for the day separable convolution arrives — has a resolver method in feature
  004's table, in the runtime's own spelling. FR-022: asserted rather than left to luck
- [ ] T012 [P] [US2] `tests/unit/test_conv1d_coverage.py`: on all three built-in boards, `MEAN` is
  recorded as a reference fallback with its source and date, and `CONV_2D`, `MAX_POOL_2D`,
  `FULLY_CONNECTED` and `SOFTMAX` as accelerated
- [ ] T013 [US2] `tests/train/test_conv1d_heads.py`: export the fixture manifest with each head and
  compare the records — the reducing head has one more distinct operator and fewer parameters; the
  operator set equals an independent reading of each exported file

### Implementation for User Story 2

- [ ] T014 [US2] Nothing to build: the export stage reads the operator set from the file and the
  coverage from the kernel data, and both already cover this template (research R7). This task is
  to **confirm that by running it**, and to write down in `research.md` what the first real
  conv1d export actually recorded — the measured counterpart to the predictions in R3

**Checkpoint**: the architecture's cost on the target is readable from the artifacts of one run.

---

## Phase 4: User Story 3 — Serve the model that asked for the template (Priority: P2)

**Goal**: the template expresses the named model's shape, and refuses what cannot be built.

**Independent Test**: build at both shapes; check the shapes and the parameter counts.

### Tests for User Story 3

- [ ] T015 [P] [US3] `tests/unit/test_window_fit.py`: a configuration that exceeds the window is
  refused with a sentence naming the block, the length when that block was reached, and a fitting
  alternative; a configuration that fits returns nothing; and the dense template, which has no
  `window_fit`, is unaffected
- [ ] T016 [P] [US3] `tests/train/test_conv1d_build.py`: build at the named model's shape — 128
  samples, 9 channels, six labels — and at the fixture's shape, asserting the input shape, the
  output shape and that a parameter count is recorded for each. **No training**: this checks that
  the template can express the shape, and nothing here claims what such a model would achieve
- [ ] T017 [P] [US3] Extend `tests/contract/test_conv1d_manifest.py` with the `CF-6` refusal for a
  window too short for the configured blocks, asserting the message names the block and the length

### Implementation for User Story 3

- [ ] T018 [US3] Implement `window_fit` in `src/caravan/templates/conv1d.py` over
  `templates/sequence.py`, composing the sentence of `contracts/template.md`: the window, the block
  that does not fit, the length there, and what would fit — a smaller kernel, a shorter stride, or
  one fewer pooling step
- [ ] T019 [US3] Call it from `CF-6` in `src/caravan/manifest/schema/__init__.py`, where the rule
  already checks a window against a template: only when the template consumes a window, the window
  is set, and the parameters validated

**Checkpoint**: the named model's shape builds, and an impossible configuration is refused at
validation with something the author can act on.

---

## Phase 5: User Story 4 — Add a template without touching the core (Priority: P2)

**Goal**: the registry's claim, proved by a second real template.

**Independent Test**: list the templates; the new one is there with its summary, and no central list
changed.

### Tests for User Story 4

- [ ] T020 [P] [US4] Extend `tests/unit/test_template_registry.py`: the default registry holds both
  templates; each has a non-empty summary; the convolutional one declares that it consumes a window
- [ ] T021 [P] [US4] `tests/contract/test_templates_listing.py` (or extend the existing listing
  test): `caravan templates` prints both with their summaries, and exits 0 in an installation with
  no training framework
- [ ] T022 [P] [US4] A test that no stage, command or report branches on a template identifier
  (FR-023, SC-009): read the sources under `src/caravan/stages/` and `src/caravan/cli/` and assert
  that neither `"mlp"` nor `"conv1d"` appears as a literal

### Implementation for User Story 4

- [ ] T023 [US4] Nothing to build if the registry works as feature 001 claimed. This task is to
  **run the tests above and fix whatever they find** — and if they find nothing, to say so in the
  completion report, because "the design held" is a result worth stating once

---

## Two requirements with no task, and why

Found by the analysis pass rather than left implicit:

- **FR-024 (the stage cache applies)** needs no task. `build.SPEC.reads` already includes
  `model.params`, so a changed block is a changed key by construction, and feature 002's generic
  projection test checks that declaration against what the code actually touches. A conv1d-specific
  cache test would assert the same machinery twice.
- **FR-025 (the gate can fail this template's runs)** needs no task either. It follows from FR-023 —
  no stage branches on a template identifier, which T022 asserts by reading the sources — together
  with feature 003's gate tests, which exercise the failure path on the machinery both templates
  share.

Both are stated here so that a reader counting tasks against requirements does not find a hole and
assume it was forgotten.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Extend `tests/layering/test_no_framework_imported.py`: `templates.builders.conv1d`
  joins the framework-importing modules; `templates.conv1d` and `templates.sequence` must import no
  framework at all
- [ ] T025 [P] Update `README.md`: the second template in the template list, with one line on what
  it is for and one on the head's trade
- [ ] T026 [P] Update `docs/roadmap.md`: `conv1d` delivered, v0.1 complete apart from the recorded
  obligations, and the `pace-cnn` port named as the zoo's work with the real data
- [ ] T027 [P] Record in `docs/budgets.md` that this feature adds no dependency, no extra and no
  rule identifier
- [ ] T028 Run the whole suite in all four environments of the continuous integration matrix and
  the quickstart end to end; record the measured figures where the documents say a figure is not
  predicted

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (foundational) blocks everything; T001 before T002, T003 independent of both
- Phase 2 (US1) depends on Phase 1 and is the MVP
- Phase 3 (US2) depends on Phase 2 having produced an exported model
- Phase 4 (US3) depends on T002 for the arithmetic and T008 for the parameters
- Phase 5 (US4) depends on T008 existing; its tests are otherwise independent
- Phase 6 depends on everything it documents or tests

### Within Each User Story

Test first, then the implementation it checks. A test that passes the moment it is written is
reported rather than quietly kept — it means it was not testing what it claimed.

### Parallel Opportunities

- T004, T005, T006 — parameters, manifest contract, fixture
- T011, T012 — the two mapping and coverage tests
- T015, T016, T017 — window fit, both shapes, the refusal
- T020, T021, T022 — the three registry claims
- T024 … T027 — four independent documents and tests

---

## Implementation Strategy

### MVP first

Phases 1 and 2 give a working template: a manifest validates, a model builds and trains, and the
pipeline exports it. That alone completes what v0.1 was waiting for.

### Then the parts that make it a TinyML template

US2 makes the architecture's cost visible in the artifacts. US3 makes the named model's shape and
the impossible configurations explicit. US4 is evidence about the design rather than new behaviour.

### Two tasks that may turn out to be nothing

T014 and T023 are written as confirmations, not as construction, because research R7 found that the
export stage and the registry already cover this template. If they are nothing, that is the result
and it gets said once. If they are not, the tests around them will say what is missing — which is
the reason they are tasks and not assumptions.
