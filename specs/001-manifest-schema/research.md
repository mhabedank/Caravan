# Phase 0 Research: Manifest Schema and Package Skeleton

Date: 2026-10-22 · Feature: [spec.md](./spec.md) · Plan: [plan.md](./plan.md)

No `[NEEDS CLARIFICATION]` markers remained in the spec, so this phase resolved the technical
choices the spec deliberately left to the plan. Every decision below states what was chosen, why,
and what was rejected. Facts about packages were checked against the package index on 2026-10-22,
not recalled.

---

## R1. Command line: the standard library, not a CLI framework

**Decision**: `argparse` with subcommands.

**Rationale**: Principle XII forbids making a dependency out of code the project could own in a
few hundred readable lines, and the command surface here is two verbs with a handful of options.
More importantly, the dependency budget is six, and it should be spent on what cannot be written
here — numeric work and flatbuffer parsing in the analysis feature. A CLI framework would take a
slot for convenience.

**Alternatives considered**: `click` and `typer` give better help output, shell completion and
type-driven argument parsing, and neither is heavy or version-constraining. Rejected for now, not
on principle: if the help output or the option surface becomes genuinely worse for users,
adding `click` is one dependency gate away and the spec's requirements do not change.

**Review point**: when the command count passes roughly six verbs, re-examine.

---

## R2. YAML: `ruamel.yaml`, because `pyyaml` would set the project's Python policy

**Decision**: `ruamel.yaml`, used in safe mode.

**Rationale**: this is the first real test of Principle XII, and the obvious choice fails it.
Checked on 2026-10-22:

| Package | Latest | CPython wheel tags | Wheel for 3.15 |
|---|---|---|---|
| `pyyaml` | 6.0.3 | cp38–cp314 | **no** |
| `ruamel.yaml` | 0.19.1 | pure `py3-none-any` | n/a — works everywhere |

Python 3.15 was released on 2026-10-09 and is the current stable minor, so the constitution
requires supporting it. With no 3.15 wheel, installing `pyyaml` there falls back to building from
the source distribution, which needs a build toolchain and would break the install budget on a
clean machine — on Windows in particular. That is precisely "a dependency setting the project's
Python policy", which Principle XII forbids, and the remedy it prescribes is to replace the
dependency.

`ruamel.yaml` publishes a pure-Python wheel with **no required dependencies**; its C library is an
optional extra (`libyaml`/`oldlibyaml`) that we do not request, so no compiled artifact is
involved at all.

**Alternatives considered**:
- `pyyaml` with a Python floor of 3.14 until a 3.15 wheel appears — rejected: that is the
  dependency choosing the Python policy, which is the failure mode Principle XII exists for.
- `pyyaml` with the build fallback accepted — rejected: breaks the install budget and needs a
  compiler on a contributor's machine.
- Writing a YAML subset parser — rejected outright. The "own it yourself" rule applies to a few
  hundred readable lines, not to a format with an attack surface.

**Costs accepted**: `ruamel.yaml` is slower than a libyaml-backed `pyyaml`, which is irrelevant for
one small manifest per run. Its API differs (an instantiated `YAML(typ="safe")` object rather than
a module-level `safe_load`), so the loader is isolated in one module. It is a one-maintainer
project, which is a bus-factor risk shared with much of the ecosystem; the isolation in one module
is also the mitigation.

---

## R3. Schema validation: pydantic v2 with unknown fields forbidden

**Decision**: pydantic v2; every model sets `extra="forbid"`; no implicit type coercion where a
wrong type should be an error.

**Rationale**: the constitution's Technical Baseline requires "a schema library with strict, typed
models", and FR-003 requires rejection rather than silent acceptance of unknown fields. `pydantic`
itself is a pure-Python wheel; its compiled core, `pydantic-core` 2.50.1, publishes cp310 through
**cp315** wheels, so it does not block the current Python (checked 2026-10-22).

**Recorded risk**: `pydantic-core` is a compiled extension and is therefore the dependency most
likely to gate a future Python bump. It happens to be ahead of the curve today. The mitigation is
already constitutional: the policy obliges support for the current and previous minor only, and
the previous minor always has wheels. If a future release leaves the current minor without a
wheel for longer than the project can accept, Principle XII's remedies apply to pydantic too —
which is why the schema models are kept free of exotic pydantic features, so that the validation
layer stays replaceable.

**Alternatives considered**: hand-written validation over dataclasses (no dependency, but hundreds
of lines of error-prone cross-field logic and far worse messages); `jsonschema` plus a thin typed
layer (two dependencies instead of one, weaker typing); `attrs` plus `cattrs` (comparable, less
idiomatic for schema errors).

---

## R4. Python floor: 3.14

**Decision**: `requires-python = ">=3.14"`.

**Rationale**: the constitution requires the current and the previous stable minor. Checked against
the release record on 2026-10-22: 3.15 released 2026-10-09, 3.14 released 2025-10-07, 3.13
released 2024-10-07. Current and previous is therefore 3.15 and 3.14.

**Consequence**: the floor moves on its own schedule, roughly every October. That is a deliberate
maintenance cost — it is cheaper than the alternative Ludwig demonstrated, where the floor rises
only when a transitive dependency finally allows it.

---

## R5. Error messages: a translation layer and a fixture library

**Decision**: pydantic validation errors are never shown raw. One module maps them to the form
FR-002 requires — field path, what was wrong, what is accepted — and every message is pinned by a
fixture: one deliberately broken manifest per rule, with its expected message asserted.

**Rationale**: SC-002 requires that every rejection names the offending field path, which cannot
be verified by inspection and will decay without fixtures. Raw pydantic messages are written for
developers reading a traceback, not for an author fixing a manifest.

**Design notes**: an unknown field is reported with the accepted field names at that position. A
field that exists in the schema but sits at the wrong level is reported with both where it was
found and where it belongs, which is cheap because the schema is known statically. A failed
cross-field rule names the fields it relates, not just one of them.

**Alternatives considered**: showing pydantic's own messages with a prefix — rejected, it fails
FR-002 for enums and cross-field rules.

---

## R6. Migration registry: an instance, not a module-level singleton

**Decision**: the version registry is an object that holds schema version identifiers and the
transform that brings each up to the next. `caravan/v0` is the only version and has no transform.
The mechanism is proven by a test that builds a registry containing a synthetic older version with
one transform, and asserts a manifest declaring it loads, migrated.

**Rationale**: Principle IX requires the mechanism to exist before the first real schema change.
A mechanism with nothing in it is only credible if it is exercised, and exercising it requires
registering a version that production must not know about — which rules out a module-level
singleton. Ludwig's registry is the model (keypath-scoped transforms, applied on a copy, file
never rewritten); the deviation is that ours is injectable.

**Alternatives considered**: a module-level registry with monkeypatching in tests — rejected as
fragile and as a design smell. Deferring the mechanism until the first schema change — rejected:
that is exactly the retrofit Principle IX was written to avoid.

---

## R7. Templates split in two halves — the design's load-bearing decision

**Decision**: a template is two separate things.

- A **parameter spec** in the core: a stable identifier, a typed parameter model that validates
  itself, and later the declaration of what the architecture needs. No training framework.
- A **builder** in the training extra: the code that actually constructs the model. Imported only
  by the training stage.

This feature implements the parameter half, and registers exactly one template, `mlp`, because
that is what the pilot model uses.

**Rationale**: Principle VII requires a template to validate its own parameters, and Principle XII
requires the core to load no training framework. A single template object would have to do both,
so the two principles are only compatible if the template is split. This is the central structural
decision of the feature and the reason it can validate a manifest with no machine-learning
dependency at all.

**Alternatives considered**:
- Validating template parameters inside the training extra — rejected: `caravan validate` would
  then need the training framework, defeating the feature's purpose.
- Declaring parameters as plain schema in the core and keeping validation generic — rejected:
  weaker errors, and it moves template-specific knowledge out of the template, against VII.
- Registering `conv1d` as well, as the design document's v0.1 plan had it — rejected for now under
  Principle X: no model in this feature needs it. The registry's extensibility is proven by a test
  that registers a second template, not by shipping an unused one.

---

## R8. Format identifiers: no vendor product names

**Decision**: the export format values are `flatbuffer` and `c_array`, not `tflite` and
`model_cc`.

**Rationale**: constitution amendment 8 (v2.0.0) forbids vendor product names in identifiers that
outlive a release, because a rename turns into a schema migration. The TensorFlow Lite to LiteRT
rename is the live example: the runtime is now documented as LiteRT for Microcontrollers while the
repository is still `tflite-micro`.

**Open for the owner**: these names are cheap to change while the schema version is `v0` and no
manifest has been published. If you prefer different neutral names, say so before 001 merges —
afterwards it is a migration, which is exactly the cost this decision exists to avoid.

---

## R9. Determinism applies to the resolved manifest, not to the report

**Decision**: the resolved manifest is byte-identical across runs of the same tool version on the
same input. The run report is not, and must not be: it carries the run's identity and date, which
are the provenance Principle III requires.

**Rationale**: FR-013 says "identical output" without naming the artifact. Read literally it
contradicts FR-012, which requires the report to record the date. The resolution is the one that
serves the purpose — two runs are comparable field by field — so key ordering in the resolved
manifest is fixed by the schema, not by input order, and no timestamp, path or machine-specific
value appears in it.

**Testable form**: resolve twice, compare bytes of the resolved manifest; resolve twice, compare
the reports with the run identity and date fields excluded.

---

## R10. Run directory: one per invocation, never overwritten

**Decision**: `runs/<UTC timestamp>-<short manifest hash>/` holding `resolved-manifest.yaml` and
`report.json`. The directory is created fresh; an existing artifact is never overwritten or
removed. The location is overridable by an option, and the override may not point into an existing
run directory.

**Rationale**: the spec's edge case list and FR-012 require it. The manifest hash in the name makes
two runs of different manifests distinguishable without opening them; the timestamp orders them.

---

## R11. The layering check: three independent levels

**Decision**: the rule "no training framework in the core" is enforced three ways, because each
level catches what the others miss.

1. **Import assertion**: after importing every core module, no training framework appears in the
   loaded module table.
2. **Hostile import**: a hook makes importing a training framework raise, and the end-to-end
   validate and render runs must still pass. This catches a lazy import inside a function, which
   level 1 would miss.
3. **Clean-environment job**: continuous integration installs only the default package into a
   fresh environment with no machine-learning framework present and runs the integration tests.

A fourth, cheap check reads the declared dependencies of the built distribution and fails if the
set is larger than the budget or contains a framework.

**Rationale**: FR-026 requires that the build fail if the core ever loads a framework. A single
`sys.modules` assertion is not enough, because the violation that matters in practice is a
function-level import that only fires in production.

---

## R12. Install budget: measured, not asserted

**Decision**: a continuous integration job creates an empty environment, installs the built
default distribution with the cache disabled, and records wall-clock time and total bytes
downloaded. Over 30 seconds or over 50 MB fails the job (SC-003).

**Rationale**: Principle V — a budget that is not measured is a warning. The expected figures with
the chosen dependency set are roughly 4 MB and a few seconds, so the budget has deliberate
headroom for the numeric and flatbuffer dependencies the analysis feature will need. That headroom
is the point: the budget is meant to bind when something heavy is proposed, not to be renegotiated
then.

---

## R13. Board descriptions: data, with a stated source per value

**Decision**: board descriptions are YAML files shipped as package data, validated against their
own model. Every value carries a source reference, and emulator support is stated as it is,
including none. This feature loads, validates and lists them, and resolves target names against
them. It does not interpret their values.

Three boards, the ones the pilot manifest targets: `s32k144`, `stm32h743`, `esp32`. Their emulator
fields are filled from the prior-art research, not from the design document's example, which named
a Renode platform for the S32K144 that does not exist:

| Board | Emulator support |
|---|---|
| `stm32h743` | Renode platform exists (`stm32h743`) |
| `s32k144` | **none** — Renode has `nxp-s32k388` and `s32k118`, not S32K144 |
| `esp32` | **none** — Renode has no ESP32/Xtensa platform beyond a sample controller |

**Rationale**: FR-023 to FR-025, and Principle VII's rule that an emulator platform must not be
named unless it exists. Getting this right in the first board file that ships is cheaper than
correcting a claim later.

---

## R14. Packaging and environments

**Decision**: `hatchling` as the build backend; `uv` for environments and the lock file, matching
the zoo's existing setup. `pytest` as the only development dependency group needed in this
feature.

**Rationale**: the build backend is not a runtime dependency and does not count against the budget.
`uv` is already how the sibling project pins its environment, and consistency between the two
repositories is worth more here than a comparison of resolvers.

---

## Summary of what this phase changed

- The YAML dependency is `ruamel.yaml`, not `pyyaml`, because of a wheel gap on the current Python
  that Principle XII turns into a disqualification (R2).
- A template is two halves, not one object, which is what lets the core stay free of a training
  framework (R7).
- Export format identifiers avoid vendor product names, and are flagged as cheap to rename now and
  expensive later (R8).
- FR-013's determinism requirement is scoped to the resolved manifest (R9).
- The S32K144 and ESP32 board files will state that no emulator platform exists for them (R13).
