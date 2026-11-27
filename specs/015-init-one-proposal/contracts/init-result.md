# Contract: the result document of `caravan init --json` (feature 015)

One JSON object on standard output per run that reaches `init` — whatever the outcome — and nothing
else there (spec FR-021 to FR-024). UTF-8, two-space indentation, keys in the order below, a trailing
newline, as `validate --json` prints. Every key is always present; a part that does not apply is
empty (`[]`) or `null` (FR-023).

A command line the parser rejects (an unknown option such as `--plain`) never reaches `init`: the
parser's usage message goes to standard error with exit code 2 and no document.

## Shape

```text
{
  "outcome":  "written" | "invalid" | "unusable" | "proposed" | "incomplete" | "refused",
  "written":  [path, ...],            // relative to the current directory; [] unless written
  "dataset":  {"path": str, "rows_read": int, "complete": bool} | null,
  "items":    [Item, ...],
  "memory":   [BoardMemory, ...],     // one per chosen board; [] while none is chosen
  "findings": [Finding, ...],         // validation findings, as validate --json prints them
  "notes":    [Note, ...],
  "next":     str | null              // the command to run next
}

Item = {
  "key": str,                         // output, output_type, normal_label, input, window, template,
                                      // params, budget, quantization, boards, name, file, agents_md
  "column": str | null,               // for key "input"
  "field": str,                       // manifest path, "" for file and agents_md
  "value": any | null,                // null when open and unanswered
  "source": "given" | "answered" | "proposed",
  "certainty": "certain" | "uncertain" | "convention" | "open" | null,   // null unless proposed
  "reason": str,
  "alternatives": [any, ...],
  "option": str,                      // e.g. "--input"
  "example": str,                     // e.g. "--input dlc=number"; valid for this data
  "stale": bool
}

BoardMemory = {
  "board": str,
  "flash_bytes": int, "board_flash_bytes": int | null, "flash_verdict": "below" | "exceeds" | "unknown",
  "ram_bytes": int,   "board_ram_bytes": int | null,   "ram_verdict":   "below" | "exceeds" | "unknown",
  "peak_layer": str,
  "label": "lower bounds, estimated before building; caravan build checks them again"
}

Finding = {"path": str, "problem": str, "found"?: any, "accepted"?: [any], "belongs_at"?: str,
           "rule"?: str}            // Finding.as_dict(), unchanged

Note = {"kind": "sampled" | "uncertain-taken" | "exceeds-board" | "agents-md-kept" | "missing"
                | "refused" | "unusable",
        "key": str | null, "column": str | null, "message": str, "example": str | null}
```

`outcome` and the exit code go together: `written` 0; `invalid`, `unusable` 1; `proposed`,
`incomplete`, `refused` 2 (see [cli-init.md](./cli-init.md)).

`next` is `caravan build <file>` after writing; for `proposed` and `incomplete` the accepting command
— the command as given, the open items' examples, `--yes`, `--json`; otherwise `null`.

## Example: a preview without `--yes` (abridged)

```json
{
  "outcome": "proposed",
  "written": [],
  "dataset": {"path": "data/synthetic", "rows_read": 5184, "complete": true},
  "items": [
    {"key": "output", "column": null, "field": "output_features[0].name", "value": "label",
     "source": "proposed", "certainty": "certain", "reason": "a column named like an answer",
     "alternatives": ["can_id", "dlc", "b0", "b1", "b2"], "option": "--output",
     "example": "--output label", "stale": false},
    {"key": "input", "column": "dlc", "field": "input_features", "value": "category",
     "source": "proposed", "certainty": "uncertain", "reason": "8 distinct integer values",
     "alternatives": ["number", null], "option": "--input",
     "example": "--input dlc=number", "stale": false},
    {"key": "boards", "column": null, "field": "export.targets", "value": null,
     "source": "proposed", "certainty": "open", "reason": "Caravan does not choose the hardware",
     "alternatives": ["esp32", "s32k144", "stm32h743"], "option": "--board",
     "example": "--board esp32", "stale": false}
  ],
  "memory": [],
  "findings": [],
  "notes": [
    {"kind": "missing", "key": "boards", "column": null,
     "message": "no board: Caravan does not choose the hardware", "example": "--board esp32"}
  ],
  "next": "caravan init --dataset data/synthetic --board esp32 --yes --json"
}
```

## Guarantees

- The same command on the same data prints the same document, byte for byte.
- A script that reads only a `proposed` or `incomplete` document can run `next` and get `written`,
  provided the examples are what it wants (SC-006).
- Paths are as given or relative to the current directory; no absolute path of the machine appears
  unless one was given.
