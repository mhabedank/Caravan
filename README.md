# Caravan

**A CSV goes in. A model your microcontroller runs comes out.**

You describe your data once, in one YAML file: which columns the model reads, which column it
answers, and which boards it has to fit. Caravan trains the model, shrinks it to 8-bit integers,
stops if shrinking cost more accuracy than you allowed, and writes the C files your firmware
compiles.

Each column's preprocessing is built into the model, so your firmware passes raw sensor values and
there is no preprocessing code to port. The manifest asks only for what a stage uses: no compliance
block, no description fields, nothing the data already says.

Caravan is the build tool for the embedded models of the
[Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo) and lives in its own
repository under Apache-2.0, so that models built with it stay portable and the framework stays
usable outside the zoo.

**Scope, deliberately narrow:** models for microcontrollers and comparable constrained hardware.
Cloud, desktop and LLM models are explicitly out of scope, and so is becoming an inference
runtime, a platform description language, a cycle-accurate simulator or a research-grade
architecture search. See `.specify/memory/constitution.md`.

## Status

**0.1.0rc3, the third release candidate.** Every stage from manifest to C array exists: `validate`,
`render`, `build`, `train`, `quantize` and `export`, with `templates` and `boards` to list what is
registered. Two templates, `mlp` and `conv1d`, and three boards, `s32k144`, `stm32h743` and `esp32`.
The manifest names its columns as Ludwig does (`caravan/v0.2`). rc1 read the previous form,
`caravan/v0.1`. `docs/releases/0.1.0.md` says what is in 0.1.0 and what is not.

rc3 adds the documentation site and test windows in the export. Part 3 of the tutorial runs an
exported model on a generic ESP32 and compares its answers with the host's. The first recorded board
run is still to come.

Not on the package index. Each version is installed from its GitHub release.

## Documentation

**<https://mhabedank.github.io/Caravan/>**, built from `docs/`. It opens with what Caravan does and
offers one way in: **the tutorial**, four parts from nothing to a model answering on a board. Its
[contents page](https://mhabedank.github.io/Caravan/contents.html) leads to the rest: the topic
guides a reader needs to choose (what `mlp` means and when to use it, what each feature type does,
how the gates work), a CLI and manifest reference with every field, a glossary, what is verified
today, and the roadmap.

## Try it

[Part 1 of the tutorial](https://mhabedank.github.io/Caravan/intro/tutorial01.html) goes from an
empty directory to an exported int8 model. With a
checkout, the example manifest validates on any supported Python:

```bash
# step: readme
caravan validate examples/picket-mlp.yaml
caravan render examples/picket-mlp.yaml --stdout
```

## Install

From the release, in a virtual environment:

```bash
pip install "caravan-ml @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc3/caravan_ml-0.1.0rc3-py3-none-any.whl"
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc3/caravan_ml-0.1.0rc3-py3-none-any.whl"
```

The first line is the core: `validate` and `render`, on Python 3.13 to 3.15. The second adds
training and converting (Python 3.13) and reading exported models (3.13 and 3.14). To build from
the tagged source instead:
`pip install "caravan-ml[train,verify] @ git+https://github.com/mhabedank/Caravan@v0.1.0rc3"`.

The default installation has two runtime dependencies, weighs about 9 MiB and pulls no
machine-learning framework, because checking and resolving a manifest does not need one.

The two extras are very different sizes, and that is the point:

| Extra | Size | Python | For |
|---|---|---|---|
| `verify` | **114 MiB**, 7 packages | 3.13, 3.14 | reading and running an exported model |
| `train` | 1,971 MiB, 41 packages | **3.13 only** | building, training, converting |

Reading an exported model needs no training framework, and the stages after quantization do
nothing else — so they are not dragged along by the conversion's weight. Neither extra reaches
3.15 yet: TensorFlow publishes no wheel above 3.13 and the model runtime none above 3.14, both
checked rather than assumed. `caravan validate` and `caravan render` run on all three.

**The extra needs Python 3.13.** TensorFlow publishes no stable wheel above 3.13, and Python
packaging has no per-extra version window, so the published floor is 3.13 until a stable
TensorFlow ships for the current Python. All of 3.13, 3.14 and 3.15 are supported and tested; on
3.14 and 3.15 the extra installs Caravan's training code and no framework, and `build` and `train`
then say so rather than failing in the resolver. `docs/ref/budgets.md` carries the reasoning and the
condition that closes the window.

## Use

```bash
caravan validate manifest.yaml     # is this manifest sound?
caravan render   manifest.yaml     # what will the pipeline actually use?
caravan build    manifest.yaml     # what model does it describe, and does it fit the boards?
caravan train    manifest.yaml     # train it on the dataset it names
caravan quantize manifest.yaml     # convert it to int8, and judge what that cost
caravan export   manifest.yaml     # write the model, its C array, its resolver and a runner
caravan templates                  # which templates are registered?
caravan boards                     # which target boards are known?
```

Every command exits:
- 0 when it did the work;
- 1 when a rule says no;
- 2 on a usage error;
- 3 on a defect in the tool itself;
- 4 when the environment is missing something that installs separately.

Every rejection names the offending field, what was wrong with it and what is accepted there.
`docs/ref/cli.md` and `docs/ref/manifest/` have the details.

Caravan carries no compliance layer. The rights to the data, and the use of a model trained on it,
are the author's. Caravan neither asks about them nor claims to have checked them.

## Where things are

| | |
|---|---|
| `.specify/memory/constitution.md` | the rules: twelve principles, the scope boundary, the gates |
| `specs/<nnn>-<name>/` | one feature's spec, plan, research, data model, contracts and tasks |
| `docs/` | the documentation site's pages; `docs/conf.py` builds them with Sphinx |
| `docs/roadmap.md` | what is planned per version, and the non-goals, each with its reason |
| `examples/` | the example manifest, and `esp32/`, the firmware part 3 of the tutorial builds |
| `docs/design/` | the design document Caravan was started from, frozen as a dated record |
| `docs/research/` | sourced research notes that decisions cite |
| `docs/ref/budgets.md` | the dependency, install and Python-version budgets, with measurements |
| `src/caravan/targets/boards/` | the board descriptions, one data file per board |

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

The suite splits three ways by what a test needs:

```bash
uv run --extra verify pytest          # everything but tests/train, on any supported Python

uv venv --python 3.13 .venv313        # conversion needs 3.13
uv pip install --python .venv313 -e ".[train,verify]" pytest
.venv313/bin/python -m pytest tests   # the whole suite
```

`tests/verify` needs the model runtime and runs on 3.13 and 3.14; `tests/train` needs the training
framework and runs on 3.13 only.

One footgun worth knowing: an editable install records the project's **extras** at install time,
so after adding or renaming one, re-run the `uv pip install -e` line. The layering tests read that
metadata, and a stale environment makes them report an extra that the file already has.
Continuous integration always installs fresh and never sees it. A test that needs a framework lives in one of those two
directories and nowhere else — putting one elsewhere turns two continuous-integration jobs red,
which is how the rule was learned.

The site builds with `uv run --group docs sphinx-build -W -b html docs _site`; every warning is an
error. See `specs/009-docs-and-board-guide/quickstart.md` for the scenarios that validate the
current feature, and
`CONTRIBUTING.md` for the dependency gate a new dependency has to pass.

## Licence

Apache-2.0. See `LICENSE`.
