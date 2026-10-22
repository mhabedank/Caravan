"""Reading and running an exported model — the half of the pipeline that needs no training.

Behind the ``verify`` extra, which carries a model runtime and no training framework, and which
installs on every Python this project supports. Nothing in the core imports this package; a stage
loads it by name when it runs.

Why it is separate from ``convert`` at all: converting needs the training framework and therefore
Python 3.13, while every stage after quantization — analysis, emulated verification, the benchmark,
the card — only ever *reads* an exported model. Measured on 2026-10-22: 114 MiB and 8 packages
here, against 1,971 MiB and 41 for the conversion half. Four stages inherit the cheaper one.
"""
