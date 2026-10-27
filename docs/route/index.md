# The route

Four legs, from nothing to a microcontroller answering. Each one ends with something you can point
at — a file that now exists, a number the run printed, a verdict the pipeline reached — and each
one tells you up front what that will be.

Stop after any leg and what you built still works. Nothing is left half-configured for the next leg
to finish.

## The legs

:::{container} prose

**[Leg 1 — Your first model](1-first-model.md)** · about 5 minutes
You run the worked example end to end. You end with an int8 model, its C array, and the run report
that says what quantization cost.

**[Leg 2 — Your own columns](2-your-columns.md)** · about 10 minutes, 15 from the start
You point the same pipeline at a table of your own and name your columns. You end with a model that
reads your data, and your own accuracy figure.

**[Leg 3 — Onto a board](3-onto-a-board.md)** · about 15 minutes, 30 from the start
You put the exported C files into a firmware project and flash a generic ESP32. You end with a board
answering, and its answers checked against your computer's.

**[Leg 4 — When it does not fit](4-when-it-does-not-fit.md)** · after the half hour
You tighten a budget until the gate refuses the run, read the per-layer table it prints, and choose
a budget on purpose. You end understanding the one thing Caravan will not let you skip.

:::

## Before you start

The clock above assumes the install is already done, and the install is the longest wait in the half
hour: about 2 GB of download for the training dependency. Leg 1 starts with it, so start it and read
on while it runs.

You need Python 3.13 for training. Linux or macOS — on Windows the commands work under WSL, and
nothing here has been tested in PowerShell. A microcontroller only matters from leg 3.

## Why it is called a route

A caravan travels in legs, and so does getting a model onto a board: the data is prepared, the model
is built, it is trained, it is shrunk, and only then does it fit in something that has a few hundred
kilobytes to spare. "Stage" already means something precise in Caravan — the pipeline's own stages
are data, build, train, quantize and export — so the parts of this route are legs, and a leg is
never a stage.

```{toctree}
:maxdepth: 1
:hidden:

1-first-model
2-your-columns
3-onto-a-board
4-when-it-does-not-fit
```
