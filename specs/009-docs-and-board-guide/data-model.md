# Data Model: Documentation Site and the First Model on a Board

Feature 009. The entities of the spec, with their fields, the rules that check them and where they
live. The interfaces between them are in `contracts/`.

## 1. Manifest field `export.test_windows`

The one schema addition (research R4). It is read by the export stage only.

| Field | Type | Default | Allowed | Read by |
|---|---|---|---|---|
| `export.test_windows` | integer | `0` | `0` to `64` | export |

**Rules:**
- `0` writes no test windows. This is the default, so no author's data enters an export set unless
  the author asks for it (Principle VI).
- A value above `0` needs `c_array` in `export.formats`, because the header uses the array's named
  positions. Without it, validation refuses the manifest at `export.test_windows`, naming
  `export.formats`.
- More than `64` is refused by the schema.
  - 64 windows of the example take about 85 KB of flash; the LoRa32 has 4 MB.
  - The bound keeps the header readable and the board run short. It is not a board limit.
- When the test part has fewer windows than asked, the export writes all it has. The record states
  both numbers. This is not an error: the fixture's test part is small by construction.
- **Schema version:** stays `caravan/v0.2`. The addition is optional with a default, so every
  `v0.2` manifest still loads unchanged. Constitution IX requires a new identifier only for a
  breaking change. `docs/manifest-changes.md` records the addition.

## 2. Test windows (`model/test_windows.h`)

Written by the export stage when `export.test_windows > 0`. Declared through `artifacts_from`, so a
missing file fails the run.

| Part | Content |
|---|---|
| Windows | `N` windows from the test part, one array per input feature, in the input's boundary element type (float32 or int32), as raw values |
| Expected | per window: the expected class index (category, binary) or value (number) |
| Host reference | per window: the int8 model's scores on the host, and its decision under the output's rule (argmax, threshold, value) |
| Score step | one quantization step of the output, read from the model file |
| Helpers | `FillWindow`, `Decide`, `DecisionName`, documented in `contracts/test-windows.md` |
| Provenance | in a comment: the model name and version, the run, the dataset version, the split, the selection rule |

**Selection:**
- The test part is formed exactly as the quantize stage forms it: same window plan, same split, same
  seed. It uses the same functions, factored out (research R4).
- **Category or binary output:** round-robin over the classes in label order. Within a class,
  windows keep test-part order. Every class appears before any appears twice.
- **Number output:** the first `N` windows in test-part order.
- No randomness, so no seed is needed beyond the split's own.

**The host reference:**
- It is the quantized model run by the measurement runtime: the same file and the same runtime as
  the quantize stage's gate.
- It is never the float model (FR-004).

**Record:** `export.json` gains `test_windows`, carrying:
- the windows written;
- the windows asked for;
- the windows available;
- the selection rule;
- the per-class counts;
- the score step.

## 3. Runner skeleton (`runner/<board>/main.cc`)

Changed by FR-005 and FR-008:
- **Arena reporting:** the skeleton reads `interpreter.arena_used_bytes()` after
  `AllocateTensors()` and hands it to a `ReportArena(size_t bytes)` function the author implements.
  Its comment says the figure is `measured` on the board it runs on, and that the arena should be
  set from it plus a margin.
- **Further changes:** whatever the board run finds wrong, for example the entry point. Each one is
  recorded in `research.md` with what failed.

## 4. Board guide firmware (`examples/lora32/`)

A PlatformIO project, kept in the repository and fetched with `examples/` exactly as `try-it.md`
already fetches it.

| Path | Role | Owned by |
|---|---|---|
| `platformio.ini` | platform, board, framework, pinned versions | repository |
| `CMakeLists.txt` | ESP-IDF project file | repository |
| `sdkconfig.defaults` | stack size, flash size, log level | repository |
| `src/CMakeLists.txt` | component registration, globs `model/*.cc` | repository |
| `src/idf_component.yml` | `espressif/esp-tflite-micro`, pinned | repository |
| `src/main.cc` | runs the windows, compares, reports. Model-agnostic: everything model-specific comes from the generated headers | repository |
| `src/oled.h`, `src/oled.cc` | SSD1306 over I2C, text only | repository |
| `src/font5x7.h` | a public-domain 5×7 font, about 500 bytes | repository |
| `src/board_pins.h` | the one place for the OLED pins, one block per revision | repository |
| `src/model/` | the export's `model_data.h`, `model_data.cc`, `resolver.h`, `test_windows.h` | the author's run; ignored by git |

**States of a board run:**

```
boot → init OLED → init model → for each window: fill, invoke, decide, compare, show → summary → hold
           │             │
           │             └─ AllocateTensors fails → "arena too small: <bytes>" on OLED + serial, halt
           └─ OLED absent or wrong pins → continue, serial only (the run is not aborted)
```

## 5. Board run record

What the firmware prints at the end of a run, and what the owner commits as
`docs/board-runs/<date>-<board>.md`. The compatibility page cites it.

| Field | Source |
|---|---|
| `date` | written by the owner (the board has no clock) |
| `board`, `revision` | the firmware's pin block (revision) and the owner (the printed label) |
| `clock_mhz` | read on the board from the CPU frequency setting |
| `firmware` | the Caravan version the firmware project was fetched from, and its commit if built from a checkout |
| `toolchain` | the ESP-IDF version (`esp_get_idf_version()`) and the esp-tflite-micro version pinned in `idf_component.yml` |
| `model` | name and version, from `model_data.h` |
| `windows`, `agreed`, `max_score_diff_steps` | counted on the board |
| `arena_used_bytes` | `interpreter.arena_used_bytes()`, labeled `measured` |

The record carries no timing figure (FR-006).

## 6. Documentation site

| Page | Path | Source of truth | Checked by |
|---|---|---|---|
| Landing | `docs/index.md` | written | site build (links) |
| Try it | `docs/try-it.md` | written, executed | release `verify` job (existing) |
| Own project | `docs/guides/own-project.md` | written | site build |
| Board guide | `docs/guides/lora32.md` | written, partly executed | firmware workflow (its `# step:` blocks) |
| CLI reference | `docs/reference/cli.md` | written | drift test against the argument parser |
| Manifest reference | `docs/reference/manifest.md` | written | drift test against the schema models |
| Rules | `docs/reference/rules.md` | written | drift test against `manifest/errors.py` |
| Compatibility | `docs/compatibility.md` | written | drift test against the registries and feature types |
| Roadmap | `docs/roadmap.md` | existing, single source | site build |
| Budgets | `docs/budgets.md` | existing | — |
| Manifest changes | `docs/manifest-changes.md` | existing | — |
| Releases | `docs/releases/*.md` | existing | existing release workflow |
| Board runs | `docs/board-runs/*.md` | the owner's runs | site build |

Excluded from the site: `docs/design/` and `docs/research/`. These are working records. They stay
in the repository and are linked from the roadmap as files on GitHub.

**Version:** every page shows the version the site describes. It is taken from the release tag at
publish time, and from the package version for a manual or local build.
