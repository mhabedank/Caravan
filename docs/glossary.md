---
description: The words Caravan's documentation uses, each defined in one or two sentences.
---

# Glossary

```{glossary}
board
  A microcontroller Caravan builds for, described in a data file that states its core, memory,
  accelerated kernels and toolchain, with a source for every value. See [Boards](ref/boards.md).

budget
  The most a model may lose when it is shrunk to {term}`int8`, set per output in the manifest:
  {mf}`output_features[].accuracy_drop_max` or {mf}`output_features[].mae_increase_max`. See
  [Budgets and gates](topics/budgets-and-gates.md).

C array
  The int8 model written as bytes in C source, `model/model_data.cc` with its header, which your
  firmware compiles in. See [What a run leaves](topics/what-a-run-leaves.md).

CNN
  Convolutional neural network: a model that slides small kernels of weights along time to find a
  pattern wherever it occurs. Caravan's `conv1d` template is one. See [Templates](topics/templates.md).

derived
  A value only the data can say — a vocabulary, the order of the labels, an embedding size. The
  data stage learns it from the {term}`training part` and writes it into the run's resolved manifest.

feature
  One column of your table that the model reads (an input feature) or answers (an output feature),
  declared in the manifest with a {term}`feature type`. See [Feature types](topics/feature-types.md).

feature type
  What kind of thing a column is: `number`, `category` or `binary`. The type decides what is learned
  from the column and what your firmware passes for it. See [Feature types](topics/feature-types.md).

fit check
  The check after the model is built and before training that compares lower bounds on its flash
  and RAM with each {term}`target`. A model that fails it cannot fit; its figures are `estimated`.
  See [Budgets and gates](topics/budgets-and-gates.md).

gate
  A check that stops a run instead of warning. Caravan has two, the {term}`fit check` and the
  {term}`quantization gate`, and no option turns either off. See
  [Budgets and gates](topics/budgets-and-gates.md).

int8
  8-bit integers, the format the exported model stores its weights in and computes with. An int8
  model is a quarter of the size of the same model in 32-bit floats. See
  [Budgets and gates](topics/budgets-and-gates.md).

interface contract
  `model/interface.json`: every input by name with its position, shape, element type, quantization
  scale and zero point, and what the output means. Firmware binds to it by name. See
  [What a run leaves](topics/what-a-run-leaves.md).

MAE
  Mean absolute error: the average distance between the model's answer and the truth, in the
  column's own unit. It is the measure behind the budget of a `number` output. See
  [Budgets and gates](topics/budgets-and-gates.md).

manifest
  The one YAML file that describes a model: where the data is, which columns go in and come out,
  the template, the budgets and the target boards. See [the manifest reference](ref/manifest/index.md).

MLP
  Multilayer perceptron: a stack of layers in which every value of one layer is connected to every
  value of the next. Caravan's `mlp` template is one. See [Templates](topics/templates.md).

normalization
  The shift and scale a `number` column learns from the {term}`training part`, so that the model
  sees values around zero. It is built into the model. See [Feature types](topics/feature-types.md).

provenance label
  One of `estimated`, `emulated` or `measured`, carried by every figure about hardware to say how
  it was obtained. See [What a run leaves](topics/what-a-run-leaves.md).

quantization
  Converting the trained model from 32-bit floats to 8-bit integers, after training. It is what
  makes a model fit a microcontroller. See [Budgets and gates](topics/budgets-and-gates.md).

quantization gate
  The check after quantization that compares the int8 model's quality on the {term}`test part`
  with the trained model's. A loss beyond the {term}`budget` fails the run and exports nothing. See
  [Budgets and gates](topics/budgets-and-gates.md).

representative samples
  The training windows run through the model to learn the range of every tensor, which int8
  conversion needs to choose its scales. {mf}`export.representative_samples` sets how many.

run
  One invocation of a command that runs a stage. It writes its own directory,
  `runs/<time>-<digest>/`, and never changes an earlier one. See
  [What a run leaves](topics/what-a-run-leaves.md).

run report
  `report.json` in a run directory: every stage, the data, the metrics, the fit check, the gate's
  verdict and the interface. See [What a run leaves](topics/what-a-run-leaves.md).

stage
  One of the five steps of the pipeline — data, build, train, quantize, export. Each stage's result
  is cached and reused while its inputs are unchanged.

target
  A {term}`board` named in {mf}`export.targets`. The model has to fit every target.

template
  The shape of the model, named in {mf}`model.template` and sized by {mf}`model.params`: `mlp` or
  `conv1d`. See [Templates](topics/templates.md).

test part
  The windows held back from training and validation. The trained and the int8 model are both
  measured on it, so the {term}`quantization gate` compares like with like.

TFLM
  TensorFlow Lite for Microcontrollers: the runtime that runs the exported model on the board. See
  [What is verified today](ref/compatibility.md).

training part
  The share of windows the model learns from. Everything learned from the data — normalization, a
  vocabulary — is learned from this part only.

vocabulary
  The values a `category` column knows: the most frequent ones in the {term}`training part`, plus
  one "unknown" entry for anything else. See [Feature types](topics/feature-types.md).

WCAG
  Web Content Accessibility Guidelines: the W3C's standard for accessible web pages.

window
  Consecutive rows of your table that together make one sample, as many as
  {mf}`preprocessing.window_size` says. Windows never overlap.
```
