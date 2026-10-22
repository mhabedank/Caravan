# Adding a schema version

The manifest is the public interface of the framework and the archival record of how a published
model was built. Principle IX therefore requires that an older manifest be **migrated, not
refused** — and that the mechanism exist before the first schema change, not after.

This procedure is written down now, while there is nothing to migrate, because that is the only
moment at which it can be written calmly.

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
   a mapping and returns the mapping one version newer. Keep it mechanical — rename a key, move a
   block, convert a form. A transform that needs to make a decision is a sign the change needs
   splitting.
4. **Add a fixture** under `tests/fixtures/manifests/valid/` that declares the old version, and
   assert it loads with the transform applied and the file unchanged on disk.
5. **Write the migration note**: what changed, which fields it affects, and the mechanical edit an
   author would make by hand. Principle IX requires the note; it is what someone reading an
   archived manifest in two years needs.
6. **Check the entailment:** if the change makes a rule unreachable, move the rule out of
   `MANIFEST_REJECTION_RULES` rather than leaving a fixture that can never fail. `CF-5` is the
   worked example — see below.

## While the schema version is `v0`

Breaking changes are permitted, but each one still ships its transform and its note. The
identifiers most likely to move are the export `formats` values, which were deliberately chosen to
avoid vendor product names so that a product rename does not become a migration (research R8).

From the first stable version onward, a breaking change requires a **new** version identifier, and
its migration must exist before the change is released.

## A rule that cannot fire is not a rule

`CF-5` ("publication requires a complete compliance block") turned out to be entailed once the
schema existed: `compliance` is required for every manifest whether or not `publish` is present,
and each of its fields already rejects an empty value. No manifest can pass the compliance section
and still fail `CF-5`, so it has no runtime check and no fixture, and it lives in `ENTAILED_RULES`
with that reasoning recorded. FR-016 is satisfied structurally, which is a stronger guarantee than
a cross-field check rather than a weaker one.

`tests/unit/test_fixture_coverage.py` enforces both directions: every rule that can reject a
manifest has a fixture, and no identifier that cannot reject one has a fixture claiming it does.
