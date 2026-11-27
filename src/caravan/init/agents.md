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
