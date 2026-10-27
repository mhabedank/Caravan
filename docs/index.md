---
layout: landing
description: Caravan turns a CSV and one YAML file into a model your microcontroller runs, and refuses it if shrinking it cost more accuracy than you allowed.
---

::::{container} hero
:::{container} wrap
# A CSV goes in. A model your microcontroller runs comes out.

```{container} lead
You describe your data once, in one YAML file: which columns the model reads, which column it
answers, and which boards it has to fit. Caravan trains the model, shrinks it to 8-bit integers,
**stops if shrinking cost more accuracy than you allowed**, and writes the C files your firmware
compiles.
```

```{container} row
[Start the route](route/index.md){.btn} <span class="cap">First model in 15 minutes. On a board in 30.</span>
```
:::
::::

:::::{container} sec
::::{container} wrap
:::{container} prose
## What you bring

- **A table of your own** — a `.csv`, `.tsv` or `.txt` file with a header row. Sensor readings, log
  lines, counters; whatever you already have.
- **Python 3.13.** Training needs exactly this version, because the training framework publishes
  nothing newer yet. Checking and previewing a manifest work on 3.13, 3.14 and 3.15.
- **About 2 GB of download, once.** The training dependency is large — roughly 2 GB installed
  against 7 MB for Caravan itself. Leg 1 says so again before the install command, because it is
  the longest wait in the half hour and worth starting before you read on.
- **Linux or macOS.** The route's commands are written for these. On Windows they work under WSL;
  nothing here has been tested in PowerShell.
- **A microcontroller — but only from leg 3.** Legs 1 and 2 need nothing but your computer. Leg 3
  is written for a generic ESP32 development board, which costs under €10.

You do not bring a model architecture, a training loop, a quantization script or a conversion step.
Those are what Caravan is.
:::
::::
:::::

:::::{container} sec
::::{container} wrap
:::{container} prose
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
    <text x="428" y="128" text-anchor="middle" fill="var(--muted,#4B5450)">fits?</text>
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
:::
::::
:::::

:::::{container} sec
::::{container} wrap
:::{container} prose
## The route

Four legs. Each one ends with something you can point at.

| Leg | You end with | About |
|---|---|---|
| [1. Your first model](route/1-first-model.md) | An int8 model and its C array, on disk | 5 min |
| [2. Your own columns](route/2-your-columns.md) | The same, reading your data, with your accuracy figure | 15 min |
| [3. Onto a board](route/3-onto-a-board.md) | A microcontroller answering, checked against your computer | 30 min |
| [4. When it does not fit](route/4-when-it-does-not-fit.md) | A failed gate read, and a budget you chose | after |

The minutes are cumulative from the start of leg 1, with the install already done.
:::
::::
:::::

:::::{container} sec
::::{container} wrap
:::{container} prose
## What Caravan is for

Models small enough to run on a microcontroller, built from tabular data, deployed through the
board's own open toolchain. It is the build tool for the embedded models of the
[Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo), and it works just as well
outside it.

Within that, it is deliberately narrow, which is what lets it be short:

- It does not run your model. The board does that, with TensorFlow Lite for Microcontrollers.
- It does not search for an architecture. You pick a template and its parameters.
- It does not describe your hardware. Boards are data files, and you can add one.
- It asks only what a stage uses. There is no compliance block and no description field.

Cloud, desktop and language models are someone else's problem.

[What is verified today](compatibility.md) is the honest account of how far each part has been
taken, and [the roadmap](roadmap.md) says what is planned and what was decided against.
:::
::::
:::::

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
