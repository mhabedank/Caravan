# Tasks: A Guided Way to Write the Manifest

**Input**: Design documents from `/specs/013-guided-manifest-setup/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included. The plan names the test files, and the spec's acceptance scenarios and
success criteria (SC-002, SC-006, FR-020) are only provable by tests. Each story's tests are written
first and fail before its implementation.

**Organization**: by user story — US1 (P1) a valid manifest from the data, US2 (P2) a short,
readable file, US3 (P3) the same without questions.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3

## Path Conventions

Single project: `src/caravan/`, `tests/` at the repository root. All tests run in the default
installation (no `train` or `verify` extra) — that is itself FR-023.

---

## Phase 1: Setup

- [ ] T001 Create the package `src/caravan/init/` with an `__init__.py` whose docstring states the
  layering rule from plan.md: no import of the YAML library (only through
  `caravan.manifest._yaml`), nothing behind an extra, standard library plus `caravan` core only.
- [ ] T002 [P] Add a `tests/fixtures/datasets/init/` directory with small hand-written CSV files for
  the profiler's edge cases, each a few rows: `empty-column.csv` (one column entirely empty),
  `constant.csv` (one column with one value), `ids.csv` (a column `sensor_id` of many integers and a
  column `code` of integers), `small-codes.csv` (an integer column with 5 distinct values),
  `missing.csv` (a number column with empty cells), `bad-name.csv` (a column `Speed (km/h)` that
  fails `NAME_PATTERN`), `headers-differ/a.csv` and `headers-differ/b.csv` (different second
  column), `no-header/x.csv` (first row numeric) and `numeric-output.csv` (a numeric `target`
  column). Record what each one is for in `tests/fixtures/datasets/init/README.md`.

---

## Phase 2: Foundational (blocking all stories)

- [ ] T003 [P] In `src/caravan/templates/registry.py`, add the frozen dataclass `TemplateStarter`
  with fields `params: Mapping[str, Any]`, `window: int | None`, `rank: int`, `note: str`, and an
  optional field `starter: TemplateStarter | None = None` on `TemplateParameterSpec`, documented like
  `window_fit` (optional so no third-party template breaks; research R7). State in the docstring that
  a starter is a proposal shown by `caravan init`, never a default a manifest resolves (Principle I).
- [ ] T004 [P] Add starters, from research R7's table:
  `src/caravan/templates/mlp.py` → `params={"hidden": [32, 16], "dropout": 0.1}`, `window=64`,
  `rank=0`; `src/caravan/templates/conv1d.py` → `params={"blocks": [{"filters": 16, "kernel": 5,
  "pool": 2}, {"filters": 32, "kernel": 3}]}`, `window=64`, `rank=1`;
  `src/caravan/templates/conv2d.py` → the two blocks and `head: average` of
  `examples/frames-conv2d.yaml`, `window=12`, `rank=2`; `src/caravan/templates/autoencoder.py` →
  `params={"encoder": [32, 16], "code": 4}`, `window=5`, `rank=0`. Each `note` is one line on when to
  choose the template.
- [ ] T005 [P] Write `tests/unit/test_template_starters.py`: for every template in
  `default_registry()` that has a starter, its `params` validate against `spec.parameters`, and when
  `spec.window_fit` is set its `window` passes it; a template registered in the test without a
  starter is accepted by the registry (SC-006, data-model "TemplateStarter" rules).
- [ ] T006 [P] In `src/caravan/data/fingerprint.py`, make the file listing public as
  `data_files(path: Path) -> tuple[Path, tuple[Path, ...]]` returning the root and the files in the
  order `_files_in` gives, raising the same `RULE_DATASET_UNREADABLE` errors as `resolve_dataset`
  for a missing path or a directory with no data file, without hashing. Have `resolve_dataset` call
  it. Extend `tests/unit/test_fingerprint.py` with one test that both agree on the file order.
- [ ] T007 [P] In `src/caravan/manifest/_yaml.py`, add `dump_commented(document) -> str` and the
  small builders it needs (`commented_map()`, `flow_map()`, `flow_list()`, a way to attach a comment
  line before a key and a start comment), serialising with ruamel's round-trip mode at indent 2,
  width 100, no sorting (research R9). Keep it the only module importing `ruamel`. Add
  `tests/unit/test_yaml_commented.py`: output is deterministic across two calls, comments appear on
  the lines asked for, a string like `yes`, `0.10` or a path containing `:` round-trips through
  `read_mapping` unchanged.
- [ ] T008 Register the verb: in `src/caravan/cli/main.py` add the `init` subparser with the
  positional `<manifest>` (optional) and the options of
  [contracts/cli-init.md](./contracts/cli-init.md) — `--dataset`, `--output`, `--output-type`,
  `--input` (append), `--template`, `--params`, `--window` (int), `--board` (append), `--budget`
  (float), `--name`, `--overwrite`, `--no-input` — and the handler entry `"init": init_command.run`.
  Create `src/caravan/cli/init.py` with a `run(args)` that returns `EXIT_USAGE` and prints "not built
  yet" so the parser is testable now. Confirm `tests/contract/test_no_skip_option.py` still passes
  (no option contains `force`, `skip`, `override` …).

**Checkpoint**: starters, file listing, commented YAML and the verb's skeleton exist; every existing
test still passes (`pytest -q` in the default installation).

---

## Phase 3: User Story 1 — From a data directory to a manifest that validates (P1) 🎯 MVP

**Goal**: `caravan init`, run in a terminal and answered by Enter at every proposal, writes a
manifest that `caravan validate` accepts.

**Independent test**: quickstart step 1 — on the synthetic fixture, accept every proposal with
`label` as the output; `caravan validate` on the file exits 0.

### Tests for US1 (write first; they fail until the implementation lands)

- [ ] T009 [P] [US1] Write `tests/unit/test_init_profile.py` for research R4 and R5 on the fixtures
  of T002 and `tests/fixtures/datasets/{synthetic,frames,anomaly,images}`: each R4 rule in order
  with its exact reason text ("every sampled cell is empty", "one value in every sampled row: carries
  no information", "2 distinct values: x and y", "integers in a column named like an identifier: a
  code, not a magnitude", "text values, N distinct", "N distinct integer values", "numeric, N distinct
  values"); the synthetic fixture gives `can_id` category, `dlc` category, `b0`–`b2` number; frames
  `c0`–`c7` number; anomaly `m0`–`m7` number; images flags `image` as image-like; a name failing
  `NAME_PATTERN` is proposed as left out with that reason; the output proposal is `label` for
  synthetic and frames and `condition` for anomaly; the offered output types follow R5 (`anomaly`
  offered for `condition` because a value is `normal`); differing headers and a missing header stop
  profiling with the files and columns named; a 1,000,000-row generated file is profiled in under 5
  seconds and reports "sampled the first 50,000 rows" (SC-005).
- [ ] T010 [P] [US1] Write `tests/unit/test_init_answers.py` for data-model "Answer set" validation:
  output and inputs must be data columns with names matching `NAME_PATTERN`, the output is never an
  input (CF-11); templates offered are only those with `output_type in spec.output_types`, ordered by
  `starter.rank` then identifier, and the proposal is the first; a `--params` mapping the template
  rejects is refused with the template's message; the window proposal is the starter's, raised to
  the smallest window `window_fit` accepts; boards are registered identifiers without repeats and the
  proposal is the board with the least RAM when it also has the least flash (`s32k144` today); the
  budget key follows `BUDGET_KEYS` with proposals 0.02 (`accuracy_drop_max`), 0.05 (`auc_drop_max`)
  and none for `mae_increase_max`; the name proposal is `<dataset directory>-<template>` normalised
  to the model name form; `version` is `0.1.0` and `representative_samples` 100.
- [ ] T011 [P] [US1] Write `tests/contract/test_init_contract.py` for the dialogue path of
  [contracts/cli-init.md](./contracts/cli-init.md): with the synthetic path then empty lines piped to
  `main(["init", str(tmp_path / "m.yaml")])`, exit 0, standard output is exactly the written path
  and a newline, standard error ends with `wrote m.yaml — valid` and `next: caravan build m.yaml`,
  and `load_manifest` finds the file valid; at most 12 answers are read for the synthetic fixture
  (SC-003); `<` goes back one question; a summary answer of a question number revisits it; end of
  input before the summary exits 2 and leaves no file and no temporary file in `tmp_path`;
  `KeyboardInterrupt` raised from the reader exits 2 without a traceback and writes nothing; an
  existing target in the dialogue asks to overwrite with "no" as the proposal and then asks for
  another file name with a proposal that does not exist yet; the images fixture exits 1 naming the
  `image` column and pointing at `docs/ref/manifest/input-features.md`; no run directory, cache or
  report is created in the working directory.

### Implementation for US1

- [ ] T012 [US1] Implement `src/caravan/init/profile.py`: `ColumnProfile` and `DataProfile` exactly
  as data-model.md lists their fields; `profile(path) -> DataProfile` using `data_files` (T006) and
  `csv` with `delimiter_for`-equivalent delimiters from `TABLE_DELIMITERS`; read rows in file order
  until 50,000 data rows or the end (research R3); keep "up to 257 distinct values, in first-seen
  order"; apply research R4's eight rules in order and set `proposal` and `reason`; apply the
  `NAME_PATTERN` rule; stop with a clear message naming files and columns when headers differ, and
  naming the file when the first row is not a header (every cell numeric). Implement R5's output
  proposal and offered output types as functions in the same module. Makes T009 pass.
- [ ] T013 [US1] Implement `src/caravan/init/answers.py`: the answer set of data-model.md as a
  dataclass with the fields `dataset`, `output`, `output_type`, `normal_label`, `inputs`,
  `template`, `params`, `window`, `boards`, `budget`, `name`, `version`, `representative_samples`,
  `manifest_path`; one proposal function and one validation function per answer, following the
  "Validation per answer" list of data-model.md and research R7/R8 for proposals, each returning a
  refusal message in the words `caravan validate` would use. Templates and boards come only from
  `default_registry()` of each registry (FR-010). Makes T010 pass.
- [ ] T014 [US1] Implement `src/caravan/init/session.py` for the dialogue mode: the question order
  of data-model.md ("Asked" column), each question printed to standard error with its proposal and,
  for columns, one line per column with its proposed type and reason; an empty line accepts; `<` pops
  the history; the inputs question takes one line of edits like `dlc=number, b2=-` or empty to accept
  all; the boards question lists every board with its RAM and flash as `caravan boards` prints them;
  the budget question explains in one sentence what it gates and labels the proposal's source
  (research R8); a summary of every answer, including `version` and `representative_samples`,
  numbered so a number revisits that answer; states `profiling → asking → summary → writing → done`
  as data-model.md describes. Reading is a function passed in, so tests can feed lines.
- [ ] T015 [US1] Implement `src/caravan/init/write.py` with a first version of the writer: build the
  mapping of contracts/manifest-output.md "Always written" and "Written only when needed" from the
  answer set via `dump_commented` (T007), with the dataset path written relative to the manifest's
  directory (FR-019); write to a temporary file in the target's directory, run `load_manifest` on it,
  `os.replace` it into place when valid and delete it otherwise; return the findings when invalid.
  (Comments and default-omission are completed in US2.)
- [ ] T016 [US1] Complete `src/caravan/cli/init.py`: turn arguments into a session, run it, map
  outcomes to the exit codes of contracts/cli-init.md (0 written and valid; 1 data `init` cannot set
  up, or findings under `--no-input`; 2 usage, unreadable data, abort; 3 when `init` offered a
  choice `validate` refuses), print the findings with `render_finding` in the dialogue and return to
  the owning question by path prefix (research R10: `model.params` → parameters,
  `preprocessing.window_size` → window, `export.targets` → boards, `output_features[0].*` → budget),
  catch `KeyboardInterrupt` and `EOFError` as an abort, print the written path alone on standard
  output. Makes T011 pass.

**Checkpoint**: quickstart steps 1, 4 (dialogue half), 6 and 7 pass by hand; T009–T011 green.

---

## Phase 4: User Story 2 — A manifest the author can read and change by hand (P2)

**Goal**: the written file is short — nothing the template, the board or the schema would supply on
its own — and commented section by section.

**Independent test**: generate with every proposal accepted; the file has no key from the "Never
written by `init`" list of contracts/manifest-output.md, a comment above every section, the left-out
columns listed; change one value by hand and it still validates.

### Tests for US2

- [ ] T017 [P] [US2] Write `tests/unit/test_init_write.py`: for the synthetic answers, the output
  equals the example in [contracts/manifest-output.md](./contracts/manifest-output.md) byte for byte
  (dataset path adjusted to the test's location); none of `defaults`, `trainer`, `random_seed`,
  `preprocessing.split`, `export.quantization`, `export.formats`, `export.test_windows`, per-feature
  `preprocessing` or `encoder`, `loss`, `threshold`, `clip`, `threshold_percentile` appears;
  `normal_label` appears only for an anomaly output whose normal value is not `normal`; the header
  names the dataset path and points at `docs/ref/manifest/index.md` and `caravan render`; every
  top-level section has one comment line; a left-out column appears in a comment above
  `input_features` with its reason, and no such line appears when none is left out; the field lines
  (excluding comments and blank lines) are no more than those of `examples/picket-mlp.yaml`
  (SC-004); replacing `hidden: [32, 16]` by `hidden: [24]` in the text still validates.

### Implementation for US2

- [ ] T018 [US2] Complete `src/caravan/init/write.py`: the header and section comments, the
  left-out-columns comment, flow style for each input feature and for number lists, the section order
  of the schema, and the omission rules of contracts/manifest-output.md; no date or version stamp
  (FR-020). Makes T017 pass.

**Checkpoint**: quickstart step 1's file reads as the contract's example; T017 green.

---

## Phase 5: User Story 3 — The same setup without questions (P3)

**Goal**: every answer from options or proposals, nothing asked; identical bytes to the dialogue.

**Independent test**: quickstart steps 2–5.

### Tests for US3

- [ ] T019 [P] [US3] Extend `tests/contract/test_init_contract.py` for `--no-input`: with only
  `--dataset` on the synthetic fixture, exit 0 and a valid file; with no options, exit 2 naming
  `--dataset`; with `--output-type number` on the synthetic fixture (no budget proposal), exit 2
  naming `--budget`; an existing target without `--overwrite` exits 2 naming `--overwrite`, with it
  exit 0; `--template mlp --output-type anomaly` on the anomaly fixture exits 2 naming `autoencoder`
  and writes nothing; `--input dlc=number --input b2=-` changes exactly those two columns; a
  `--window` too short for the conv1d starter exits 1 with the template's `window_fit` finding and
  writes nothing; standard input is never read under `--no-input`.
- [ ] T020 [P] [US3] Write `tests/integration/test_init_byte_identical.py`: for each of the
  synthetic, frames and anomaly fixtures, the piped dialogue (dataset path, then empty lines) and
  `--no-input --dataset …` write byte-identical files; two `--no-input` runs write byte-identical
  files (FR-020, US3 scenario 3).
- [ ] T021 [P] [US3] Write `tests/integration/test_init_combinations.py` (SC-002, SC-006): for each
  of the synthetic, frames and anomaly fixtures, for each output type `init` offers for the proposed
  output column, for each template it offers for that type, and for each registered board, run
  `--no-input` with a budget given where there is no proposal; every run exits 0 and the file passes
  `load_manifest`. Register a third-party template with a starter in the test's registry and assert
  it is offered and its manifest validates.

### Implementation for US3

- [ ] T022 [US3] Complete the `no-input` mode in `src/caravan/init/session.py` and the option
  handling in `src/caravan/cli/init.py`: options fill answers first and are never asked; `--input`
  parses `<column>=<type>` and `<column>=-`; `--params` is read with the YAML reader in `_yaml.py`
  (add a `read_text_mapping(text)` there, flow mapping only); an option value `init` would not offer
  is a usage error listing the values it would; a missing answer without a proposal is a usage error
  naming its option; under `--no-input` standard input is never read. Makes T019–T021 pass.

**Checkpoint**: quickstart steps 2–5 pass; the whole suite is green in the default installation.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T023 [P] Add `caravan init` to `docs/ref/cli.md`: a row in "By task" ("Write a first manifest
  from your data, by answering questions"), an entry under "Commands" declared like the others with
  every option and the exit codes of contracts/cli-init.md, so
  `tests/contract/test_docs_reference.py::test_every_command_has_exactly_one_entry` passes.
- [ ] T024 [P] Add `caravan init` to the command list in `README.md` ("write a first manifest by
  answering questions") and a short paragraph in `docs/intro/tutorial01.md` where the manifest is
  first written: the reader may instead run `caravan init` and compare its file with the one the
  tutorial builds; keep every `# step:` block of the tutorial unchanged so its CI run is unaffected.
- [ ] T025 [P] Update `docs/roadmap.md` per its own rules (append, never rewrite `planned`): a row
  for `caravan init` (feature 013, constitution v4.3.0), and two rows for the owner's later steps of
  2026-11-16 — a full-screen interface as an optional extra, and editing an existing manifest (needs
  its own amendment).
- [ ] T026 Run `pytest -q` and `pytest tests/layering -q` in a default installation on Python 3.13
  and 3.15; run quickstart.md steps 1–7 by hand and record the results, including the measured
  profiling time on a million rows, in a "Status at close" section at the end of this file.
- [ ] T027 Mark the spec's checklist and the PR description up to date: what is in, what is
  deliberately not (image inputs, editing, the full-screen extra), and the measured SC-001/SC-005
  figures.

---

## Dependencies

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish.
- US2 changes only `write.py`, which US1 creates; it can start once T015 exists.
- US3 needs the session (T014) and the CLI (T016); its tests T019–T021 can be written as soon as
  Phase 2 is done.
- T008 must precede T011, T016, T019 and T023 (the verb must exist).
- T003 precedes T004 and T005; T006 precedes T012; T007 precedes T015.

## Parallel opportunities

- Phase 2: T003, T006, T007 together; then T004 and T005 together; T008 alongside any of them.
- US1: T009, T010, T011 together (three test files); T012 and T013 together after them.
- US3: T019, T020, T021 together.
- Polish: T023, T024, T025 together.

## Implementation strategy

**MVP is US1**: after Phase 3, an author can run `caravan init`, accept the proposals and get a
manifest that validates — the owner's complaint answered. US2 makes the file pleasant to keep; US3
makes the whole feature testable in CI without a terminal and is what proves SC-002 for every
combination, so the pull request is not ready to merge before it. Push in validated batches: one
push after Phase 2, one after each story, one after Polish.
