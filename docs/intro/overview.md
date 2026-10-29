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
<svg viewBox="0 0 720 252" role="img" aria-labelledby="flow-t flow-d" style="max-width:100%;height:auto">
  <title id="flow-t">Caravan's five stages and its two gates</title>
  <desc id="flow-d">Five stages run left to right: data, build, train, quantize and export, and the export ends in the firmware. The fit check stands between build and train, the quantization gate between quantize and export. Either can send the run down to a shared end: the run stops and nothing is exported. Under each stage, what it leaves behind: schema.json, fit.json, metrics.json, the int8 .tflite and the C array. A bracket marks that caravan export runs all five.</desc>
  <path d="M0,50 V42 H628 V50" fill="none" stroke="var(--border-strong,#7A847C)" stroke-width="1"/>
  <text x="314" y="33" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)" text-anchor="middle">caravan export runs all five and reuses what is cached</text>
  <path d="M233,136 L233,218 Q233,226 241,226 L567.5,226" fill="none" stroke="var(--border-strong,#7A847C)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="574,226 567,222 567,230" fill="var(--border-strong,#7A847C)"/>
  <path d="M505,136 L505,218 Q505,226 513,226 L521,226" fill="none" stroke="var(--border-strong,#7A847C)" stroke-width="1.5" stroke-linejoin="round"/>
  <text x="0" y="84" font-family="JetBrains Mono, monospace" font-size="10.5" font-weight="600" fill="var(--muted,#4B5450)">01</text>
  <rect x="0" y="94" width="84" height="36" rx="2" fill="var(--accent,#062544)"/>
  <text x="42" y="116.5" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--on-accent,#EFF2F0)" text-anchor="middle">data</text>
  <text x="0" y="150" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)">schema.json</text>
  <text x="110" y="84" font-family="JetBrains Mono, monospace" font-size="10.5" font-weight="600" fill="var(--muted,#4B5450)">02</text>
  <rect x="110" y="94" width="84" height="36" rx="2" fill="var(--accent,#062544)"/>
  <text x="152" y="116.5" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--on-accent,#EFF2F0)" text-anchor="middle">build</text>
  <text x="110" y="150" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)">fit.json</text>
  <text x="272" y="84" font-family="JetBrains Mono, monospace" font-size="10.5" font-weight="600" fill="var(--muted,#4B5450)">03</text>
  <rect x="272" y="94" width="84" height="36" rx="2" fill="var(--accent,#062544)"/>
  <text x="314" y="116.5" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--on-accent,#EFF2F0)" text-anchor="middle">train</text>
  <text x="272" y="150" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)">metrics.json</text>
  <text x="382" y="84" font-family="JetBrains Mono, monospace" font-size="10.5" font-weight="600" fill="var(--muted,#4B5450)">04</text>
  <rect x="382" y="94" width="84" height="36" rx="2" fill="var(--accent,#062544)"/>
  <text x="424" y="116.5" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--on-accent,#EFF2F0)" text-anchor="middle">quantize</text>
  <text x="382" y="150" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)">int8 .tflite</text>
  <text x="544" y="84" font-family="JetBrains Mono, monospace" font-size="10.5" font-weight="600" fill="var(--muted,#4B5450)">05</text>
  <rect x="544" y="94" width="84" height="36" rx="2" fill="var(--accent,#062544)"/>
  <text x="586" y="116.5" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--on-accent,#EFF2F0)" text-anchor="middle">export</text>
  <text x="544" y="150" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)">C array</text>
  <rect x="654" y="94" width="66" height="36" rx="2" fill="var(--surface,#FCFCFB)" stroke="var(--border-strong,#7A847C)" stroke-width="1"/>
  <text x="687" y="116.5" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--text,#062544)" text-anchor="middle">C files</text>
  <text x="654" y="150" font-family="JetBrains Mono, monospace" font-size="11" font-weight="400" fill="var(--muted,#4B5450)">firmware</text>
  <path d="M88,112 L100.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="107,112 100,108 100,116" fill="var(--text,#062544)"/>
  <path d="M198,112 L220.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="227,112 220,108 220,116" fill="var(--text,#062544)"/>
  <path d="M240,112 L262.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="269,112 262,108 262,116" fill="var(--text,#062544)"/>
  <path d="M360,112 L372.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="379,112 372,108 372,116" fill="var(--text,#062544)"/>
  <path d="M470,112 L492.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="499,112 492,108 492,116" fill="var(--text,#062544)"/>
  <path d="M512,112 L534.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="541,112 534,108 534,116" fill="var(--text,#062544)"/>
  <path d="M632,112 L644.5,112" fill="none" stroke="var(--text,#062544)" stroke-width="1.5" stroke-linejoin="round"/><polygon points="651,112 644,108 644,116" fill="var(--text,#062544)"/>
  <rect x="230" y="88" width="6" height="48" rx="0" fill="var(--accent-use,#CA6A0A)"/>
  <text x="233" y="70" font-family="Archivo, sans-serif" font-size="10.5" font-weight="650" fill="var(--muted,#4B5450)" text-anchor="middle" letter-spacing="1.05">FIT CHECK · F-1</text>
  <rect x="502" y="88" width="6" height="48" rx="0" fill="var(--accent-use,#CA6A0A)"/>
  <text x="505" y="70" font-family="Archivo, sans-serif" font-size="10.5" font-weight="650" fill="var(--muted,#4B5450)" text-anchor="middle" letter-spacing="1.05">QUANTIZATION GATE · Q-4</text>
  <text x="243" y="184" font-family="Archivo, sans-serif" font-size="13" font-weight="500" fill="var(--text,#062544)">too big for a board</text>
  <text x="243" y="199" font-family="Archivo, sans-serif" font-size="12" font-weight="400" fill="var(--muted,#4B5450)">refused before training</text>
  <text x="515" y="184" font-family="Archivo, sans-serif" font-size="13" font-weight="500" fill="var(--text,#062544)">int8 cost too much</text>
  <text x="515" y="199" font-family="Archivo, sans-serif" font-size="12" font-weight="400" fill="var(--muted,#4B5450)">per-layer error table</text>
  <rect x="574" y="204" width="146" height="44" rx="2" fill="var(--bg,#EFF2F0)" stroke="var(--border-strong,#7A847C)" stroke-width="1" stroke-dasharray="3 2.5"/>
  <text x="588" y="223" font-family="Archivo, sans-serif" font-size="13" font-weight="600" fill="var(--text,#062544)">the run stops</text>
  <text x="588" y="238" font-family="Archivo, sans-serif" font-size="12" font-weight="400" fill="var(--muted,#4B5450)">nothing is exported</text>
</svg>
<figcaption>Two gates, and neither can be switched off. The fit check refuses a model that cannot fit a board before any training starts; the quantization gate stops a model that lost more accuracy than your manifest allows, and says which layer cost the most.</figcaption>
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
