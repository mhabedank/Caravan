---
description: Caravan's documentation — where to start, where to get help, and where each part of Caravan is explained.
---

# Caravan documentation

Caravan turns sensor data and one YAML file into a machine-learning model that runs on a
microcontroller. Everything you need to know about it is here.

## First steps

New to Caravan? Start here.

**From scratch:** [Caravan at a glance](intro/overview.md) · [Installation](intro/install.md)

**Tutorial:**
[Part 1: Your first model](intro/tutorial01.md) ·
[Part 2: Your own data](intro/tutorial02.md) ·
[Part 3: Onto a board](intro/tutorial03.md) ·
[Part 4: When it does not fit](intro/tutorial04.md)

## Getting help

- Look up a word in the [glossary](glossary.md).
- Look up a field, a command, a rule or a board in the {ref}`genindex`.
- Read [what is verified today](ref/compatibility.md) for how far each part has been taken.
- Report a problem in the [issue tracker](https://github.com/mhabedank/Caravan/issues).

## How the documentation is organized

- **Tutorials** take you through a series of steps to a working result. Start with the
  [tutorial](intro/tutorial.md) if you are new.
- **Topic guides** explain one subject and why it works the way it does.
- **Reference guides** describe every field, command, rule and board. You look things up in them.
- **How-to guides** are recipes for one goal, for when you already know the basics.

## The manifest

The manifest is the one YAML file that describes a model: where the data is, which columns go in
and come out, and what the model has to fit.

- **Tutorial:** [Part 2: Your own data](intro/tutorial02.md)
- **Topic guides:** [Templates](topics/templates.md) · [Feature types](topics/feature-types.md)
- **Reference:** [The manifest reference](ref/manifest/index.md) ·
  [Schema changes](ref/manifest-changes.md)

## The pipeline and the CLI

Five stages — data, build, train, quantize, export — turn a manifest into files, and the `caravan`
command runs them.

- **Tutorial:** [Part 1: Your first model](intro/tutorial01.md)
- **Topic guide:** [The pipeline and the CLI](topics/pipeline.md)
- **Reference:** [The CLI reference](ref/cli.md)

## Boards and targets

A board is a data file that states its memory and its toolchain; `export.targets` lists the boards
a model has to fit.

- **Tutorial:** [Part 3: Onto a board](intro/tutorial03.md)
- **Reference:** [Boards](ref/boards.md) · [What is verified today](ref/compatibility.md)
- **How-to guide:** [Add a board](howto/add-a-board.md)

## Verification

Every model is measured again after it is shrunk to 8-bit integers. A run that loses more accuracy
than its budget allows, or does not fit its boards, exports nothing.

- **Tutorial:** [Part 4: When it does not fit](intro/tutorial04.md)
- **Topic guide:** [Budgets and gates](topics/budgets-and-gates.md)
- **Reference:** [Validation rules](ref/rules.md)
- **How-to guide:** [Choose a budget](howto/choose-a-budget.md)

## The exported model and the firmware

A run leaves an int8 model, the same model as a C array, and the interface contract your firmware
binds to.

- **Tutorial:** [Part 3: Onto a board](intro/tutorial03.md)
- **Topic guide:** [What a run leaves](topics/what-a-run-leaves.md)
- **Reference:** [Board runs](ref/board-runs/index.md)

## The project

- [Roadmap](roadmap.md) — what is planned, and what was decided against.
- [Release notes](releases/0.1.0.md)
- [Caravan's own budgets](ref/budgets.md) — dependencies, install time and supported Pythons.
- [Image credits](credits.md)

```{toctree}
:hidden:
:maxdepth: 2

intro/overview
intro/install
intro/tutorial
topics/pipeline
topics/templates
topics/feature-types
topics/budgets-and-gates
topics/what-a-run-leaves
ref/manifest/index
ref/cli
ref/rules
ref/boards
ref/manifest-changes
ref/compatibility
ref/board-runs/index
ref/budgets
howto/add-a-board
howto/choose-a-budget
glossary
roadmap
releases/0.1.0
```
