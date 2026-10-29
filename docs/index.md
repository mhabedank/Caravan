---
layout: landing
eyebrow: Embedded machine learning
tagline: Turn sensor data into models that run on the device.
lead: >-
  Describe the model in one YAML file. Caravan trains it, shrinks it to fit the board, checks it
  still answers right, and writes the code your firmware compiles.
description: Caravan turns sensor data and one YAML file into machine-learning models that run on microcontrollers, shrunk to fit the board and checked before they ship.
---

# Caravan

{.band .band-example}
## You write one file. Caravan builds the model.

```yaml
model:
  name: picket-mlp
  template: mlp
  params: {hidden: [32, 16]}

preprocessing:
  window_size: 64      # records per answer

input_features:       # what goes in
  - {name: can_id, type: category}
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}

output_features:      # what comes out
  - name: label       # normal, dos, fuzzy, replay
    type: category
    accuracy_drop_max: 0.02

export:
  targets: [esp32, stm32h743]
```

<figure>
<svg viewBox="0 0 264 332" role="img" aria-labelledby="net-t">
  <title id="net-t">The model this file builds: five inputs over a window of 64 records, one-hot encoding
  and standardising built in, dense layers of 32 and 16 units, and four outputs: normal, dos, fuzzy
  and replay.</title>
  <g stroke="var(--border-strong,#7A847C)" stroke-width="1.4"><line x1="132" y1="46" x2="132" y2="62"/><line x1="132" y1="102" x2="132" y2="118"/><line x1="132" y1="158" x2="132" y2="174"/><line x1="132" y1="214" x2="132" y2="230"/><line x1="132" y1="270" x2="132" y2="286"/></g>
  <g><rect x="12" y="6" width="240" height="40" rx="6" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M18 6h228a6 6 0 0 1 6 6v12h-240v-12a6 6 0 0 1 6-6z" fill="var(--muted,#4B5450)"/><text x="21" y="19" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Input</text><text x="21" y="39" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">5 features · 64 each</text><rect x="12" y="62" width="240" height="40" rx="6" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M18 62h228a6 6 0 0 1 6 6v12h-240v-12a6 6 0 0 1 6-6z" fill="var(--gain-ink,#1C5E3F)"/><text x="21" y="75" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Preprocessing</text><text x="21" y="95" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">one-hot · standardise</text><rect x="12" y="118" width="240" height="40" rx="6" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M18 118h228a6 6 0 0 1 6 6v12h-240v-12a6 6 0 0 1 6-6z" fill="var(--text,#062544)"/><text x="21" y="131" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Dense</text><text x="21" y="151" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">32 · relu</text><rect x="12" y="174" width="240" height="40" rx="6" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M18 174h228a6 6 0 0 1 6 6v12h-240v-12a6 6 0 0 1 6-6z" fill="var(--text,#062544)"/><text x="21" y="187" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Dense</text><text x="21" y="207" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">16 · relu</text><rect x="12" y="230" width="240" height="40" rx="6" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M18 230h228a6 6 0 0 1 6 6v12h-240v-12a6 6 0 0 1 6-6z" fill="var(--text,#062544)"/><text x="21" y="243" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Dense</text><text x="21" y="263" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">4 · softmax</text><rect x="12" y="286" width="240" height="40" rx="6" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M18 286h228a6 6 0 0 1 6 6v12h-240v-12a6 6 0 0 1 6-6z" fill="var(--muted,#4B5450)"/><text x="21" y="299" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Output</text><text x="21" y="319" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">normal · dos · fuzzy · replay</text></g>
</svg>
<figcaption>The model this file builds. Scaling and encoding are inside it, so the board gets raw
values.</figcaption>
</figure>

The whole file, every field explained, is in the [manifest reference](reference/manifest.md); the
commands that run it are in the [CLI reference](reference/cli.md).

{.band .band-3 .band-alt}
## Why Caravan

### One file

Describe the model in one YAML file. No training code, no quantization script, no conversion step.

### Any microcontroller

One manifest exports for ESP32, STM32 and NXP S32K. A board is a data file, so adding yours is a
file, not a fork.

### Fits, or fails

Every model is shrunk to 8-bit integers and checked. If it loses more accuracy than you allowed, or
does not fit the board, nothing is exported.

### Raw values in

Scaling and lookups are built into the model. Your firmware passes raw sensor readings; there is no
preprocessing code to port.

{.band .band-tiles}
## The route

Four steps from the worked example to firmware for your board.

{.leg .leg-1}
### [Your first model](route/1-first-model.md)

**5 minutes.** A classifier that spots attacks on a CAN bus, as C code ready to compile.

{.leg .leg-2}
### [Your own data](route/2-your-columns.md)

**10 minutes.** A model trained on your own sensor data, with its accuracy on your data.

{.leg .leg-3}
### [Onto a board](route/3-onto-a-board.md)

**15 minutes.** Firmware for an ESP32 under €10, with your model inside, built and ready to flash.

{.leg .leg-4}
### [When it does not fit](route/4-when-it-does-not-fit.md)

**Then.** Which layer costs too much, and what to change so it fits.

{.band .band-figure}
## What it actually does

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
<figcaption>The gate is the part that matters. A model that lost more accuracy than your manifest
allows does not get exported with a warning — the run fails, and tells you which layer cost the
most.</figcaption>
</figure>

Your firmware passes raw sensor values. Each column's preprocessing — scaling a number, looking up
a category — is built into the model itself, so there is no preprocessing code to port and no
chance of your board and your computer disagreeing about it.

{.band .band-cols .band-alt}
## What you bring

- **A table of your own** — a `.csv`, `.tsv` or `.txt` file with a header row. Sensor readings, log
  lines, counters; whatever you already have.
- **Python 3.13.** Training needs exactly this version, because the training framework publishes
  nothing newer yet. Checking and previewing a manifest work on 3.13, 3.14 and 3.15.
- **About 2 GB of download, once.** The training dependency is large — roughly 2 GB installed
  against 7 MB for Caravan itself. It is the longest wait in the half hour, and leg 1 says so again
  before the install command so you can start it and read on.
- **Linux or macOS.** The route's commands are written for these. On Windows they work under WSL;
  nothing here has been tested in PowerShell.
- **A microcontroller — but only from leg 3.** Legs 1 and 2 need nothing but your computer.

You do not bring a model architecture, a training loop, a quantization script or a conversion step.
Those are what Caravan is.

{.band .band-cols}
## What Caravan is for

Models small enough to run on a microcontroller, built from tabular data, deployed through the
board's own open toolchain. It is the build tool for the embedded models of the
[Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo), and it works just as well
outside it.

Within that it is deliberately narrow, which is what lets it be short:

- It does not run your model. The board does that, with TensorFlow Lite for Microcontrollers.
- It does not search for an architecture. You pick a template and its parameters.
- It does not describe your hardware. Boards are data files, and you can add one.
- It asks only what a stage uses. There is no compliance block and no description field.

Cloud, desktop and language models are someone else's problem.

[What is verified today](compatibility.md) is the honest account of how far each part has been
taken, and [the roadmap](roadmap.md) says what is planned and what was decided against.

```{toctree}
:caption: Start
:maxdepth: 1
:hidden:

route/index
```

```{toctree}
:caption: Concepts
:maxdepth: 1
:hidden:

concepts/templates
concepts/feature-types
concepts/budgets-and-gates
concepts/what-a-run-leaves
```

```{toctree}
:caption: Reference
:maxdepth: 1
:hidden:

reference/cli
reference/manifest
reference/rules
budgets
manifest-changes
```

```{toctree}
:caption: Project
:maxdepth: 1
:hidden:

compatibility
roadmap
releases/0.1.0
board-runs/index
```
