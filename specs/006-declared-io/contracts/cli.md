# Contract: what changes at the command line

No verb is added or removed (Principle XII). Exit codes are unchanged: 0 success, 1 a rule or a
gate, 2 usage, 3 internal, 4 environment.

## `caravan validate`

- A previous-form manifest validates. Its notices are printed after the verdict, one per line:

  ```text
  picket-mlp.yaml: valid (migrated from caravan/v0 to caravan/v0.1)
      dropped compliance — Caravan carries no compliance layer (Principle VI)
      dropped model.topic — no stage read it; the output's kind says what the model does
      moved dataset.window → inputs[0].window
      …
  ```

- With `--json`, the notices appear under `migration_notices`, as `path`, `action`, `to` and
  `reason`.
- A removed field written in a `caravan/v0.1` manifest is an error at its path with the message in
  `contracts/manifest.md`, exit code 1.

## `caravan render`

- The resolved YAML goes to its usual destination. Notices go to stderr, so the YAML stays parseable
  when piped.
- Derived fields print as `derived` (`contracts/manifest.md`).

## `caravan build | train | quantize | export`

- The stage sequence gains `data` before `build` and `fit` after `build`. `build` therefore also
  runs the fit check, as Principle V in 3.0.0 requires before any training.
- A run's `resolved.yaml` is written after the `data` stage and holds the derived values. If `data`
  fails, the run report records the failure, and `resolved.yaml` holds the markers.
- The run report gains:
  - `manifest.migration_notices`;
  - `fit`, from `model/fit.json`, or the F-1 finding on failure;
  - `interface`, from `model/interface.json`, on export.

## Rule identifiers

- New: CF-9, CF-10, CF-11, DS-11, DS-12, F-1.
- Retired and reserved: CF-3, CF-5, CF-7, CF-8, DS-9.
- A test asserts that every new rule can be reached and is covered, as every earlier rule set has
  one.
