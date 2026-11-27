# Contract: the `AGENTS.md` that `caravan init --agents-md` writes (feature 015)

Written beside the manifest, only after the manifest has validated, never over an existing
`AGENTS.md` (spec FR-025 to FR-029). The text below is the whole file; `{manifest}` — the manifest's
file name, as it is in that directory — is its only variable. No date, no version, no value from the
manifest. English.

````markdown
# Working on this model with Caravan

This directory describes one small model for microcontrollers in a Caravan manifest,
`{manifest}`. The manifest is the only description of the model: its data, inputs and outputs,
template, boards and budgets. To change the model, edit the manifest, then check it.

## Commands

| What | Command |
|---|---|
| Check the manifest | `caravan validate {manifest} --json` |
| Every value as Caravan resolves it | `caravan render {manifest} --stdout` |
| Build the model, and check before training that it can fit the boards | `caravan build {manifest} --json` |
| Then, in order | `caravan train`, `caravan quantize`, `caravan export`, each with `{manifest} --json` |

Every command runs offline. `validate`, `build` and the later stages write a report under
`runs/`; `render --stdout` writes nothing to disk.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | done |
| 1 | a rule said no: the manifest is invalid, or a gate failed; the output names the rule and the field |
| 2 | the command line is wrong |
| 3 | a defect in Caravan, not in this project |
| 4 | a part that installs separately is missing (the `train` or `verify` extra) |

## What belongs to the author

- The budgets in the manifest are gates. When one fails, report the failure and the table Caravan
  prints with it. Do not loosen a budget to make it pass; that is the author's decision.
- The data, its labels, the template, its parameters, the window and the boards are the author's
  choices. Do not generate or change data or labels, and do not try templates, parameters, windows,
  thresholds or budgets one after another until a gate passes. Make such a change only as the author
  states it.
- Datasets, raw data and credentials stay out of the repository.
- Caravan checks no licence, permission or use of the data, and neither does this file.

## Reference

Every manifest field: https://mhabedank.github.io/Caravan/ref/manifest/index.html
Every command: https://mhabedank.github.io/Caravan/ref/cli.html
````

## Checks

- Every command in the table exists, with the options shown (a test runs the parser on each line).
- `render` is given with `--stdout`, the form a program reads (its resolved manifest); the others
  with `--json` (spec FR-027).
- The text contains no value from the manifest besides its name (a test writes two manifests that
  differ in everything but the name and compares the guides).
- The "What belongs to the author" section is present verbatim (Principles V, VI, XI).
- The links resolve to pages the documentation build produces (the docs job checks links).
