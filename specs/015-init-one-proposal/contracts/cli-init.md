# Contract: `caravan init` (feature 015)

Supersedes `specs/013-guided-manifest-setup/contracts/cli-init.md` where the two differ; everything
not restated here — what is written, the guarantees on the written file — is as feature 013 states.

```text
caravan init [<manifest>] [--dataset <path>] [--output <column>] [--output-type <type>]
             [--normal-label <value>] [--input <column>=<type>]... [--template <id>]
             [--params <yaml-flow-mapping>] [--window <rows>] [--board <id>]...
             [--quantization int8|none] [--budget <value>] [--name <model-name>]
             [--agents-md] [--overwrite] [--yes] [--no-input] [--json]
```

## Options

| Option | Answers / does | Change from feature 013 |
|---|---|---|
| `<manifest>` | the file to write | — |
| `--dataset` … `--name` | one item each, as in feature 013 | — |
| `--agents-md` | also write `AGENTS.md` beside the manifest ([agents-md.md](./agents-md.md)) | new |
| `--overwrite` | confirms replacing an existing `<manifest>`; never applies to `AGENTS.md` | — |
| `-y`, `--yes` | accept every proposal not given as an option; ask nothing | new |
| `--no-input` | ask nothing; without `--yes`, write nothing | **meaning changed**: no longer accepts proposals |
| `--json` | one result document on standard output ([init-result.md](./init-result.md)); ask nothing | new |
| `--plain` | — | **removed** |

No option skips or silences a check (`tests/contract/test_no_skip_option.py`). `--yes` does not
confirm an overwrite and does not answer an open item.

## Is anyone there to ask?

`init` asks only when standard input and standard error are both terminals and none of `--yes`,
`--no-input`, `--json` is given. Otherwise it never reads standard input.

## The flow with a person

1. **Data** — asked only when `--dataset` is not given. Readable directories and tables in the
   current directory are offered as numbered choices.
2. **Proposal** — shown once, in the layout below.
3. **Boards** — asked unless `--board` is given: every registered board with its RAM and flash and the
   model's lower bounds against them. Several as `1,3`. No board is proposed.
4. **Uncertain and open items** — each one not given, in the order output, output type, normal value,
   inputs, window, budget. All uncertain inputs are **one** step:

   ```text
   ? These columns could be read more than one way  (input_features)
       can_id   category   integers named like an identifier   or: number, -
       dlc      category   8 distinct integer values           or: number, -
   Enter to accept as shown, or edits like dlc=number, can_id=- >
   ```

   Enter takes the proposal; `<` goes back one step.
5. **Proposal** — shown again, now with the memory line per board.
6. **Decision**:

   ```text
   Enter: write synthetic-mlp.yaml · a: adjust · q: stop >
   ```

   `a` lists the items, numbered; the chosen one is asked with its question from feature 013 (lists,
   the columns, the window table and strip, the drawing, the parameter form, the memory panel), then
   back to 5. Enter is offered only when the proposal is ready (nothing open, nothing marked to check
   again); otherwise the line names what is missing. `q`, end of input or an interrupt: nothing
   written.

## The proposal, as shown

At most 24 lines of at most 80 characters (SC-007). One line per item:
`  <label, 10>  <value, 26>  <certainty>: <reason>`, cut with `…` at 80. Input columns are grouped by
proposed type; uncertain columns are named one per line, up to four, and beyond four grouped by
proposed type on one `uncertain` line each. The full reasons are in the JSON document and in the
question that asks the item. Figures below are illustrative.

```text
caravan init — proposal from data/synthetic, all 5,184 rows read

  output      label → category           certain: named like an answer
  inputs      number: b0, b1, b2         certain: numeric, 250+ distinct values
              category: can_id           uncertain: integers named like an id
              category: dlc              uncertain: 8 distinct integers
  window      16 rows                    certain: 0% mixed, ≥7 test windows each
  template    mlp, hidden [32, 16]       convention: first for a category output
  quantize    int8                       convention: accelerated on every board
  budget      accuracy_drop_max 0.02     convention: examples' value, not advice
  boards      —                          open: you choose the hardware
  name        synthetic-mlp              convention: data directory and template
  file        synthetic-mlp.yaml         convention: the model's name
  AGENTS.md   not written                convention: --agents-md writes one
```

Once boards are chosen, the boards line shows them (`answered` or `given`), and one memory line per
board follows it, with the label once:

```text
  boards      s32k144, esp32             answered
  memory      s32k144  flash ≥ 9.8 of 512 KB · RAM ≥ 2.6 of 64 KB   ✓
              esp32    flash ≥ 9.8 of 4096 KB · RAM ≥ 2.6 of 520 KB  ✓
              lower bounds, estimated before building; build checks again
```

A bound that exceeds a board, or a board that states no figure, is marked `✗` and printed as a note
before the decision. Certainty is always a word, never only a colour.

## Without a person

| Given | Result | Exit |
|---|---|---|
| `--yes`, nothing open | written; uncertain proposals taken are listed, each with its option | 0 |
| `--yes`, something open | nothing written; one line per open item with option and example | 2 |
| no `--yes` | nothing written; the proposal on standard error, the open items as above, then the accepting command | 2 |

```text
caravan init: nothing written: no one to ask, and --yes was not given
caravan init: no board: Caravan does not choose the hardware; give it with --board, for example
  --board esp32 (registered: esp32, s32k144, stm32h743)
caravan init: to accept the proposal: caravan init --dataset data/synthetic --board esp32 --yes
```

The accepting command is the command as given, plus each open item's example, plus `--yes`, quoted
for a POSIX shell.

Under `--yes`, the uncertain proposals taken, on standard error:

```text
caravan init: took 2 uncertain proposals: can_id as category (--input can_id=number to change),
  dlc as category (--input dlc=number to change)
```

## Streams

- Standard error: questions, the proposal, notes, findings, the final lines. With `--json`: nothing
  but a trace on a defect.
- Standard output: on success the written manifest's path, one line, as in feature 013; with
  `--json`, the result document and nothing else, in every outcome.
- Standard input: answers, one line each — read only when there is a person.

## Exit codes and outcomes

| Code | Outcome (`--json`) | When |
|---|---|---|
| 0 | `written` | the manifest (and the guide, when asked) is written and validates |
| 1 | `invalid` | without a person: the answers make a manifest `validate` refuses; findings printed, nothing written |
| 1 | `unusable` | the data cannot be set up by `init`: image inputs, no usable input, no template or no window size fits |
| 2 | `proposed` | no person and no `--yes` |
| 2 | `incomplete` | an open item has no answer |
| 2 | `refused` | an option value `init` would not offer (with the values it would), an unreadable data path or a header problem, an existing file without `--overwrite`, or `--plain`/`--tui` (as unknown options, by the parser, without a document) |
| 2 | — | stopped by the person (`q`, end of input, interrupt); never with `--json` |
| 3 | — | a defect in `init`: it offered a choice `validate` refuses |

`4` is not used: `init` needs nothing that installs separately.

## Final lines (success)

Standard error:

```text
wrote synthetic-mlp.yaml — valid
wrote AGENTS.md
next: caravan build synthetic-mlp.yaml
```

(`wrote AGENTS.md` only with `--agents-md`; `kept AGENTS.md: it exists, and init never changes it`
when one is there.) Standard output: `synthetic-mlp.yaml`.

## Change note (for `docs/releases/0.1.0.md`)

`caravan init` shows one proposal and asks only the boards and what it is unsure of. `--yes` accepts
the proposals; `--no-input` now only means "never ask" and writes nothing without `--yes` — a script
that used `--no-input` to accept adds `--yes`. Without a terminal, `init` never asks. `--plain` and the
`authoring` extra are gone: the line mode is the only interface, and an install that names
`authoring` gets the default installation. New: `--json`, `--agents-md`.
