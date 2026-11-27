# Data Model: `caravan init` Proposes the Whole Manifest at Once

**Feature**: 015-init-one-proposal | **Date**: 2026-11-27

Nothing here is a manifest field: the schema does not change (Principle I). These are the objects
`init` holds while it runs, and the one document it prints. They extend feature 013's model
(`specs/013-guided-manifest-setup/data-model.md`): the column profile, the answer set and the session
stay as they are, with the additions below.

## Certainty

One of four values (spec FR-002), fixed per rule (research R1):

| Value | Meaning | Asked in a terminal? | Taken by `--yes`? |
|---|---|---|---|
| `certain` | from the data, by a rule that settles it | no | yes |
| `uncertain` | from the data, by a rule that does not settle it | yes | yes, and listed (FR-016) |
| `convention` | not from the data: a documented starting value | no | yes |
| `open` | no proposal | yes | no: a missing answer (FR-015) |

## Column profile (feature 013) — additions

| Field | Type | Meaning |
|---|---|---|
| `certainty` | Certainty | of `proposal`, set by the rule that made it |
| `alternatives` | tuple of type or `None` | what else the values allow, for the columns step and the JSON document |
| `never_decreasing` | bool | numeric, and no value below the one before it within any file (R1's new rule) |

Validation: `certainty` is `certain` only for the rules R1 classifies so. A test enforces it against
every shipped tabular dataset (FR-003).

## Item

One entry of the proposal. Identity: `key`, plus `column` for an input.

| Field | Type | Meaning |
|---|---|---|
| `key` | text | `output`, `output_type`, `normal_label`, `input`, `window`, `template`, `params`, `budget`, `quantization`, `boards`, `name`, `file`, `agents_md` |
| `column` | text or none | the column, for `key = input` |
| `field` | text | where it lands in the manifest, e.g. `output_features[0].type`; empty for `file` and `agents_md` |
| `value` | any | the answer, the given option's value, or the proposal; none when open |
| `source` | `given`, `answered`, `proposed` | where the value came from |
| `certainty` | Certainty or none | of the proposal; none for `given` and `answered` |
| `reason` | text | one line, naming the rule (research R1) |
| `alternatives` | list | the other values the question would offer |
| `option` | text | the option that sets it, e.g. `--output-type` |
| `example` | text | the option with a value valid here (research R5) |
| `stale` | bool | answered earlier, no longer fits a later change (feature 013, FR-035) |

`dataset` is not an item: it is given or asked before there is a proposal, and appears in the
document's `dataset` field.

## Proposal

The complete set of items for one manifest, derived after the data is read (FR-001).

| Field | Type | Meaning |
|---|---|---|
| `dataset` | path | as given, and the sample note ("read all 5,184 rows") |
| `items` | list of Item | in the order of feature 013's `ORDER`, inputs in column order |
| `memory` | list of Board memory | one per chosen board (FR-006); empty while no board is chosen |
| `to_ask` | list of keys | the items a person is asked: open or uncertain, not given, not yet answered; uncertain inputs as one entry |
| `notes` | list of Note | `init`'s own notes so far (sampled data, a board a bound exceeds, …): the line mode prints them before the decision, `--yes` on standard error, `--json` in the document |
| `ready` | bool | nothing open, nothing stale, every check passes — the decision may offer "accept" |

Derived, never stored: recomputed after every answer, because an answer can change a later item's
proposal and certainty (research R2).

## Board memory

| Field | Type | Meaning |
|---|---|---|
| `board` | text | a registered board |
| `flash_bytes`, `ram_bytes` | int | the lower bounds, as `build`'s fit check computes them |
| `board_flash_bytes`, `board_ram_bytes` | int or none | the board description's figures; none when it states none |
| `verdict` | `below`, `exceeds`, `unknown` | per resource, from `caravan.targets.fit`; anything but `below` is marked and becomes a note |
| `peak_layer` | text | the layer that sets the RAM floor |
| `label` | text | `lower bounds, estimated before building; caravan build checks them again` (Principle IV) |

## Note

A finding of `init`'s own, beside the validation findings (which keep `Finding.as_dict()`).

| `kind` | When |
|---|---|
| `sampled` | the proposal rests on the first 50,000 rows |
| `uncertain-taken` | `--yes` took an uncertain proposal; names the item and its option |
| `exceeds-board` | a lower bound exceeds a chosen board, or the board states no figure |
| `agents-md-kept` | an `AGENTS.md` already exists and was left unchanged |
| `missing` | an open item without an answer; names the option and example |
| `refused` | an option value `init` would not offer, unreadable data, an existing file without `--overwrite`: the reason, for outcome `refused` |
| `unusable` | the data cannot be set up (image inputs, no usable column, no template or window that fits): the reason, for outcome `unusable` |

## Result document

The JSON object `init --json` prints; the contract is [contracts/init-result.md](./contracts/init-result.md).

| Field | Type |
|---|---|
| `outcome` | `written`, `invalid`, `unusable`, `proposed`, `incomplete`, `refused` |
| `written` | list of paths, relative to the current directory; empty unless `written` |
| `dataset` | `{path, rows_read, complete}`, or none when the data could not be read |
| `items` | list of Item |
| `memory` | list of Board memory |
| `findings` | list of validation findings |
| `notes` | list of Note |
| `next` | the command to run next: `caravan build <file>` after writing; the accepting command otherwise |

## Agent guide

`AGENTS.md`, beside the manifest (FR-025 to FR-029); text in [contracts/agents-md.md](./contracts/agents-md.md).
Its only variable is the manifest's file name.

## States of a run

```text
start ─▶ reading data ─┬─▶ unusable (exit 1) / refused (exit 2)
                       └─▶ proposed ─┬─ person ──▶ asking ─▶ deciding ─┬─ accept ─▶ writing
                                     │                       ▲  │      ├─ adjust ─▶ asking one item ─┐
                                     │                       └──┼──────┘                             │
                                     │                          └───────────────────────────────────┘
                                     │                                  └─ stop ──▶ stopped (exit 2)
                                     ├─ --yes ──▶ (open items? incomplete, exit 2) ─▶ writing
                                     └─ no person, no --yes ─▶ proposed (exit 2)
writing ─▶ validating ─┬─▶ written (exit 0)
                       └─▶ invalid (exit 1 without a person; with a person, back to the item that owns the first finding, as in feature 013)
```

An existing target file without `--overwrite` is caught when the `file` item is checked: in a
terminal it is asked again (feature 013's `!` suffix stays); otherwise it is `refused`.
