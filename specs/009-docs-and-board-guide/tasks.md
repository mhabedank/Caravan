# Tasks: Documentation Site and the First Model on a Board

**Input**: `/specs/009-docs-and-board-guide/` (spec, plan, research, data-model, contracts,
quickstart)

**Tests**: requested by the constitution's workflow gates. Tests come before their implementation.

**Cost rule (constitution 4.1.0)**: commit and push to `009-docs-and-board-guide` without a PR. Open
one PR when every task through T046 is done and the local validation (T045) is green. T047–T051
need the owner and the board, and follow the merge.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Add a `docs` group to `[dependency-groups]` in `pyproject.toml`:
  `sphinx==9.2.0`, `myst-parser==5.1.0` (research R1).
  - It is not an extra and does not touch `[project.optional-dependencies]`.
  - Add `_site/` to `.gitignore`.
  - Run `uv lock` and confirm the dependency-budget test still passes:
    `uv run pytest tests -k budget -q`.
- [ ] T002 [P] Widen the step-name pattern in `tests/support_docs.py` from `[a-z]+` to `[a-z-]+`,
  and update its docstring. Add a case to the existing tests of `support_docs` (find them with
  `grep -rl support_docs tests`): a block `# step: board-copy` is read.

---

## Phase 2: Foundational (blocks US1)

- [ ] T003 Write `tests/train/test_test_part.py`. On the synthetic fixture, with the example
  manifest's resolved inputs, the new `caravan.data.test_part.test_part(records, inputs, output)`
  returns exactly the windows and targets the quantize stage measured, in the same order. Compare
  against the sample count that `quantization.json` records for a run of the example.
- [ ] T004 Create `src/caravan/data/test_part.py` holding the test-part formation now inside
  `src/caravan/stages/quantize.py` (`plan_windows`, `split_for`, `assemble_samples`, `select` of
  the test indices):
  - It returns test features, test targets and the label list.
  - `stages/quantize.py` calls it. Its behaviour and record are unchanged: the existing quantize
    tests pass unchanged.
  - The module imports numpy only inside functions, like its neighbours, and is declared where
    feature 008 declared the extra-only modules for the layering test.
- [ ] T005 [P] Add `output_score_step(model_path, output_name) -> float` to
  `src/caravan/runtime/inspect.py`: the scale of the int8 tensor that the output's DEQUANTIZE reads,
  or of the output itself when it is int8. Test it in `tests/verify/` on
  `tests/fixtures/models/example-typed.tflite`: the step is positive, and for a softmax output it
  equals 1/256.

**Checkpoint**: the test part has one implementation, and the score step can be read.

---

## Phase 3: User Story 1 — the model on the LoRa32, answers on the OLED (P1)

**Goal**: `caravan export` writes test windows. A firmware project in `examples/lora32/` builds for
both LoRa32 environments. The guide's blocks build it in a workflow that blocks a release.

**Independent test**: quickstart §2 and §3. On the board: quickstart §4 (owner, T047).

### Tests

- [ ] T006 [P] [US1] Add to `tests/unit/test_features_schema.py` (or a new
  `tests/unit/test_export_schema.py`) the cases for `export.test_windows`, data-model §1:
  - default `0`;
  - `0` to `64` accepted;
  - `65` and `-1` refused at `export.test_windows`;
  - `> 0` without `c_array` in `export.formats` refused at `export.test_windows`, naming
    `export.formats`;
  - `render` shows the default.
- [ ] T007 [P] [US1] Write `tests/train/test_test_windows.py`, on the synthetic fixture with
  `test_windows: 8`:
  - `model/test_windows.h` exists and is listed in `export.json` with its digest.
  - `export.json["test_windows"]` records asked 8, written 8, available, rule `round-robin by class`,
    per-class counts with every label present, and `score_step` > 0.
  - Round-robin: the first four windows have four different expected classes.
  - The host decisions equal the argmax of the host scores. The host scores equal
    `run_model(quantized, window)` for each window.
  - With `test_windows: 0`, there is no header and no `test_windows` key.
  - Asking for more than the test part holds writes all of them and records both numbers.
  - Changing only `test_windows` re-runs export alone: build, train and quantize are `reused`.
  - Unchanged, a re-run reuses export too.
  - A `number` output (use `write_number_dataset` from `tests/support.py`) gives rule
    `test order`, float expectations, and agreement by `score_step`.
- [ ] T008 [P] [US1] Write `tests/train/test_test_windows_compile.py`. It belongs in the train
  suite only, because `test_windows.h` needs a real export. Skip with a reason when `g++` is
  missing, matching `tests/unit/test_c_array_compiles.py`; the release `check` job runs on
  ubuntu-latest, which has it. Compile `model_data.cc` and a translation unit including
  `test_windows.h` with the host `g++ -std=c++17 -fsyntax-only -Wall -Wextra -Werror`, against a
  stub `tensorflow/lite/micro/micro_interpreter.h` that declares only what
  contracts/test-windows.md uses (`MicroInterpreter::input`, `TfLiteTensor` with `type`, `bytes`,
  `data.f`, `data.i32`).
- [ ] T009 [P] [US1] Extend `tests/unit/test_skeleton.py`:
  - the generated runner calls `interpreter.arena_used_bytes()` after `AllocateTensors()`;
  - it declares `static void ReportArena(size_t bytes);`;
  - its comment says the figure is measured on the board it runs on.

### Implementation

- [ ] T010 [US1] Add `test_windows: int = Field(default=0, ge=0, le=64)` to `ExportSpec` in
  `src/caravan/manifest/schema/export.py`.
  - Add a model validator: `test_windows > 0` without `"c_array"` in `formats` →
    `field_error("export.test_windows", ...)`, naming `export.formats`.
  - Add its comment: why 64, and why the default is 0 (Principle VI).
- [ ] T011 [US1] Create `src/caravan/export/test_windows.py`:
  - **`select(targets, labels, count, output_type)`:** round-robin by class in label order, keeping
    test order within a class. For `number`, the first `count` windows.
  - **`host_reference(model_path, windows, output)`:** scores via `caravan.runtime.measure.run_model`.
    Decisions are argmax for category, the threshold from the resolved output for binary, and the
    value for number.
  - **`header(...)`:** the text of contracts/test-windows.md, with:
    - its constants, data arrays and the inline `FillWindow`, `Decide` and `DecisionName`;
    - `namespace caravan_windows`;
    - `static const` arrays;
    - the provenance comment;
    - floats written with `repr` + `f`.
  - Reuse `_C_TYPES` and the input bindings of `src/caravan/export/skeleton.py` rather than
    redefining them.
- [ ] T012 [US1] Wire it into `src/caravan/stages/export.py`:
  - `SPEC.reads_dataset=True`;
  - add the reads `export.test_windows`, `preprocessing.split`, `random_seed`;
  - in `_skeletons`/`artifacts_from`, add `model/test_windows.h` when `export.test_windows > 0`.
  - In `run`, when `> 0`: call `caravan.data.test_part.test_part(context.records(), …)`, then
    `select`, `host_reference` and `output_score_step`. Write the header, and add the
    `test_windows` record to `export.json` (data-model §2).
  - Print one summary line in `src/caravan/cli/export.py`: `test windows: 16 of 21 (round-robin
    by class)`.
- [ ] T013 [US1] Add `ReportArena` to `src/caravan/export/skeleton.py`:
  - After `AllocateTensors()` succeeds, the runner calls
    `ReportArena(interpreter.arena_used_bytes());`.
  - The declaration and the comment above `kArenaBytes` say:
    - the figure is `measured` on the board it runs on;
    - set the arena from it with a margin;
    - the floor stays a floor.
  - Update `FLOOR_CAVEAT` in `src/caravan/export/artifacts.py` so it names the runner's report
    beside emulated verification.
- [ ] T014 [US1] Set `test_windows: 16` under `export:` in `examples/picket-mlp.yaml`, with a
  one-line comment. Add `model/test_windows.h` to the "What you get" list of `docs/try-it.md`:
  16 windows of the test part with the host's int8 answers, for the board guide. Check that `tests/integration/test_try_it_guide.py` and the README step still
  pass.
- [ ] T015 [US1] Create the PlatformIO project `examples/lora32/` per data-model §4 and research R3
  and R5:
  - **`platformio.ini`:**
    - `[env]` with `platform = platformio/espressif32 @ 6.13.0`, `framework = espidf`,
      `board = ttgo-lora32-v21`, `monitor_speed = 115200`;
    - `[env:lora32]` and `[env:lora32-v1]`, the latter with `build_flags = -DCARAVAN_LORA32_V1`.
  - **`CMakeLists.txt`:** the ESP-IDF project, named `caravan_lora32`.
  - **`sdkconfig.defaults`:** 240 MHz; flash size 4 MB, DIO; main task stack 8192; the task
    watchdog off; `CONFIG_NN_SKIP_NUDGE` not set.
  - **`src/CMakeLists.txt`:** `idf_component_register` globbing `*.cc` and `model/*.cc`, with
    `INCLUDE_DIRS . model`.
  - **`src/idf_component.yml`:** `espressif/esp-tflite-micro: "==1.4.1"`.
  - **`.gitignore`:** `src/model/*` except `src/model/README.md`, `.pio/`, `managed_components/`,
    `sdkconfig.*` (except `sdkconfig.defaults`).
  - **`src/model/README.md`:** "the export's files go here; see docs/guides/lora32.md".
- [ ] T016 [P] [US1] Create `examples/lora32/src/board_pins.h`:
  - the default block: SDA 21, SCL 22, reset −1, address 0x3C, revision name `V1.3/V1.6/V2.x`;
  - the `#ifdef CARAVAN_LORA32_V1` block: SDA 4, SCL 15, reset 16, OLED supply GPIO 21 driven low,
    revision `V1.0`;
  - a comment that GPIO16 is the flash chip select on PICO-D4 revisions and is never driven there;
  - sources named (research R5).
- [ ] T017 [P] [US1] Create `examples/lora32/src/font5x7.h`:
  - a public-domain 5×7 ASCII font, characters 32–126, with its source and licence named in the
    header comment;
  - `examples/lora32/src/oled.h` / `oled.cc`: `OledInit(pins)` returns bool and never aborts;
    `OledClear()`, `OledLine(row, text)` and `OledShow()`;
  - the driver: `i2c_new_master_bus` plus `esp_lcd_new_panel_io_i2c` and
    `esp_lcd_new_panel_ssd1306`, with the IO settings of research R5;
  - a 1,024-byte framebuffer (page `y/8`, bit `y%8`) pushed with `esp_lcd_panel_draw_bitmap`;
  - a failed init leaves every call a no-op, so the run continues on serial (contracts/
    board-output.md).
- [ ] T018 [US1] Create `examples/lora32/src/main.cc` (`extern "C" void app_main()`), model-agnostic,
  using only `model_data.h`, `resolver.h` and `test_windows.h`:
  - **Setup:** OLED init, `CaravanResolver()`, `MicroInterpreter` with `kArenaBytes`, then
    `AllocateTensors`.
  - **On failure:** the halt-and-repeat error line.
  - **Arena:** `arena_used_bytes()`.
  - **Per window:** `FillWindow`, `Invoke`, `Decide`, the agreement and `max_diff_steps` rule of
    contracts/test-windows.md, the serial line, and the OLED screen held for 1.5 s.
  - **At the end:** the summary, then the run record block exactly as contracts/board-output.md
    shows. It reads `esp_get_idf_version()`, the CPU frequency, and a `CARAVAN_FIRMWARE` string
    defined in `platformio.ini` (the Caravan version), then holds.
  - No timing is printed (FR-006).
- [ ] T019 [US1] Build locally against the example's export:
  1. `uv run caravan export examples/picket-mlp.yaml`.
  2. Copy `model/{model_data.h,model_data.cc,resolver.h,test_windows.h}` into
     `examples/lora32/src/model/`.
  3. `pip install platformio==6.2.0` into a scratch venv.
  4. `pio run -e lora32` and `-e lora32-v1` in `examples/lora32`.

  Then:
  - Commit the generated `examples/lora32/dependencies.lock`.
  - Fix every error or warning that originates in Caravan's generated files, in Caravan's
    generators, not in the firmware (FR-008).
  - Record each one in research R8 with the message and the fix.
  - Record the cold build time, and the flash and static RAM figures `pio` prints, labeled
    `estimated`: they come from the linker for this firmware. The RAM figure excludes heap and the
    arena's actual use. A board measurement only comes from T047 (Principle IV).
- [ ] T020 [US1] Write `docs/guides/lora32.md`:
  - **Prerequisites:** try-it done, the board, a USB cable.
  - **How to tell the revision** (research R5) and which environment to pick.
  - **The USB-serial chip and the driver per OS,** the Linux `dialout` fix, and `pio device list`.
  - **Executable blocks:**
    - `# step: board-tools`: `pip install platformio==6.2.0`;
    - `# step: board-copy`: find the newest run (`run=$(ls -td runs/*/ | head -1)`) and copy its
      four files into `examples/lora32/src/model/`;
    - `# step: board-build`: `cd examples/lora32 && pio run -e lora32` (and back).
  - **The hardware block,** never run by CI: `# step: board-flash`, with
    `pio run -e lora32 -t upload` and `pio device monitor`.
  - **What the OLED and the serial port show,** quoting contracts/board-output.md, and what
    `agree`, `DISAGREE`, `over_one_step` and `measured` mean.
  - **Setting the arena** from the measured figure.
  - **Troubleshooting:** dark OLED (use serial, check the environment); the arena error; the
    auto-reset failing (IO0 to GND plus RST); the SD card out before flashing; the image upside
    down.
  - **Using your own model:** set `test_windows`, re-export, copy the four files; nothing else
    changes.
  - **Recording a run:** paste the record block into `docs/board-runs/<date>-lora32.md`.
- [ ] T021 [P] [US1] Create `docs/board-runs/index.md`: what a board run record is (data-model §5),
  that it is the evidence the compatibility page cites, and an empty list to be filled.
- [ ] T022 [US1] Create `.github/workflows/firmware.yml`:
  - **Triggers:**
    - `workflow_call`;
    - `pull_request` with `paths`: `src/caravan/export/**`, `src/caravan/stages/export.py`,
      `src/caravan/data/test_part.py`, `examples/lora32/**`, `examples/picket-mlp.yaml`,
      `.github/workflows/firmware.yml`. No documentation path: a change to `docs/guides/lora32.md`
      alone starts nothing (constitution, Resources & Cost Discipline). Its blocks are checked by
      the next code PR on these paths and by every release;
    - `workflow_dispatch`.
  - **Job:** ubuntu-latest, `astral-sh/setup-uv`, Python 3.13, `uv sync --extra train --extra
    verify`.
  - **Cache:** `actions/cache` for `~/.platformio/{packages,platforms,penv,.cache}` and
    `~/.cache/pip`, keyed on the hashes of `examples/lora32/platformio.ini` and
    `examples/lora32/dependencies.lock`.
  - **Run:**
    - run the export of the example;
    - extract and run the guide's `board-tools`, `board-copy` and `board-build` blocks with
      `tests/support_docs.py`, inside the uv environment;
    - then `pio run -e lora32-v1`.
  - **Report:** write the elapsed time and `pio`'s size lines to `$GITHUB_STEP_SUMMARY`.
  - **Permissions:** `contents: read`.
- [ ] T023 [US1] Wire the firmware check into `.github/workflows/release.yml`: a job `firmware`
  that `uses: ./.github/workflows/firmware.yml`, with `needs: [check]`. Add it to the `release`
  job's `needs`, so a firmware that does not build blocks the release (FR-009). Keep `verify` as it
  is.

**Checkpoint**: quickstart §2 and §3 pass locally, and the firmware builds for both environments.

---

## Phase 4: User Story 2 — find out how to use Caravan from one site (P1)

**Goal**: a site built with `-W`, whose references are complete against the code and which
publishes a release.

**Independent test**: quickstart §1.

### Tests

- [ ] T024 [P] [US2] Write `tests/contract/test_docs_reference.py` (research R7):
  - **CLI:** every subcommand of `caravan.cli.main.build_parser()` has a `## caravan <verb>`
    section in `docs/reference/cli.md`. Every option string of that subparser (from
    `_actions[*].option_strings`, except `-h`/`--help`) appears inside that section. `--version`
    and exit codes `0`–`4` appear in the page.
  - **Manifest:** walk `Manifest` and its nested pydantic models, including the input and output
    feature models and their per-type preprocessing models, into paths of the form
    `input_features[].preprocessing.normalization`. Each path must appear in backticks in
    `docs/reference/manifest.md`.
  - **Rules:** every value of a `RULE_*` constant in `caravan.manifest.errors` has a `### <id>`
    heading in `docs/reference/rules.md`. Every member of `RETIRED_RULES` has
    `### <id> (retired)`.
  - **Compatibility:** every template from `caravan.templates` registry discovery, every board in
    `src/caravan/targets/boards/`, and every implemented feature type appear in
    `docs/compatibility.md`.
  - **Messages:** each failure lists what is missing and from which page.
  - Imports only the core. It runs in the default job.

### Implementation

- [ ] T025 [US2] Create `docs/conf.py` (research R1):
  - `project = "Caravan"`;
  - `release = version` from `CARAVAN_VERSION`, else parsed from `src/caravan/__init__.py`
    textually, without importing Caravan;
  - `extensions = ["myst_parser"]`;
  - `source_suffix = {".md": "markdown"}`;
  - `exclude_patterns = ["design/**", "research/**", "_build", "conf.py"]`;
  - `myst_heading_anchors = 3`;
  - `html_theme = "alabaster"`;
  - `html_title = f"Caravan {release}"`.

  Show the version in the page footer too: alabaster `html_theme_options` or `html_context`.
- [ ] T026 [US2] Create `docs/index.md`, the landing page per contracts/docs-site.md:
  - what Caravan is;
  - what it is not;
  - install (the release URLs, matching README and try-it);
  - the pipeline line;
  - direct links to the five main sections;
  - the `{toctree}` in the navigation order of the contract;
  - "This site describes Caravan {sub-ref}`release`" or the equivalent substitution.
- [ ] T027 [P] [US2] Write `docs/reference/cli.md`: one section per verb (`validate`, `render`,
  `build`, `train`, `quantize`, `export`, `templates`, `boards`) in the shape of
  contracts/docs-site.md.
  - Purpose, arguments, options with defaults, what each reads and writes in the run directory,
    exit codes.
  - The global options and exit codes 0–4 from the docstring of `src/caravan/cli/main.py`, quoted
    exactly.
- [ ] T028 [P] [US2] Write `docs/reference/manifest.md`:
  - every field path of `caravan/v0.2` as a table per section: type, default, allowed values, read
    by, rules;
  - the per-type keys marked with their type;
  - `export.test_windows` included;
  - the complete example manifest at the end.

  Sources: `src/caravan/manifest/schema/*.py`, `src/caravan/manifest/resolve.py` (defaults) and
  each stage's `SPEC.reads`.
- [ ] T029 [P] [US2] Write `docs/reference/rules.md`:
  - one `### <id>` per rule in `src/caravan/manifest/errors.py`, grouped by prefix (V, CF, B, T,
    DS, X and the others present);
  - for each: what it checks, where it is reported, how to fix it;
  - retired identifiers as `### <id> (retired)`, with what replaced them, from
    `docs/manifest-changes.md` and the specs.
- [ ] T030 [US2] Add the `orphan`/toctree placement for every existing page under `docs/` per
  contracts/docs-site.md, and fix every warning `sphinx-build -W` reports in the existing pages:
  - `try-it.md`, `roadmap.md`, `budgets.md`, `manifest-changes.md`, `releases/0.1.0.md`.
  - Turn links into `design/` and `research/` into absolute GitHub URLs.
- [ ] T031 [US2] Create `.github/workflows/docs.yml`:
  - **Triggers:**
    - `workflow_call` with input `tag`;
    - `workflow_dispatch` with input `tag`, default empty. Resolve empty to the latest release tag
      with `git describe --tags --abbrev=0` after a full fetch.
  - **Build job:** check out the tag, `uv sync --group docs` on Python 3.13, then
    `CARAVAN_VERSION=<tag without v> uv run sphinx-build -W -b html docs _site`, then
    `actions/upload-pages-artifact@v5` with `path: _site`.
  - **Deploy job:** `actions/deploy-pages@v5` in environment `github-pages`.
  - **Permissions:** `contents: read`, `pages: write`, `id-token: write`.
  - Precede the build with `actions/configure-pages@v6` (no `enablement`).
- [ ] T032 [US2] In `.github/workflows/release.yml`, add a step to the `check` job after the
  suite: `uv sync --group docs` and `uv run sphinx-build -W -b html docs _site`. A broken link or an
  unlisted page then blocks the release before anything is tagged (FR-020). Then call the docs
  workflow: a job `docs` that `uses:
  ./.github/workflows/docs.yml`, with `needs: [check, release]` and `tag:
  ${{ needs.check.outputs.tag }}`. Its permissions block grants `pages: write` and
  `id-token: write` to that job only.
- [ ] T033 [US2] Leave the CI paths of `.github/workflows/ci.yml` unchanged: no new documentation
  path (constitution, Resources & Cost Discipline; research R7).
  - The completeness test (T024) runs on every PR that touches code, which is where code and pages
    drift apart.
  - It also runs in the release workflow's `check` job, which runs the whole suite.
  - Add a comment to `ci.yml` next to the existing exceptions saying that the new pages are
    deliberately not listed, and why.

**Checkpoint**: quickstart §1 passes. A removed option fails the test, and an unlisted page fails
the build.

---

## Phase 5: User Story 3 — know what works today and what is planned (P2)

**Goal**: one compatibility page with provenance, and the roadmap on the site.

**Independent test**: decide from `docs/compatibility.md` alone whether `category` input on
`stm32h743` works today, and how far it is verified.

- [ ] T034 [US3] Write `docs/compatibility.md`:
  - **Input types:** `number`, `category` (with dense and one-hot encoders), `binary`.
  - **Output types:** `category`, `binary`, `number`, each with its budget key and decision.
  - **Ludwig's absent types,** each with the reason (feature 008 research, section 5).
  - **Templates:** `mlp`, `conv1d`, with their parameters linked to the reference.
  - **Boards table:**
    - board, core, clock, RAM, flash, accelerator;
    - verification state per research R10, with dates and the evidence linked: `esp32` built in
      the firmware workflow (date of T019), not run; `s32k144` and `stm32h743` export only, never
      compiled for;
    - emulator support from each board's description.
  - **Python versions per installation:** core 3.13–3.15, `train` 3.13, `verify` 3.13–3.14.
  - **The operators** the export can emit, from `src/caravan/export/methods.py`, and which the
    accelerators cover.
  - **Quantization:** int8 only implemented.
  - **Formats:** `flatbuffer`, `c_array` (`onnx` refused).
  - **Stages:** implemented vs planned, with a link to the roadmap.
  - **Known limits:** the deferred export-with-runtime-only, and the SC-006 note of `pace-cnn` if
    the owner has decided it.
- [ ] T035 [US3] Update `docs/roadmap.md` (FR-017):
  - a v0.1 row for feature 009 (documentation site, test windows, LoRa32 guide; state `in
    progress`);
  - the rc3 goal paragraph quoting the owner's goal of 2026-10-26;
  - absolute GitHub URLs for links into `design/` and `research/`;
  - no other row rewritten (the file's own rules).

**Checkpoint**: T024's compatibility check passes, and the page answers the independent test.

---

## Phase 6: User Story 4 — start an own project from own data (P2)

**Goal**: a guide from a CSV of one's own to a manifest, ending in the board guide.

**Independent test**: quickstart §5 (owner, T049), and, without the board, a CSV not from the
fixture reaching `caravan export` by following the guide.

- [ ] T036 [US4] Write `docs/guides/own-project.md`:
  1. Lay out the CSV directory and its header row.
  2. Choose each column's type, with examples: a code is a `category`, a measurement a `number`,
     yes/no a `binary`.
  3. Choose the output and its budget.
  4. Choose the window size.
  5. Choose the split, and when to use `fixed`.
  6. Choose the template and its parameters.
  7. Choose the boards and their budgets.
  8. Set `test_windows`.
  9. Run `validate`, `render`, `export`.
  10. Read the report.
  11. Go to the board guide.

  Each choice links its entry in the manifest reference. Absorb the "Your own data" section of
  `docs/try-it.md`, so nothing is duplicated.

  The worked example manifest is one ```yaml block whose first line is
  `# example: own-project`. T038 reads exactly that block.
- [ ] T037 [US4] Replace the "Your own data" section of `docs/try-it.md` with two sentences and a
  link to the own-project guide. The step blocks are untouched. Run
  `uv run pytest tests/integration/test_try_it_guide.py -q`.
- [ ] T038 [US4] Validate the own-project guide by following it once with a CSV derived at test time
  from the fixture, renamed columns and a binary output: `write_binary_dataset` in
  `tests/support.py`. Add `tests/train/test_own_project_guide.py`, which writes that CSV and the
  manifest the guide's worked example shows (extract it from the guide's ```yaml block marked
  `# example: own-project`), and runs it through `export` with `test_windows: 4`.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T039 [P] Shorten `README.md` to:
  - what Caravan is and is not;
  - the status;
  - the install lines (the `pip install "caravan-ml @ ` line stays first, because the release
    workflow reads it);
  - the readme `# step: readme` block;
  - a link to `https://mhabedank.github.io/Caravan/`.

  Run the tests that read the README.
- [ ] T040 [P] Add the `export.test_windows` addition to `docs/manifest-changes.md`: optional,
  default 0, stays `caravan/v0.2`, refused by an rc2 build as unknown (research R4).
- [ ] T041 [P] Add an rc3 paragraph to `docs/releases/0.1.0.md`: the site, test windows, the LoRa32
  guide, and what the board run will establish. No version bump in this feature, because the
  release is the owner's decision.
- [ ] T042 Run the site build locally: `uv run --group docs sphinx-build -W -b html docs _site`.
  Fix every warning, then open `_site/index.html` and check:
  - each main section is one click away (SC-005);
  - every page shows the version.
- [ ] T043 Re-read every number the new pages quote (sizes, counts, versions) against its source (a
  run report, a registry, a test). Remove any number without one (Principle IV, gate before
  reporting a number).
- [ ] T044 Re-run the constitution check of `plan.md` against what was built. Note any change in
  research R8 or in the plan.
- [ ] T045 Local validation, as CI will run it:
  - `uv run ruff check src tests && uv run ruff format --check src tests`;
  - `pytest tests/unit tests/contract tests/integration tests/layering` on 3.13, 3.14 and 3.15;
  - `--extra verify pytest tests/verify tests/unit tests/contract` on 3.13 and 3.14;
  - the train suite on 3.13;
  - the site build with `-W`;
  - the firmware build of T019 for both environments, from a clean `examples/lora32/src/model/`.
- [ ] T046 Mark every task `[X]`, commit, push, and open one draft PR for the feature. Its body
  follows the repository's PR template if one exists. Watch CI and drive it to green.

---

## Phase 8: After the merge — owner and board (not part of the PR)

- [ ] T047 [US1] The owner follows `docs/guides/lora32.md` from an empty directory on their LoRa32
  (quickstart §4).
  - Record whether it took at most two hours (SC-001).
  - Record the agreement and `max_score_diff_steps` (SC-002).
  - Every defect found is fixed in Caravan per FR-008, in a follow-up PR.
- [ ] T048 [US3] Commit the run record as `docs/board-runs/<date>-lora32.md` and list it in
  `docs/board-runs/index.md`. Update the `esp32` row of `docs/compatibility.md` to `measured`, on a
  LoRa32 with that date (SC-008).
- [ ] T049 [US4] The owner carries out one project of their own to the board with the site only
  (SC-007). Defects are fixed or listed under "Known limits" on the compatibility page.
- [ ] T050 The owner sets Settings → Pages → Source to "GitHub Actions" (research R2). After that,
  dispatch `docs.yml` once with the latest release tag (quickstart §6).
- [ ] T051 Needs T050 first: the release workflow's docs job fails while Pages is not set to
  "GitHub Actions". On the owner's go-ahead only: release `v0.1.0rc3` (version bump PR, release workflow).
  The release now builds the firmware before publishing and deploys the site after.

---

## Dependencies & Execution Order

- **Phase 1** → everything.
- **Phase 2** → US1 (T003/T004 before T011/T012; T005 before T012).
- **US1:**
  - tests T006–T009 → T010–T013 → T014;
  - T015–T018 can start in parallel with T010–T013, but T019 needs both;
  - T020 needs T019 (it quotes what worked);
  - T022 needs T020's blocks, and T023 needs T022.
- **US2:**
  - T024 first, then T025–T030 (T027–T029 parallel);
  - T031 needs T025, and T032 needs T031 and T023's release layout;
  - T033 is independent.
- **US3** needs T025 (page in the toctree), and T034 needs T019's date. T035 is independent.
- **US4** needs T028 (it links the manifest reference). T038 needs T036.
- **Polish** after all stories. T046 last.
- **Phase 8** after the merge. T050 before T051.

## Parallel Opportunities

- **Phase 2:** T005 beside T003/T004.
- **US1:**
  - T006, T007, T008, T009 together;
  - then T016 and T017 beside T010–T013;
  - T021 any time.
- **US2:** T027, T028, T029 together, beside T025/T026.
- **Across stories:** once Phase 2 is done, US2's T024–T029 can proceed beside US1's firmware work.
- **Polish:** T039, T040, T041 together.

## Implementation Strategy

1. **MVP is US1 through T019:** test windows exported and a firmware that builds for both LoRa32
   environments. That is the riskiest part (first cross-compile of Caravan's C) and the one the
   owner tests by hand.
2. **Then US2,** so the site exists to carry the guide.
3. **Then US3 and US4,** which are content on top of US2.
4. **One PR at T046.** The board run (T047) comes after the merge, and its defects follow in
   their own PR before rc3.
