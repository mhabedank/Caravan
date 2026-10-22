# Implementation Plan: Manifest Schema and Package Skeleton

**Branch**: `001-manifest-schema` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-manifest-schema/spec.md`

## Summary

Build the manifest contract and the package that carries it: a strict, versioned schema with
actionable errors, an in-memory migration path so an archived manifest never becomes unreadable,
a resolved-manifest artifact that makes every default visible, and a package skeleton whose
dependency and install budgets are enforced by tests rather than by intent.

The technical approach follows from one constraint: the core must run without a training
framework. That single rule decides the dependency set (two runtime dependencies, the command
line on the standard library), splits the template registry into a parameter half and a builder
half, and makes the layering check a test rather than a convention.

## Technical Context

**Language/Version**: Python, floor 3.14 — the current stable minor is 3.15 (released 2026-10-09)
and the previous is 3.14 (2025-10-07), which is exactly the window the constitution requires.

**Primary Dependencies**: two at runtime — `pydantic` (v2, strict typed models) and `ruamel.yaml`
(manifest parsing). The command line uses the standard library's `argparse`. That is 2 of the 6
direct runtime dependencies the constitution allows, leaving room for the ones that genuinely
cannot be written here (numeric and flatbuffer handling in the analysis feature).

**Storage**: files only. Manifests are read from the working tree; artifacts are written into a
per-invocation run directory. Nothing is written outside it, and no state persists between runs.

**Testing**: `pytest` as a development dependency only, so it does not count against the runtime
budget. Three test layers: unit, contract (command line surface and schema), integration
(end-to-end on the pilot manifest). A fixture library of deliberately broken manifests, one per
rule, with the expected message asserted.

**Target Platform**: any machine with a supported Python — Linux, macOS, Windows. No hardware, no
emulator, no accelerator, no network.

**Project Type**: single Python package exposing a command line application.

**Performance Goals**: a verdict on a manifest in under 2 seconds (SC-001); a cold install of the
default package in under 30 seconds and under 50 MB (SC-003). Both measured in continuous
integration, not estimated. The expected install is around 4 MB, so the budget has deliberate
headroom for later features.

**Constraints**: no training framework reachable from the core (Principle XII); no network access
in any command of this feature; the author's manifest file is never modified; the resolved
manifest is byte-identical across runs.

**Scale/Scope**: one manifest schema version (`caravan/v0`), one registered template (`mlp`), three
board descriptions (the boards the pilot manifest targets), two commands. Roughly 1,500 lines of
implementation and a comparable amount of test code.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

### Before research

| Principle | Gate | Verdict |
|---|---|---|
| I. Declarative Manifest | No code in the manifest; no defaults section; no per-model script | PASS — the schema has no field that carries code or a path outside its declared fields |
| III. Reproducible by Construction | Provenance recorded; resolution deterministic | PASS — the run report carries tool version, manifest hash and both schema versions |
| IV. Provenance Labels | No unlabeled hardware number | PASS by absence — this feature produces no hardware number |
| V. Budgets Are Gates | No switch that silences a gate | PASS — no flag skips validation; the install budget fails the build |
| VI. Compliance Enforced by Schema | Compliance required; publish refuses before network | PASS — compliance is a required block; no command in this feature can reach the network |
| VII. Targets and Templates Are Data | Registry, not an enumeration; boards as data | PASS — see the template split in research R7 |
| VIII. No Lock-In | No hosted service; portable artifacts | PASS — everything runs offline |
| IX. Stable Manifest Contract | Declared version, migration registry, refusal only for unknown | PASS — the mechanism ships with v0 and is proven by test |
| X. Built for Real Models | Driven by a named model | PASS — `picket-mlp` is the only driver; one template, three boards |
| XI. No Claude in Model Learning | No model data produced | PASS by absence |
| XII. Small Core, Few Dependencies | Budget, layering, install, Python policy | PASS — 2 runtime dependencies, 0 extras in this feature, layering enforced by test |

No violations. Complexity Tracking stays empty.

### After design

Re-checked once the design existed. Three things the design surfaced, all resolved inside the
principles rather than against them:

1. **Principle XII would have been violated by the obvious YAML choice.** `pyyaml` publishes no
   wheel for Python 3.15, so on the current stable Python it installs by building from source,
   which needs a toolchain and breaks the install budget on a clean machine. That is a dependency
   setting the project's Python policy, which Principle XII forbids. Resolved by choosing
   `ruamel.yaml`, which ships a pure-Python wheel with no required dependencies (research R2).
   **PASS, and the rule earned its place on the first feature.**
2. **Principle VII and Principle XII pull against each other on templates.** A template has to
   validate its own parameters (VII) and build a model (the point of a template) — but building a
   model needs the training framework that must stay out of the core (XII). Resolved by splitting
   a template into a parameter half, which lives in the core, and a builder half, which lives in
   the training extra and is only ever loaded by the training stage (research R7). This feature
   implements the parameter half only. **PASS.**
3. **FR-013's "identical output" needed a scope.** A run report contains the run's own identity
   and timestamp, so two runs cannot be byte-identical in every artifact. The determinism
   requirement applies to the resolved manifest; the report differs only in its run identity and
   date fields, which are themselves the provenance Principle III requires (research R9).
   **PASS, with the refinement recorded rather than assumed.**

## Project Structure

### Documentation (this feature)

```text
specs/001-manifest-schema/
├── spec.md               # Feature specification
├── plan.md               # This file
├── research.md           # Phase 0: decisions, rationale, alternatives
├── data-model.md         # Phase 1: entities and validation rules
├── quickstart.md         # Phase 1: runnable validation scenarios
├── contracts/
│   ├── cli.md            # Command line contract: arguments, exit codes, output
│   ├── manifest-v0.md    # The manifest contract, field by field
│   └── run-report.md     # Run report and run directory contract
├── checklists/
│   └── requirements.md   # Specification quality checklist
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
pyproject.toml                      # distribution caravan-ml, command caravan, Apache-2.0
LICENSE                             # Apache-2.0 full text
NOTICE
.gitignore
src/caravan/
├── __init__.py                     # version only; imports nothing heavy
├── cli/
│   ├── main.py                     # argparse wiring, exit-code policy
│   ├── validate.py                 # the validate command
│   ├── render.py                   # the render command
│   └── listing.py                  # caravan templates, caravan boards
├── manifest/
│   ├── schema/                     # pydantic models for caravan/v0, extra="forbid"
│   │   ├── __init__.py             #   the Manifest root and the cross-field rules
│   │   ├── model.py                #   one module per manifest section, so six tasks run parallel
│   │   ├── dataset.py
│   │   ├── train.py
│   │   ├── export.py
│   │   ├── compliance.py
│   │   └── misc.py                 #   verify, bench, publish
│   ├── _yaml.py                    # the only module that imports ruamel.yaml
│   ├── load.py                     # read → migrate → validate, one entry point
│   ├── migrate.py                  # version registry and per-version transforms
│   ├── resolve.py                  # default expansion → resolved manifest
│   └── errors.py                   # pydantic errors → actionable messages
├── templates/
│   ├── registry.py                 # identifier → template parameter spec
│   └── mlp.py                      # parameter schema for the pilot's template
├── targets/
│   ├── schema.py                   # board description model, incl. toolchain and honest emulator support
│   ├── registry.py                 # load and list board descriptions
│   └── boards/
│       ├── s32k144.yaml
│       ├── stm32h743.yaml
│       └── esp32.yaml
└── run/
    ├── paths.py                    # per-invocation run directory
    └── report.py                   # run report writer

tests/
├── unit/                           # schema rules, migration registry, error rendering
├── contract/                       # command line surface, exit codes, report shape
├── integration/                    # end-to-end validate and render on the pilot manifest
├── layering/                       # no training framework reachable from the core
└── fixtures/
    └── manifests/
        ├── valid/picket-mlp.yaml   # the pilot manifest, the acceptance fixture
        └── invalid/*.yaml          # one per rule, each with its expected message
```

**Structure Decision**: one package under `src/`, split by pipeline concern rather than by
technical layer, because the concerns are what the constitution governs: `manifest/` owns the
contract of Principle IX, `templates/` and `targets/` own the registries of Principle VII, `run/`
owns the artifacts of Principle III, and `cli/` owns the surface of the pipeline contract. The
`src/` layout is chosen so that tests run against the installed package, which is what makes the
layering and install-budget checks meaningful — a flat layout would let tests import from the
working tree and hide a packaging mistake.

`tests/layering/` is a directory of its own rather than a file in `unit/`, because it is the
executable form of a constitutional rule and should be visible as such.

## Complexity Tracking

No constitution violations to justify. The table stays empty by design, and the one place where
two principles pulled against each other (templates: VII against XII) was resolved by a split
inside the principles, recorded in research R7 rather than as a deviation.
