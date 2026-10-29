# Leg 3: onto a board

:::{container} leg-head
**15 minutes.**

You will end with **a microcontroller running your model**, and **its answers compared with your
computer's**, window by window, with a count of how many agree.

This is the leg that needs hardware.
:::

## What you need

**A classic ESP32 development board.** The firmware targets the plain ESP32 DevKit profile
(`esp32dev`), which fits any classic ESP32 module with 4 MB of flash: "ESP32 DevKitC", "NodeMCU-32S",
"ESP32-WROOM-32 dev board" and the many unlabelled ones. They cost under €10.

For a different classic board, set `board = esp32dev` in `examples/esp32/platformio.ini` to your
board's PlatformIO identifier. `pio boards esp32` lists them. This leg is written for the classic
ESP32.

**A USB cable that carries data.** A charge-only cable is the most common reason a board does not
appear.

**No board?** [Without a board](#without-a-board) below still gives you a compiled firmware and the
flash and RAM figures for your model.

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

**The first build** downloads the compiler toolchain, ESP-IDF and Espressif's TensorFlow Lite Micro
component, then compiles all of it. Later builds take seconds.

**The result** ends in `SUCCESS`, with lines like these:

```text
RAM:   [==        ]  19.2% (used 62856 bytes from 327680 bytes)
Flash: [===       ]  31.9% (used 334717 bytes from 1048576 bytes)
```

Those are the linker's figures for this firmware with this model: <span class="prov estimated">estimated</span>.
The RAM figure includes the 48 KB the firmware reserves for the model's working memory. The board
reports what the runtime needs when you run it.

**Warnings** about `shadows a parameter` come from the TensorFlow Lite Micro sources and you can
ignore them.

## Flash and watch

```bash
# step: board-flash
cd examples/esp32
pio run -e esp32dev -t upload
pio device monitor
cd ../..
```

PlatformIO finds a single connected board by itself; `pio device list` shows the port. Close the
monitor with Ctrl+C. Press the board's RST button to run the windows again.

## What you have

:::{container} leg-check
The serial port prints one line per window:

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

:::

**Reading the result.** `agreed 12/12` with `max_diff_steps 0` means the board's scores are
bit-identical to your computer's. Quantized arithmetic is integer arithmetic, and Espressif's
accelerated kernels keep their requantization bit-exact.

- **A difference of one step** is the smallest difference the output can express. Both answers are
  the same at the edge of rounding.
- **More than one step** is reported as `over_one_step`. The usual cause is stale files in
  `src/model/`: a `test_windows.h` from one run and a `model_data.cc` from another. Copy all four
  again from the same run.
- **`DISAGREE`** means the board and your computer would act differently on the same input. Do not
  ship that. First check that all four files come from one run.

**`arena: used N of 49152 bytes (measured, esp32)`** is what the model's working memory costs on the
device, read from the runtime. To get that RAM back, set `kArenaBytes` in `src/main.cc` to this
figure plus a margin.

## Without a board

Run everything up to and including **Build**. You end with a compiled binary and the linker's flash
and RAM figures for your model (<span class="prov estimated">estimated</span>), which tell you
whether it fits the part. Flashing a board adds the comparison of its answers with your computer's.

## Next

**[Leg 4 — when it does not fit](4-when-it-does-not-fit.md)** is where the gate refuses a run on
purpose, so the first time you see it is one you caused.

If you stop here, you have a model on a board and a count of how many of its answers match your
computer's.
