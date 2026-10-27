# Leg 3: onto a board

:::{container} leg-head
**About 15 minutes**, 30 from the start of leg 1 — plus a first build that downloads a toolchain.

You will end with **a microcontroller answering**, and **its answers checked against your
computer's**, window by window, with a count of how many agreed.

This is the leg that needs hardware.
:::

## What you need

**A classic ESP32 development board.** Written and verified against the plain ESP32 DevKit profile
(`esp32dev`), which fits any classic ESP32 module with 4 MB of flash — the boards sold as
"ESP32 DevKitC", "NodeMCU-32S", "ESP32-WROOM-32 dev board" and the many unlabelled ones. Under €10.

If yours differs, one line changes. In `examples/esp32/platformio.ini`, `board = esp32dev` becomes
your board's PlatformIO identifier — `pio boards esp32` lists them. An ESP32-S3 or -C3 is a
different architecture: the firmware is portable but the pin of this leg is the classic ESP32, and
nothing here has been run on the newer ones.

**A USB cable that carries data.** A charge-only cable is the most common reason a board does not
appear.

**No hardware at all?** Read on to the end — there is a path that still gives you something
countable, below.

## Install PlatformIO

Into the same virtual environment as Caravan:

```bash
# step: board-tools
pip install platformio==6.2.0
pio --version
```

`pio --version` prints `PlatformIO Core, version 6.2.0`.

## Hand the export to the firmware

The firmware project is `examples/esp32/`, and it came with the example in leg 1. It is
model-agnostic: everything it knows about your model arrives as four files from your newest run.

```bash
# step: board-copy
run=$(ls -td runs/*/ | head -1)
ls "${run}model/test_windows.h"
cp "${run}model/model_data.h" "${run}model/model_data.cc" "${run}model/resolver.h" \
  "${run}model/test_windows.h" examples/esp32/src/model/
```

`test_windows.h` is the file this leg turns on. It exists because the manifest asked for it
(`export.test_windows: 16`), and it holds windows of the test part together with **the answers your
computer gave for them**. Without it, "the board works" would mean "the board did not crash".

If `ls` says it is missing, your manifest does not ask for it — add `test_windows: 16` under
`export` and run `caravan export` again.

## Build

```bash
# step: board-build
cd examples/esp32
pio run -e esp32dev
cd ../..
```

**Time.** The first build downloads the compiler toolchain, ESP-IDF and Espressif's TensorFlow Lite
Micro component, then compiles all of it: allow 10 to 20 minutes, and it is not counted in this
leg's fifteen. Later builds take seconds.

**The result** ends in `SUCCESS`, with lines like these:

```text
RAM:   [==        ]  19.2% (used 62856 bytes from 327680 bytes)
Flash: [===       ]  31.9% (used 334717 bytes from 1048576 bytes)
```

Those are the linker's figures for this firmware with this model, so they are
<span class="prov estimated">estimated</span> — a linker is not a board. The RAM figure includes the
48 KB the firmware reserves for the model's working memory, which is a starting value with room to
spare; the board will tell you what the runtime actually needed.

**Warnings** about `shadows a parameter` come from the TensorFlow Lite Micro sources, not from your
model, and are harmless.

## Flash and watch

```bash
# step: board-flash
cd examples/esp32
pio run -e esp32dev -t upload
pio device monitor
cd ../..
```

PlatformIO finds a single connected board by itself; `pio device list` shows the port if you need
it. The monitor closes with Ctrl+C, and if you opened it after the run had finished, press the
board's RST button to run it again.

## What you have

:::{container} leg-check
On the serial port, one line per window:

```text
caravan board run
model: picket-mlp 0.2.0
board: esp32 clock_mhz=240
arena: used 10816 of 49152 bytes (measured, esp32)
window 1/12: board=normal host=normal expected=normal agree max_diff_steps=0
window 2/12: board=dos    host=dos    expected=dos    agree max_diff_steps=0
...
summary: agreed 12/12, max_diff_steps 0
```

Then a run record to paste into a note of your own.
:::

**What to expect, and what a disagreement means.** `agreed 12/12` with `max_diff_steps 0` is the
normal result, and it is a strong statement: the board produced bit-identical scores to your
computer. That is possible because the quantized arithmetic is integer arithmetic and Espressif's
accelerated kernels keep their requantization bit-exact.

- **A difference of one step** is the smallest difference the output can express, and is
  acceptable: the two are the same answer at the edge of rounding.
- **More than one step** is reported as `over_one_step` and is worth investigating. The usual cause
  is stale files in `src/model/` — a `test_windows.h` from one run and a `model_data.cc` from
  another. Copy all four again from the same run.
- **A disagreement in the decision** — `DISAGREE` — means the board and your computer would act
  differently on the same input. Do not ship that. It is a real finding, and the files being from
  one run is the first thing to rule out.

**`arena: used N of 49152 bytes (measured, esp32)`** is the one figure in this leg that is a
measurement, because it comes from the runtime on the device rather than from analysis. It is what
the model's working memory actually cost. If you need that RAM back, set `kArenaBytes` in
`src/main.cc` from this figure with a margin.

## Without a board

The firmware builds without one, and the build is the part that can fail. Run everything up to and
including **Build**: you end with a compiled binary and the linker's flash and RAM figures for your
own model, which tells you whether it fits the part at all.

What that path cannot tell you is the only thing the board can: whether the model *answers the
same* on the device as on your computer. Flash figures are
<span class="prov estimated">estimated</span>, and agreement is not estimable — it is either
measured or unknown.

## Next

**[Leg 4 — when it does not fit](4-when-it-does-not-fit.md)** is where the gate refuses a run on
purpose, so the first time you see it is one you caused.

If you stop here, you have a model running on hardware that you have checked rather than hoped
about. That is the end of the half hour.
