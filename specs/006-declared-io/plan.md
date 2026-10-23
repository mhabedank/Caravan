# Implementation Plan: Declared Inputs and Outputs, and a Lean Manifest

**Branch**: `006-declared-io` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-declared-io/spec.md`

## Summary

The first feature under constitution 3.0.0. It changes the manifest more than any feature since
001.

- **The manifest.** It moves to `caravan/v0.1`:
  - the compliance block, two descriptive fields and three sections of stages that do not exist yet
    go;
  - the model's input and output are declared, Ludwig-style, as lists holding exactly one each;
  - labels and input columns are derived from the data unless the author pins them.
- **Old manifests.** Every previous-form manifest migrates in memory, with one notice per field it
  loses or moves.
- **The pipeline gains two internal stages:**
  - `data` derives what the data says once, cached by dataset version;
  - `fit` compares the built model's lower bounds with every target board before any training.
- **The export** gains an interface contract: names mapped to the positions the microcontroller
  runtime actually uses, read from the file.

Three measurements shaped the design (research R4, R5):
- The converter keeps the input's name but drops the output's unless the model returns a dict.
- With two outputs, the converter reverses their order in the graph.
- The microcontroller runtime binds by position and ignores signatures entirely.

So the build rewires each template's model into a named, dict-output model, verified to change
neither a weight nor an operator. The contract then maps each declared name to the position the
file actually uses.

## Technical Context

**Language/Version**: Python 3.13 for the pipeline. The core — schema, migration, validation, the
fit arithmetic, the interface emitters — runs on 3.13, 3.14 and 3.15 like every core module.

**Primary Dependencies**: none new. Keras and TensorFlow in `train` (rewiring, the fit check's
layer reading). `ai_edge_litert.schema_py_generated` in `verify` (reading signatures and
quantization parameters from the file). The dependency and extras budgets are untouched.

**Storage**: files in the run directory; the stage cache of feature 002.

**Testing**: pytest, in the existing layout:
- `tests/unit` and `tests/integration` for the core;
- `tests/train` for the conversion half;
- `tests/verify` for the runtime half;
- `tests/contract` for the CLI;
- `tests/layering` for the import rules.

**Target Platform**: a developer machine. The artifacts target Cortex-M and Xtensa boards, and
nothing here executes on them.

**Project Type**: single Python package with a command line interface.

**Performance Goals**:
- A fully cached run reads no data, as today.
- The `fit` stage adds under a second to a build of the pilot: it reads layer shapes, not data.

**Constraints**:
- Principle VIII: no network, and nothing rewrites a converted model.
- Principle XII: no training framework in the core.
- Principle IX: no rewrite of the user's file.
- FR-027: generated files byte-identical across runs.

**Scale/Scope**:
- one schema version and its migration;
- two internal stages;
- seven new rules and five retired;
- one new artifact (`interface.json`) and additions to two generated C files;
- the documentation of the migration.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.* Checked against
constitution **3.0.0**.

| Principle | How this feature satisfies it | Verdict |
|---|---|---|
| I — declarative manifest | Inputs and outputs are declared, each with a kind. The output kind replaces `task`. Every remaining field is read by a stage: `model.name` and `model.version` by `export`, which writes them into the interface contract (data model, *Stages*). Derived values are not asked for. No defaults section is introduced. | pass, see the note on fields |
| II — embedded targets | Nothing widens the target class. | pass |
| III — reproducible | The migration runs in memory on every load. Derived values enter the resolved manifest and the cache keys. Stages read the declarations field by field, so a budget change re-runs only `quantize` and `export`, and a board change only `fit` and `export` (FR-031; data model, *Stages*). The cache invalidates once, as documented (R9). | pass |
| IV — labelled numbers | Every fit figure is `estimated`, with its method. Interface numbers are read from the file, not reported as hardware behaviour. | pass |
| V — gates | Every class output states its budget; there is no default (FR-029). `fit` fails on a lower bound that exceeds a board and has no skip option. The accuracy gate becomes per output. Neither relaxes the other. | pass |
| VI — the author's data | The compliance layer, licence fields and rules CF-3, CF-5, CF-8 and DS-9 are removed. Nothing claims a licence was checked (SC-006). Data and credentials stay out of the repository. | pass |
| VII — boards are data | The fit check reads `flash_kb`, `ram_kb` and their recorded sources from the board descriptions; no board logic in code. | pass |
| VIII — portable artifacts | The interface contract is plain JSON plus C constants. Names map to positions read from the file. The runner skeleton binds by name. No flatbuffer is rewritten (R4). | pass |
| IX — stable contract | A new version identifier, a registered transform and notices. The file is never rewritten. Unknown and removed fields are rejected with their path. A migration note ships (`docs/migrations/caravan-v0.1.md`). | pass |
| X — real models | `series` and `class` are justified by `picket-mlp` and `picket-conv1d`. Several inputs or outputs are **not** built: the research found no documented application (`docs/research/2026-10-23-multi-io-on-mcu.md`), and the owner chose the declaration form only. | pass |
| XI — no Claude in learning | Nothing here labels, generates or evaluates data. | pass |
| XII — small core | No new verb, no dependency and no extra. The fit arithmetic and the emitters are core; reading a Keras model and a flatbuffer stay behind their extras. A layering test covers the new modules. | pass |
| Pipeline contract | The constitution's stages are what a user invokes: "Each stage MUST be separately invocable" names the verbs. `data` and `fit` are cache units inside the `build` verb, which is the constitution's "build (with the fit check before training)"; `caravan build` runs both and is separately invocable. They are not new pipeline stages in the constitution's sense and not new verbs. | pass, see Complexity Tracking |

**Note on fields.** Principle I says every field must be read by at least one stage. Two fields
are settled by the constitution itself rather than by a stage function: `apiVersion`, which
Principle IX requires every manifest to declare and the loader reads, and `dataset.source`, which
names the data that `data`, `build`, `train` and `quantize` read. A first draft of this plan let
`model.name` and `model.version` count as read because the run report records them; the analysis of
2026-10-23 rejected that as a reinterpretation of Principle I. `export` now reads both and writes
them into the interface contract and the header, which also tells a firmware author which model
they hold.

### Re-check after Phase 1 design

Re-read after writing the data model and the four contracts.

- **Interface contract.** Writing it showed that the runner skeleton of feature 004 binds by literal
  position (`interpreter.input(0)`). That breaks Principle VIII in 3.0.0, so the skeleton changes
  (`contracts/interface.md`, *The runner skeleton*). It is a violation found and closed by this
  feature, not one introduced by it.
- **Fit check.** Writing it showed that counting stand-alone activation layers could make the "lower
  bound" exceed the truth: a ReLU is fused into its convolution and has no buffers. Excluding such
  layers is what keeps the check inside Principle V's permission to pass without deciding (R6). A
  test pins the ordering against the export's floor.
- **Migration contract.** The retired rules' invalid fixtures become valid after migration, so they
  move to a migration fixture directory rather than being deleted silently.

- **Analysis of 2026-10-23** (`/speckit-analyze`) found three conflicts with the constitution, now
  closed. Stages read whole declaration lists, so a budget change would have retrained (III);
  stages now read field by field, which needs an index in the projection's paths. The pilot left
  its budget to a default (V); the budget is now required. Identity fields were counted as read by
  reinterpreting "stage" (I); `export` now reads them.

No unjustified violation remains.

## Project Structure

### Documentation (this feature)

```text
specs/006-declared-io/
├── plan.md              # this file
├── spec.md              # 4 stories, 31 requirements, 6 success criteria
├── research.md          # R1–R10; R4–R6 measured or read at source, with versions and date
├── data-model.md        # the declarations, the derived values, the fit and interface records, stages
├── quickstart.md        # how to see it work and refuse
├── contracts/
│   ├── manifest.md      # caravan/v0.1, removed fields, the migration
│   ├── interface.md     # interface.json, the C additions, the skeleton
│   ├── fit-check.md     # method, verdicts, F-1, what it may not do
│   └── cli.md           # what changes at the command line
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/caravan/
├── manifest/
│   ├── schema/
│   │   ├── __init__.py        # Manifest: + inputs, outputs, CF-9/10/11; − compliance, CF-3/5/7/8
│   │   ├── io.py              # new: InputDeclaration, OutputDeclaration, the name pattern
│   │   ├── removed.py         # new: the removed-field table and its messages (FR-001)
│   │   ├── dataset.py         # − labels, window, license, permitted_use
│   │   ├── model.py           # − topic, task
│   │   ├── export.py          # − accuracy_drop_max
│   │   ├── misc.py            # − VerifySpec, BenchSpec, PublishSpec
│   │   └── compliance.py      # deleted
│   ├── migrate.py             # caravan/v0 → caravan/v0.1, transforms return notices
│   ├── load.py                # carries notices; removed-field messages ahead of "unknown field"
│   ├── resolve.py             # the new shape; `derived` markers; merge of derived values
│   └── errors.py              # + CF-9, CF-10, CF-11, DS-11, DS-12, F-1; RETIRED_RULES
├── data/
│   ├── reader.py              # label column and input columns from the declarations; no fixed "label"
│   └── reader_bridge.py       # unchanged in rule; takes columns
├── stages/
│   ├── base.py                # project(): an index in a path (`outputs[0].labels`), FR-031
│   ├── data.py                # new, train: DataSchema, DS-5/11/12
│   ├── fit.py                 # new, train: reads layer shapes from the built model
│   ├── build.py               # reads inputs/outputs; rewires into a named, dict-output model (R4)
│   ├── train.py               # reads inputs/outputs; dict targets; − DS-9
│   ├── quantize.py            # reads outputs[0].accuracy_drop_max; gate per output
│   └── export.py              # + interface.json; passes bindings to the emitters
├── targets/
│   └── fit.py                 # new, core: floors and verdicts from plain layer records and boards
├── runtime/
│   └── flatbuffer.py          # + signatures, positions, quantization parameters (verify)
├── export/
│   ├── interface.py           # new, core: interface.json and the C additions from a reading
│   ├── c_array.py             # header and source take the interface additions
│   └── skeleton.py            # binds by the named constants
├── cli/
│   ├── pipeline.py            # stage sequence data → build → fit → …; resolved.yaml after data
│   ├── validate.py, render.py # notices; render notices to stderr
│   └── build.py, train.py, quantize.py, export.py   # their stage lists
└── run/report.py              # + migration_notices, fit, interface

docs/migrations/caravan-v0.1.md   # new: the migration note Principle IX requires
README.md                          # manifest example, stage list, the compliance paragraph removed

tests/
├── unit/test_migration_v01.py            # every transform step, every notice, file untouched
├── unit/test_projection_index.py         # indexed paths; a budget change keeps data/build/train keys
├── unit/test_resolve_v01.py              # the new shape, `derived` markers, merge_derived
├── unit/test_every_field_is_read.py      # Principle I and SC-001
├── contract/test_no_compliance_in_outputs.py  # SC-006
├── train/test_declared_io_end_to_end.py  # same windows and split as the migrated pilot
├── train/test_interface_reordered_outputs.py  # research R4's reversal, kept as a test
├── unit/test_io_declarations.py          # CF-9/10/11, removed-field messages
├── unit/test_fit_floors.py               # the arithmetic on hand-built layer records; F-1
├── unit/test_interface_emit.py           # JSON and C additions; escaping; determinism
├── unit/test_retired_rules.py            # the five identifiers appear in no rule table
├── unit/test_rules_coverage_v01.py       # every new rule is reachable and covered
├── integration/test_validate_migrated.py # every valid fixture through migration (SC-002)
├── integration/test_render_derived.py    # `derived` markers; notices on stderr only
├── train/test_data_stage.py              # derivation, pinning both ways, DS-11/12, no read when reused
├── train/test_rewire_names.py            # weights and operators unchanged; signature names (R4)
├── train/test_fit_stage.py               # pass record; F-1 before training; no retrain on board change
├── train/test_fit_floor_ordering.py      # fit floor ≤ export floor, both templates
├── train/test_migration_same_model.py    # SC-003
├── verify/test_interface_positions.py    # positions from the signature, not assumed
├── verify/test_interface_contract_alone.py  # SC-005
├── contract/test_cli_contract.py         # notices, exit codes, removed fields (extended)
└── layering/                             # new core modules import no framework (extended)

tests/fixtures/manifests/
├── valid/picket-mlp-v01.yaml, picket-conv1d-v01.yaml   # the new form
├── invalid/v01-*.yaml                                   # the refusals of quickstart §3
├── gate/too-big-for-s32k144.yaml                        # valid, fails F-1 (quickstart §6)
└── migration/                                           # former cf-3, cf-8 fixtures, with expected notices
```

**Structure Decision**: the layout follows the layering rule, as in every earlier feature.

- `targets/fit.py` holds the floors and verdicts as arithmetic over plain records, so it is core and
  tested on every Python. Only extracting those records from a Keras model needs `train`.
- `export/interface.py` is core for the same reason feature 004 put the emitters there: once a
  reading exists, the rest is formatting.
- The declarations get their own schema module (`io.py`), because they are the new centre of the
  manifest and carry their own rules.
- The removed-field table is a module of its own, because the same table drives the migration, the
  validation message and the migration note, and three copies would drift.

## Complexity Tracking

| Choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| Two internal stages, `data` and `fit`, run by the `build` verb | `data` puts derived values into the projection, so they are in every key (R3). `fit` must sit outside `train`'s key, or adding a board retrains (R6). | Folding `data` into `build` hides the labels in an artifact three later stages must read back. Folding `fit` into `build` makes `export.targets` a build input, so every board change retrains, against Principle III. |
| Rewiring the template's model rather than changing builders | The declared names must survive conversion (R4), and builders are a third-party extension point | Changing the builder signature breaks every registered third-party template; wrapping the model as a nested layer hides the per-layer tables of features 002 and 003. |
| A schema version identifier (`caravan/v0.1`) inside the pre-stable series | Principle IX requires the loader to know which form it holds | Recognising the old form by its shape is silent reinterpretation; `v1` would claim a stability nobody has decided on. |
