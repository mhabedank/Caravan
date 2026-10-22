# Phase 1 Data Model: Manifest Schema and Package Skeleton

Date: 2026-10-22 · Spec: [spec.md](./spec.md) · Plan: [plan.md](./plan.md) · Research: [research.md](./research.md)

Field types are stated in the abstract; the contract files hold the wire form. Rules are numbered
so tasks and tests can cite them.

---

## Manifest (`caravan/v0`)

The root object. One file, one model version.

| Field | Type | Required | Default | Rules |
|---|---|---|---|---|
| `apiVersion` | version identifier | yes | — | V-1, V-2 |
| `model` | Model | yes | — | |
| `dataset` | Dataset | yes | — | |
| `train` | Train | no | all defaults | |
| `export` | Export | yes | — | |
| `verify` | Verify | no | all defaults | |
| `bench` | Bench | no | all defaults | |
| `publish` | Publish | no | absent | CF-5 |
| `compliance` | Compliance | yes | — | |

Unknown fields are rejected at every level (FR-003). No `defaults` key exists at any level
(FR-014, Principle I).

### Model

| Field | Type | Required | Default | Rules |
|---|---|---|---|---|
| `name` | string | yes | — | lower-case, digits and hyphens, starting alphanumeric, at least 3 characters |
| `version` | string | yes | — | three dot-separated non-negative integers |
| `topic` | string | yes | — | non-empty |
| `task` | string | yes | — | non-empty |
| `template` | template identifier | yes | — | T-1 |
| `params` | template-defined object | no | template's own defaults | T-2 |

### Dataset

| Field | Type | Required | Default | Rules |
|---|---|---|---|---|
| `source` | string | yes | — | non-empty; shape only, D-1 |
| `split` | Split | no | 0.7 / 0.15 / 0.15, stratified | CF-1 |
| `window` | integer or absent | no | absent | greater than zero when present; CF-6 |
| `labels` | list of strings | yes | — | at least 2, unique, each non-empty |
| `representative_samples` | integer or absent | no | absent | CF-4 |

**Split**: `train`, `val`, `test` as fractions, plus `stratified` (boolean, default true). Named
parts, never a positional list (FR-018).

### Train

| Field | Type | Default | Rules |
|---|---|---|---|
| `epochs` | integer | 50 | greater than zero |
| `batch` | integer | 256 | greater than zero |
| `optimizer` | one of `adam`, `sgd`, `adamw` | `adam` | |
| `learning_rate` | number | 0.001 | greater than zero |
| `early_stopping` | boolean | true | |
| `patience` | integer | 5 | zero or more |
| `seed` | integer | 42 | recorded in every run report (Principle III) |

### Export

| Field | Type | Required | Default | Rules |
|---|---|---|---|---|
| `quantization` | one of `int8`, `float16`, `none` | no | `int8` | CF-4 |
| `formats` | list of `flatbuffer`, `c_array`, `onnx` | no | `[flatbuffer, c_array]` | non-empty, unique; R8 |
| `targets` | list of board identifiers | yes | — | at least 1, unique; B-1, CF-2 |
| `accuracy_drop_max` | number | no | 0.02 | between 0 and 1 inclusive |

### Verify

| Field | Type | Default | Rules |
|---|---|---|---|
| `emulator` | one of `renode`, `none` | `none` | CF-7 |

The default is `none`, not `renode`, departing from the design document: no emulator stage exists
yet, and more importantly two of the three boards the pilot targets have no Renode platform at all
(research R13). A default that cannot be honoured for most targets is a false promise.

### Bench

| Field | Type | Default | Rules |
|---|---|---|---|
| `metrics` | list of `latency_p50`, `latency_p99`, `ram_peak`, `flash` | `[latency_p50, ram_peak, flash]` | non-empty, unique |

### Publish

| Field | Type | Required | Default | Rules |
|---|---|---|---|---|
| `hf_repo` | string | yes | — | non-empty, `owner/name` shape |
| `license` | one of `apache-2.0`, `mit`, `cc-by-4.0` | no | `apache-2.0` | |

### Compliance — required

| Field | Type | Required | Rules |
|---|---|---|---|
| `eu_ai_act_class` | one of `minimal-risk`, `limited-risk`, `high-risk` | yes | CF-3 |
| `privacy` | one of `no-personal-data`, `anonymized`, `personal-data` | yes | CF-3 |
| `intended_use` | string | yes | at least 20 characters, not whitespace only |
| `known_limits` | list of strings | yes | at least 1, each non-empty |

---

## Rules

### Version rules

- **V-1**: `apiVersion` must be a known schema version identifier. An unknown one is refused, and
  the refusal lists the implemented versions (FR-009).
- **V-2**: a manifest with no `apiVersion` is treated as the oldest known version and migrated
  from there (FR-007).

### Template rules

- **T-1**: `model.template` must be a registered identifier. An unregistered one is rejected with
  the registered identifiers listed (FR-022).
- **T-2**: `model.params` is validated by the named template's own parameter model, which rejects
  unknown parameters with the same quality of message as the schema itself (FR-021, edge case).

### Board rules

- **B-1**: every entry of `export.targets` must be a known board identifier. An unknown one is
  rejected with the known identifiers listed (FR-023).

### Dataset rules

- **D-1**: `dataset.source` is checked for shape only — non-empty, and recognisable as either a
  filesystem path or a hub dataset reference. It is **not** resolved, and the run report records it
  as unresolved with the reason (FR-020).

### Cross-field rules

- **CF-1**: `dataset.split` parts sum to 1 within 1e-6, and every part is strictly greater than
  zero. A part of zero is rejected: a part with no data cannot be trained on, tuned on or
  evaluated against, and the frozen test part is the reference for every later result.
- **CF-2**: `export.targets` has no duplicates — rejected, never silently de-duplicated.
- **CF-3**: `compliance.privacy` of `personal-data` together with `eu_ai_act_class` of
  `minimal-risk` is rejected as a contradiction, naming both fields.
- **CF-4**: `export.quantization` of `int8` requires `dataset.representative_samples` of at least
  100. Calibration data determines the quantized activation ranges; too few or unrepresentative
  samples are a known cause of accuracy collapse, so the count is a schema requirement rather than
  a convention. 100 is the documented floor, not a recommendation — more is better, and the
  training feature will report the realised count.
- **CF-5**: when `publish` is present, every required `compliance` field must be present and
  non-empty. Checked before any network access is possible (FR-016, Principle VI).
- **CF-6**: when the named template declares that it consumes a time window,
  `dataset.window` must be present; when it declares it does not, `dataset.window` must be absent.
  This is how a template states a dataset requirement without the core knowing anything about
  model architecture.
- **CF-7**: `verify.emulator` of `renode` is rejected when any named target's board description
  states that no emulator platform exists for it. Naming an emulator for a board that has none is
  the false claim Principle VII forbids, and it is cheaper to reject it here than to discover it
  in the verification stage.

---

## Template parameter spec (core half)

What the core knows about a template. The builder half lives in the training extra and is not part
of this feature (research R7).

| Field | Type | Purpose |
|---|---|---|
| `identifier` | string | stable name used by `model.template`; never changes |
| `parameters` | typed model | validates `model.params`, with its own defaults |
| `consumes_window` | boolean | drives CF-6 |
| `summary` | string | one line, shown when listing templates |

Registered in this feature: `mlp` — parameters `hidden` (list of integers, each greater than zero,
at least one entry) and `dropout` (number from 0 to below 1, default 0.0); `consumes_window` true.

The registry is a mapping from identifier to spec, populated by the modules in the templates
package and extensible from outside the package without editing a central list (FR-021). Its
extensibility is proven by a test that registers a second template, not by shipping an unused one.

---

## Board description

One declarative file per board, shipped as package data.

| Field | Type | Required | Rules |
|---|---|---|---|
| `board` | identifier | yes | lower-case, digits and hyphens; must equal the file stem |
| `family` | string | yes | |
| `core` | string | yes | |
| `clock_mhz` | number | yes | greater than zero |
| `ram_kb` | number | yes | greater than zero |
| `flash_kb` | number | yes | greater than zero |
| `accel` | one of `cmsis-nn`, `esp-nn`, `none` | yes | a build-level claim, not a model-level one |
| `interfaces` | list of strings | yes | non-empty, unique |
| `toolchain` | Toolchain | yes | named by Principle VII; no stage in this feature reads it |
| `emulator` | Emulator or `null` | yes | `null` states that none exists; E-1 |
| `sources` | mapping | yes | S-1 |
| `notes` | string | no | |

**Toolchain**: `compiler` (the cross compiler a firmware build uses), `optimization` (the
optimization level Caravan builds with — a project decision, not a vendor default) and `runtime`
(the inference runtime, `tflm` throughout). Principle VII requires the field; no stage in this
feature interprets it, which is exactly why it has to be present now: adding it after the export
and analysis stages exist means migrating every board file that was shipped without it.

**Emulator**: `backend` (currently only `renode`), `platform` (the backend's own platform
identifier) and `status` (`supported` or `experimental`).

- **E-1**: the field is required and may be `null`, so "no emulator" is stated rather than omitted.
  A platform identifier must not be recorded unless it exists in the named backend (Principle VII).
- **S-1**: `sources` must contain an entry for every one of `clock_mhz`, `ram_kb`, `flash_kb`,
  `accel`, `toolchain` and `emulator`, each a citation a reader can check (FR-024). A value that is
  a project decision rather than a datasheet fact says so in its citation.

Shipped in this feature, with emulator support as the prior-art research established it:

| Board | `accel` | `emulator` |
|---|---|---|
| `stm32h743` | `cmsis-nn` | Renode, platform `stm32h743` |
| `s32k144` | `cmsis-nn` | `null` — Renode models S32K388 and S32K118, not S32K144 |
| `esp32` | `esp-nn` | `null` — Renode has no ESP32 platform |

---

## Resolved manifest

The manifest with every default expanded and every implicit value made explicit (FR-011). Same
shape as the manifest, with these differences:

- every optional field is present with its effective value;
- `model.params` is expanded with the template's parameter defaults;
- `apiVersion` is the effective version after migration, and the declared version is recorded in
  the run report rather than in the manifest, so the resolved form describes one schema only;
- key order is fixed by the schema, not by the input file, so two runs are byte-comparable (R9);
- no timestamp, absolute path or machine-specific value appears anywhere in it.

It is an artifact, never a file an author maintains.

---

## Run report

The machine-readable record of one invocation (FR-012).

| Field | Purpose |
|---|---|
| `caravan_version` | the tool that produced it |
| `command` | which command ran |
| `started_at` | UTC timestamp |
| `manifest_path`, `manifest_sha256` | which input, and its exact content |
| `dataset` | the dataset identifier as the manifest states it — provenance, not a resolution (Principle III) |
| `template` | the template identifier the manifest names (Principle III) |
| `schema_version_declared`, `schema_version_effective` | both, always (FR-010) |
| `migrations_applied` | ordered list, empty when none |
| `outcome` | `valid`, `invalid` or `error` |
| `gates` | each rule group checked, with its result |
| `findings` | for an invalid manifest: field path, what was wrong, what is accepted |
| `unresolved` | references deliberately not resolved, with the reason (D-1) |
| `artifacts` | paths written by this run, relative to the run directory |
| `seed` | the effective training seed, carried for provenance even though nothing trains here |

---

## Load sequence

```text
bytes → parse (safe mode) → apiVersion present? ──no──→ treat as oldest known (V-2)
                                   │yes
                                   ▼
                         known version? ──no──→ refuse, list implemented versions (V-1)
                                   │yes
                                   ▼
                      migrate in memory to current (FR-008; file untouched)
                                   ▼
                    schema validation, unknown fields forbidden (FR-003)
                                   ▼
            template resolved (T-1) → template parameters validated (T-2)
                                   ▼
                       board identifiers resolved (B-1)
                                   ▼
                        cross-field rules CF-1 … CF-7
                                   ▼
                 valid manifest → (render) resolve defaults → write artifacts
```

Every step that can fail produces a finding in the report as well as a message on the error
stream. The first failing step stops the sequence, except within schema validation, where all
field errors of one pass are collected and reported together — one run should tell an author
everything that is wrong at that level, not the first thing only.
