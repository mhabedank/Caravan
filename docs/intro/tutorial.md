# Tutorial

<figure class="tutorial-figure">
<img src="../_static/images/route-road-to-the-board/route-road-to-the-board-960.webp"
     srcset="../_static/images/route-road-to-the-board/route-road-to-the-board-480.webp 480w, ../_static/images/route-road-to-the-board/route-road-to-the-board-960.webp 960w, ../_static/images/route-road-to-the-board/route-road-to-the-board-1600.webp 1600w"
     sizes="(max-width: 860px) 100vw, 860px" width="1600" height="900" decoding="async"
     alt="A small orange-yellow van drives along a long straight road across flat country at dawn, towards a low workshop building on the horizon (AI-generated image)">
</figure>

Four parts take you from nothing to a microcontroller running your model. Each part ends with
something you can point at: a file on disk, a number the run printed, a verdict the pipeline
reached, and each one says at the top what that is. Every part leaves a working result.

## The parts

- **[Part 1: Your first model](tutorial01.md)** · 5 minutes. You end with an int8 model, its C
  array, and a report of what shrinking the model cost.
- **[Part 2: Your own data](tutorial02.md)** · 10 minutes. You end with a model that reads the
  columns you chose, and your own accuracy figure.
- **[Part 3: Onto a board](tutorial03.md)** · 15 minutes. You end with an ESP32 running your model,
  and its answers compared with your computer's.
- **[Part 4: When it does not fit](tutorial04.md)**. You end having made the fit check refuse a
  run, and you know what it prints.

## Before you start

[Install Caravan](install.md) first. Parts 1 and 2 need nothing but your computer; part 3 needs an
ESP32 development board. If you want the whole picture before you start,
[Caravan at a glance](overview.md) walks one manifest through every stage.

```{toctree}
:maxdepth: 1
:hidden:

tutorial01
tutorial02
tutorial03
tutorial04
```
