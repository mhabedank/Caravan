# Contract: The Stage Cache

Date: 2026-10-22 · Feature: 002 · Decisions: R7, R8 in [research.md](../research.md)

Principle III requires that a stage result be reusable when nothing it depends on has changed. This
is that mechanism, and the one place in the feature where being approximately right is the same as
being wrong: a cache that reuses a result it should not have is a silent incorrect answer.

## What a stage declares

```python
BUILD = StageSpec(
    name="build",
    reads=("model.template", "model.params", "dataset.window", "dataset.labels"),
    reads_dataset=True,
    upstream=None,
    artifacts=("model/built.keras", "model/built.json"),
)
```

The runner builds a **projection** from `reads` and hands the stage only that. A stage does not
receive the resolved manifest, so it cannot read a field it did not declare. The declaration is not
a comment that may drift from the code; it is the only access path.

`dataset.source` appears in no `reads` set. The identity of a result depends on the data, not on
where the data sits, so moving a dataset must not retrain and changing it must.

## The key

`sha256` over canonical JSON — `sort_keys=True`, `separators=(",", ":")`, UTF-8 — of:

```json
{
  "tool": "0.1.0.dev1",
  "schema": "caravan/v0",
  "stage": "train",
  "inputs": {"train.epochs": 50, "train.batch": 256, "...": "..."},
  "dataset": "sha256:4f1c…",
  "upstream": "sha256:9b22…"
}
```

- `tool` is in the key on purpose. A different tool version may produce a different model, and
  Principle III makes provenance part of the result. It costs a full retrain after a version bump,
  which is correct and, at this size, cheap.
- `dataset` is present only when the stage declared `reads_dataset`.
- `upstream` is the previous stage's key, so a changed build invalidates its training.

## The test that makes this real

Not a list of cases. The test walks **every leaf path of the pilot manifest**, changes it, and
asserts the key moves if and only if that path is in the stage's declared set. A field added to the
schema later cannot quietly escape it, and the two requirements it covers are the ones a reviewer
cannot verify by reading: editing compliance text never retrains (FR-015), and changing a template
parameter, the seed, a training setting or the dataset always does (SC-005).

## The store

```text
.caravan/cache/<stage>/<key>/
├── result.json          # the key's inputs, the run that produced it, the time, the artifacts
├── model/built.keras    # the stage's artifacts, exactly as declared
└── model/built.json
```

- `--cache-dir` moves the store; the default is `./.caravan/cache`, beside `runs/`, and both are
  ignored by git.
- A reused result is **copied** into the new run directory, never linked and never referenced. A run
  directory is complete on its own: a report that pointed into the cache would stop being readable
  the moment the cache was cleaned.
- An entry whose artifacts are missing or unreadable counts as absent, and the stage runs (FR-018).
  A corrupt entry is not an error to report; it is a cache miss.
- Nothing in the store is ever mutated. A new result is a new key.

## Bypass

`--fresh` ignores the cache for this run, produces the result again, and writes it to the store
under the same key. The report records `fresh: true`.

This is a cache bypass, not a gate being silenced, and the distinction is in the contract because
the constitution's Principle V turns on it: every rule still runs under `--fresh`, no threshold
moves, and there is no option anywhere that can skip a rule. What `--fresh` buys is a recomputation,
which is why it is safe to have.

## What the report records per stage

```json
"stages": [
  {"name": "build", "outcome": "reused", "key": "sha256:9b22…",
   "produced_by_run": "2026-10-22T17-04-31Z-ab12cd", "duration_s": 0.04,
   "artifacts": ["model/built.keras", "model/built.json"]},
  {"name": "train", "outcome": "produced", "key": "sha256:1d7e…",
   "upstream_key": "sha256:9b22…", "fresh": false, "duration_s": 18.4,
   "artifacts": ["model/trained.keras", "checkpoints/best.keras",
                 "checkpoints/final.keras", "metrics.json", "training-history.json"]}
]
```

`outcome` is `produced` or `reused` and is never omitted, which is what SC-004 checks: editing
compliance text and training again performs no training, and the report says the result was reused.
