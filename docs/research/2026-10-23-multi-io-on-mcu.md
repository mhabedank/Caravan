# Several input or output tensors on microcontrollers — 2026-10-23

Status: one focused research round, run to answer the Principle X question in spec 006 (several
inputs and outputs). One research agent checked each claim against the primary source it names,
fetched directly rather than from search snippets. The claims were not put to a vote as in the
deep-research runs. Anything it could not check is listed under "Unverified".

The question: is there a **documented application class**, as Principle X in constitution 3.0.0
defines it, for models with several input tensors or several output tensors? That means a use shown
to run on microcontroller-class hardware, with a public dataset or benchmark, recorded with
sources. Several tensors means separate tensors in the converted model, not channels concatenated
into one.

## Verdict

- **Several inputs: no documented application for the multi-branch pattern.** The question was
  whether any microcontroller model with public data takes several input tensors for sensor fusion,
  human activity recognition (HAR), CAN or battery estimation. None was found. Every
  microcontroller sensor-fusion system checked either concatenates the channels into one input or
  runs two separate models. The only multi-input model verified on microcontroller-class hardware
  follows a different pattern: a stateful recurrent network that takes its recurrent state as
  extra inputs (RNNoise, below).
- **Several outputs: there is a documented application class, but only for vision detection.**
  ST's `st_yoloxn` person detector has three output tensors and fits an STM32H7 board. Its input
  is an image and its outputs are box grids, which Caravan does not build. For a series input with
  several class heads on a microcontroller, nothing was found.

## Several inputs

| Application | Tensors | Hardware and figures | Data and licence | Series → class? |
|---|---|---|---|---|
| RNNoise noise suppression (Arm ML-Zoo, int8, TFLM) | **4 inputs**: features (1,1,42) and three GRU states (1,24), (1,48), (1,96). **5 outputs**: three states, gains (1,1,22), VAD probability (1,1,1). The evaluation kit feeds the state outputs back into the inputs (`m_gruStateMap = {{0, 3}, {2, 2}, {3, 1}}`). | Corstone-300 FVP / MPS3 FPGA (Cortex-M55 + Ethos-U55): "NPU TOTAL cycles: 104514" per inference; model 113,472 B. No CPU-only RAM, flash or latency figures. | Edinburgh DataShare 10283/2791, "Creative Commons Attribution 4.0 International Public License"; model Apache-2.0 | Partly: a series of features plus state in; gains and a probability out |

Not usable as justification:
- **Kitchen HAR with several wearable sensors** (arXiv 2409.06341) runs on nRF52840, i.MX RT1062,
  STM32L4S5 and STM32F767, but with **one concatenated input**: "the data fusion concatenating
  channels as input were selected to build a neural network running on the MCU".
- **Livestock multimodal TinyML** (arXiv 2504.11467, Coral Dev Board Micro) uses **two separate
  models**, joined by decision-level fusion through a label lookup table.
- **Dual-input battery SOC network** (PMC9457470) does have two inputs: a voltage and current
  series, plus a state-of-health scalar. But it has no hardware deployment, the dataset has no
  stated licence, and the output is a regression value.
- **Joint SOC and SOH, and keyword spotting combined with speaker verification** (arXiv
  2206.13708): no microcontroller deployment found.
- **TinyM²Net, audio and image** (arXiv 2202.04303): Raspberry Pi 4 and FPGA, not a
  microcontroller. Search result only, not fetched.
- **CAN intrusion detection**: no microcontroller result found with separate inputs for the
  identifier and the payload.

## Several outputs

| Application | Tensors | Hardware and figures | Data and licence | Series → class? |
|---|---|---|---|---|
| `st_yoloxn` person detection (STM32 model zoo) | Parsed from `st_yoloxn_d033_w025_192_int8.tflite`: input `[1,192,192,3]` uint8; **3 outputs** `[1,12,12,6]`, `[1,24,24,6]`, `[1,6,6,6]` float32 | STM32H747I-DISCO, Cortex-M7 at 400 MHz, 192×192: 350.27 ms. On STM32H7: activations 184.92 KiB, RAM 197.46 KiB, flash 999.56 KiB (STEdgeAI 4.0.0) | COCO 2017 person: annotations CC BY 4.0; images under the Flickr Terms of Use (**not** CC BY). The pretrained weights are under ST SLA0044, which is not an open licence | No: image → box grids |
| RNNoise (as above) | 5 outputs | as above | as above | Partly |
| Arm evaluation kit, YOLO Fastest (face) | two outputs (`GetOutputTensor(0)`, `GetOutputTensor(1)`) | Corstone-300/310 FVP / MPS3 FPGA; figures not checked | not checked | No |

Not usable: ST SSD MobileNet v1/v2 have two outputs, but the STM32H7 is marked unsupported in
their README. `st_yololcv1`, `yolov2t`, `yolov8n` and `st_yolodv2milli` have one output each.

## What this means for spec 006

- Principle X does **not** cover a multi-branch classifier with several **series** inputs and
  several **class** outputs. No microcontroller application with public data was found for it.
- What is documented falls into two patterns:
  1. **Several outputs for detection**: image input, box-grid outputs, H7 class.
  2. **Recurrent state as extra inputs and outputs**: RNNoise, Cortex-M55, simulator or FPGA only.

  Both need input or output kinds that Caravan does not have yet.
- The declaration form can still be a list (spec 006, FR-007). That costs nothing now and keeps a
  second input or output from being a breaking change later.

## Unverified

- RNNoise on a physical Cortex-M board with RAM, flash and latency figures: not found.
- The RNNoise `.tflite` binary could not be downloaded (Git LFS refused). Its tensor layout comes
  from two independent primary sources: the ML-Zoo README and the evaluation kit's C++ code. The
  kit pins the model by sha256 `9c582545…`, which matches the LFS pointer.
- MLPerf Tiny, the TFLM examples and Edge Impulse were not checked file by file for multi-head
  models.
- The time-series models of the ST zoo (HAR and others) were not checked for their number of
  outputs.

## Sources

1. Arm ML-Zoo, RNNoise int8 README —
   https://github.com/ARM-software/ML-zoo/blob/master/models/noise_suppression/RNNoise/tflite_int8/README.md
2. Arm ML Embedded Evaluation Kit, `source/lib/mlek/fwk/tflm/RNNoiseModel.{hpp,cc}`,
   `source/app/use_case/noise_reduction/src/UseCaseHandler.cc`,
   `source/app/use_case/object_detection/src/UseCaseHandler.cc`,
   `resources/use_case_resources.json` —
   https://gitlab.arm.com/artificial-intelligence/ethos-u/ml-embedded-evaluation-kit
3. Evaluation kit, noise reduction documentation —
   https://gitlab.arm.com/artificial-intelligence/ethos-u/ml-embedded-evaluation-kit/-/raw/main/docs/use_cases/noise_reduction.md
4. Edinburgh DataShare, noisy speech database — https://datashare.ed.ac.uk/handle/10283/2791
5. STM32 model zoo, object detection READMEs and the `st_yoloxn` model file —
   https://github.com/STMicroelectronics/stm32ai-modelzoo/tree/main/object_detection
6. STM32 model zoo, object detection licence table (SLA0044) —
   https://github.com/STMicroelectronics/stm32ai-modelzoo/blob/main/object_detection/LICENSE.md
7. COCO terms of use — https://cocodataset.org/dataset/termsofuse.htm
8. Kitchen HAR — https://arxiv.org/pdf/2409.06341
9. Livestock multimodal TinyML — https://arxiv.org/pdf/2504.11467
10. Dual-input SOC network — https://pmc.ncbi.nlm.nih.gov/articles/PMC9457470/
11. TinyM²Net — https://arxiv.org/abs/2202.04303 (search result only)
12. Personalised keyword spotting by multi-task learning — https://arxiv.org/pdf/2206.13708
    (search result only)
