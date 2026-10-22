# Contract: Run Directory and Run Report

Date: 2026-10-22 · Feature: 001

Every invocation that writes anything writes it here, and nowhere else.

## Run directory

```text
runs/
└── 20261022T110431Z-9f3c1a2e/
    ├── report.json
    └── resolved-manifest.yaml      # render only
```

- The name is a UTC timestamp in basic ISO form, a hyphen, and the first eight hex characters of
  the manifest's SHA-256 — **extended by feature 002** with an optional `-2`, `-3`, … when runs of
  the same manifest start inside the same second, which the stage cache made an everyday case. The
  timestamp orders runs; the hash distinguishes runs of different
  manifests without opening them.
- The directory is created fresh by the invocation. If it exists, the run fails rather than
  overwriting — the only way to collide is to run the same manifest twice within the same second,
  and losing one of those is better than overwriting either.
- Nothing outside the run directory is written, created or removed, including the input manifest.
- `--runs-dir` moves the parent; it may not point inside an existing run directory.

## `report.json`

```json
{
  "caravan_version": "0.1.0.dev1",
  "command": "render",
  "started_at": "2026-10-22T11:04:31Z",
  "manifest_path": "manifests/picket-mlp.yaml",
  "manifest_sha256": "9f3c1a2e…",
  "dataset": "datasets/car-hacking/",
  "template": "mlp",
  "schema_version_declared": "caravan/v0",
  "schema_version_effective": "caravan/v0",
  "migrations_applied": [],
  "outcome": "valid",
  "gates": [
    {"name": "schema", "result": "pass"},
    {"name": "template-parameters", "result": "pass", "detail": "mlp"},
    {"name": "targets", "result": "pass", "detail": "s32k144, stm32h743, esp32"},
    {"name": "cross-field", "result": "pass"}
  ],
  "findings": [],
  "unresolved": [
    {"kind": "dataset-reference", "value": "datasets/car-hacking/", "reason": "not resolved in this stage"},
    {"kind": "dataset-terms", "value": "unknown", "reason": "not stated by the author; not verified by this tool"}
  ],
  "artifacts": {"resolved_manifest": "resolved-manifest.yaml"},
  "seed": 42
}
```

Field rules:

- `dataset` and `template` are provenance fields in their own right, not derived from `gates` or
  `unresolved`. Principle III names both in the record every artifact must carry, so a reader gets
  them without parsing a gate's `detail` string. `dataset` repeats the manifest's identifier
  verbatim and says nothing about resolution — that is what `unresolved` is for.
- `schema_version_declared` and `schema_version_effective` are both always present, even when
  equal (FR-010). `migrations_applied` is an ordered list of the transforms that ran.
- `outcome` is one of `valid`, `invalid`, `error`, matching exit codes 0, 1 and 3.
- `gates` lists every rule group that was reached, in order, each `pass`, `fail` or `skipped` with
  the reason. A group that was never reached is absent rather than reported as passing.
- `findings` is empty on success and otherwise carries the same entries as the `--json` output,
  including the `rule` identifier.
- `unresolved` records what was deliberately not checked. A dataset reference always appears here
  in this feature (rule D-1), so no reader can mistake a valid manifest for a resolved dataset. The
  dataset's terms appear whenever `permitted_use` is `unknown`, so that silence about a licence is
  visible as silence rather than passing for a clean result (FR-032). Where the author did state a
  permitted use, the statement is recorded and no `unresolved` entry is written for it — Caravan
  enforces it, and still never claims to have verified it.
- `artifacts` paths are relative to the run directory, never absolute, so a run directory can be
  moved or archived.
- The report is written for a failed run too. A run that produced no verdict at all, because the
  tool itself failed, writes a report with `outcome: error` where it can, and never a partial
  `resolved-manifest.yaml`.

## Determinism

Two runs of `render` on the same manifest with the same tool version produce:

- byte-identical `resolved-manifest.yaml` — fixed key order, no timestamp, no absolute path, no
  machine-specific value (research R9, SC-005);
- `report.json` differing **only** in `started_at` and in the run directory name. A test asserts
  exactly that by comparing the two reports with those fields removed.

## What the report is not

It is not a log. One invocation writes one report, at the end, describing what was decided. Progress
output goes to standard error and is not persisted. A later feature adds the measured results of
training and analysis to this same structure, each with the provenance label Principle IV requires;
this feature establishes the shape and writes no hardware number at all.
