# Boards

A board is a description file: its core, its clock, its RAM and flash, the accelerated kernels it
has, its interfaces, the toolchain its firmware is built with, and whether an emulator exists for
it. Every value carries the source it was taken from. `caravan boards` lists the boards this
version ships, and {mf}`export.targets` names the ones a model has to fit.

The files are in `src/caravan/targets/boards/`, one per board, named after the board's
identifier. [Add a board](../howto/add-a-board.md) shows how to write one, and
[the description file](#the-description-file) below lists its fields.
[What is verified today](compatibility.md) says how far each board has been taken.

| Board | Core, clock | RAM, flash | Accelerated kernels | Emulator |
|---|---|---|---|---|
| {board}`esp32` | Xtensa LX6, 240 MHz | 520 KB, 4,096 KB | ESP-NN | none |
| {board}`s32k144` | Cortex-M4F, 80 MHz | 64 KB, 512 KB | CMSIS-NN | none |
| {board}`stm32h743` | Cortex-M7, 480 MHz | 1,024 KB, 2,048 KB | CMSIS-NN | Renode `stm32h743` |

The fit check compares a model's lower bounds with the RAM and flash below. Its verdict is
<span class="prov estimated">estimated</span> for every board.

:::{board} esp32
**Family** `espressif-esp32` · **Core** `xtensa-lx6` at 240 MHz

- **RAM** 520 KB — the ESP32 series data sheet, internal SRAM.
- **Flash** 4,096 KB — the typical module configuration of the development boards.
- **Accelerated kernels** ESP-NN, which has optimised kernels for Xtensa. CMSIS-NN is Arm-only.
- **Interfaces** CAN, I²C, SPI, UART, Wi-Fi, Bluetooth.
- **Toolchain** `xtensa-esp32-elf-gcc`, `-O2`, TensorFlow Lite for Microcontrollers.
- **Emulator** none. Renode has no ESP32 or Xtensa platform beyond its sample controller.

[Part 3 of the tutorial](../intro/tutorial03.md) builds firmware for this board.
:::

:::{board} s32k144
**Family** `nxp-s32k` · **Core** `cortex-m4f` at 80 MHz, from the NXP S32K1xx data sheet

- **RAM** 64 KB — the S32K1xx data sheet, SRAM. The 4 KB FlexRAM is not counted.
- **Flash** 512 KB — the S32K1xx data sheet, program flash.
- **Accelerated kernels** CMSIS-NN, which supports the Cortex-M4 with DSP and FPU.
- **Interfaces** CAN FD, I²C, SPI, UART.
- **Toolchain** `arm-none-eabi-gcc`, `-O3`, TensorFlow Lite for Microcontrollers.
- **Emulator** none. Renode has the S32K388 and the S32K118, not the S32K144.

An automotive microcontroller rated to ASIL-B.
:::

:::{board} stm32h743
**Family** `st-stm32h7` · **Core** `cortex-m7` at 480 MHz, from ST's RM0433 reference manual

- **RAM** 1,024 KB — RM0433, system RAM map.
- **Flash** 2,048 KB — RM0433, embedded flash.
- **Accelerated kernels** CMSIS-NN, which supports the Cortex-M7 with DSP and FPU.
- **Interfaces** CAN FD, I²C, SPI, UART.
- **Toolchain** `arm-none-eabi-gcc`, `-O3`, TensorFlow Lite for Microcontrollers.
- **Emulator** Renode, platform `stm32h743`.

The performance reference among the three. It is not an automotive part.
:::

The toolchain of every board is Caravan's own build decision, not a vendor default.

## The description file

One YAML file per board. Every field below except `notes` is required, and no other field is
accepted.

(board-file-board)=
**`board`** · string — The identifier: lower case letters, digits and hyphens, starting with a letter or digit. It must equal the file name without `.yaml`, and it is what {mf}`export.targets` accepts.

(board-file-family)=
**`family`** · string — The family the part belongs to, such as `st-stm32h7`.

(board-file-core)=
**`core`** · string — The processor core, such as `cortex-m7`.

(board-file-clock-mhz)=
**`clock_mhz`** · number · needs a source — The CPU clock in MHz, greater than 0.

(board-file-ram-kb)=
**`ram_kb`** · number · needs a source — The RAM available to firmware, in KB, greater than 0. The fit check compares the model's working-memory floor with it.

(board-file-flash-kb)=
**`flash_kb`** · number · needs a source — The flash available for the program, in KB, greater than 0. The fit check compares the model's size with it.

(board-file-accel)=
**`accel`** · string · needs a source — The accelerated kernel library: `cmsis-nn`, `esp-nn` or `none`.

(board-file-interfaces)=
**`interfaces`** · list of strings — The board's interfaces, at least one: `can`, `i2c`, `spi`, `uart` and the like.

(board-file-toolchain)=
**`toolchain`** · mapping · needs a source — How firmware for the board is built: `compiler`, `optimization` and `runtime`, which is `tflm`.

(board-file-emulator)=
**`emulator`** · mapping or `null` · needs a source — An emulator platform — `backend: renode`, `platform` and `status` (`supported` or `experimental`) — or `null`. A platform must be one Renode has (rule {rule}`E-1`); `null` needs its reason in `sources`.

(board-file-sources)=
**`sources`** · mapping — One citation a reader can check for each of `clock_mhz`, `ram_kb`, `flash_kb`, `accel`, `toolchain` and `emulator` (rule {rule}`S-1`).

(board-file-notes)=
**`notes`** · string, optional — Anything a reader of the file needs to know about the part.

