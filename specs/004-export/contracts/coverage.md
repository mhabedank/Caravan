# Contract: Accelerated Kernel Coverage

**Feature**: 004 · **Date**: 2026-10-22

A board description says `accel: cmsis-nn`. That sentence is about the build, not about the model:
acceleration is chosen per operator, and an operator with no accelerated kernel falls back to the
reference implementation without announcing it. Principle VII requires the export to record which
side of that line each operator falls on. This is what that record promises and, more importantly,
what it does not.

## The claim, stated exactly

For a (target, operator) pair, the record states:

> the accelerated library this board declares **does** / **does not** supply a kernel for this
> operator, according to `<source>`, read on `<date>`.

That is all. It does not say the kernel will be selected, which depends on operand shapes and build
flags, and it does not say anything will be faster. Those are claims the toolchain settles, and this
stage has no toolchain (FR-023).

## Where the answer comes from

A data file per library under `caravan/targets/kernels/`, in the same spirit as the board
descriptions: data, with its source and its date, not code.

```yaml
library: cmsis-nn
runtime: tflm
source: "tensorflow/lite/micro/kernels/cmsis_nn/ in tensorflow/tflite-micro"
read_on: 2026-10-22
operators:
  FULLY_CONNECTED: fully_connected.cc
  SOFTMAX: softmax.cc
  ADD: add.cc
  MUL: mul.cc
  CONV_2D: conv.cc
  DEPTHWISE_CONV_2D: depthwise_conv.cc
  AVERAGE_POOL_2D: pooling.cc
  MAX_POOL_2D: pooling.cc
  PAD: pad.cc
  TRANSPOSE: transpose.cc
  TRANSPOSE_CONV: transpose_conv.cc
unmapped: [batch_matmul.cc, maximum_minimum.cc, svdf.cc, unidirectional_sequence_lstm.cc]
```

`unmapped` is the honest half. One kernel file can register several operators — `pooling.cc`
registers both pooling operators, checked in the source — so an entry is only written once it has
been read, and a file whose operators no implemented template can produce stays listed as unmapped
rather than guessed at. An operator that is in neither `operators` nor a mapped file is recorded as
a fallback, which is correct: a missing accelerated kernel *is* a fallback.

## The three outcomes, and they are three

| Situation | What is recorded |
|---|---|
| The board's library supplies a kernel | accelerated, with the source file as evidence |
| The board's library has no kernel for it | falls back to the reference implementation |
| The board declares no library at all | a stated verdict: nothing is accelerated here |

And one refusal: a board declaring a library for which there is **no data file** refuses the run
(`X-5`). "Unknown" printed next to an operator is the silence Principle IV exists against, and a
new accelerated library is a data file somebody has to read a source for — which is exactly the
cost Principle VII intends it to have.

## On the pilot model, today

| Operator | `cmsis-nn` (s32k144, stm32h743) | `esp-nn` (esp32) |
|---|---|---|
| `RESHAPE` | falls back | falls back |
| `FULLY_CONNECTED` | accelerated | accelerated |
| `SOFTMAX` | accelerated | accelerated |

Two of three on every board, with the same operator falling back everywhere. A non-trivial answer
on the first model the framework ever exports, which is the argument for recording it rather than
assuming the `accel` field means the whole model is accelerated.
