# Contract: `caravan init`

**Feature**: 013-guided-manifest-setup

```text
caravan init [<manifest>] [--dataset <path>] [--output <column>] [--output-type <type>]
             [--input <column>=<type>]... [--template <id>] [--params <yaml-flow-mapping>]
             [--window <records>] [--board <id>]... [--quantization int8|none] [--budget <value>]
             [--name <model-name>] [--overwrite] [--no-input] [--plain]
```

Writes one new manifest. Never edits an existing one (constitution v4.3.0, Principle XII).

## Options

| Option | Answers | Notes |
|---|---|---|
| `<manifest>` | the file to write | default proposal `<name>.yaml` in the current directory |
| `--dataset` | the data | a directory of `.csv`/`.tsv`/`.txt` files with a header row, or one such file |
| `--output` | the column the model answers | |
| `--output-type` | `category`, `binary`, `number`, `anomaly` | only types the column's values allow |
| `--input` | one input column and its type, or `<column>=-` to leave it out | repeatable; columns not named keep their proposal |
| `--template` | a registered template | must answer the output type |
| `--params` | the template's parameters as a YAML flow mapping | e.g. `'{hidden: [32, 16]}'` |
| `--window` | records per window | only for a template that consumes a window |
| `--board` | a registered board | repeatable, order kept |
| `--quantization` | `export.quantization` | `int8` (proposed) or `none`; written only when `none` |
| `--budget` | the int8 budget of the output | key chosen by output type: `accuracy_drop_max`, `mae_increase_max` or `auc_drop_max` |
| `--name` | `model.name` | |
| `--overwrite` | confirms replacing an existing `<manifest>` | skips no check |
| `--no-input` | ask nothing; take options, then proposals | a missing answer with no proposal is a usage error |
| `--plain` | the line dialogue even when the `authoring` extra is installed | the full-screen interface starts only with the extra, and with both standard input and output terminals |

No option skips or silences a check (`tests/contract/test_no_skip_option.py` walks this verb too).

## Streams

- Questions, proposals, reasons, the summary and findings: **standard error**.
- On success, the written path, one line: **standard output**. Nothing else is written there.
- Answers are read from **standard input**, one line per question, whether or not it is a terminal.
  An empty line accepts the proposal — at the summary, the proposal is to write; `<` goes back one
  question.

## Exit codes

| Code | When |
|---|---|
| 0 | the manifest was written and validates |
| 1 | a rule says no: with `--no-input`, the answers produce a manifest `validate` refuses (findings printed, nothing written); or the data cannot be set up by `init` (image inputs, no usable input column) |
| 2 | usage: unknown option, an option value `init` would not offer (with the values it would), unreadable data path, data without a header or with differing headers, a missing answer under `--no-input`, the target exists without `--overwrite` under `--no-input`, or the session was aborted (interrupt, end of input) |
| 3 | a defect in `init` itself: it offered a choice that `validate` refuses (should not happen; the tests cover every offered combination, SC-002) |

`4` is not used: `init` needs nothing that installs separately.

## Final lines (success)

On standard error:

```text
wrote picket.yaml — valid
next: caravan build picket.yaml
```

On standard output:

```text
picket.yaml
```

## Guarantees

- The written file passes `caravan validate` unchanged (FR-003); `init` runs the same function on the
  exact bytes before moving them into place.
- The same answers and the same data produce byte-identical files (FR-020), in either mode.
- An aborted or refused run leaves no file and no temporary file behind (FR-004).
- `init` reads only the data it is pointed at, opens no network connection, and creates no run
  directory, cache or report.
