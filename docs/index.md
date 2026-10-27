# Caravan

**A declarative pipeline for small machine learning models that run on microcontrollers.**

This site describes Caravan {{ release }}.

You write one YAML manifest per model. It names:
- the columns of your data the model reads, each with a type, as in Ludwig;
- the column it answers;
- the boards it must fit.

Caravan does the rest:
- checks the model against the boards before training;
- trains it and quantizes it to int8;
- refuses a model that quantization made worse than you allowed;
- writes the C files a firmware compiles, with each input's preprocessing already inside the model.

Your firmware passes raw sensor values.

```text
manifest → data (split, fit) → build (fit check) → train → quantize (int8 gate) → export
```

## What it is not

Caravan is deliberately narrow:
- **Scope:** only models for microcontrollers and comparable constrained hardware. Cloud, desktop
  and language models are out of scope.
- **What it is not:** an inference runtime (the board runs TensorFlow Lite Micro), a platform
  description language, a cycle-accurate simulator, or an architecture search.
- **The manifest** asks only for what a stage uses: no compliance block and no description fields.

## Install

Caravan is installed from its GitHub release, not from the package index. In a virtual
environment:

```bash
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc3/caravan_ml-0.1.0rc3-py3-none-any.whl"
```

**Python versions:**
- Training and conversion need Python 3.13. The training framework publishes nothing newer yet.
- Without the extras, `validate` and `render` work on Python 3.13 to 3.15.

[Compatibility](compatibility.md) has the details.

## Where to go

- **[Try it](try-it.md):** from an empty directory to an exported model, in one sequence of
  commands.
- **[On the board: LILYGO LoRa32](guides/lora32.md):** the exported model on a microcontroller,
  its answers compared with your computer's.
- **[Your own project](guides/own-project.md):** from a CSV of your own to a manifest.
- **[CLI reference](reference/cli.md):** every command and option.
- **[Manifest reference](reference/manifest.md):** every field, its default, and the rules that
  check it.
- **[Compatibility](compatibility.md):** what works today, and how far each part is verified.
- **[Roadmap](roadmap.md):** what is planned, and what was decided against.

```{toctree}
:caption: Start
:maxdepth: 1
:hidden:

try-it
guides/own-project
guides/lora32
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
