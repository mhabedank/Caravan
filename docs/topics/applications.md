# Applications

:::{admonition} You will learn
:class: learn
- which kinds of problem Caravan serves today, and with which template;
- how to choose between `mlp`, `conv1d`, `conv2d` and `autoencoder` from the shape of your data;
- what the reference models cost when a template expresses them;
- what is not served yet, and why.
:::

Which {term}`template` serves which problem. The classes are the applications shown to run on
microcontrollers in the research note of 2026-10-23, Part A
([on GitHub](https://github.com/mhabedank/Caravan/blob/main/docs/research/2026-10-23-mcu-ml-landscape.md)).
Caravan grows by these classes and by named models (constitution, Principle X), so this page is also
the record of what is not served yet, and why.

Nine of the twelve are served.

## Served

| Application | What the data looks like to Caravan | Output | Template | Example |
|---|---|---|---|---|
| Activity recognition, hand posture | a window of IMU readings: rows × channels | `category` | `conv1d`, `mlp` | `pace-cnn` in the zoo |
| Arc fault detection | a window of current readings | `category` or `binary` | `conv1d` | — |
| Battery state of charge | voltage, current and temperature over a window | `number` | `mlp`, `conv1d` | — |
| CAN intrusion detection | one row per frame, a window of frames | `category` | `mlp`, `conv1d` | [`picket-mlp.yaml`](https://github.com/mhabedank/Caravan/blob/main/examples/picket-mlp.yaml) |
| ECG classification, one label per window | 1–12 leads over a window | `category` | `conv1d` | — |
| Machine anomaly from sound or vibration | feature frames, one row per frame (5 × 40 log-mel for `hum-fan`, 5 × 128 for MLPerf Tiny) | `anomaly` | `autoencoder` | [`anomaly-autoencoder.yaml`](https://github.com/mhabedank/Caravan/blob/main/examples/anomaly-autoencoder.yaml) |
| Keyword spotting | MFCC frames, one row per frame (49 × 10 in MLPerf Tiny) | `category` | `conv2d` | [`frames-conv2d.yaml`](https://github.com/mhabedank/Caravan/blob/main/examples/frames-conv2d.yaml) |
| Person present (Visual Wake Words) | an image, 96 × 96 | `binary` or `category` | `conv2d` with an `image` input | [`images-conv2d.yaml`](https://github.com/mhabedank/Caravan/blob/main/examples/images-conv2d.yaml) |
| Image classification | an image, 32 × 32 | `category` | `conv2d` with an `image` input | as above |

### How to choose

- **Rows that are moments in time, columns that are different sensors:** `conv1d`. The columns are
  channels; the convolution runs along time.
- **Rows that are frames, columns that are neighbouring frequencies:** `conv2d`. A pattern has
  extent along both, and the convolution runs along both. Every input column becomes a column of
  the plane, so a `category` input's one-hot or embedding channels sit beside the others as if they
  were neighbouring frequencies; a convolution reads meaning into that neighbourhood which is not
  there. Give `conv2d` number columns that really are neighbours, and leave categories to `conv1d`
  or `mlp`.
- **No temporal pattern worth convolving, or very small boards:** `mlp`.
- **Faults are rare and varied, normal data is plentiful:** `autoencoder` with an `anomaly` output
  ({mf}`output_features[].type`).
  It learns from normal windows alone; the column telling normal from abnormal is still needed,
  because the gate measures how well the score separates them.
- **Images:** `conv2d` with one `image` input. The device passes the camera's 8-bit pixels at the
  declared size; cropping and binning to that size is the camera's or the firmware's job.

### What the references cost

Measured on 2026-10-29 by building and converting. Parameter counts are
the template's; sizes and floors are of the int8 model and are `estimated`, not a claim that a board
holds them — the working memory a board needs is larger than the floor and is measured on the
board.

| Reference | As this template expresses it | Parameters | Notes |
|---|---|---|---|
| `hum-fan`, machine-sound anomaly | `autoencoder`, encoder [64, 64], code 8, at 5 × 40 | 35,280 | the zoo's hand-built model, exactly |
| MLPerf Tiny keyword spotting, DS-CNN (a depthwise-separable convolutional neural network) | `conv2d`, a (10, 4) block of 64 filters at stride 2 and four separable blocks of 64, at 49 × 10 | 24,908 | 43,048 bytes int8; every operator accelerated on CMSIS-NN and ESP-NN |
| MLPerf Tiny Visual Wake Words, MobileNetV1 at width 0.25 | `conv2d`, a 3 × 3 block of 8 at stride 2 and thirteen separable blocks, at 96 × 96 × 3 | 221,794 | Keras counts 219,058 without convolution biases; the template keeps them, and they fold away at conversion |

The research note cites 38.6K parameters for the keyword-spotting DS-CNN. The MLPerf code builds
24,908.

## Not served yet

| Application | What it would need | Why it is not built |
|---|---|---|
| ECG with several labels at once | a multi-label output type | an output type, not a template; no named model asks for it yet |
| Object detection | an image input (now there) and a grid or box output | the output kind, and boards with more memory than the built-in ones; detection references run on Cortex-M7 or with an NPU |
| Pose, segmentation, depth, face | dense outputs with several heads | microcontrollers with an NPU; no board for them |
| Audio events with a signal output, noise suppression | a signal output | an output kind, and M55-class hardware with an NPU |

### Considered and not built

- **A recurrent template (LSTM).** Battery health and CAN intrusion detection have recurrent models
  that run on microcontrollers (8,961 and 6,272 parameters, on an ST SPC58). Both classes are
  served by the templates above, the ESP32's accelerated library has no recurrent kernel, and no
  named model needs one. Recorded on the [roadmap](../roadmap.md).
- **Feature extraction inside Caravan** (MFCC, log-mel, spectra). Data arrives as frames. Where
  that step should live — in the model, in generated C, or outside Caravan — is still open.

:::{seealso}
{mf}`model.template` and {mf}`model.params` for every template's parameters,
{mf}`input_features[].type` for the `image` input, and [Templates](templates.md) for `mlp` and
`conv1d` in depth.
:::
