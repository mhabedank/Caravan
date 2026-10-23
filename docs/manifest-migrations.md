# Adding a schema version

The manifest is the public interface of the framework and the archival record of how a published
model was built. Principle IX therefore requires that an older manifest be **migrated, not
refused** — and that the mechanism exist before the first schema change, not after.

This procedure was written down while there was nothing to migrate, because that is the only
moment at which it can be written calmly. Feature 006 was its first use: `caravan/v0` →
`caravan/v0.1`, with its note below.

## The mechanism

`caravan.manifest.migrate.SchemaVersionRegistry` holds the known versions, oldest first, and the
transform that brings each one up to the next. `migrate()` reads `apiVersion`, deep-copies the
mapping, applies every transform from the declared version onwards, and returns the result
together with the declared version, the effective version and the list of transforms applied.

Three properties matter and are covered by `tests/unit/test_migration.py`:

- the author's file is never rewritten — migration happens in memory, on a copy;
- a manifest that declares no version is treated as the oldest known one (rule V-2);
- only an **unknown** declared version is refused, and the refusal names the versions this build
  implements (rule V-1).

The registry is an instance rather than a module-level singleton, so a test can build one
containing a synthetic older version with a real transform. A mechanism with nothing in it is
credible only if it is exercised.

## The procedure

1. **Decide that the change is breaking.** A new optional field with a default is not: old
   manifests keep validating. A renamed field, a removed field, a changed meaning or a narrowed
   type is.
2. **Add the new version identifier** to `versions` in `default_registry()`, after the current
   one. The order is the migration order.
3. **Write the transform** for the version that is now no longer newest. It takes the manifest as
   a mapping and returns the mapping one version newer, together with one notice for every field
   it dropped, moved or added — `validate`, `render` and the run report print them, so nothing
   changes silently. Keep it mechanical — rename a key, move a block, convert a form. A transform
   that needs to make a decision is a sign the change needs splitting.
4. **Add a fixture** under `tests/fixtures/manifests/valid/` that declares the old version, and
   assert it loads with the transform applied and the file unchanged on disk.
5. **Write the migration note**: what changed, which fields it affects, and the mechanical edit an
   author would make by hand. Principle IX requires the note; it is what someone reading an
   archived manifest in two years needs.
6. **Check the entailment:** if the change makes a rule unreachable, move the rule out of
   `MANIFEST_REJECTION_RULES` rather than leaving a fixture that can never fail — see below. A
   rule whose field the change removes is retired, not deleted.

## While the schema version is `v0`

Breaking changes are permitted, but each one still ships its transform and its note. The
identifiers most likely to move are the export `formats` values, which were deliberately chosen to
avoid vendor product names so that a product rename does not become a migration (research R8).

From the first stable version onward, a breaking change requires a **new** version identifier, and
its migration must exist before the change is released.

## A rule that cannot fire is not a rule

`DS-7` and `X-5` live in `ENTAILED_RULES` with the reasoning recorded: no state of the schema can
reach them, so they have no fixture. `CF-5` was the first worked example, until feature 006 retired
it with the rest of the compliance layer.

## A rule that is retired stays reserved

`CF-3`, `CF-5`, `CF-7`, `CF-8` and `DS-9` were removed in feature 006 and sit in `RETIRED_RULES`:
in no rule group, in no fixture's expectation, raised by no module (`tests/unit/test_retired_rules.py`).
An identifier that came back with another meaning would make an old run report lie.

`tests/unit/test_fixture_coverage.py` enforces both directions: every rule that can reject a
manifest has a fixture, and no identifier that cannot reject one has a fixture claiming it does.

## `caravan/v0` → `caravan/v0.1` (feature 006, 2026-10-23)

Constitution 3.0.0 removed the compliance layer (Principle VI) and every field no stage reads
(Principle I), and made the manifest declare what goes into the model and what comes out. The
transform is `caravan.manifest.migrate.migrate_v0_to_v01`, driven by the one table in
`caravan/manifest/schema/removed.py`.

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

The migration names the input `input` and the output `output`, the names the templates have always
given their first and last layers. A hand-written new form picks names of its own; they become the
names a firmware author binds by (`model/interface.json`, the C header).

### Three things to know

- **Pin the labels to keep an old model.** Derived labels are sorted as text. A manifest that
  stated another order and drops the list trains a model whose output units are in a different
  order — a different model. The migration keeps the stated list, so a migrated manifest builds
  exactly the model it built before. On the synthetic fixture the difference decides whether the
  int8 gate passes (`specs/006-declared-io/research.md`, R11).
- **An unstated budget is written in.** The previous form defaulted `accuracy_drop_max` to 0.02;
  the migration states 0.02 and says so with an `added` notice.
- **Every cache entry misses once.** Every stage reads different paths now (`outputs[0].labels`
  rather than `dataset.labels`), and the projection is the key. This is correct, not a cache
  defect.

A manifest that stated `permitted_use: benchmark-only` and asked for publication was refused by
rule CF-8. It now migrates, and its notice says that Caravan no longer enforces that statement:
the restriction is the author's to keep.
