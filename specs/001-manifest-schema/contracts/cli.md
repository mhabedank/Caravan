# Contract: Command Line Surface

Date: 2026-10-22 · Feature: 001 · Status: contract for implementation

The command line is the contract for both users and continuous integration, so its exit codes and
its streams are part of the interface, not an implementation detail.

## Commands

### `caravan validate <manifest>`

Checks one manifest. Writes nothing except a run report, unless `--no-report` is given.

| Option | Meaning | Default |
|---|---|---|
| `--runs-dir <path>` | where the run directory is created | `./runs` |
| `--no-report` | check only, write nothing at all | off |
| `--json` | findings on standard output as one JSON document | off |
| `-q`, `--quiet` | suppress the human summary; exit code only | off |

There is no option that skips a rule, lowers a threshold or continues past a failure (FR-005).

### `caravan render <manifest>`

Checks one manifest and, when it is valid, writes the resolved manifest and the run report into a
new run directory.

| Option | Meaning | Default |
|---|---|---|
| `--runs-dir <path>` | where the run directory is created | `./runs` |
| `--stdout` | write the resolved manifest to standard output instead of a run directory | off |
| `--json` | findings on standard output as one JSON document | off |

With `--stdout`, nothing is written to disk and no run directory is created, so the command stays
usable in a pipeline. The resolved manifest on standard output is byte-identical to the one that
would have been written to a file.

### `caravan templates` and `caravan boards`

List the registered template identifiers and the known board identifiers, one per line, with the
one-line summary. These exist because every rejection of an unknown identifier promises a list,
and a user needs a way to ask for that list without triggering an error.

### `caravan --version`

Prints the distribution version and exits.

## Exit codes

The pipeline contract requires a failed rule to be distinguishable from a crash (FR-004).

| Code | Meaning |
|---|---|
| 0 | the manifest is valid; any requested artifact was written |
| 1 | the manifest is invalid, or a declared schema version is unknown — a rule said no |
| 2 | usage error: unknown option, missing argument, unreadable path |
| 3 | internal failure of the tool itself — a defect, reported as one, with a trace |

Code 1 is never used for an internal failure, and code 3 is never used for a manifest that merely
broke a rule. A continuous integration job can therefore treat 3 as "file a bug" and 1 as "fix the
manifest".

**Extended by feature 002**: code 4 means the environment is incomplete — a part that has to be
installed separately is not there. It is neither a broken rule nor a defect, which is why it is its
own code rather than one of these four. See `specs/002-build-and-train/contracts/cli.md`, which also
carries the enumerated verb list that Principle XII's fixed verb set refers to.

## Streams

- **Standard output** carries the answer: the resolved manifest under `--stdout`, the JSON document
  under `--json`, the lists, the version. Nothing else.
- **Standard error** carries messages for people: the human-readable summary and every finding.
- With `--quiet`, standard error stays empty on success.

This split is what makes `caravan render manifest.yaml --stdout > resolved.yaml` safe.

## Message form

Every finding, on either stream, carries the three parts FR-002 requires:

```text
manifest.yaml: dataset.split.train — expected a number between 0 and 1, found "0.7 "
    the parts of dataset.split must sum to 1.0 and each be greater than zero
```

```text
manifest.yaml: model.templte — unknown field
    accepted here: name, version, topic, task, template, params
    did you mean: template
```

```text
manifest.yaml: export.targets[0] — unknown board "s32k145"
    known boards: esp32, s32k144, stm32h743
```

```text
manifest.yaml: apiVersion — unknown schema version "caravan/v1"
    this build implements: caravan/v0
```

Rules:

- The field path is the first thing after the file name, always, in dotted form with list indices.
- A cross-field rule names every field it relates, not only the one it was detected on.
- An unknown field lists the accepted names at that position, and suggests the nearest one when the
  edit distance is small.
- A field that exists in the schema but at another level says where it was found and where it
  belongs.
- No message contains a pydantic type name, a Python traceback or an internal module path. Those
  belong to exit code 3 only.

## JSON form

Under `--json`, standard output carries one document:

```json
{
  "manifest": "manifest.yaml",
  "outcome": "invalid",
  "schema_version_declared": "caravan/v0",
  "schema_version_effective": "caravan/v0",
  "findings": [
    {
      "path": "export.targets[0]",
      "problem": "unknown board",
      "found": "s32k145",
      "accepted": ["esp32", "s32k144", "stm32h743"],
      "rule": "B-1"
    }
  ],
  "unresolved": [
    {"kind": "dataset-reference", "value": "datasets/car-hacking/", "reason": "not resolved in this stage"}
  ]
}
```

The `rule` field carries the identifier from the data model, so a test can assert which rule fired
rather than matching prose.

## Guarantees

- No command in this feature opens a network connection. A test asserts it by making socket
  creation raise.
- No command writes to or near the input manifest. A test asserts the input file's hash is
  unchanged after every command.
- No command requires a training framework (FR-026).
- `validate` and `render` on the same valid manifest agree: the same findings, the same unresolved
  references, the same effective schema version.
