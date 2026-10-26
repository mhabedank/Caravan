# Research: Documentation Site and the First Model on a Board

Feature 009. Every version, pin and default below was checked on 2026-10-26 against primary
sources: package registries, release pages, unpacked package tarballs and the vendors' schematics.
Where a source was contradictory or could not be checked, the entry says so.

## R1 — The site generator: Sphinx with MyST

**Decision.** Sphinx 9.2.0 with MyST-Parser 5.1.0 and Sphinx's bundled `alabaster` theme.
- They are pinned exactly in a `docs` dependency group in `pyproject.toml`. That group is not an
  extra and is not published.
- The site is built with `sphinx-build -W -b html docs _site` on Python 3.13.

**Rationale.** Sphinx is the only maintained, stable option whose own warnings cover all three
checks FR-020 asks for. `-W` turns each warning into a failed build. A trial build with these exact
pins confirmed each one (exit code 1):
- a page outside every toctree: `toc.not_included`;
- a broken link to a page: `myst.xref_missing`;
- a broken link to an anchor: `myst.xref_missing`, with `myst_heading_anchors = 3`.

Other settings:
- `exclude_patterns` keeps `design/` and `research/` out.
- A page that is deliberately unlisted says `orphan: true` in its front matter.
- `release` comes from an environment variable and goes into `html_title`, so it is on every page.

No plugin and no extra theme package are needed.

**Alternatives rejected:**

| Option | Why not (checked 2026-10-26) |
|---|---|
| MkDocs 1.6.1 + Material | MkDocs' last stable release is 2024-08-30. The `mkdocs` name now carries 2.0 pre-releases, an incompatible rewrite without plugins. Material 9.8.0 is marked "Inactive", requires `mkdocs<2`, and its own release notes set end of life on 2027-05-05. |
| Zensical 0.0.73 | Alpha, releasing every few days, and it has no check for pages missing from the navigation, which FR-020 requires. |
| ProperDocs 1.6.7 | A fork of MkDocs 1.6.1 with the validation keys. No release for seven months, no bundled theme (the obvious one is Material, see above), and the fork is publicly disputed. |
| Plain GitHub Pages (Jekyll), no build | No link or navigation check at all. FR-020 would have to be written by hand. |
| Furo theme | Optional polish for one more dependency, last released ten months ago. Alabaster ships with Sphinx. |

**Consequences:**
- `docs/index.md` carries the navigation as a MyST `{toctree}` directive. On github.com that block
  shows as a code block. The site is the place to read the documentation; the files stay readable
  on GitHub.
- Sphinx 9.2 needs Python ≥ 3.13, which is the project's floor anyway.

## R2 — Publishing to GitHub Pages

**Decision.** A workflow `.github/workflows/docs.yml` builds and deploys the site. It has two
triggers:
- `workflow_call`, from the release workflow after the release is published;
- `workflow_dispatch`, for the owner by hand.

It uses these actions:
- `actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5`;
- `permissions: {contents: read, pages: write, id-token: write}`;
- the `github-pages` environment.

The workflow checks out the release tag it is given, or by hand the latest release tag. So the site
always describes a released version (FR-019).

**The owner sets this once.** Settings → Pages → Build and deployment → Source: "GitHub Actions".
`configure-pages` cannot enable Pages with `GITHUB_TOKEN`: its `enablement` input needs a personal
token or an App with administration rights. A credential like that is not worth holding for a
one-time switch.

**CI minutes.** Changes that touch only documentation trigger nothing (Resources & Cost
Discipline). The site moves only on a release or by hand (FR-021).

**Rejected alternatives:**
- **Publishing on every push to `main` that touches `docs/`:** this violates the documentation-only
  rule, and the site would describe an unreleased `main`.
- **"Deploy from a branch":** it builds with Jekyll, so no Sphinx and no checks.

## R3 — Firmware toolchain: PlatformIO, espressif32 6.13.0, ESP-IDF 5.5.3, esp-tflite-micro 1.4.1

**Decision:**
- **PlatformIO Core** 6.2.0, installed with `pip` into the author's environment.
- **Platform** `platformio/espressif32 @ 6.13.0`. Its `framework-espidf ~3.50503.0` is ESP-IDF
  5.5.3, and its toolchain is `toolchain-xtensa-esp-elf 14.2.0+20251107`.
- **Board** `ttgo-lora32-v21`. Under `framework = espidf` the board only sets the MCU, flash and
  upload settings, which are identical across the LoRa32 revisions.
- **Components** `espressif/esp-tflite-micro == 1.4.1`, through the ESP-IDF Component Manager
  (`src/idf_component.yml`, supported by the platform since 5.2.0). `dependencies.lock` is
  committed so the resolved `esp-nn` stays fixed too (Principle III).

**Rationale:**
- esp-tflite-micro 1.4.1 requires `idf >= 5.1`, and its CI tests v5.1, v5.3, v5.4, v5.5 and v6.0.
- The newest platform, 8.0.0 (2026-10-19), ships ESP-IDF 6.1.0, which is not in that matrix. So
  does 7.1.3. 6.13.0 is the newest platform whose ESP-IDF the component is tested against.
- Moving to 8.0.0 is a later, measured step: build it, then change the pin.
- The component's operator resolver has all 19 methods Caravan's resolver table can emit. I checked
  this in `micro_mutable_op_resolver.h` of 1.4.1. Its TFLM source corresponds to upstream
  `bfeb43aa` (2026-09-01).

**ESP-NN.**
- 1.4.1 always builds with ESP-NN (`-DESP_NN`). On the classic ESP32 it uses the generic optimised
  C kernels; the assembly kernels are S3-only.
- `CONFIG_NN_SKIP_NUDGE` ("non-bit-exact requantization, ±1 LSB") defaults to off. The Kconfig help
  recommends off "for matching reference outputs". The firmware leaves it off.
- So the board's scores are expected to equal the host's. SC-002's one-step tolerance is a margin,
  not an expectation, and any difference is shown (contracts/board-output.md).

**Interpreter API in 1.4.1:**
- the constructor takes model, resolver, arena and size;
- `AllocateTensors`, `Invoke`, `input(i)` and `output(i)`;
- `arena_used_bytes()`, valid after allocation;
- `tflite::InitializeTarget()` is an empty stub;
- `MicroPrintf` writes to stderr with no setup;
- the entry point is `extern "C" void app_main(void)`.

**Cost.** A cold PlatformIO ESP-IDF setup downloads about 540 MB compressed. That is the
toolchain, ESP-IDF, esptool and cmake, plus pip dependencies and components. The firmware workflow
caches `~/.platformio/{packages,platforms,penv,.cache}` and `~/.cache/pip`, keyed on
`platformio.ini` and `dependencies.lock`. The first-build time on a runner is not measured yet.
Implementation records it.

**Not verified until built.** That 1.4.1 builds on ESP-IDF 5.5.3 under PlatformIO. The sandbox
reaches both registries (checked), so implementation builds it before anything is claimed.

**Rejected alternatives:**
- **Arduino IDE / Arduino framework:** the TFLite libraries there trail upstream by years, and the
  models need EQUAL, CAST and SUM. The owner chose PlatformIO.
- **Plain ESP-IDF:** the heaviest install. The owner chose PlatformIO.
- **The pioarduino fork:** not needed for `framework = espidf`.

## R4 — Test windows: a manifest field read by the export stage

**Decision.** `export.test_windows` (integer, default `0`, at most `64`; data-model §1). The export
stage reads it. When it is above 0, the stage:
1. forms the test part exactly as the quantize stage does;
2. selects windows deterministically;
3. runs them through the quantized model with the measurement runtime;
4. writes `model/test_windows.h` (contracts/test-windows.md).

The shared part is moved out of `stages/quantize.py` into one function both stages call, so the two
cannot drift.
- The export `StageSpec` changes to `reads_dataset=True`.
- It also gains the reads `preprocessing.split`, `random_seed` and `export.test_windows`.
- The header is declared through `artifacts_from`, so a header that should exist and does not fails
  the run.

**Rationale:**
- FR-003 asks for windows the firmware includes without writing code and without a new verb.
- Principle I puts every choice of a model's build in its manifest, and Principle III wants the run
  reproducible from it.
- A field read by exactly one stage fits the stage cache as designed. Changing the count re-runs
  only the export.
- Default `0` keeps the author's data out of every export set unless asked for (Principle VI).
- The example manifest sets `16`, so `try-it` and the board guide get them.

**Rejected alternatives:**

| Alternative | Why not |
|---|---|
| A CLI option on `export` | Outside the manifest, so outside the cache key and the resolved manifest. It would be an undeclared artifact, against the pipeline contract. |
| A new verb | Needs a constitutional amendment (Principle XII), for something one stage can do. |
| A script in the guide | The author would run code that is not Caravan's (FR-003). The windows must come from the same split code as the gate, or they prove nothing. |
| Always writing them | Puts the author's data into every export set without asking (Principle VI). |
| Written by the quantize stage | Changing the count would then re-quantize: a field only the export needs would invalidate an earlier stage (Principle III). |

**Schema version.** It stays `caravan/v0.2`. The field is optional with a default, so no existing
manifest changes meaning (Principle IX asks for a new identifier only for a breaking change).
`docs/manifest-changes.md` records the addition. An rc2 build refuses the field by path, as it
refuses any unknown field.

## R5 — The OLED: ESP-IDF's own SSD1306 driver and a 5×7 font

**Decision:**
- The display uses `esp_lcd_new_panel_ssd1306` and `esp_lcd_new_panel_io_i2c` on the `i2c_master`
  bus driver, all in ESP-IDF 5.5.
- IO settings: `dev_addr 0x3C`, `control_phase_bytes 1`, `lcd_cmd_bits 8`, `lcd_param_bits 8`,
  `dc_bit_offset 6`, `scl_speed_hz 400000`.
- The firmware keeps a 1,024-byte framebuffer: page `y/8`, bit `y%8`, LSB at the top. It is pushed
  with `esp_lcd_panel_draw_bitmap`.
- Text uses a public-domain 5×7 font of about 500 bytes, kept in the project.

**Rationale.** No component beyond ESP-IDF itself. Text on a 128×64 screen needs no graphics
library (Principle XII's spirit applies to the firmware the guide hands over). The official example
uses LVGL, which is a large managed component for drawing eight lines of text.

**Pins** (LILYGO schematics and repositories):

| Revision | SDA | SCL | OLED reset | Note |
|---|---|---|---|---|
| V1.3, V1.6 / V2.0, V2.1_1.6, T3 V1.6.1 | 21 | 22 | none | the default build environment `lora32` |
| V1.0 | 4 | 15 | GPIO16, pulse low then high | the environment `lora32-v1`. It also drives GPIO21 low, the OLED supply on V1.0 according to Meshtastic. No LILYGO schematic confirms this. |

- **"One setting changes them" (FR-007):** the author picks the PlatformIO environment, either
  `pio run -e lora32` or `-e lora32-v1`. The pins live in `src/board_pins.h`, selected by the
  environment's build flag.
- **GPIO16 is never driven on the V1.6.x revisions.** There it is the flash chip select of the
  ESP32-PICO-D4, although some third-party pin maps name it the OLED reset.

**Telling the revisions apart** (for the guide):
- **V1.0:** ESP32 chip visible, PRG and RST buttons, no SD slot.
- **V1.3:** ESP32 chip visible, no SD slot, U.FL antenna.
- **V1.6.x / V2.1:** ESP32-PICO-D4, microSD slot, SMA antenna, power switch, a single RST button.
- The silkscreen (`T3_V1.6 20180606`, `T3_v1.6.1 20210104`, `T3_V1.3`) decides when it is there.

**Flashing.**
- V1.3 and V1.6.x have the auto-reset circuit, so no button is needed.
- If auto-reset fails on V1.6.x, which has no BOOT button: hold IO0 to GND while pressing RST.
- Remove the SD card before flashing: its MISO is the GPIO2 strapping pin.

**USB-serial.** Both CP2104 (schematics) and CH9102 (current product pages) appear across batches.
The guide tells the author to read the chip beside the USB connector.
- **Linux:** `cp210x` gives `/dev/ttyUSB0`, `cdc_acm` gives `/dev/ttyACM0`. Join the `dialout`
  group.
- **macOS and Windows:** the vendor's driver. On macOS the CH9102 driver must be approved under
  Driver Extensions.
- The macOS port names are from secondary sources. The guide says "the port PlatformIO lists" and
  uses `pio device list` instead of naming them.

**Orientation.** ESP-IDF's SSD1306 init leaves mirroring off, and the image may appear rotated by
180° on some modules. The firmware calls `esp_lcd_panel_mirror(panel, true, true)` if the owner's
run shows that. It is not assumed beforehand.

## R6 — The automated firmware build (FR-009)

**Decision.** A reusable workflow `.github/workflows/firmware.yml`, on Python 3.13 with the `train`
and `verify` extras. It:
1. installs Caravan from the checkout;
2. runs the board guide's executable blocks against the example (export with test windows, copy
   into the firmware project);
3. runs `pio run -e lora32` and `pio run -e lora32-v1`.

It is triggered:
- **by `workflow_call` from the release workflow,** as a job the `release` job needs. A firmware
  that does not build blocks the release; the existing `verify` job runs after publication and
  could not.
- **on pull requests that touch what the firmware compiles:** `src/caravan/export/**`,
  `src/caravan/stages/export.py`, `src/caravan/data/test_part.py`, `examples/lora32/**`,
  `examples/picket-mlp.yaml` and the workflow itself. A broken header is caught at review, not at
  release. `docs/guides/lora32.md` is deliberately not a trigger: a change to it alone is a
  documentation-only change and must start nothing. Its blocks are checked by the next code PR on
  these paths and by every release.

**Step blocks.** The board guide marks its blocks with `# step: board-…`. `tests/support_docs.py`
reads step names matching `[a-z]+` today, so it is widened to `[a-z-]+`. The hardware blocks
(`board-flash`) are documented but never run by CI.

**Rejected alternatives:**
- **Building in the `verify` job:** it runs after the release is published, so it could not block.
- **Building on every PR:** about 540 MB of downloads for changes that cannot affect the firmware.

## R7 — Keeping the references honest (FR-015)

**Decision.** One test module, `tests/contract/test_docs_reference.py`, in the default job, with no
extras. It checks four things:
- **CLI.** It walks `caravan.cli.main.build_parser()`. Every subcommand needs a heading
  `## caravan <verb>` in `docs/reference/cli.md`. Every option string of that subcommand, such as
  `--runs-dir` or `--json`, must appear in that section. The global `--version` and exit codes 0–4
  must appear in the page.
- **Manifest.** It walks the pydantic models from `Manifest`, including the per-type input and
  output keys, into dotted paths in the reference's notation (`input_features[].preprocessing.normalization`).
  Each path must appear in backticks in `docs/reference/manifest.md`.
- **Rules.** Every `RULE_*` value in `caravan.manifest.errors`, and every member of
  `RETIRED_RULES`, needs a heading in `docs/reference/rules.md`. A retired one is marked
  `(retired)`.
- **Compatibility.** Every registered template, every board description and every feature type of
  the schema must appear in `docs/compatibility.md`.

Each failure names exactly what is missing, and where (spec, Story 2, scenario 5).

**CI paths, unchanged.** No new page joins the exceptions in `ci.yml`. A change that touches only
documentation starts no workflow (Resources & Cost Discipline).
- The drift the test exists for comes from code: a new option, field or rule. Every PR that
  touches code runs the suite, and so the test.
- A pure documentation change that breaks a reference is caught at the latest by the release
  workflow's `check` job, which runs the whole suite and now also `sphinx-build -W` before anything
  is tagged.
- The `docs/try-it.md` exception from feature 007 stays as it was. This feature adds none.

**Rejected alternative: generating the references.** Generated text is accurate but says only what
the code says. The references need the why, examples and fixes. A check of hand-written pages keeps
both.

## R8 — What the board run is expected to find (FR-008)

No exported C has been cross-compiled yet. Building the firmware is the first time, so these are
the expected sites of defects. Implementation records here what actually failed, with the fix.
- **The runner skeleton** has no `arena_used_bytes()` report (Principle IV requires the runner to
  take it from the runtime). Its `int main()` is not ESP-IDF's entry point. The arena report is
  added for every board.
- **`model_data.h` / `.cc`** use `constexpr` and an `extern const char* const` label array, so they
  are compiled by Xtensa GCC 14 for the first time.
- **`resolver.h`** is checked against esp-tflite-micro 1.4.1 (all 19 methods present, R3). Each
  method's signature is confirmed at build time.

**What the first cross-compile found (2026-10-26, T019).** The example's export, with 12 test
windows, was built in `examples/lora32/` with PlatformIO 6.2.0, espressif32 6.13.0 (ESP-IDF 5.5.3,
Xtensa GCC 14.2) and esp-tflite-micro 1.4.1 (esp-nn 1.4.1, `dependencies.lock`). Both environments,
`lora32` and `lora32-v1`, link.
- **No defect in the generated files.** `model_data.h`, `model_data.cc`, `resolver.h` and
  `test_windows.h` compile with no error and no warning under ESP-IDF's flags. Every warning in the
  log comes from the component's own TFLM sources (`-Wshadow` in `reference/sub.h`), not from
  anything Caravan writes.
- **Two gaps in the header were found by writing a model-agnostic firmware, before the first
  build.** Both are fixed in the generator:
  - the output's position was reachable only through a constant named after the output, so a
    firmware would need the output's name: `kOutputPosition`;
  - the record needed which Caravan exported the model: `kExportedBy`.
- **The runner skeleton** gained the arena report. Its `int main()` stays: the skeleton is per
  board but not per framework, and on ESP-IDF the entry point is `app_main`, which the board
  guide's firmware shows. The skeleton's comment already says it is a starting point that Caravan
  has not built.
- **Build figures, `estimated`** (the linker's static figures for this firmware, not a board
  measurement; the RAM figure excludes the heap and what the arena actually uses):
  - flash 368,153 bytes of the 1 MB application partition;
  - static RAM 63,960 of 327,680 bytes, of which 49,152 are the arena reserved by `kArenaBytes`.
- **Build time, measured in this sandbox:** about 4.5 minutes per environment from a clean
  project, with the PlatformIO packages already downloaded. The packages take 2.6 GB on disk.
- **Not checked:** running the firmware. Espressif's QEMU for the ESP32 could run it as an
  emulated rung outside Caravan's ladder, but executing a downloaded emulator binary was not
  permitted in this session. The board run (T047) is the first execution.

## R9 — Where the existing documents go (FR-022)

| Document | On the site | Change |
|---|---|---|
| `README.md` | not a page | shortened to a pointer: what Caravan is, install, link to the site |
| `docs/try-it.md` | Guides | its "Your own data" section moves into `guides/own-project.md` and is replaced by a link. Its step blocks are unchanged. |
| `docs/manifest-changes.md` | Reference | gains the `export.test_windows` addition |
| `docs/budgets.md` | Reference | none |
| `docs/roadmap.md` | Project | gains feature 009 and the rc3 goal (FR-017). Links to `design/` and `research/` point at GitHub. |
| `docs/releases/0.1.0.md` | Project | none |
| `docs/design/`, `docs/research/` | excluded | stay in the repository as working records |

The site URL is `https://mhabedank.github.io/Caravan/`.

## R10 — The compatibility page before and after the board run

Before the owner's run, `esp32` stands at:
- **built:** the guide's firmware compiles for it in the firmware workflow, with the date;
- **not run:** no run on a board yet.

`s32k144` and `stm32h743` stand at "export only, never compiled for". After the owner's run, the
record goes into `docs/board-runs/<date>-lora32.md`, and `esp32` becomes `measured`, on a LoRa32
with that date (SC-008).

A board is never shown above the rung it has reached. Compiling is not a rung of the verification
ladder, so it is stated as what it is and given no provenance label.
