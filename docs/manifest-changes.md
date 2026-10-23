# Schema changes

The manifest is the public interface of the framework. How it may change depends on where Caravan
is (constitution 4.0.0, Principle IX).

## Before 1.0.0: variable, with a change note

Until Caravan 1.0.0 the schema, the command line, the run report and the artifacts may change
without migration and without compatibility. What holds in every phase:

- every manifest declares its schema version (`apiVersion`);
- the author's file is never rewritten;
- an unknown field is refused with its path and the accepted fields;
- a manifest whose version this build does not implement — older, newer, **or none declared** — is
  refused with rule V-1, naming the implemented version and pointing here. It is never migrated and
  never read as some other version;
- a breaking change gets a new version identifier and a section below: what changed, and the edit
  an author makes by hand.

A run stays reproducible without migration because every provenance record carries the Caravan
version that produced it (Principle III): an old manifest runs with the Caravan it was written for.

## The procedure for a breaking change

1. **Decide that the change is breaking.** A new optional field with a default is not: existing
   manifests keep validating. A renamed field, a removed field, a changed meaning or a narrowed
   type is.
2. **Change the version identifier** in `caravan/manifest/version.py` (`SCHEMA_VERSION`) and in
   the schema's `apiVersion` literal. Rewrite the fixtures under `tests/fixtures/manifests/` in the
   new form; nothing in the test suite keeps the old one alive.
3. **Give a removed or moved field its own message** in `caravan/manifest/schema/removed.py`, so an
   author who still writes it learns that it is gone, not that it is misspelt.
4. **Write the change note** as a section below.
5. **Check the entailment:** if the change makes a rule unreachable, move the rule out of
   `MANIFEST_REJECTION_RULES` rather than leaving a fixture that can never fail. A rule whose field
   the change removes is retired, not deleted.

## From 1.0.0: stable

1.0.0 is a deliberate amendment of the constitution. From it, a breaking change requires a new
version identifier and a registered migration that upgrades an older manifest in memory, with a
notice for every field it drops, moves or adds — the full rules of Principle IX, written before the
first change that needs them.

## A rule that cannot fire is not a rule

`DS-7` and `X-5` live in `ENTAILED_RULES` with the reasoning recorded: no state of the schema can
reach them, so they have no fixture.

## A rule that is retired stays reserved

`CF-3`, `CF-5`, `CF-7`, `CF-8` and `DS-9` were removed in feature 006 with the compliance layer;
`V-2`, which read a manifest without a version as the oldest known one, was retired by constitution
4.0.0. They sit in `RETIRED_RULES`: in no rule group, in no fixture's expectation, raised by no
module (`tests/unit/test_retired_rules.py`). An identifier that came back with another meaning
would make an old run report lie.

`tests/unit/test_fixture_coverage.py` enforces both directions: every rule that can reject a
manifest has a fixture, and no identifier that cannot reject one has a fixture claiming it does.

## `caravan/v0` → `caravan/v0.1` (feature 006, 2026-10-23)

Constitution 3.0.0 removed the compliance layer (Principle VI) and every field no stage reads
(Principle I), and made the manifest declare what goes into the model and what comes out. The
messages for the removed fields come from `caravan/manifest/schema/removed.py`.

### What changes, and the edit an author makes by hand

| Previous form | New form | Why |
|---|---|---|
| `model.topic`, `model.task` | — | no stage read them; the output's `kind` says what the model does |
| `compliance` | — | Caravan carries no compliance layer; a project that needs one adds it on top |
| `dataset.license`, `dataset.permitted_use` | — | Caravan does not check data rights and does not claim to |
| `verify`, `bench`, `publish` | — | no stage reads them yet; each returns with its stage |
| `dataset.window` | `inputs[0].window` | a window describes how the input is cut |
| `dataset.labels` | `outputs[0].labels` (optional) | labels are derived from the data; a list only pins their order |
| `export.accuracy_drop_max` | `outputs[0].accuracy_drop_max` (**required**) | the budget is per output, and stated (Principle V) |
| the `label` column | `outputs[0].column`, default `label` | the output names the column it reads |
| every other column | `inputs[0].columns`, default all but the output's | the input names the columns it reads |

By hand, the pilot goes from

```yaml
apiVersion: caravan/v0
model: {name: picket-mlp, version: 0.1.0, topic: automotive-security, task: can-ids,
        template: mlp, params: {hidden: [32, 16], dropout: 0.1}}
dataset: {source: data/, window: 64, labels: [normal, dos, fuzzy, replay],
          representative_samples: 500}
export: {targets: [s32k144, stm32h743, esp32], accuracy_drop_max: 0.02}
compliance: {...}
```

to

```yaml
apiVersion: caravan/v0.1
model: {name: picket-mlp, version: 0.1.0, template: mlp, params: {hidden: [32, 16], dropout: 0.1}}
inputs: [{name: frames, kind: series, window: 64}]
outputs: [{name: attack, kind: class, labels: [normal, dos, fuzzy, replay], accuracy_drop_max: 0.02}]
dataset: {source: data/, representative_samples: 500}
export: {targets: [s32k144, stm32h743, esp32]}
```

The names (`frames`, `attack`) are the author's choice; they become the names a firmware author
binds by (`model/interface.json`, the C header).

### Two things to know

- **Pin the labels to keep an old model.** Derived labels are sorted as text. A manifest that
  stated another order and drops the list trains a model whose output units are in a different
  order — a different model. Keep the stated list under `outputs[0].labels` to build exactly the
  model it built before. On the synthetic fixture the difference decides whether the int8 gate
  passes (`specs/006-declared-io/research.md`, R11).
- **State the budget.** The previous form defaulted `accuracy_drop_max` to 0.02; the new form has
  no default, so write the value you relied on.

A manifest still in the previous form is refused with V-1 at `apiVersion`; a previous-form field
written into a `caravan/v0.1` manifest is refused at its own path with the reason in the table
above.
