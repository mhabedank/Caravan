# On the board: LILYGO LoRa32

From the model `try-it` exported to the same model running on a LILYGO LoRa32 (an ESP32 with a
small OLED). The board runs windows of the test part through the model and shows, per window, its
answer, the answer the int8 model gave on your computer, and the expected one.

When every window agrees, what Caravan measured on your computer is what the microcontroller does.

You need:

- **The try-it guide done.** You need its directory, with the virtual environment active, the
  `examples/` directory and a run under `runs/`. If not, do [Try it](../try-it.md) first.
- **A LILYGO LoRa32 and a USB data cable.** Some cables carry only power.
- **About 3 GB of disk and an internet connection** for the first build. PlatformIO downloads the
  ESP32 toolchain and ESP-IDF once.

Nothing here uses the LoRa radio or Wi-Fi, and the firmware holds no keys or credentials.

## Which LoRa32 do you have?

The revisions differ in where the OLED is wired. The firmware has one build environment per
wiring:

| Your board | Looks like | Environment |
|---|---|---|
| **V2.0 / V2.1 / "T3 V1.6" / "T3 V1.6.1"** | ESP32-PICO-D4 module, **microSD slot**, SMA antenna connector, power switch, one button (RST) | `lora32` |
| **V1.3** | ESP32 chip visible, no SD slot, small U.FL antenna connector | `lora32` |
| **V1.0** | ESP32 chip visible, no SD slot, two buttons (PRG and RST) | `lora32-v1` |

- The label printed on the board decides when you can read it: `T3_V1.6 20180606`,
  `T3_v1.6.1 20210104` or `T3_V1.3` all mean `lora32`.
- If unsure, start with `lora32`. A wrong guess costs nothing: the OLED stays dark, and the results
  still arrive on the serial port.
- If your board has an SD card in it, take it out before flashing. Its pins share a pin the ESP32
  reads while starting.

## The USB connection

The board's USB port goes through a USB-serial chip: a **CP2104** or a **CH9102**, depending on
the batch. It is the small chip next to the USB connector, and its marking says which one you
have.

- **Linux.** Both work without a driver: the CP2104 as `/dev/ttyUSB0`, the CH9102 as
  `/dev/ttyACM0`. To use the port without root, add yourself to the `dialout` group once, then log
  out and back in:

  ```bash
  sudo usermod -a -G dialout $USER
  ```

- **macOS.** Install the vendor's driver: Silicon Labs' "CP210x VCP" for a CP2104, WCH's "CH34x
  VCP" for a CH9102. Then allow it under System Settings → Privacy & Security.
- **Windows.** The same two vendor drivers. The board appears as a `COM` port.

Once PlatformIO is installed (next step), `pio device list` shows the port. You need not type it:
PlatformIO finds a single board by itself.

## Install PlatformIO

Into the same virtual environment as Caravan:

```bash
# step: board-tools
pip install platformio==6.2.0
pio --version
```

`pio --version` prints `PlatformIO Core, version 6.2.0`.

## Hand the export to the firmware

The firmware project is `examples/lora32/`. It came with the example. The model goes into its
`src/model/` directory: four files from the newest run's `model/` directory.

```bash
# step: board-copy
run=$(ls -td runs/*/ | head -1)
ls "${run}model/test_windows.h"
cp "${run}model/model_data.h" "${run}model/model_data.cc" "${run}model/resolver.h" \
  "${run}model/test_windows.h" examples/lora32/src/model/
```

**What the files are:**
- `model_data.h` and `model_data.cc`: the model as a C array, with a named position for every
  input and the output.
- `resolver.h`: exactly the operators the model needs.
- `test_windows.h`: the test windows.

`test_windows.h` exists because the example manifest asks for it: `export.test_windows: 16`. The
example's test part holds 12 windows, so all 12 are written, three of each class. If `ls` says the
file is missing, your run predates that line: run `caravan export examples/picket-mlp.yaml` again.

## Build

```bash
# step: board-build
cd examples/lora32
pio run -e lora32
cd ../..
```

For a V1.0 board, use `-e lora32-v1` instead.

**Time.** The first build downloads the toolchain, ESP-IDF and Espressif's TensorFlow Lite Micro
component, then compiles all of it. Allow 10 to 20 minutes. Later builds take seconds.

**The result.** It ends in `SUCCESS`, with lines like these:

```text
RAM:   [==        ]  19.5% (used 63960 bytes from 327680 bytes)
Flash: [====      ]  35.1% (used 368153 bytes from 1048576 bytes)
```

These are the linker's figures for this firmware with the example model, not a measurement on the
board. The RAM figure includes the 48 KB reserved for the model's working memory.

**Warnings.** Warnings about `shadows a parameter` come from the TensorFlow Lite Micro sources, not
from your model, and are harmless.

## Flash and watch

Connect the board and run:

```bash
# step: board-flash
cd examples/lora32
pio run -e lora32 -t upload
pio device monitor
cd ../..
```

`pio device monitor` shows the serial output. It closes with Ctrl+C. If you opened it after the
run had finished, press the board's RST button to run again.

### On the OLED

One screen per window, each held for a second and a half:

```text
picket-mlp 0.2.0
window  3/12
board : fuzzy
host  : fuzzy
expect: fuzzy
AGREE  diff 0 steps
arena 9876 B meas.
agreed so far 3/3
```

At the end the summary stays on screen:

```text
picket-mlp 0.2.0
DONE 12 windows
agreed 12/12
max diff 0 steps
arena 9876 B meas.

details: serial
115200 baud
```

The arena figure in these two pictures is a placeholder. Your board shows its own.

### On the serial port

The same, one line per window, then a summary and a record:

```text
caravan board run
model: picket-mlp 0.2.0
board: lora32 rev=V1.3/V1.6/V2.x clock_mhz=240
arena: used 9876 of 49152 bytes (measured, lora32)
window 1/12: board=dos host=dos expected=dos agree max_diff_steps=0
...
summary: agreed 12/12, max_diff_steps 0
--- board run record ---
...
--- end ---
```

### What the words mean

- **`board`, `host` and `expected`:**
  - `board` is the board's answer;
  - `host` is what the same int8 model answered on your computer when Caravan exported it;
  - `expected` is what the data says.

  A model can be wrong about `expected` on some window and still be right on the board. What this
  run checks is that the board **agrees with the host**.
- **`agree` / `DISAGREE`:**
  - for a category or yes/no output, whether board and host chose the same class;
  - for a number output, whether they are within one step (below).

  Every window should say `agree`.
- **`max_diff_steps`:** how far the board's raw scores are from the host's, in quantization steps
  of the output. For the example a step is 1/256.
  - 0 means identical.
  - 1 is still within what the rounding of a different processor can explain.
  - Above 1 the line says `over_one_step`. That is worth reporting even when the answer agrees.
- **`arena … (measured, lora32)`:** how much working memory the model actually used on your board,
  as the microcontroller runtime reports it. This is a measurement on your board. Caravan's own
  figure for the same model, `working memory: floor` in the export's output, is a lower bound
  computed on your computer.

## Smaller working memory

The firmware reserves 48 KB for the model (`kArenaBytes` in `src/main.cc`). That is far more than
the example needs. If your own firmware needs the RAM:
1. Set `kArenaBytes` to the measured figure plus a margin, say 25 %, rounded up to a multiple of
   1,024.
2. Build and flash again.

If it is too small, the board says so instead of running:

```text
error: arena too small (kArenaBytes=4096); raise kArenaBytes in src/main.cc
```

## When something is off

| What you see | What to do |
|---|---|
| The OLED stays dark, the serial port shows the run | The OLED wiring of the other environment. Build and flash with `-e lora32-v1` (or back to `lora32`). The serial line `oled: not found on SDA … / SCL …` says which pins were tried. |
| Upload fails with "Failed to connect" | Most boards enter flashing mode by themselves. If yours does not, hold the BOOT/PRG button while the upload starts. On a 1.6.x board without that button, connect the IO0 pin to GND, press RST, upload, then remove the wire. Take out any SD card. |
| No serial port appears | A power-only cable, or the USB-serial driver (above). |
| `error: input … does not match test_windows.h` | The four files come from different runs. Copy all four from one run again. |
| The image is upside down | Some modules mount the display rotated. The results are unaffected. Report it, with your revision, so the firmware can account for it. |
| A window says `DISAGREE` or `over_one_step` | Keep the whole serial output and report it: that is exactly what this run exists to find. |

## Your own model

Nothing in the firmware is specific to the example. For a model of your own:
1. Set `export.test_windows` in its manifest, for example 16.
2. Add `esp32` to `export.targets`.
3. Export it.
4. Copy its four files as above, then build and flash.

[Your own project](own-project.md) goes from your own data to that manifest.

## Recording a run

The block between `--- board run record ---` and `--- end ---` is the evidence that the model runs
on this board. To record it for the project:
1. Copy it into a new file `docs/board-runs/<date>-lora32.md`.
2. Fill in the date, and the revision printed on your board.
3. Add the file to [the list of board runs](../board-runs/index.md).

The [compatibility page](../compatibility.md) cites it.
