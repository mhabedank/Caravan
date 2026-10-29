# Add a board

**Goal:** a board of your own that {cmd}`caravan boards` lists and {mf}`export.targets` accepts.

**You need:** the board's datasheet or reference manual, and a checkout of Caravan. A board is a
data file inside the package, so adding one is a file, not a code change.

## 1. Install Caravan from a checkout

```bash
git clone https://github.com/mhabedank/Caravan.git && cd Caravan
python3.13 -m venv .venv && . .venv/bin/activate
pip install -e ".[train,verify]"
```

An editable install reads the board files from the checkout, so a file you add is seen at once.

## 2. Start from a board that resembles yours

Copy the closest of the three, named after your board's identifier. The identifier is lower case
letters, digits and hyphens, and it must equal the file name:

```bash
cp src/caravan/targets/boards/stm32h743.yaml src/caravan/targets/boards/stm32f746.yaml
```

## 3. Fill in every field from the datasheet

Set each field to your part's value. [The description file](../ref/boards.md#the-description-file)
says what each one means:

- [`board`](#board-file-board) — the identifier, the same as the file name;
- [`family`](#board-file-family) and [`core`](#board-file-core);
- [`clock_mhz`](#board-file-clock-mhz), [`ram_kb`](#board-file-ram-kb) and
  [`flash_kb`](#board-file-flash-kb) — the {term}`fit check` compares a model with the last two;
- [`accel`](#board-file-accel) — `cmsis-nn` for a Cortex-M with DSP extensions, `esp-nn` for an
  Espressif Xtensa part, otherwise `none`;
- [`interfaces`](#board-file-interfaces);
- [`toolchain`](#board-file-toolchain) — the compiler and optimisation level your firmware uses;
- [`emulator`](#board-file-emulator) — the Renode platform, or `null`;
- [`notes`](#board-file-notes), if a reader needs to know something about the part.

## 4. Record the source of every value

Under [`sources`](#board-file-sources), write where each of `clock_mhz`, `ram_kb`, `flash_kb`,
`accel`, `toolchain` and `emulator` comes from, precisely enough that a reader can check it. For
an STM32F746, for example:

```yaml
sources:
  clock_mhz: "ST RM0385 reference manual, clock tree"
  ram_kb: "ST RM0385, memory map: SRAM1 and SRAM2, DTCM not counted"
  flash_kb: "ST RM0385, embedded flash"
  accel: "CMSIS-NN supports Cortex-M7 with DSP and FPU"
  toolchain: "the toolchain this project's firmware is built with"
  emulator: "Renode supported boards list, read on the day you checked it"
```

A value without a source is refused (rule {rule}`S-1`), and so is an emulator platform Renode does
not have (rule {rule}`E-1`). If there is no emulator, write `emulator: null` and the reason under
`sources`.

## 5. Check that Caravan accepts it

```bash
caravan boards
```

Your board is in the list, with its core, clock, RAM, flash and kernel library. A file that breaks
a rule makes the command fail and names the rule and the field.

Then name it in a manifest's {mf}`export.targets` and validate:

```bash
caravan validate manifest.yaml
```

`valid` means the manifest accepts the board, and the next {cmd}`caravan export` checks the model
against its RAM and flash before training.

## Result

A board file the pipeline accepts, with a source for every value. The fit check's verdict on it is
<span class="prov estimated">estimated</span>, as for every board; [part 3 of the
tutorial](../intro/tutorial03.md) shows how a board's own answers are compared with your computer's.

:::{note}
To contribute the board to Caravan, add its entry to [Boards](../ref/boards.md) and its row to
[what is verified today](../ref/compatibility.md) as well. The project's reference check fails
until both list it.
:::
