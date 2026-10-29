---
description: What you need for Caravan, how to install it, and the one command that proves it works.
---

# Installation

## What you need

- **A table of your own** — a `.csv`, `.tsv` or `.txt` file with a header row: sensor readings,
  log lines, counters. Part 1 of the tutorial uses the example's data; part 2 uses yours.
- **Python 3.13.** Training needs exactly this version, because the training framework publishes
  nothing newer. On 3.14 and 3.15, {cmd}`caravan validate` and {cmd}`caravan render` work, and
  {cmd}`caravan export` stops with a message naming the version it needs, before it writes
  anything.
- **A 2 GB download, once.** Nearly all of it is the training framework; Caravan itself is 7 MB.
- **Linux, macOS, or WSL on Windows.** The commands are written for a POSIX shell.
- **A microcontroller from part 3 on.** Parts 1 and 2 need nothing but your computer.

You do not bring a model architecture, a training loop, a quantization script or a conversion step.
Those are what Caravan is.

## Install

Caravan is installed from its GitHub release, into a virtual environment of its own. The download
is the long wait: start it and read on.

```bash
# step: install
python3.13 -m venv caravan-try
. caravan-try/bin/activate
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc4/caravan_ml-0.1.0rc4-py3-none-any.whl"
caravan --version
```

The `.` line activates the environment, and every later command of the tutorial runs inside it. If
`pip` reports that your Python is too old, the environment is not active: run `deactivate` and the
`.` line again.

## Check it

The last line of the block is the check. It prints:

```text
caravan-ml 0.1.0rc4
```

That is Caravan installed, with the training and verification parts. Go on to
[part 1 of the tutorial](tutorial01.md).
