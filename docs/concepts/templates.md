# Templates: what `mlp` and `conv1d` mean, and which to pick

A **template** is the shape of the model. You do not write layers; you name a template and give it
a few parameters, and Caravan builds the model from that. There are two, and the names are
abbreviations that deserve expanding.

## `mlp` — a multilayer perceptron

**MLP** stands for *multilayer perceptron*, which is the oldest and plainest kind of neural network:
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

**Conv1d** is short for *one-dimensional convolution*. **CNN**, the abbreviation you may have seen,
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

## Which one, for data you can describe

| If your data is like this | Pick | Because |
|---|---|---|
| A few sensors, and the classes differ in their typical values | `mlp` | The level carries the signal, and the simplest model that can see it is the one to use |
| Vibration, motion, or anything where a waveform's shape matters | `conv1d` | The shape is the signal, and it needs to be recognised wherever in the window it falls |
| A handful of codes and counters, no time structure to speak of | `mlp` | There is no shape along time for a convolution to find |
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

The `conv1d` is the smaller *file* here and the `mlp` the simpler *operator set*, which is the
trade worth knowing: convolutions reuse their weights, so they buy pattern-matching cheaply in
flash, and they pay for it in the number of kernels the board's runtime has to carry and in working
memory while the model runs. A smaller file is not automatically the model that fits.

Which is the point of the fit check: you do not have to predict this. Name the boards in
`export.targets` and the build stage compares the model against each one *before* training spends
your time. [Budgets and gates](budgets-and-gates.md) explains what it checks and what its answer is
worth.

## Adding a third

Templates are data in the package, not forks of Caravan, and the roadmap says which are planned.
`caravan templates` lists what is registered in the version you have.
