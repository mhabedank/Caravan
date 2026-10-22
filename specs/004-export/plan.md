# Implementation Plan: Export

**Branch**: `004-export` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-export/spec.md`

## Summary

Take the quantized model of feature 003 and produce what a firmware author actually needs: the
serialised model, a C array with its header, an operator resolver holding exactly this model's
operators, a per-operator record of accelerated kernel coverage for every target board, and a
runner skeleton. Two findings from measurement shape the whole feature. The operator set must be
read from the model file, because the desktop interpreter reports a delegate node of its own that
does not exist on a microcontroller. And the conversion must fix the input batch to one, because
the converted mlp otherwise carries four operators of shape plumbing for a batch dimension that is
always one on a board — fixing it is faithful to the last bit and takes the graph from six distinct
operators to three.

The feature also closes an honesty gap it inherited: Principle VIII asks the export to document the
tensor arena size, and no desktop tool can supply that figure. The stage computes a floor by a named
method, labels it a floor, says what it omits, and the principle gains one sentence naming the stage
that supplies the real number.

## Technical Context

**Language/Version**: Python 3.13 for the whole pipeline; the proving half of this feature runs on
3.13 and 3.14 (the `verify` extra's window). Generated output is C++ as the runtime's own generator
writes it (research R3).

**Primary Dependencies**: no new ones. Reading the model file uses
`ai_edge_litert.schema_py_generated`, which is already inside the `verify` extra. The emitters use
the standard library. The dependency budget and the extras budget are untouched.

**Storage**: files in the run directory; the stage cache of feature 002.

**Testing**: pytest. The proving half runs in the `measure` matrix (3.13, 3.14) with no training
framework; conversion is exercised in the `train` job.

**Target Platform**: Caravan runs on a developer machine. The artifacts target Cortex-M and Xtensa
boards, and nothing in this feature executes anything for them.

**Project Type**: single Python package with a command line interface.

**Performance Goals**: the export of the pilot fixture completes in under 30 seconds (SC-001). It
reads one file of a few kilobytes and writes text; the budget is generous on purpose.

**Constraints**: no network (Principle VIII). No training framework needed for the proving half
(Principle XII). Generated files byte-identical across runs (FR-005). No figure about a target's
behaviour anywhere in the output.

**Scale/Scope**: one new stage, one new command verb, five new rule identifiers, two kernel coverage
data files, one amendment to the conversion of feature 003, one constitution amendment.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How this feature satisfies it | Verdict |
|---|---|---|
| I — own little code | No new dependency. The schema binding, the resolver's method list and the kernel directories are read from sources that already exist rather than reimplemented. | pass |
| IV — no unverified claim | The operator set is read from the file (FR-009). Every number names its method. The two memory figures are labelled with what they bound and in which direction. The feature states three things it may not claim: that the skeleton builds, that a kernel will be selected, and what the arena is. | pass |
| V — budgets are gates | Export happens only for a model that passed the accuracy gate (FR-008, rule X-2). No flag routes around it. | pass |
| VII — boards and templates are data | The accelerated library comes from the board description, and the libraries themselves become data files with a source and a date, not code. A board naming a library with no data refuses the run. | pass |
| VIII — no lock-in, portable artifacts | A standard flatbuffer, a plain byte array in a C-family source with its header, a runner skeleton naming the board's own toolchain. Nothing requires Caravan to use. No network. | **conditional — see below** |
| IX — no data in the repository | Nothing but the existing synthetic fixture. | pass |
| X — build what a named model needs | Only the operators the implemented templates produce are mapped in the coverage data; the rest are recorded as unmapped rather than guessed. | pass |
| XI — no Claude in model learning | Nothing in this feature labels, generates or evaluates data. | pass |
| XII — the layering rule and the budget | The proving half needs no training framework. No new extra, no new dependency, no change to the Python policy. | pass |

### The one conditional, and what closes it

Principle VIII requires: "The export MUST document the runtime, the operator set and the tensor
arena size it requires." The runtime and the operator set are exact and come from data. The arena
figure cannot be produced here at all — the runtime plans that memory with its own allocator on the
target, and the analysis tool available in the `verify` extra reports model and buffer sizes and no
arena (research R2, checked 2026-10-22).

There are three ways to handle a MUST that cannot be met, and only one of them is honest:

1. *Emit the sum of the read-write tensors and call it the arena.* This is what the first draft of
   the research intended, and it is wrong twice over: buffer reuse makes the sum an upper bound on
   the tensor area, not a floor, and scratch buffers mean it is not a bound on the arena in either
   direction. A number wrong by an unknown amount in an unknown direction, labelled as a
   requirement, is the exact failure Principle IV exists to prevent.
2. *Document a deviation in this plan and move on.* Permitted by the governance section, but it
   would leave a MUST in the constitution that no stage can ever satisfy, so every future feature
   would re-document the same deviation.
3. **Amend the principle by one sentence**: the export documents the runtime, the operator set and a
   **computed floor** on the working memory with the method named; the figure a target requires is
   documented by the stage that can measure it. This is chosen.

The amendment is MINOR, because it narrows what a MUST requires of one stage rather than only
clarifying wording, and it is a task of this feature (T002) rather than a silent reinterpretation.
The floor itself is the peak of simultaneously live read-write tensors — a real lower bound, since
any planner must hold at once what is live at once — computed on the pilot model as 648 bytes
against a read-write total of 720.

### Re-check after Phase 1 design

Re-read after the data model and the contracts were written. Three things changed and all three
tightened the alignment:

- The report carries **both** memory figures with their directions, because showing one invites a
  reader to treat it as *the* number (data model, `GraphInspection`).
- `RunnerRequirements.floor_is_not_the_requirement` is a sentence rather than a flag: what has to
  reach the reader is the sentence.
- Rule `X-5` was added after writing the coverage contract: a board naming an accelerated library
  with no sourced data refuses the run instead of printing "unknown" beside every operator.

No new violation. The conditional above remains the only one, and task T002 closes it.

## Project Structure

### Documentation (this feature)

```text
specs/004-export/
├── plan.md              # This file
├── spec.md              # 5 stories, 32 requirements, 10 success criteria
├── research.md          # R1–R8, every claim with its command or URL and date
├── data-model.md        # the types, which half of the install each belongs to, the X rules
├── quickstart.md        # how to see it work and see it refuse
├── contracts/
│   ├── cli.md           # `caravan export`
│   ├── artifacts.md     # the exported set, file by file
│   └── coverage.md      # what a coverage verdict claims, and what it does not
└── checklists/
    └── requirements.md  # 14 of 16, with the two exceptions explained
```

### Source Code (repository root)

```text
src/caravan/
├── cli/
│   ├── main.py                    # + the `export` subcommand
│   └── export.py                  # new: the command handler and the human summary
├── stages/
│   └── export.py                  # new: StageSpec, the stage body, the X rules
├── runtime/                       # extra `verify` — reads an exported model
│   ├── flatbuffer.py              # new: GraphInspection, OperatorRecord, the lifetime floor
│   └── inspect.py                 # unchanged (feature 003)
├── export/                        # new, core — turns a reading into text, needs no extra
│   ├── c_array.py                 # the array and its header, as the runtime's generator writes them
│   ├── resolver.py                # the resolver, from the explicit method table
│   ├── methods.py                 # new: builtin operator → resolver method, with source and date
│   ├── skeleton.py                # the runner skeleton per target
│   └── artifacts.py               # Artifact, ExportSet, RunnerRequirements
├── targets/
│   ├── kernels.py                 # new, core: KernelLibrary, CoverageVerdict, the lookup
│   └── kernels/
│       ├── cmsis-nn.yaml          # new data: operators, source, date, unmapped
│       └── esp-nn.yaml            # new data
├── convert/
│   └── batch.py                   # new, extra `train`: clone a trained model onto a batch of one
└── manifest/
    └── errors.py                  # + X-1 … X-5 as EXPORT_RULES

tests/
├── contract/test_export_contract.py      # the CLI contract, exit codes, the refusals
├── unit/test_c_array.py                  # round-trip, alignment, determinism
├── unit/test_resolver_methods.py         # the method table against the operators templates emit
├── unit/test_kernel_coverage.py          # the three outcomes and the refusal
├── unit/test_working_memory_floor.py     # the lifetime arithmetic, on hand-built graphs
├── unit/test_export_rules_coverage.py    # every X rule is reachable and covered
├── verify/test_flatbuffer_reading.py     # the operator set, with no training framework
├── verify/test_interpreter_differs.py    # the delegate node the file does not contain
└── train/test_export_end_to_end.py       # the pilot fixture, quantize then export
```

**Structure Decision**: the split follows the layering rule rather than tidiness. `runtime/`
grows the flatbuffer reader because reading an exported model is what that package is for and what
the `verify` extra buys. `export/` is new and lives in the **core**: once a reading exists, turning
it into a C array, a resolver and a skeleton is string formatting over plain data, and putting it
behind an extra would deny it to the default installation for no reason. `convert/batch.py` sits
with the conversion, behind the `train` extra, because cloning a Keras model needs Keras. The
kernel libraries become data under `targets/`, beside the board descriptions, because they are the
same kind of thing: a claim about hardware with a source and a date.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Principle VIII's arena clause cannot be satisfied by this stage | The figure is planned by the runtime's allocator on the target; no desktop tool reports it (research R2) | Emitting the read-write sum as "the arena" is wrong in an unknown direction (buffer reuse makes it an upper bound on the tensor area; scratch buffers are not in it) and would be a Principle IV violation to avoid a Principle VIII one. Documenting a deviation instead of amending would leave a MUST nothing can ever satisfy. The amendment names the stage that measures it. |
| A new source package (`export/`) rather than putting the emitters in `stages/export.py` | Four emitters with distinct contracts and their own tests: the array, the resolver, the method table, the skeleton | One module would mix the byte-level array contract with C++ code generation and the board-specific skeleton, and the method table is data with a source and a date that wants to be read on its own. |
