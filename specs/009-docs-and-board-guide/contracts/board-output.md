# Contract: What the LoRa32 Firmware Shows

The output of `examples/lora32/` on its two channels. The serial port carries everything. The OLED
carries what fits.

## Serial (115200 baud)

One line per event, so the output can be pasted and compared.

```
caravan board run
model: picket-mlp 0.2.0
board: lora32 rev=V2.1 clock_mhz=240
arena: used 9876 of 32768 bytes (measured, lora32)
window 1/16: board=dos host=dos expected=dos agree max_diff_steps=0
window 2/16: board=fuzzy host=fuzzy expected=fuzzy agree max_diff_steps=1
...
summary: agreed 16/16, max_diff_steps 1
--- board run record ---
date: <fill in>
board: lora32
revision: V2.1
clock_mhz: 240
firmware: caravan 0.1.0rc3 examples/lora32
toolchain: esp-idf v5.x.y, esp-tflite-micro 1.x.y
model: picket-mlp 0.2.0
windows: 16
agreed: 16
max_score_diff_steps: 1
arena_used_bytes: 9876 (measured)
--- end ---
```

- Values in this example are placeholders and not measurements.
- `agree` becomes `DISAGREE` when the decisions differ.
- A score more than one step away is flagged `over_one_step` on its line.
- The record block is copied verbatim into `docs/board-runs/<date>-lora32.md`. The owner adds the
  date and the printed revision label.

**Failure lines.** In both cases the firmware halts and repeats the line every five seconds, so a
late-opened monitor still sees it.

```
error: arena too small (kArenaBytes=4096); raise kArenaBytes in src/main.cc
error: input <name> does not match test_windows.h (type or size); re-export and copy model/ again
```

## OLED (128×64, 21 columns × 8 lines of 5×7 text)

While running, one screen per window, held for 1.5 s:

```
picket-mlp 0.2.0
window  3/16
board : dos
host  : dos
expect: dos
AGREE  diff 0 steps
arena 9876 B meas.
agreed so far 3/3
```

At the end, the summary stays on screen:

```
picket-mlp 0.2.0
DONE 16 windows
agreed 16/16
max diff 1 step
arena 9876 B meas.

details: serial
115200 baud
```

**Rules for both channels:**
- Labels are cut to fit the screen. The serial line always carries them in full.
- The OLED never shows a number the serial port does not.
- No timing figure appears on either channel (FR-006).
- `meas.` / `measured` travels with the arena figure everywhere it is shown (Principle IV).
