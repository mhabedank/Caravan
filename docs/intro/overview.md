---
description: Caravan at a glance — one manifest followed through every stage, from your table to the C files your firmware compiles.
---

# Caravan at a glance

Caravan turns a table of sensor data and one YAML file into a model that runs on a
microcontroller. This page follows one {term}`manifest` through every {term}`stage` to the files
your firmware compiles, and says what Caravan is for and what it leaves out.

## The manifest

This is `examples/picket-mlp.yaml`, the worked example of the tutorial. It reads five columns of
synthetic CAN bus traffic and answers which of four kinds of traffic a window of 64 frames is.

```yaml
apiVersion: caravan/v0.2

model:
  name: picket-mlp
  version: 0.2.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1

input_features:                 # what goes in
  - name: can_id
    type: category
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}

output_features:                # what comes out: normal, dos, fuzzy or replay
  - name: label
    type: category
    accuracy_drop_max: 0.02

preprocessing:
  window_size: 64               # records per answer
  split: {type: stratify, column: label, probabilities: [0.7, 0.15, 0.15]}

dataset: ../tests/fixtures/datasets/synthetic
trainer: {epochs: 50, batch_size: 256, learning_rate: 0.001, early_stop: 5}
random_seed: 42

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [s32k144, stm32h743, esp32]
  representative_samples: 500
  test_windows: 16
```

Everything it does not say has a default, and {cmd}`caravan render` prints the manifest with every
default filled in. {cmd}`caravan validate` checks the file without reading any data.

## What it does

<figure>
<svg viewBox="0 0 580 150" role="img" aria-labelledby="flow-t" style="max-width:100%;height:auto">
  <title id="flow-t">Your table and your manifest go in; a trained model is shrunk to int8; a gate
  compares the shrunken model with the trained one and stops the run if it lost too much accuracy;
  what comes out is a model file, C sources and the interface contract your firmware binds to.</title>
  <g fill="var(--text,#062544)" font-family="JetBrains Mono, monospace" font-size="12">
    <rect x="2" y="34" width="92" height="62" fill="none" stroke="var(--border-strong,#7A847C)" stroke-width="1.5" rx="6"/>
    <text x="14" y="58">your table</text><text x="14" y="76">your YAML</text>
    <rect x="130" y="34" width="104" height="62" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)" stroke-width="1.5" rx="6"/>
    <text x="146" y="58">trained</text><text x="146" y="76">model</text>
    <rect x="270" y="34" width="104" height="62" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)" stroke-width="1.5" rx="6"/>
    <text x="286" y="58">int8</text><text x="286" y="76">model</text>
    <rect x="462" y="34" width="116" height="62" fill="none" stroke="var(--border-strong,#7A847C)" stroke-width="1.5" rx="6"/>
    <text x="476" y="52">.tflite</text><text x="476" y="70">C array</text><text x="476" y="88">contract</text>
    <path d="M98 65 H126 M238 65 H266 M378 65 H404 M452 65 H458" stroke="var(--text,#062544)" stroke-width="1.5" fill="none"/>
    <path d="M126 65 l-7 -4 v8 z M266 65 l-7 -4 v8 z M458 65 l-7 -4 v8 z" fill="var(--text,#062544)"/>
  </g>
  <g font-family="Archivo, sans-serif" font-size="11">
    <rect x="404" y="20" width="48" height="90" fill="none" stroke="var(--mark,#CA6A0A)" stroke-width="2.5"/>
    <text x="428" y="14" text-anchor="middle" fill="var(--mark,#CA6A0A)" font-weight="700">gate</text>
    <text x="428" y="131" text-anchor="middle" fill="var(--muted,#4B5450)">within budget?</text>
    <text x="48" y="118" text-anchor="middle" fill="var(--muted,#4B5450)">you write</text>
    <text x="182" y="118" text-anchor="middle" fill="var(--muted,#4B5450)">Caravan</text>
    <text x="322" y="118" text-anchor="middle" fill="var(--muted,#4B5450)">Caravan</text>
    <text x="520" y="118" text-anchor="middle" fill="var(--muted,#4B5450)">your firmware</text>
  </g>
</svg>
<figcaption>The gate is the part that decides. A model that lost more accuracy than your manifest
allows is not exported with a warning: the run fails, and says which layer cost the most.</figcaption>
</figure>

{cmd}`caravan export` runs five stages in order. Each one reads only the part of the manifest it
needs, and its result is cached, so a change that only a later stage reads never repeats an earlier
one.

**1. Data.** Reads the columns the {term}`features <feature>` name and nothing else, cuts them into
non-overlapping {term}`windows <window>` of {mf}`preprocessing.window_size` rows, and splits the
windows into training, validation and test parts. Each column learns its preprocessing from the
{term}`training part` only: `dlc` and the bytes learn a shift and a scale, `can_id` learns a
{term}`vocabulary`. See [Feature types](../topics/feature-types.md) and the
[input features](../ref/manifest/input-features.md).

**2. Build.** Builds the model from the {term}`template` — here an `mlp` with dense layers of 32 and
16 units — with each column's preprocessing inside it. Then the {term}`fit check` compares lower
bounds on its flash and RAM with every board in {mf}`export.targets`, before any training. See
[Templates](../topics/templates.md) and [the model section](../ref/manifest/model.md).

**3. Train.** Trains the model on the training part and measures it on the {term}`test part`,
into `metrics.json`. See [the trainer section](../ref/manifest/trainer.md).

**4. Quantize.** Converts the trained model to {term}`int8`, calibrated on
{term}`representative samples <representative samples>` from the training part, and measures it
again on the same test part. The {term}`quantization gate` compares the two: this manifest allows
two points of accuracy, set by
{mf}`accuracy_drop_max <output_features[].accuracy_drop_max>`. Lose more and the run stops here.
See [Budgets and gates](../topics/budgets-and-gates.md).

**5. Export.** Writes the int8 model, the same model as a {term}`C array`, the operators it needs,
and the {term}`interface contract`: every input by name, and what the output means. See
[What a run leaves](../topics/what-a-run-leaves.md) and [the export section](../ref/manifest/export.md).

Your firmware passes raw sensor values. Each column's preprocessing — scaling a number, looking up
a category — is built into the model, so there is no preprocessing code to port and nothing for
your board and your computer to disagree about. [The pipeline](../topics/pipeline.md) explains the
stages in full.

## What Caravan is for

Models small enough to run on a microcontroller, built from tabular data, deployed through the
board's own open toolchain. It is the build tool for the embedded models of the
[Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo), and it works outside it.

It is narrow on purpose, and that is what keeps it short:

- It does not run your model. The board does that, with {term}`TFLM`, TensorFlow Lite for
  Microcontrollers.
- It does not search for an architecture. You pick a template and its parameters.
- It does not describe your hardware. Boards are data files, and you can add one.
- It asks only what a stage uses. There is no compliance block and no description field.

Cloud, desktop and language models are out of its scope.

[What is verified today](../ref/compatibility.md) states how far each part has been taken, and
[the roadmap](../roadmap.md) says what is planned and what was decided against.

## Next

[Install Caravan](install.md), then start with [part 1 of the tutorial](tutorial01.md).
