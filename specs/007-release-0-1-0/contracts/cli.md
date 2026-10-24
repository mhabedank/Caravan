# Contract: what changes at the command line

No verb is added or removed. Exit codes are unchanged.

## `--framework-output` (build, train, quantize, export)

- **Default.** While stages run, everything written to standard output and standard error by the
  training framework, the converter or a library is written to `framework.log` in the run directory
  instead. Caravan's own summary, findings and JSON are unaffected, because Caravan prints only
  after the stages.
- **With `--framework-output`.** Nothing is redirected and no `framework.log` is written.
- **On failure.** When a run stops, whether at a rule, a missing extra or an internal error, the
  descriptors are restored first, then Caravan reports. If `framework.log` is not empty, the last
  line of the message is:

  ```text
      framework output: <run dir>/framework.log
  ```

## `--json` on the stage verbs

The JSON document on stdout is the only thing on stdout. That was not true before this feature:
Keras printed its export listing there.

## `caravan --version`

Prints `caravan-ml <version>`, where the version equals the tag the package was built from.
