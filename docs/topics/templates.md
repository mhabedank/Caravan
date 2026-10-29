# Templates: what `mlp`, `conv1d`, `conv2d` and `autoencoder` mean, and which to pick

:::{admonition} You will learn
:class: learn
- what a template is, and what `mlp`, `conv1d`, `conv2d` and `autoencoder` stand for;
- when the level of a reading decides, when the shape of a pattern over time does, and when a
  pattern spans two axes;
- why an anomaly detector learns from normal data only;
- what each template's parameters change;
- why the smaller file is not always the model that fits.
:::

A **{term}`template`** is the shape of the model. You do not write layers; you name a template and give it
a few parameters, and Caravan builds the model from that. There are four, and most of the names are
abbreviations that deserve expanding. Three of them answer a question about a window — which class,
yes or no, how much — and the fourth says how unusual the window is.

## `mlp` — a multilayer perceptron

**{term}`MLP`** stands for *multilayer perceptron*, which is the oldest and plainest kind of neural network:
a stack of layers where every value in one layer is connected to every value in the next. "Dense"
and "fully connected" mean the same thing.

What that means for your data: the whole window is flattened into one long row of numbers, and the
model learns weights over all of it at once. It has no idea that your rows are consecutive in time
— row 1 and row 16 are just two positions in a list to it.

**When it is the right answer.** When the *level* of your readings is what distinguishes the thing
you are looking for. A machine running hot, a bus carrying more frames than usual, a battery whose
voltage has sagged. If you could tell the classes apart from the averages, an `mlp` will find it.

**Its parameters:**

- `hidden` — a list of layer widths, at least one. `[16]` is one layer of sixteen; `[32, 16]` is two
  layers, the second narrower. Start with `[16]`. Go wider or deeper only when the model underfits,
  which you see as a training accuracy that is already poor.
- `dropout` — between 0 and 1, default 0. During training it randomly ignores that fraction of the
  connections, which makes the model lean less on any one of them. Reach for it when training
  accuracy is much better than test accuracy. `0.1` is a normal first try.

## `conv1d` — a one-dimensional convolutional network

**Conv1d** is short for *one-dimensional convolution*. **{term}`CNN`**, the abbreviation you may have seen,
stands for *convolutional neural network*. One-dimensional means the dimension it slides along is
time: a small window of weights — a kernel — passes over your readings looking for a shape, and
reports where it found one.

What that means for your data: the model learns *patterns over time*, and finds them wherever in
the window they occur. A spike followed by a decay is the same spike whether it happens at row 3 or
row 11.

**When it is the right answer.** When the *shape* of a pattern matters more than where it sits in
the window: vibration, motion from an accelerometer, anything audio-like, a gait, a stroke of a
pump. If a human would recognise it from the squiggle rather than from the average, this is the one.

**Its parameters:**

- `blocks` — a list, at least one. Each block has `filters` (how many different shapes it looks
  for), `kernel` (how many time steps a shape spans), and optionally `stride`, `padding`,
  `normalise`, `pool` and `dropout`.
- `head` — `average` (the default) or `flatten`. `average` takes the mean over time, which throws
  away *where* a pattern was and keeps *whether* it was there; `flatten` keeps the position and
  costs more weights.

## `conv2d` — a two-dimensional convolutional network

**Conv2d** is *two-dimensional convolution*: the same idea as `conv1d`, but the kernel slides along
two axes instead of one. The thing it slides over is a **plane**, and Caravan makes one of two
kinds:

- **a window of frames** — the window's rows are the plane's rows, and the input columns are its
  columns. Keyword spotting looks like this once the audio has become frames: 49 frames of 10
  coefficients each is a 49 × 10 plane.
- **an image** — height by width, with its colour channels, from one `image` input. `conv2d` is the
  only template that takes one ([Feature types](feature-types.md#image) says what the device then
  passes).

What that means for your data: the model finds a pattern that has extent along *both* axes — a
ridge across neighbouring frequencies that also lasts a few frames, an edge or a corner in a
picture — wherever in the plane it sits. `conv1d` cannot see that, because it treats the columns as
unrelated channels and only slides along time.

**When it is the right answer.** When the columns are *neighbours* of one another, not just
different sensors: frequency bins, coefficients of a spectrum, pixels. And whenever the input is an
image. When the columns are different sensors — a temperature beside a current — their order means
nothing, a pattern across them is an accident of how you listed them, and `conv1d` or `mlp` is the
honest choice. The same holds for a `category` input: its learned channels sit beside the others in
the plane as if they were neighbours, and they are not.

**Its parameters:**

- `blocks` — a list, at least one. Each block has `filters` and `kernel`, and the kernel is an
  integer for a square or `[rows, columns]` for a rectangle. `kind` is `standard` (the default) or
  `separable`. A separable block is a *depthwise* convolution, one small kernel per channel,
  followed by a 1 × 1 convolution that mixes the channels into the block's `filters`. It does
  nearly the same job for a fraction of the weights, which is why the small keyword-spotting and
  person-detection reference models are built almost entirely from it. Optionally `stride`,
  `padding`, `normalise`, `pool` and `dropout`, as for `conv1d`, with `stride` and `pool` also
  given per axis.
- `head` — `average` (the default) or `flatten`, as for `conv1d`: `average` keeps *whether* a
  pattern was in the plane, `flatten` keeps *where*.

A plane that is too small for its blocks — a kernel or a stride that leaves nothing on one axis —
is refused before training ({rule}`CF-6`).

## `autoencoder` — anomaly detection from normal data

An **{term}`autoencoder`** is a network trained to give back its own input. It squeezes the window
through a narrow middle layer, the *code*, and rebuilds it on the other side. Because the code is
narrow it cannot copy the window; it has to learn what windows usually look like.

Caravan trains it on **normal** windows only. Afterwards, a window like the ones it learned from
comes back nearly unchanged, and a window unlike them comes back wrong. How wrong — the mean squared
difference between the window and its reconstruction — is the {term}`anomaly score`, and it is
computed inside the model, so your firmware receives one number and compares it with a threshold
the run chose for it.

**When it is the right answer.** When faults are rare and each one is different — a bearing that
starts to rattle, a fan with a chipped blade, a pump running dry — and normal operation is what you
have hours of. A classifier needs examples of every fault it should name; an autoencoder needs only
to know what normal is. You still need a column that tells normal from abnormal windows, because
that is how the {term}`quantization gate` measures whether the score still separates them after
8-bit.

It answers an `anomaly` output and nothing else, and an `anomaly` output is answered by nothing
else ({rule}`CF-18`).

**Its parameters:**

- `encoder` — a list of layer widths from the input towards the code, at least one. `[32, 16]`
  narrows in two steps.
- `code` — the width of the middle layer. Narrower forces the model to keep only what normal
  windows have in common, and rebuilds them less exactly; wider rebuilds everything better,
  including the anomalies it ought to get wrong. `examples/anomaly-autoencoder.yaml` uses a code
  of 4 after `[32, 16]`; the zoo's machine-sound detector uses 8 after `[64, 64]`.
- `decoder` — the widths back out. Left out, it is the encoder reversed, which is the usual choice.
- `dropout` — as for `mlp`.

## Which one, for data you can describe

| If your data is like this | Pick | Because |
|---|---|---|
| A few sensors, and the classes differ in their typical values | `mlp` | The level carries the signal, and the simplest model that can see it is the one to use |
| Vibration, motion, or anything where a waveform's shape matters | `conv1d` | The shape is the signal, and it needs to be recognised wherever in the window it falls |
| A handful of codes and counters, no time structure to speak of | `mlp` | There is no shape along time for a convolution to find |
| Frames of a spectrum — neighbouring frequencies, one row per frame | `conv2d` | A pattern has extent along time and along frequency, and the convolution has to run along both |
| An image | `conv2d` with an `image` input | It is the only template that takes one |
| Plenty of normal data, rare and varied faults | `autoencoder` with an `anomaly` output | It learns what normal looks like, so it needs no example of each fault |
| You do not know yet | `mlp` with `hidden: [16]` | It trains in seconds, so it is the cheapest way to find out whether the problem is learnable at all |

When in doubt, run the `mlp` first. If it does poorly and you believe the shape matters, try
`conv1d`. That is two runs of a few minutes, which is cheaper than reasoning about it.

## What each costs

On the same committed synthetic data, so the two are comparable:

| | `mlp` (the pilot) | `conv1d` (the fixture) |
|---|---|---|
| Parameters | — | 2,180 |
| Exported model | 14,848 bytes | 7,888 bytes |
| Operators | 3 | 6, in 8 nodes |

The `conv1d` is the smaller *file* here and the `mlp` the simpler *operator set*. That is the
trade: convolutions reuse their weights, so they buy pattern-matching cheaply in
flash, and they pay for it in the number of kernels the board's runtime has to carry and in working
memory while the model runs. A smaller file is not automatically the model that fits.

`conv2d` and `autoencoder` are measured against published reference models rather than against this
fixture: the keyword-spotting and person-detection networks of MLPerf Tiny, and the zoo's
machine-sound detector. [Applications](applications.md) gives their parameters and sizes.

Which is the point of the {term}`fit check`: you do not have to predict this. Name the boards in
{mf}`export.targets` and the build stage compares the model against each one *before* training
spends your time. [Budgets and gates](budgets-and-gates.md) explains what it checks and what its answer is
worth.

## Adding another

Templates are data in the package, not forks of Caravan, and [the roadmap](../roadmap.md) says
which are planned. {cmd}`caravan templates` lists what is registered in the version you have.

:::{seealso}
{mf}`model.template` and {mf}`model.params` in [the `model` section](../ref/manifest/model.md),
[Applications](applications.md) for which template serves which kind of problem, and the templates
this version registers in [what is verified today](../ref/compatibility.md).
:::
