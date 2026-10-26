# Implementation Plan: Documentation Site and the First Model on a Board

**Branch**: `009-docs-and-board-guide` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-docs-and-board-guide/spec.md`

## Summary

**Two deliverables for `v0.1.0rc3`.**

**1. A documentation site.**
- Built with Sphinx 9.2.0 and MyST from `docs/`, published to GitHub Pages on each release and by
  hand.
- Pages: a landing page, a CLI reference, a manifest reference, a rules page, a compatibility page,
  the roadmap, and three guides (try-it, own project, LoRa32).
- One test keeps the references complete against the argument parser, the schema models, the rule
  table and the registries.

**2. The first exported model on a microcontroller.**
- A PlatformIO firmware project in `examples/lora32/` runs the model on a handful of test-part
  windows.
- It shows on the OLED and the serial port, for each window, the decision, the expected class and
  agreement with the host's int8 reference, plus the arena the runtime measured.
- What makes it model-agnostic is one schema addition: `export.test_windows` (default 0, read by
  the export stage only). It writes `model/test_windows.h`, holding the windows, their expected
  classes, the host's int8 scores and decisions, and the helpers that fill and decide.
- The firmware builds in a workflow that blocks a release and runs on pull requests touching the
  export. The owner runs it on the board.

## Technical Context

**Language/Version**:
- Python ≥ 3.13 for Caravan. The site builds on 3.13, because Sphinx 9.2 needs ≥ 3.13.
- C++17 for the firmware, built by Xtensa GCC 14.2 (the `toolchain-xtensa-esp-elf 14.2.0+20251107`
  that PlatformIO ships).

**Primary Dependencies**: nothing is added to the package, its extras or the default installation.
- **Documentation:** `sphinx==9.2.0` and `myst-parser==5.1.0`, in a `docs` dependency group. It is
  not an extra and is not published.
- **Firmware, outside the package:**
  - PlatformIO Core 6.2.0;
  - `platformio/espressif32 @ 6.13.0` (ESP-IDF 5.5.3);
  - `espressif/esp-tflite-micro == 1.4.1`, with ESP-NN, locked in `dependencies.lock`.

**Storage**: files.
- The export writes `model/test_windows.h` and records `test_windows` in `export.json`.
- Board runs are recorded as Markdown under `docs/board-runs/`.

**Testing**: pytest, with the suites split as before.
- **New in the core suite:** the docs-reference test (contract); `export.test_windows` schema tests
  (unit).
- **New in the `train` suite:**
  - the test windows: selection, header content, cache behaviour;
  - a host `g++` compile of the generated `test_windows.h` together with `model_data.h`, extending
    feature 004's host compile.
- **The firmware build** is a workflow, not a pytest test.
- **The board run** is manual, by the owner.

**Target Platform**:
- the documentation: GitHub Pages;
- the firmware: LILYGO LoRa32 (ESP32, Xtensa LX6, 240 MHz, 4 MB flash), every common revision,
  which the `esp32` board description covers.

**Project Type**: CLI and library, plus documentation and an example firmware project.

**Performance Goals**: none on hardware. The firmware reports no timing (FR-006). The firmware
workflow's cold build time is measured and recorded, not targeted.

**Constraints**:
- Changes that touch only documentation start no workflow.
- The site describes a release.
- Test windows come from the same split code as the accuracy gate.
- The firmware needs no component beyond esp-tflite-micro.
- Nothing about hardware is claimed before the owner's run.

**Scale/Scope**: about 8 new documentation pages and 3 rewritten ones. One schema field, one export
artifact, one refactor shared by quantize and export, one firmware project of about 6 source files,
and two workflows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I — declarative, every field read | `export.test_windows` is a declared field with a documented default, read by the export stage. The firmware needs no edit of framework code, and the model-specific parts come from generated headers | pass |
| II — embedded only | the landing page states scope and non-goals. The guide ends on a microcontroller | pass |
| III — reproducible | the test windows come from the manifest, the dataset version and the split seed. The export's key moves with them. The firmware pins the platform, the ESP-IDF and the component, and the lock file is committed | pass |
| IV — labeled | the arena figure is `measured` with the board everywhere it appears. No timing anywhere. The compatibility page shows each board at the rung it reached; compiling is stated as compiling, not as a rung | pass |
| V — budgets as gates | unchanged. The test windows exist only after a passed gate, because the export needs a quantized model | pass |
| VI — the data is the author's | default `0` puts no data in an export set unasked. The guide uses the synthetic fixture only | pass |
| VII — targets are data | no board added. The LoRa32 is an `esp32`, and its revisions differ only in firmware pins, not in the description | pass |
| VIII — no lock-in | the firmware uses the vendor's open component and an open build tool. The exported files are toolchain-independent | pass |
| IX — schema honesty | the addition is optional with a default, so it stays `caravan/v0.2` (not breaking). Recorded in `docs/manifest-changes.md` | pass |
| X — real models | the guide serves the owner's own projects (Story 4). The example is the pilot | pass |
| XI — no Claude in learning | no model is trained, labeled or evaluated by Claude. The test windows are produced by the pipeline from the fixture | pass |
| XII — small core | no verb, no runtime dependency, no extra. The site tools are a dependency group. The firmware's dependencies are the firmware's | pass |
| Pipeline contract | the header is a declared artifact (`artifacts_from`), and its count is in `export.json` | pass |
| Verification ladder | the ESP32 has no emulated rung. The board run is the measured rung and is recorded with board, firmware, clock and toolchain | pass |
| Resources & cost | documentation-only changes run nothing: no new path in `ci.yml`, and no documentation path among the firmware workflow's triggers. The firmware build runs on release and on PRs touching the export. The site publishes on release or by hand. No cash cost | pass |
| Credentials | none in the firmware or the repository. No radio and no Wi-Fi | pass |

**Post-implementation re-check** (T044, 2026-10-26): all rows still pass. Two things changed in
the building, both recorded in research:
- the export stage kept `reads_dataset=False` (R4);
- the test-windows header gained `kOutputPosition` and `kExportedBy`, so the firmware needs no
  model-specific name (R8).

Neither touches a principle.
- **Numbers on the new pages:** each has a source. The linker figures are labeled `estimated`, the
  arena figures in the guide's pictures are marked as placeholders, and no page carries a timing
  figure.
- **The firmware:** contains no credential and no radio or network code.
- **The pages:** are in English.

**Post-design re-check** (after research, data model and contracts): all rows still pass. Three
design choices were checked against the constitution specifically:
- **The manifest field instead of a CLI option** (R4): Principle I, Principle III, and the pipeline
  contract's declared artifacts.
- **Workflows triggered only by release, dispatch and code paths** (R2, R6): Resources & Cost
  Discipline.
- **The compatibility page's "built" state** (R10): Principle IV, no label on a non-rung.

Nothing needs a Complexity Tracking entry.

## Project Structure

### Documentation (this feature)

```text
specs/009-docs-and-board-guide/
├── plan.md              # this file
├── research.md          # R1–R10
├── data-model.md        # the field, the header, the skeleton, the firmware, the run record, the pages
├── quickstart.md        # validation scenarios 1–6
├── contracts/
│   ├── test-windows.md  # model/test_windows.h
│   ├── board-output.md  # serial and OLED output, the run record block
│   └── docs-site.md     # navigation, page shapes, checks, publishing
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/caravan/
├── manifest/schema/export.py      # + test_windows (0–64; >0 needs c_array)
├── data/test_part.py              # NEW: the test part, shared by quantize and export
├── stages/quantize.py             # uses data/test_part.py
├── stages/export.py               # new reads (split, seed, test_windows), writes model/test_windows.h
├── export/test_windows.py         # NEW: selection, host reference, header text
├── export/skeleton.py             # + arena_used_bytes report
└── runtime/inspect.py             # + the output's score step (the int8 tensor before DEQUANTIZE)

examples/
├── picket-mlp.yaml                # + test_windows: 16
└── lora32/                        # NEW: PlatformIO project
    ├── platformio.ini             # envs lora32, lora32-v1
    ├── CMakeLists.txt
    ├── sdkconfig.defaults
    ├── dependencies.lock
    ├── .gitignore                 # src/model/, .pio/, managed_components/, sdkconfig.*
    └── src/
        ├── CMakeLists.txt
        ├── idf_component.yml
        ├── main.cc
        ├── oled.h, oled.cc
        ├── font5x7.h
        ├── board_pins.h
        └── model/                 # the export's files are copied here (ignored)

docs/
├── conf.py                        # NEW: Sphinx + MyST, version from CARAVAN_VERSION
├── index.md                       # NEW: landing page and toctree
├── try-it.md                      # "Your own data" moves out
├── guides/own-project.md          # NEW
├── guides/lora32.md               # NEW, with board-* step blocks
├── reference/cli.md               # NEW
├── reference/manifest.md          # NEW
├── reference/rules.md             # NEW
├── compatibility.md               # NEW
├── board-runs/index.md            # NEW (the owner's records join it)
├── roadmap.md, budgets.md, manifest-changes.md, releases/0.1.0.md   # existing, updated
└── design/, research/             # excluded from the site

tests/
├── contract/test_docs_reference.py   # NEW
├── unit/test_export_schema.py        # + test_windows
├── train/test_test_windows.py        # NEW
└── support_docs.py                   # step names may contain hyphens

.github/workflows/
├── ci.yml        # paths unchanged: documentation-only changes start nothing
├── docs.yml      # NEW: build with -W and deploy; workflow_call + workflow_dispatch
├── firmware.yml  # NEW: guide blocks + pio run, both envs; workflow_call + pull_request paths
└── release.yml   # check also builds the site with -W; release needs firmware; docs after release

pyproject.toml    # + [dependency-groups] docs
README.md         # shortened, points to the site
```

**Structure Decision**: one project.
- The firmware lives under `examples/` because `try-it.md` already fetches that directory from the
  tagged source. The board guide fetches nothing new.
- The test-part code moves to `data/` because two stages need it. Duplicating it would let the
  windows and the gate drift apart.

## Order of Work

1. **Test windows end to end in Python:** the shared test part, the schema field, the export
   artifact, the host compile, the example manifest. This is what the firmware needs.
2. **The firmware, built locally against the example's export:** both environments. Every defect
   in exported C found here is fixed in Caravan (FR-008) and recorded in research R8.
3. **The firmware and docs workflows,** and the release workflow wiring.
4. **The site:** `conf.py`, the landing page, the references with their drift test, compatibility,
   guides, roadmap, README.
5. **Local validation:**
   - lint and format;
   - the full suite in the CI matrix's environments;
   - the site build with `-W`;
   - the firmware build.
6. **Pull request.**
7. **After the merge:**
   - the owner's board run (SC-001, SC-002), then their own project (SC-007);
   - the run record and the compatibility update (SC-008);
   - rc3 on the owner's go-ahead.

## Complexity Tracking

No constitutional violations to justify.
