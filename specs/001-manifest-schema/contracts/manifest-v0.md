# Contract: Manifest `caravan/v0`

Date: 2026-10-22 · Feature: 001 · Field rules: [../data-model.md](../data-model.md)

The wire form of the manifest. Field semantics, types and rules live in the data model; this file
fixes the shape, so that a manifest written against it is accepted by any build that implements
`caravan/v0`.

## The pilot manifest, in full

This is the acceptance fixture (SC-004) — the real `picket-mlp` manifest, which must validate and
render.

```yaml
apiVersion: caravan/v0

model:
  name: picket-mlp
  version: 0.1.0
  topic: automotive-security
  task: can-ids
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1

dataset:
  source: datasets/car-hacking/
  split:
    train: 0.7
    val: 0.15
    test: 0.15
    stratified: true
  window: 64
  labels: [normal, dos, fuzzy, replay]
  representative_samples: 500

train:
  epochs: 50
  batch: 256
  optimizer: adam
  early_stopping: true

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [s32k144, stm32h743, esp32]
  accuracy_drop_max: 0.02

verify:
  emulator: none

bench:
  metrics: [latency_p50, ram_peak, flash]

publish:
  hf_repo: mhabedank/picket-mlp
  license: apache-2.0

compliance:
  eu_ai_act_class: limited-risk
  privacy: no-personal-data
  intended_use: "CAN bus intrusion detection on gateway and zonal ECUs"
  known_limits:
    - "Trained on the HCRL Car-Hacking dataset; behaviour on zero-day attacks is untested"
```

Three differences from the design document's example, each deliberate:

| Design document | Here | Why |
|---|---|---|
| `split: [0.7, 0.15, 0.15]` | named parts | FR-018; the positional list was the form Ludwig had to migrate away from |
| `formats: [tflite, model_cc]` | `[flatbuffer, c_array]` | constitution amendment 8: no vendor product names in durable identifiers |
| `verify: {emulator: renode}` | `emulator: none` | two of these three boards have no Renode platform (research R13), and CF-7 would reject the claim |

Added: `representative_samples`, now required by CF-4 because the export declares int8.

## The minimal manifest

Everything that is not required, left out. This must validate (FR-014: a minimal manifest is
sufficient).

```yaml
apiVersion: caravan/v0

model:
  name: pilot-min
  version: 0.0.1
  topic: automotive-security
  task: can-ids
  template: mlp
  params:
    hidden: [8]

dataset:
  source: datasets/example/
  window: 32
  labels: [normal, attack]
  representative_samples: 100

export:
  targets: [stm32h743]

compliance:
  eu_ai_act_class: minimal-risk
  privacy: no-personal-data
  intended_use: "Example model used to exercise the schema end to end"
  known_limits:
    - "Not trained; exists to validate the manifest contract"
```

`train`, `verify` and `bench` are absent and take their defaults; `publish` is absent, so nothing
can be published; `split` takes 0.7/0.15/0.15. `window` is present because the `mlp` template
declares that it consumes one (CF-6), and `representative_samples` because quantization defaults to
int8 (CF-4). Those two are the only non-obvious requirements in a minimal manifest, and both are
reported with the rule that demands them.

## Board description form

```yaml
board: stm32h743
family: st-stm32h7
core: cortex-m7
clock_mhz: 480
ram_kb: 1024
flash_kb: 2048
accel: cmsis-nn
interfaces: [can-fd, i2c, spi, uart]
toolchain:
  compiler: arm-none-eabi-gcc
  optimization: "-O3"
  runtime: tflm
emulator:
  backend: renode
  platform: stm32h743
  status: supported
sources:
  clock_mhz: "ST RM0433 reference manual, clock tree"
  ram_kb: "ST RM0433, system RAM map"
  flash_kb: "ST RM0433, embedded flash"
  accel: "CMSIS-NN supports Cortex-M7 with DSP and FPU"
  toolchain: "Caravan build decision, not a vendor default; unexercised until the export stage exists"
  emulator: "Renode supported boards list, platform stm32h743, read 2026-10-22"
notes: "Performance reference; not an automotive part"
```

A board with no emulator states it:

```yaml
board: s32k144
family: nxp-s32k
core: cortex-m4f
clock_mhz: 80
ram_kb: 64
flash_kb: 512
accel: cmsis-nn
interfaces: [can-fd, i2c, spi, uart]
toolchain:
  compiler: arm-none-eabi-gcc
  optimization: "-O3"
  runtime: tflm
emulator: null
sources:
  clock_mhz: "NXP S32K1xx data sheet"
  ram_kb: "NXP S32K1xx data sheet, SRAM plus 4 KB FlexRAM excluded"
  flash_kb: "NXP S32K1xx data sheet, program flash"
  accel: "CMSIS-NN supports Cortex-M4 with DSP and FPU"
  toolchain: "Caravan build decision, not a vendor default; unexercised until the export stage exists"
  emulator: "Renode supported boards list read 2026-10-22: nxp-s32k388, nxp-s32k388evb and s32k118 only; no S32K144"
notes: "ASIL-B automotive MCU; bench hardware only, no emulated rung"
```

The `emulator` source on a `null` entry carries the evidence for the absence, with the date it was
checked. A later Renode release may add the platform, and then the change is one line with a new
citation.

## Compatibility promise for `v0`

While the schema version is `v0`, a breaking change is permitted, but it ships with its migration
and a note (Principle IX). In practice, for this feature:

- the identifiers most likely to change are the `formats` values (research R8) — cheap now, a
  migration later;
- the `caravan/v0` identifier itself does not change until the schema is declared stable;
- a manifest that validates today keeps loading afterwards, through migration if necessary. That
  is the promise, and the registry that keeps it exists from this feature on, with nothing in it.
