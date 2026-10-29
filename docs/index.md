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
  <g><rect x="12" y="6" width="240" height="40" rx="2" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M14 6h236a2 2 0 0 1 2 2v16h-240v-16a2 2 0 0 1 2-2z" fill="var(--muted,#4B5450)"/><text x="21" y="19" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Input</text><text x="21" y="39" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">5 features · 64 each</text><rect x="12" y="62" width="240" height="40" rx="2" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M14 62h236a2 2 0 0 1 2 2v16h-240v-16a2 2 0 0 1 2-2z" fill="var(--gain-ink,#1C5E3F)"/><text x="21" y="75" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Preprocessing</text><text x="21" y="95" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">one-hot · standardise</text><rect x="12" y="118" width="240" height="40" rx="2" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M14 118h236a2 2 0 0 1 2 2v16h-240v-16a2 2 0 0 1 2-2z" fill="var(--text,#062544)"/><text x="21" y="131" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Dense</text><text x="21" y="151" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">32 · relu</text><rect x="12" y="174" width="240" height="40" rx="2" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M14 174h236a2 2 0 0 1 2 2v16h-240v-16a2 2 0 0 1 2-2z" fill="var(--text,#062544)"/><text x="21" y="187" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Dense</text><text x="21" y="207" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">16 · relu</text><rect x="12" y="230" width="240" height="40" rx="2" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M14 230h236a2 2 0 0 1 2 2v16h-240v-16a2 2 0 0 1 2-2z" fill="var(--text,#062544)"/><text x="21" y="243" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Dense</text><text x="21" y="263" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">4 · softmax</text><rect x="12" y="286" width="240" height="40" rx="2" fill="var(--surface-2,#E4E8E5)" stroke="var(--border-strong,#7A847C)"/><path d="M14 286h236a2 2 0 0 1 2 2v16h-240v-16a2 2 0 0 1 2-2z" fill="var(--muted,#4B5450)"/><text x="21" y="299" font-family="Archivo, sans-serif" font-size="11" font-weight="700" fill="var(--bg,#EFF2F0)">Output</text><text x="21" y="319" font-family="JetBrains Mono, monospace" font-size="11.5" fill="var(--text,#062544)">normal · dos · fuzzy · replay</text></g>
</svg>
<figcaption>The model this file builds. Scaling and encoding are inside it, so the board gets raw
values.</figcaption>
</figure>

The whole file, every field explained, is in the [manifest reference](ref/manifest/index.md); the
commands that run it are in the [CLI reference](ref/cli.md).

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
## The tutorial

Four parts from the worked example to firmware for your board.

{.part .part-1}
### [Your first model](intro/tutorial01.md)

**5 minutes.** A classifier that spots attacks on a CAN bus, as C code ready to compile.

{.part .part-2}
### [Your own data](intro/tutorial02.md)

**10 minutes.** A model trained on your own sensor data, with its accuracy on your data.

{.part .part-3}
### [Onto a board](intro/tutorial03.md)

**15 minutes.** Firmware for an ESP32 under €10, with your model inside, built and ready to flash.

{.part .part-4}
### [When it does not fit](intro/tutorial04.md)

Which layer costs too much, and what to change so it fits.

```{toctree}
:hidden:

contents
```
