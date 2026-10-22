# Learnings from prior art

Date: 2026-10-22 · Status: research note, input to the constitution and to the first specs

The design document positions Caravan against Ludwig, MCUNet/TinyNAS/TinyEngine, Once-for-All,
Edge Impulse and TFLM+CMSIS-NN. This note records what those projects have already learned the
hard way, and what each learning costs us if we ignore it now. Two findings contradict
assumptions in the design document; they are marked **correction**.

Every claim here has a source at the bottom. Where a source is secondary or I could not confirm
it, that is stated.

---

## A. From Ludwig — the direct inspiration

### A1. Store the schema version in the manifest and ship a mechanical upgrader, not a rejection

Ludwig keeps a `ludwig_version` key inside the config and runs
`upgrade_config_dict_to_latest_version()` on **every** load, before the config object is built.
The migrations live in a `VersionTransformationRegistry`; each one is a function registered with
`@register_config_transformation(version, prefixes=[...])`, where `prefixes` scopes the transform
to a keypath such as `input_features` or `trainer`. A transform runs when
`from_version < version <= to_version`; a config with no version gets every migration. The upgrade
runs on a copy, so the user's file is never rewritten.

Our draft constitution (Principle IX) says an old manifest is *rejected* with a migration message.
Ludwig's design is better for exactly our case: the manifest is not only an input, it is the
archival record of how a published model was built. A rejection turns every archived manifest into
dead weight the moment the schema moves.

**Consequence:** declare the schema version, auto-upgrade in memory, never rewrite the file, and
record both the original and the effective version in the run report. The registry costs nothing
to add while it holds zero transforms, and is expensive to retrofit after the first migration is
needed.

### A2. Ludwig's schema churned in three places — and we have all three

By migration count, Ludwig's churn concentrated in 0.5 and 0.6, in:

- the trainer section (`training` → `trainer`, then changed again in 0.6 twice and 0.7),
- preprocessing and split settings (`force_split`/`split_probabilities`/`stratify` → one `split`
  block),
- encoder and decoder parameters (un-nested top-level keys → nested under `encoder`/`decoder`).

Our analogues are `train`, `dataset.split` and `model.params`.

**Consequence:** the design document already nests template parameters under `model.params` and
models the split as an object — those are the shapes Ludwig had to migrate *to*. Keep them. Note
the inconsistency in the design document itself: the example manifest writes
`split: [0.7, 0.15, 0.15]` (a list) while the pydantic schema defines a `Split` object. Resolve
that to the object form before the first manifest is published, not after. And expect `train` to
be the section that moves most: keeping it thin and template-agnostic, with everything
template-specific inside `model.params`, limits the blast radius.

### A3. Do not build a `defaults` section

Ludwig's top-level `defaults` block sets type-global preprocessing, encoder, decoder and loss
settings, overridden per feature. Its own documentation shows the cost: you must repeat `type`
whenever you touch an encoder parameter, only one default encoder per feature type is allowed,
some keys are silently ignored depending on the tokenizer, the block covers only four sections
(combiner and trainer are configured elsewhere), and the YAML and CLI examples on the page use
different key names for the same setting.

**Consequence:** Caravan resolves defaults from exactly two places — the template and the board
description — and offers no user-facing defaults/override hierarchy. One manifest, one model, no
inheritance.

### A4. Emit the resolved manifest as a run artifact

Ludwig can print a fully populated config, but only through a separate `render_config` command.
Its per-run `description.json` is documented as "a file containing a description of the training
process with all the information to reproduce it" — while, per the same page, library versions and
a commit hash are not among the things it records.

**Consequence:** Caravan writes the fully resolved manifest *and* the provenance record into every
run directory, as an artifact, not as an optional command. This is what makes Principle III
checkable and lets two runs be diffed.

### A5. Scope discipline is a survival property, not tidiness

Ludwig is alive — v0.17.9 released 2026-08-16, an LF AI & Data project, repo active in
October 2026. But the Linux Foundation health score is Fair (54/100), dragged down by maintainer
coverage, and v0.17's headline features are LLM and VLM work (VLM fine-tuning, GRPO alignment)
sitting in the same codebase as the declarative tabular core.

**Consequence:** this is the empirical argument for Principle II. Excluding the zoo's LLM models
from Caravan is not only about a clean abstraction — it is what keeps a project with one
maintainer reviewable. It is also a bus-factor warning about Caravan itself: the smaller the
surface, the longer it stays maintainable.

---

## B. From MCUNet / MCUNetV2 — what actually binds on an MCU

### B1. Peak activation memory binds, it is concentrated early, and one number is not enough

MCUNetV2 names the imbalanced memory distribution as the primary memory bottleneck of most CNN
designs: the first few blocks use an order of magnitude more memory than the rest of the network.
Its remedy (patch-based inference) reduces peak memory of existing networks by 4–8×. MCUNet makes
the same point from the other side: MobileNetV2's peak memory sits in a single block, while a
network with a balanced per-block activation profile fits more capacity into the same SRAM budget.

**Consequence:** the analyze stage must produce a per-layer activation-memory profile and report
the peak **together with the layer that causes it**. An aggregate "RAM: x KB" hides the only thing
a contributor can act on. A model with an acceptable average can fail on one early tensor. This is
also what turns the hardware requirement record of Principle VII from documentation into a usable
output.

### B2. FLOPs is a ranking heuristic inside a feasible set, not a cost model

TinyNAS uses the FLOPs distribution of networks that **already satisfy** the memory constraint to
rank search spaces, on the assumption that within one model family higher FLOPs correlate with
higher accuracy. It is not used as a predictor of latency or memory.

**Consequence:** a FLOPs-derived latency figure in Stage 4 is a crude ordering signal, nothing
more. This supports keeping the heuristic deliberately simple and strictly subordinate to
measurement (Principle IV) — a sophisticated-looking estimator would invite exactly the
misreading the provenance label exists to prevent.

### B3. Their result comes from co-design; we deliberately do not own the runtime

MCUNet's numbers come from searching the architecture and the inference engine together
(TinyNAS + TinyEngine). Caravan standardizes on TFLM and does not own the runtime (Principle II).

**Consequence:** we cannot recover performance by changing the engine, so the template search space
must be restricted up front to operators the target's kernel library actually accelerates.
Which leads directly to C2.

---

## C. From TFLM / CMSIS-NN — the runtime we standardize on

### C2 and C1 below are the most consequential findings in this note.

### C1. **Correction:** the tensor arena cannot be computed from the flatbuffer, and the runtime's own report under-counts

- `arena_used_bytes()` is a debugging aid, valid only *after* `AllocateTensors()` has run.
- It counts tensor memory but omits scratch buffers (tflite-micro issue #890).
- A more recent report (open at the time of writing) adds that the memory planner's own temporary
  working memory during `AllocateTensors()` is never counted, so the figure can be **smaller than
  the smallest arena that actually works** — worst for models with many tensors.
- The arena normally needs 16-byte alignment; unaligned, add 16 bytes.
- The documented sizing method is empirical: start small, read the runtime's error, iterate. The
  community heuristic (sum of consecutive feature maps plus margin) is explicitly not exact.
- `RecordingMicroInterpreter` with `PrintAllocations()` gives a head/tail/per-allocation
  breakdown.

The design document plans Stage 4 as "RAM/Flash-Schätzung aus dem Flatbuffer" and puts `ram_peak`
in the bench metrics. The first half is possible only as an estimate, in principle, not for want of
effort.

**Consequences:**

1. A RAM number from Stage 4 is `estimated` and can never be promoted to `measured` by improving
   the estimator. Principle IV's label is not bureaucracy here, it is the honest state of the art.
2. An `estimated` RAM figure must carry a stated safety margin, and the margin must be policy, not
   a guess per model.
3. The generated runner must report the arena from the runtime itself (recording interpreter), so
   Stage 5 and Stage 6 produce the real figure.
4. **Renode is promoted in importance.** It is not a convenience for contributors without
   hardware; it is the only mechanism that yields a trustworthy RAM figure for a board nobody has
   on the bench. Which makes C3 a problem.

### C2. **Correction:** CMSIS-NN acceleration is per-operator *and per-shape*, and the fallback is silent

- Whether an optimized kernel runs depends on the layer's settings and its input/output shapes,
  not only the operator type. Reported example: the ADD kernel calls the optimized CMSIS-NN int8
  routine only when broadcasting does not apply, and otherwise uses the generic implementation.
- Operators with no CMSIS-NN implementation fall back to the default (reference) kernel.
- In the `cmsis_nn` backend, float32 cases still dispatch to TFLM reference ops; TFLM rejects
  hybrid models (float activations, int8 weights) in `Prepare`.
- Selection happens at build time (`OPTIMIZED_KERNEL_DIR=cmsis_nn`), and which kernels are linked
  is what sets the flash footprint.
- No source documents any warning or diagnostic for the silent fallback. I found no published
  figure for op-resolver flash overhead either — to be measured, not assumed.

**Consequences:**

1. `accel: cmsis-nn` in a board description is a claim about the *build*, not about the model.
   Caravan must verify per-operator coverage for the actual converted graph and record, per
   operator, whether an accelerated kernel was linked.
2. The export must emit a minimal operator resolver containing exactly the operators the model
   uses. An all-operators resolver inflates flash, and flash is a gated budget.
3. Without that verification, a card's flash and latency numbers may silently describe reference
   kernels while claiming an accelerated target.

### C3. **Correction:** Renode has no S32K144

The supported-boards list contains `nxp-s32k388`, `nxp-s32k388evb` and `s32k118`. It does **not**
contain S32K144. Supported and relevant to us: `stm32h743` (plus `nucleo_h753zi` in family),
`arduino_nano_33_ble`, `nrf52840`. Not supported: ESP32 / Xtensa — the only Xtensa entry is
`xtensa-sample-controller`, which confirms the design document's suspicion.

The design document's example board file claims `renode: {platform: s32k144, status: experimental}`.
That platform does not exist.

**Consequences (answers open question 8):**

1. The emulated rung of the verification ladder exists for STM32H743 and the Nano 33 BLE, and does
   **not** exist for the two boards already owned (ESP32, D1 Mini) or for the S32K144.
2. Board descriptions must be able to say `renode: none` honestly, and the constitution should
   require that rather than tolerate an aspirational platform name.
3. If S32K-family emulation matters, the Renode-verifiable members are S32K388 (quad Cortex-M7 —
   a much larger part, different budget class) and S32K118 (Cortex-M0+ — smaller). The S32K144
   stays bench-only hardware.
4. Sequencing: the first *new* board to buy is Nucleo-H743 or Nano 33 BLE, not the S32K144 —
   because those are the ones where emulated verification and hardware measurement can be
   compared against each other, which is how the estimator in C1 gets calibrated at all.

### C4. int8 calibration is a real failure mode, and there is a standard tool for it

Calibration data determines activation ranges; a tiny or unrepresentative set yields poor scales,
and practitioner guidance warns specifically against synthetic random inputs. TensorFlow's
Quantization Debugger produces per-layer error metrics as CSV, supports full-integer (int8)
quantization only, expects the same dataset type as `representative_dataset`, and supports
selectively leaving high-error layers in float — in Google's own example, skipping ~10 of 111
layers improved accuracy but did not reach the float model.

**Consequence:** `dataset.representative_samples` is already in the schema; it should be required
when quantization is int8 rather than optional, with a documented minimum. When the accuracy gate
of Principle V fails, the pipeline should emit the per-layer error table instead of only a verdict
— that is the difference between a gate that blocks and a gate that helps. Selective float
fallback is a v0.2+ option, and it changes the operator set, so it interacts with C2.

---

## D. From the measurement side — MLPerf Tiny

Do not invent a benchmark protocol. MLPerf Tiny's: run inference for at least 10 seconds and at
least 10 iterations, take inferences-per-second, and report the median of five runs. Energy uses
the same procedure reported as µJ per inference and is optional; latency is always required. The
measurement window excludes pre- and post-processing. All benchmarks are single-stream. The EEMBC
EnergyRunner harness runs on a host, talks to the device under test over serial, and ships as
partially implemented C++ to be integrated on the device; energy measurement needs an external
board (e.g. ST LPM01A).

These figures are from the 2021–2022 papers; the current MLCommons run rules should be checked
before pinning exact parameters.

**Consequence:** Stage 6 adopts this shape — minimum duration and iteration count, median of five
runs, window excluding pre/post-processing — so our numbers are comparable to published TinyML
results instead of being internally consistent only. The design document's `latency_p50` and
`latency_p99` need a stated protocol behind them; a single-run p50 is not comparable to anything.

---

## E. Ecosystem risks worth recording

### E1. "TFLite" is being renamed to LiteRT

The rename was announced 2024-09; the Python package is `ai-edge-litert`; the microcontroller
runtime is documented as "LiteRT for Microcontrollers" while the upstream repository is still
`tensorflow/tflite-micro`, with Tier-1 CI on Arm Cortex-M (CMSIS-NN/Corstone), Cadence Xtensa,
RISC-V, Qualcomm Hexagon and x86. Reports that the old TF Lite packages are in maintenance mode
are secondhand; I could not confirm them against the TensorFlow README.

**Consequences:**

1. Do not bake vendor product names into enum values you must support forever. `formats: [tflite,
   model_cc]` will read as legacy, and a rename becomes a schema migration — precisely Ludwig's
   `training` → `trainer`. Either choose neutral values (`flatbuffer`, `c_array`) or accept that
   the migration registry of A1 is required from day one. Both is better.
2. Pin the converter toolchain by package name and version in the provenance record, because which
   package provides the converter is actively moving.

### E2. The vendor-risk argument against Edge Impulse got stronger

Qualcomm agreed to acquire Edge Impulse (announced March 2025 at Embedded World). It keeps its
branding as "a Qualcomm company", states that third-party hardware support remains, and the
platform is being optimized for Qualcomm Dragonwing processors.

**Consequence:** nothing suggests the product got worse, but ownership of the pipeline now sits
with a silicon vendor — the dependency Principle VIII refuses. This belongs in README positioning,
not in the constitution.

---

## F. Proposed constitution amendments

Drafted against v1.0.0, for the owner to accept, reword or reject. None of these widens the scope
of the framework; each one closes a trap that the sources above show is real.

1. **Principle IX (Stable Manifest Contract)** — replace rejection-only with: the framework stores
   the schema version in the manifest, upgrades an older manifest in memory through a registered
   migration per version, never rewrites the user's file, and records both the original and the
   effective version in the run report. Rejection stays for a version the framework does not know.
   (A1)
2. **Principle I (Declarative Manifest)** — add: there is no defaults or inheritance section;
   defaults resolve from the template and the board description only. (A3)
3. **Pipeline & Artifact Contract** — add: every run writes the fully resolved manifest, with all
   defaults expanded, next to its report. (A4)
4. **Principle IV (provenance labels)** — add: a memory figure derived from the model graph is
   `estimated` by definition and MUST carry the safety margin applied; a figure from the runtime's
   own allocation report counts as `emulated` or `measured` according to where it ran. (C1)
5. **Principle V (Budgets Are Gates)** — add: the analyze stage reports peak activation memory
   together with the layer that causes it, and a failed accuracy gate emits the per-layer
   quantization error table, not only a verdict. (B1, C4)
6. **Principle VII (Targets and Templates Are Data)** — add: a board description states its
   emulator support honestly, `none` included, and names the source of the claim; an accelerated
   kernel library named by a board is a build-level claim, so the export records per operator
   whether an accelerated kernel was linked, and emits a minimal operator resolver. (C2, C3)
7. **Target Hardware & the Verification Ladder** — add: hardware benchmarks follow an established
   public protocol (minimum duration and iterations, median of five runs, window excluding
   pre/post-processing) so results are comparable outside this project. (D)
8. **Technical Baseline** — name the runtime as TFLM / LiteRT for Microcontrollers, require the
   converter toolchain to be pinned by package and version in the provenance record, and prefer
   format identifiers that are not vendor product names. (E1)

Roadmap consequences, outside the constitution:

- Renode (planned v0.3) carries more weight than the roadmap assumes: it is the only source of a
  trustworthy RAM figure for a board that is not on the bench (C1). Consider pulling the
  Renode rung earlier for the one board where it works end to end.
- The next board to acquire should be Nucleo-H743 or Nano 33 BLE rather than the S32K144, because
  only those allow emulated and measured results to be compared — which is the only way the
  Stage 4 estimator ever gets calibrated (C1, C3).
- `representative_samples` becomes required for int8 with a documented minimum (C4).

---

## Sources

Ludwig:
- https://raw.githubusercontent.com/ludwig-ai/ludwig/master/ludwig/utils/backward_compatibility.py
- https://ludwig.ai/latest/configuration/defaults/
- https://ludwig.ai/latest/user_guide/command_line_interface/
- https://ludwig.ai/latest/user_guide/api/LudwigModel/
- https://github.com/ludwig-ai/ludwig/releases
- https://insights.linuxfoundation.org/project/ludwig

MCUNet / MCUNetV2:
- https://arxiv.org/pdf/2007.10319
- https://proceedings.neurips.cc/paper_files/paper/2021/file/1371bccec2447b5aa6d96d2a540fb401-Paper.pdf
- https://arxiv.org/html/2110.15352
- https://arxiv.org/pdf/2403.19076

TFLM / CMSIS-NN:
- https://github.com/tensorflow/tflite-micro/blob/main/tensorflow/lite/micro/docs/memory_management.md
- https://github.com/tensorflow/tflite-micro/issues/890
- https://github.com/tensorflow/tflite-micro/issues/2474
- https://github.com/tensorflow/tflite-micro/issues/3766
- https://github.com/tensorflow/tflite-micro/blob/main/README.md
- https://community.st.com/t5/edge-ai/how-to-use-tflite-micro-runtime-with-optimized-kernel-from-cmsis/td-p/230051
- https://developers.google.com/edge/litert/conversion/tensorflow/quantization/quantization_debugger

Renode:
- https://renode.readthedocs.io/en/latest/introduction/supported-boards.html
- https://renode.io/news/renode-support-for-nxp-s32k/

MLPerf Tiny:
- https://arxiv.org/pdf/2106.07597
- https://github.com/mlcommons/tiny/tree/master/benchmark

Ecosystem:
- https://developers.googleblog.com/tensorflow-lite-is-now-litert/
- https://developers.google.com/edge/litert
- https://www.hackster.io/news/qualcomm-to-acquire-edge-impulse-as-it-seeks-to-gain-ground-in-the-artificial-intelligence-of-things-2db3bb6f0d63
