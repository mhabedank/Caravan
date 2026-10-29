# The route

<figure class="route-figure">
<img src="../_static/images/route-road-to-the-board/route-road-to-the-board-960.webp"
     srcset="../_static/images/route-road-to-the-board/route-road-to-the-board-480.webp 480w, ../_static/images/route-road-to-the-board/route-road-to-the-board-960.webp 960w, ../_static/images/route-road-to-the-board/route-road-to-the-board-1600.webp 1600w"
     sizes="(max-width: 860px) 100vw, 860px" width="1600" height="900" decoding="async"
     alt="A small orange-yellow van drives along a long straight road across flat country at dawn, towards a low workshop building on the horizon (AI-generated image)">
</figure>

Four legs take you from nothing to a microcontroller running your model. Each leg ends with
something you can point at: a file on disk, a number the run printed, a verdict the pipeline
reached. Each leg tells you at the top what that is.

Every leg leaves a working result. Stop after any of them and you keep what you built.

## The legs

:::{container} prose

**[Leg 1 — Your first model](1-first-model.md)** · 5 minutes
You end with an int8 model, its C array, and a report of what shrinking the model cost.

**[Leg 2 — Your own columns](2-your-columns.md)** · 10 minutes
You end with a model that reads the columns you chose, and your own accuracy figure.

**[Leg 3 — Onto a board](3-onto-a-board.md)** · 15 minutes
You end with an ESP32 running your model, and its answers compared with your computer's.

**[Leg 4 — When it does not fit](4-when-it-does-not-fit.md)**
You end having made the fit check refuse a run, and you know what it prints.

:::

## Before you start

Leg 1 starts with the install. It downloads 2 GB, nearly all of it the training framework, so start
it and read on while it runs.

You need Python 3.13 and a POSIX shell (Linux, macOS, or WSL on Windows). You need a
microcontroller from leg 3.

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
