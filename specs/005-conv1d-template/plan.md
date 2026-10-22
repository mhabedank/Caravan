# Implementation Plan: The conv1d Template

**Branch**: `005-conv1d` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-conv1d-template/spec.md`

## Summary

Add the convolutional template: a typed parameter half in the core, a builder half behind the
training extra, and a fixture manifest so the whole pipeline runs on the committed synthetic
dataset. The architecture it must express comes from `pace-cnn`'s input contract, read from the
zoo: 128 samples across 9 channels, six classes.

Most of this feature is small because four features of machinery already exist. What is genuinely
new is two things. The parameter model carries a *list of blocks* rather than parallel lists,
because a convolution block is four or five numbers and parallel lists let a reader pair the wrong
ones. And the window arithmetic — whether the configured blocks fit the window at all — needs a
home: the template spec gains one optional field, and the cross-field rule that already checks a
window against a template calls it.

The feature also writes down a measured trade rather than hiding it: the head that reduces over
time costs three times fewer parameters and one more operator on the reference implementation,
because neither built-in accelerated library has a kernel for the reduction.

## Technical Context

**Language/Version**: Python 3.13 for the pipeline; the parameter half runs on 3.13, 3.14 and 3.15
because it needs nothing but the core.

**Primary Dependencies**: none new. The parameter half uses the schema library already in the two
runtime dependencies; the builder half uses the framework already in the `train` extra.

**Storage**: the run directory and the stage cache, both unchanged.

**Testing**: pytest. The parameter half is tested in the no-extras matrix; the builder and the
end-to-end path in the `train` job.

**Target Platform**: Caravan runs on a developer machine. The models this template describes target
Cortex-M and Xtensa boards, and nothing here runs anything for them.

**Performance Goals**: the fixture's end-to-end run stays inside the budgets the earlier stages
already carry (60 s for quantize, 30 s for export). A convolution on a 64-sample window is not
where this project spends time.

**Constraints**: the parameter half imports no training framework (Principle XII). No dataset
enters the repository (Principle IX). No stage may branch on a template identifier. No new
dependency, extra, or rule identifier.

**Scale/Scope**: two new source files, one registry field, one extended rule, one fixture manifest,
and the tests for them.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How this feature satisfies it | Verdict |
|---|---|---|
| I — own little code | Two small files over machinery that exists. No new dependency. The sequence arithmetic is nine lines, verified against the framework rather than trusted to it. | pass |
| IV — no unverified claim | Every operator and byte figure in the spec and the research was measured and dated; the named model's quality and latency are quoted from the zoo's records with their benchmark, hardware and date; and the feature states plainly that it claims nothing about what a model built here achieves. | pass |
| V — budgets are gates | The accuracy gate applies unchanged and can fail this template's runs (FR-025). | pass |
| VII — templates and boards are data-like | A template is two files and a registration; no central list is edited (FR-004), proved by the listing test rather than asserted. | pass |
| IX — no data in the repository | The acceptance path uses the committed synthetic fixture. The named model's dataset is never fetched, referenced or required. | pass |
| X — build what a named model needs | Every parameter traces to the named model's shape. Separable convolution was measured, found cheap, and still left out because nothing needs it — with the measurement recorded so the next model finds it. | pass |
| XI — no Claude in model learning | Nothing here labels, generates or evaluates data. | pass |
| XII — the layering rule and the budget | The parameter half imports no framework; the builder is loaded by name; the dependency and extras counts are untouched (FR-026). | pass |

No conditional, and no deviation to document. The one open question this feature had — where the
window check belongs — is a design decision with three candidates, resolved in research R6 without
touching a principle.

### Re-check after Phase 1 design

Re-read after the data model and the contract were written. Two things changed, both narrowing:

- **The head's default is `average`**, decided on the measurement rather than left open: it is the
  smaller model, and a template for microcontrollers should default to the cheaper side of a trade
  and let the author buy the other.
- **`window_fit` returns a sentence, not a boolean.** The check's value is the message — the block
  that does not fit, the length when it was reached, and what would fit instead. A boolean would
  have forced the core to compose that sentence, and the core does not know what a kernel is.

## Project Structure

### Documentation (this feature)

```text
specs/005-conv1d-template/
├── plan.md              # This file
├── spec.md              # 4 stories, 26 requirements, 10 success criteria
├── research.md          # R1–R8, every claim with its command or path and date
├── data-model.md        # the parameters, the window check, the builder's one decision
├── quickstart.md        # how to see it work and see it refuse
├── contracts/
│   └── template.md      # what the template promises, refuses, and does not promise
└── checklists/
    └── requirements.md  # 14 of 16, with the two exceptions explained
```

### Source Code (repository root)

```text
src/caravan/
├── templates/
│   ├── conv1d.py                    # new, core: ConvBlock, Conv1dParameters, SPEC, window_fit
│   ├── sequence.py                  # new, core: the length arithmetic of research R5
│   ├── registry.py                  # + the optional `window_fit` field on TemplateParameterSpec
│   └── builders/
│       └── conv1d.py                # new, extra `train`: blocks to a model
└── manifest/
    └── schema/__init__.py           # CF-6 also asks the template whether the window fits

tests/
├── unit/test_conv1d_parameters.py   # every parameter's rejection, named and positioned
├── unit/test_sequence_length.py     # the arithmetic, against the cases research R5 verified
├── unit/test_window_fit.py          # the refusal's message: block, length, alternative
├── unit/test_template_registry.py   # (existing) + the second real template is discovered
├── contract/test_conv1d_manifest.py # validate and render; T-2 and CF-6 end to end
├── train/test_conv1d_build.py       # both shapes: the fixture's, and the named model's
└── train/test_conv1d_pipeline.py    # build → train → quantize → export on the fixture

tests/fixtures/manifests/valid/picket-conv1d-fixture.yaml   # new
```

**Structure Decision**: the arithmetic goes in its own core module rather than inside the template,
because it is the part most worth testing on its own and the part a second sequence template would
want. Everything else follows the shape the dense template already set: parameters in
`templates/`, builder in `templates/builders/`, and nothing else in the project learning that this
template exists.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| One field on `TemplateParameterSpec` (`window_fit`) | The window arithmetic needs both the template's parameters and the dataset's window; neither half can see both | A validator inside the parameter model cannot see `dataset.window`. A build-time refusal would let a manifest that can never work pass `caravan validate`, which is the verb's whole purpose. Special-casing the identifier in the core is forbidden by this feature's own FR-023. |
| A separate module for the sequence arithmetic | Nine lines that decide whether a refusal is trustworthy, verified against the framework on 14 cases | Inlining it in the template would make the cases hard to test and would hide them from the next sequence template that needs the same formulas. |
| A list of blocks rather than parallel lists | A convolution block is four or five values; parallel lists let a reader pair the wrong kernel with the wrong filter count and the schema cannot tell | The dense template's `hidden: [32, 16]` works because a layer there is one number. It does not generalise. |
