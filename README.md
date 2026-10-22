# Caravan

A declarative pipeline for small machine learning models that run on microcontrollers.

One YAML manifest per model describes *what* to build. The pipeline does the rest: architecture
from a template, training, int8 quantization, export, footprint analysis against a target board,
emulated verification, hardware benchmark, model card, publication.

Caravan is the build tool for the embedded models of the
[Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo) and lives in its own
repository under Apache-2.0, so that models built with it stay portable and the framework stays
usable outside the zoo.

**Scope, deliberately narrow:** models for microcontrollers and comparable constrained hardware.
Cloud, desktop and LLM models are explicitly out of scope, and so is becoming an inference
runtime, a platform description language, a cycle-accurate simulator or a research-grade
architecture search. See `.specify/memory/constitution.md`.

## Status

Early. Feature 001 implements the manifest contract and the package skeleton: `caravan validate`
and `caravan render`, with no machine-learning framework in the core.

## Install

```bash
pip install caravan-ml      # the command is `caravan`
```

The default installation has two runtime dependencies and pulls no machine-learning framework,
because checking and resolving a manifest does not need one. Training support installs separately.

## Use

```bash
caravan validate manifest.yaml     # is this manifest sound?
caravan render   manifest.yaml     # what will the pipeline actually use?
caravan templates                  # which templates are registered?
caravan boards                     # which target boards are known?
```

`validate` exits 0 when the manifest is sound, 1 when a rule says no, 2 on a usage error and 3 on
a defect in the tool itself. Every rejection names the offending field, what was wrong with it and
what is accepted there.

```text
manifest.yaml: export.targets[0] — unknown board "s32k145"
    known boards: esp32, s32k144, stm32h743
```

`render` writes the fully resolved manifest — every default expanded — next to a run report, so
two runs can be compared field by field.

## A manifest

```yaml
apiVersion: caravan/v0
model:
  name: picket-mlp
  version: 0.1.0
  topic: automotive-security
  task: can-ids
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1
dataset:
  source: datasets/car-hacking/
  window: 64
  labels: [normal, dos, fuzzy, replay]
  representative_samples: 500
export:
  targets: [s32k144, stm32h743, esp32]
compliance:
  eu_ai_act_class: limited-risk
  privacy: no-personal-data
  intended_use: "CAN bus intrusion detection on gateway and zonal ECUs"
  known_limits:
    - "Trained on the HCRL Car-Hacking dataset; behaviour on zero-day attacks is untested"
```

The compliance block is required by the schema, not by a review checklist. Responsibility for the
rights to the data stays with whoever brings the data: the manifest may state a licence and a
permitted use, Caravan holds the author to what they state, and reports what they did not state as
unverified rather than as a checked fact.

## Where things are

| | |
|---|---|
| `.specify/memory/constitution.md` | the rules: twelve principles, the scope boundary, the gates |
| `specs/<nnn>-<name>/` | one feature's spec, plan, research, data model, contracts and tasks |
| `docs/roadmap.md` | what is planned per version, and the non-goals, each with its reason |
| `docs/design/` | the design document Caravan was started from, frozen as a dated record |
| `docs/research/` | sourced research notes that decisions cite |
| `docs/budgets.md` | the dependency, install and Python-version budgets, with measurements |
| `src/caravan/targets/boards/` | the board descriptions, one data file per board |

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

See `specs/001-manifest-schema/quickstart.md` for the scenarios that validate the current feature,
and `CONTRIBUTING.md` for the dependency gate a new dependency has to pass.

## Licence

Apache-2.0. See `LICENSE`.
