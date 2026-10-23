# Contract: what changes at the command line

No verb is added or removed (Principle XII). Exit codes are unchanged: 0 success, 1 a rule or a
gate, 2 usage, 3 internal, 4 environment.

## `caravan validate`

- A previous-form manifest (`caravan/v0`), or one with no `apiVersion`, is refused with V-1 at
  `apiVersion`, exit code 1, naming `caravan/v0.1` and `docs/manifest-changes.md` (constitution
  4.0.0). No did-you-mean is offered for a version: changing only the version would not make an
  older form valid.
- With `--json`, the document carries `schema_version`, the version as declared (`null` when none
  is), in place of the former declared and effective pair.
- A removed field written in a `caravan/v0.1` manifest is an error at its path with the message in
  `contracts/manifest.md`, exit code 1.

## `caravan render`

- The resolved YAML goes to its usual destination; with `--stdout`, nothing else is printed to
  stdout, so the YAML stays parseable when piped.
- Derived fields print as `derived` (`contracts/manifest.md`).

## `caravan build | train | quantize | export`

- The stage sequence gains `data` before `build` and `fit` after `build`. `build` therefore also
  runs the fit check, as Principle V in 3.0.0 requires before any training.
- A run's `resolved.yaml` is written after the `data` stage and holds the derived values. If `data`
  fails, the run report records the failure, and `resolved.yaml` holds the markers.
- The run report carries one `schema_version` in place of `schema_version_declared`,
  `schema_version_effective` and `migrations_applied`, and gains:
  - `fit`, from `model/fit.json`, or the F-1 finding on failure;
  - `interface`, from `model/interface.json`, on export.

## Rule identifiers

- New: CF-9, CF-10, CF-11, DS-11, DS-12, F-1, X-6.
- Retired and reserved: CF-3, CF-5, CF-7, CF-8, DS-9, and V-2 (constitution 4.0.0).
- A test asserts that every new rule can be reached and is covered, as every earlier rule set has
  one.
