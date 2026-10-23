# ML on microcontrollers and small SoCs: applications, sensors, data

Date: 2026-10-23 · Status: research note, input to the manifest's input/output model and to the
zoo's resource index. Parts D and E (sensors, geo data) are an **interim state**, recorded so the
work is not lost; they are marked as such.

The scope is domain-agnostic. Mobility is the zoo's use, not Caravan's boundary.

**Method.** A deep-research workflow (106 agents) extracted 119 claims from 24 sources and put 25
of them through three adversarial votes each: 22 confirmed, 3 refuted. The budget stopped there,
so the licence of most datasets and the whole of Part C were checked afterwards by hand, against
the original source: the Zenodo REST API, the README inside the UCI HAR archive, the dataset
pages, and the sensor datasheets. The workflow's verified claims, with votes and evidence, are in
[`2026-10-23-mcu-ml-landscape.claims.json`](2026-10-23-mcu-ml-landscape.claims.json). Every
claim below has a source at the bottom; where a source is secondary or a claim could not be
confirmed, that is stated next to it.

**Summary.**

- The applications fall into three modality families — image, audio, time series — plus event
  streams such as the CAN bus. The outputs are more varied than "a class": values,
  reconstructions, grids, signals and several heads at once all occur.
- A benchmark dataset is not a usable dataset. Of the four MLPerf Tiny v0.5 tasks, only keyword
  spotting rests on data that is cleanly usable commercially.
- The zoo's resource index holds essentially no data of this kind, and has no fields to judge it.
- Sensors deliver very different things: fixed-rate multichannel counts, 1-bit bitstreams, 2D
  frames, compressed frames, variable-length point lists, slow scans, and event streams. Several
  need host-side computation before a model can see them.

---

## A. Applications

| Application | Input | Output | Reference size (int8) | Hardware |
|---|---|---|---|---|
| Keyword spotting | audio 1 s / 16 kHz → MFCC 49×10 | class (12) | DS-CNN, 38.6K parameters, 52.5 KB | Cortex-M4F |
| Audio events, noise suppression | audio | class, or a **signal** | RNNoise, MicroNet | M55 + Ethos-U55 |
| Machine anomaly (acoustic) | audio features 5×128 | **reconstruction** → anomaly score (AUC 0.85) | FC autoencoder, 270 KB | M4F |
| Person present (Visual Wake Words) | image 96×96 | class (2) | MobileNetV1, 325 KB; MCUNetV2 at ≤ 32 kB SRAM | M4/M7 |
| Image classification | image 32×32 | class (10) | ResNet, 96 KB | M4F |
| Object detection | image 96–128 px | **grid** (FOMO 12×12) or boxes | 0.47–1.2M parameters, 53–511 kB peak SRAM; µYOLO < 800 KB flash, < 350 KB RAM | M7 (e.g. STM32H743), MCUs with NPU |
| Pose, segmentation, depth, re-ID, face | image | dense outputs, several heads | in the ST model zoo for the STM32N6 (M55 + NPU) | MCU with NPU |
| Activity (HAR), hand posture | IMU, ToF | class | survey class "TinyML ≤ 250 KB" | M0–M4 |
| Arc fault detection (AFCI) | current time series | class | ST model zoo | M4/M7 |
| ECG | 1–12 leads, 100–500 Hz | class, often **multi-label** | ≤ 250 KB | M4 |
| Battery state of charge | voltage, current, temperature | **value** | 6.36 KB flash on an STM32F413 (abstract only) | M4 |
| CAN intrusion detection | **event sequence** (timestamp, ID, DLC, 8 bytes) or signal time series | class / attack type | CNN, LSTM, MLP; no verified MCU figures found | — |

Reference points: MLPerf Tiny v0.5, the STM32 model zoo (v4.0 online, v4.1 on GitHub), the Arm
ML Embedded Evaluation Kit. MLPerf Tiny has since reached v1.3 with a streaming wake-word task,
so the four v0.5 tasks are no longer the whole suite. MLPerf v0.5 does not measure pre- and
post-processing such as feature extraction. NXP eIQ, Espressif and Silicon Labs are not covered.

**Where a small SoC is needed:** high-resolution detection, multi-stage pipelines (detection plus
OCR), anything that needs a Linux stack. An NPU helps only conditionally. On the i.MX 93 the
Ethos-U65 gives 6–11× over the A55 CPU, for int8 models with supported operators. On the i.MX 8M
Plus a TinyYOLOv3 ran **slower** on the NPU than on the CPU (1.18 Hz against 1.99 Hz); the gain
there was CPU load. Both are single case studies on different software stacks.

**Refuted, not to be used:** "under 256 kB SRAM is typical" (1–2), µYOLO's resolution limits as
the MCU/SoC boundary (0–3), and "the Ethos-U65 only accelerates per-tensor int8" (0–3).

## B. Data

| Dataset | Domain, properties | Licence (where checked) | Commercial | Derivatives |
|---|---|---|---|---|
| Speech Commands v2 | KWS, 105,829 utterances | CC BY 4.0 (Google blog) | yes | yes |
| MIMII | machine sound, 8 channels, 16 kHz | CC BY-SA 4.0 (Zenodo API) | yes | yes, share-alike |
| MIMII DUE | machine sound | CC BY-NC-SA 4.0 (Zenodo API) | **no** | NC-SA |
| DCASE 2020 Task 2 dev | machine sound | CC BY-NC-SA 4.0 (Zenodo API) | **no** | NC-SA |
| DCASE 2023 Task 2 dev | machine sound | CC BY 4.0 (Zenodo API) | yes | yes |
| ToyADMOS (MLPerf anomaly) | machine sound | NTT "Software License Agreement for Evaluation" (LICENSE.pdf) | **no** | **prohibited** |
| Visual Wake Words / COCO | image | images under Flickr terms per image; annotation licence not checked at the original | unclear | unclear |
| CIFAR-10 | 60,000 images, 32×32 | **no licence**, a citation request only | unclear | unclear |
| UCI HAR | smartphone IMU | landing page: CC BY 4.0 — README in the archive: *"Any commercial use is prohibited."* | **no** | unclear |
| WISDM (UCI 507) | phone and watch, accel + gyro, 20 Hz, 51 subjects, 18 activities | CC BY 4.0 (landing page only) | yes\* | yes\* |
| PAMAP2 (UCI 231) | 3 IMUs at 100 Hz + heart rate ~9 Hz, 9 subjects | CC BY 4.0 (landing page only) | yes\* | yes\* |
| MIT-BIH Arrhythmia | 48 × 30 min, 360 Hz, 2 channels | ODC-By 1.0, open | yes | yes |
| PTB-XL | 21,799 × 10 s, 12 leads, 500/100 Hz, multi-label | CC BY 4.0, open | yes | yes |
| CWRU bearing data | vibration | **no licence** on the pages | unclear | unclear |
| NASA PCoE battery | Li-ion ageing | **no licence**, citation request; one set currently not downloadable | unclear | unclear |
| CALCE battery | cells, dynamic profiles | "open access", **no licence** | unclear | unclear |
| ROAD (ORNL) | CAN, candump + signal CSV, 3.5 h, one vehicle | CC BY 4.0 (Zenodo API) | yes | yes |
| HCRL Car-Hacking | CAN: timestamp, ID, DLC, DATA[0–7], flag | "for academic purposes", no licence | **no**/unclear | unclear |
| Driver Behavior (Mendeley) | smartphone sensors | CC BY 4.0 (page label; extracted, not re-checked) | yes? | yes? |

\* Landing page only. UCI HAR shows that a landing page and the archive can contradict each other.

What follows:

1. **Benchmark is not usability.** Of MLPerf Tiny's four tasks only KWS is cleanly usable.
2. **Licences belong to a version.** DCASE Task 2 is NC in 2020 and CC BY in 2023; MIMII is CC
   BY-SA, MIMII DUE is NC-SA.
3. **Many central engineering datasets carry no licence at all:** CWRU, NASA, CALCE, CIFAR.
4. **The ROAD authors advise against HCRL**, partly because its ambient and attack data come in
   different formats.
5. **Datasets ship their own splits**: speaker-disjoint for Speech Commands, patient-wise folds
   for PTB-XL. Splitting windows at random ignores the split that prevents leakage.

**Aggregators.**

- **Zenodo**: REST API with `license.id` (checked). Already a harvester of the index.
- **Hugging Face**: `/api/datasets/{id}/croissant` returns licence, fields and splits (checked on
  two datasets; the licence is the dataset card's tag, correctly `unknown` for CIFAR-10). Already
  a harvester, but it supplies only 101 entries.
- **UCI**: `ucimlrepo` returns good metadata (task, instances, feature types) but **no licence
  field**.
- **PhysioNet**: each database page names its licence and access class (open or credentialed).
- **Papers with Code**: **shut down in July 2025**, redirects to Hugging Face Trending Papers; its
  dataset catalogue is gone (secondary sources).
- **Edge Impulse**: public projects can be listed without authentication; licences vary per
  project; bulk download is not documented.
- **Kaggle, OpenML**: offer Croissant export (according to the Croissant README, not checked).
- **Not checked:** IEEE DataPort, TFDS, MLCommons, the DCASE pages.

## C. The gap in the zoo's resource index

Counted in `mobility-model-zoo-catalog` at `d81c642`: 7,840 entries. `structured_data` has 3,177
(`table` 1,580, `gtfs` 996, `geodata` 454, `spreadsheet` 109, `gtfs_rt` 33). **`sensor_data`
occurs 0 times, `time_series` twice**, both a "PublicTransportAI" table dataset from Hugging Face.
The 139 `field_recording` entries are mostly Wikimedia pronunciation clips, not measurements.
None of the datasets in Part B is in the index.

| Field | Croissant (incl. RAI) | DCAT / schema.org | Conclusion |
|---|---|---|---|
| Sensor type, placement, device | — (RAI defines no sensor property) | — | own field |
| Channels (names, units) | partly, through `recordSet` field structure | — | take from Croissant, add units |
| Sampling rate, or event-based | — | `dcat:temporalResolution` (a duration) | the DCAT field fits regular series |
| Extent (hours, samples, subjects) | — | — | own field |
| Label scheme and granularity (per window, event or recording; multi-label) | prose only (`rai:dataAnnotationProtocol`, `rai:annotationsPerItem`) | — | own field |
| Shipped splits | yes, as `recordSet` | — | take over |
| Real, synthetic or simulated | — (RAI names it only as a topic) | — | own field |
| Personal data | `rai:personalSensitiveInformation` | — | the index already has `personal_data` |

Proposal for the index: a small `content.sensor` block, analogous to `content.transcripts` —
sensors (type, placement, channels, unit, rate or "event-based"), extent, label (scheme,
granularity, classes), splits, origin — filled from Croissant where the source provides it. Two
rules with it: licence evidence points at the licence text **shipped with the data**, not the
landing page (the lesson of UCI HAR); and the licence is recorded per version.

Harvesters, by value: (1) switch Hugging Face to the Croissant endpoint; (2) extend Zenodo's
search terms to sensor, IMU, CAN, vibration, battery; (3) PhysioNet, excluding credentialed
databases; (4) UCI, metadata from `ucimlrepo`, licence from the archive; (5) Kaggle and OpenML
through Croissant.

**Open decision for the owner:** the index tests for mobility relevance (its FR-003). For the zoo
that fits, and only CAN, driving IMU, battery, road condition and traffic sound would enter. A
domain-agnostic index of ML-on-MCU data would be a different tool with a different scope.

## D. Sensors and what they output (interim)

| Sensor class | Example part | What the part delivers | Rate | Host work before a model sees it |
|---|---|---|---|---|
| IMU | Bosch BMI270 | 3-axis accel + 3-axis gyro, 16-bit counts; scale set by full-scale range (±2…16 g, ±125…2000 dps) | accel 12.5 Hz–1.6 kHz, gyro 25 Hz–6.4 kHz | counts → physical units; on-chip step counter and gesture/activity features exist |
| MEMS microphone (PDM) | ST MP45DT02 (app note); Nordic PDM | **1-bit stream** at 1–3.25 MHz | 16 kHz PCM after decimation by 64 or 80 | decimation filter (CIC/FIR) to 16-bit PCM, then usually MFCC or a spectrogram |
| Camera, always-on | Himax HM01B0 | 320×320 monochrome; 320×240 window; 2×2 binning; interface 1/4/8-bit (8-bit disputed by one vendor) | up to 60 fps window, 120 fps binned | crop/scale to the model's input |
| Camera, general | OmniVision OV2640 (ESP32 driver) | YUV422/420, RGB565/555, **JPEG**, raw RGB 8/10-bit; up to 1600×1200 | JPEG faster; raw above QVGA needs PSRAM | JPEG must be decoded; colour conversion; resize |
| Multizone ToF | ST VL53L5CX | distance for 4×4 or 8×8 zones, up to 4 m, 63° FoV | 15 Hz or 60 Hz (source inconsistent per mode) | a small 2D frame; per-zone status not checked |
| Thermal array | Melexis MLX90640 | 32×24 = 768 pixels, **raw IR, Ta and VDD values**; FoV 55°×35° or 110°×75° | 0.5–64 Hz | **temperatures are computed on the host** from EEPROM calibration parameters |
| FMCW radar, raw | Infineon BGT60TR13C | 1 TX, 3 RX; three 12-bit ADCs up to 4 MSps; FIFO 8192 × 24 bit | chirps and frames, configurable | **all radar processing on the host**: FFTs to range/Doppler, then features |
| FMCW radar, processed | TI IWR6843 | TLV packets; detected points with range, Doppler, x, y, z | per frame | **a variable number of points per frame** (forum-level sources) |
| Gas / environment | Bosch BME688 | temperature, pressure, humidity, gas scan; IAQ, bVOC/CO₂ equivalents | a standard gas scan takes **10.8 s** | heater-profile scans; classification trained in BME AI-Studio |
| GNSS | u-blox (UBX-NAV-PVT) | lat/lon int32 in 1e-7°, height mm, ground speed mm/s, heading 1e-5°, accuracy estimates | navigation rate not checked for M10 | see Part E |
| CAN bus | (any controller) | frames: timestamp, ID, DLC, up to 8 data bytes (CAN FD: more) | **event-driven**, irregular | decode, or translate to signals |

What the outputs are, as kinds of input a manifest must be able to describe:

- **Fixed-rate multichannel series** in counts with a scale (IMU, current, ECG front ends).
- **A bitstream that needs DSP first** (PDM audio).
- **2D frames** (cameras, thermal arrays, 8×8 ToF), sometimes **compressed** (JPEG).
- **Variable-length sets** (radar point clouds; Wi-Fi and cell scans in Part E).
- **Event streams** (CAN).
- **Slow, multi-step scans** (gas).
- **Values that are only meaningful after host-side calibration** (thermal temperatures, radar
  spectra).

Not checked: PPG (MAX30102, page returned 503), ECG front ends, current sensing, magnetometer,
barometer, load cells, event cameras.

## E. Geo data (interim)

**What GNSS delivers.** UBX-NAV-PVT carries latitude and longitude as int32 in units of 1e-7°,
height in mm, ground speed in mm/s, heading of motion in 1e-5°, and accuracy estimates for
position, speed and heading (ROS and Zephyr message definitions derived from the u-blox protocol;
the u-blox page itself failed to load).

**Datasets.**

| Dataset | Content | Licence | Commercial |
|---|---|---|---|
| GeoLife (Microsoft Research) | 17,621 trajectories, 1–5 s or 5–10 m between points for 91 %; transport-mode labels from 69 users (walk, bike, bus, car, subway, train, airplane, boat, run, motorcycle); PLT text format | "Microsoft Research License Agreement — Non-Commercial Use Only" (in the user guide) | **no** |
| SHL (Sussex-Huawei Locomotion) | 2,812 h labelled, 4 phones at body positions, 3 participants, 8 modes, 28 context labels; plain text, timestamp in ms, includes GPS, Wi-Fi and cell scans | "made publicly available solely for non-profit and research purposes" (download page) | **no** |

**Applications.** Transport-mode detection is the common one. The pattern in the literature is
IMU-led detection with GPS used sparingly, because GPS is power-hungry; one LSTM study reached
96.9 % on four modes from accelerometer, gyroscope, magnetometer and barometer without GPS. No
source documented a complete MCU pipeline combining GPS, IMU and on-device inference.

**A quantisation consequence (own arithmetic, not from a source).** An int8 tensor has 256 levels.
Absolute latitude over ±90° quantised per tensor gives a step of 180/256 ≈ 0.70°, about 78 km.
Absolute coordinates are therefore useless as int8 model inputs; they must become relative
positions (deltas, local east/north) or derived quantities (speed, heading change) before
quantisation. The same holds for any input with a large offset and a small useful variation.

**In the index.** 454 `geodata`, 996 `gtfs` and 33 `gtfs_rt` entries exist. Their content was not
inspected: whether any of them is a trajectory dataset rather than maps or timetables is open. A
text search found 3 entries mentioning trajectory or GPS-trace terms, also not inspected.

## F. What this means for Caravan

- **Input kinds**: regular series (rates from 20 Hz to 16 kHz), event sequences (CAN), images,
  precomputed features, scalars, and variable-length sets. TFLM tensors are planned ahead of time,
  so variable-length inputs need a fixed form (padding, voxels, top-k); whether TFLM rejects
  dynamic shapes outright was searched for and not confirmed.
- **Output kinds**: class (single or **multi-label**), value, reconstruction with an anomaly
  score, grid, signal, several heads. TFLM supports several inputs and outputs natively
  (`inputs_size()`, `input(i)`, `outputs_size()`, `output(i)` in `micro_interpreter.h`).
- **Shipped splits** must be usable instead of random splits of windows.
- **Preprocessing** (PDM decimation, MFCC, radar FFT, thermal calibration, JPEG decode) decides
  what the model sees. Where it lives — in the graph, in generated C, or outside Caravan — is an
  open design question. MLPerf v0.5 does not measure it.
- **Input scaling** is part of the interface, not a detail: absolute coordinates and raw counts
  with large offsets do not survive int8.
- **Formats** a reader would meet: CSV/TSV (today), candump, WFDB, MATLAB, WAV, image files with
  labels, Excel, PLT, plain text with variable-length rows.

## Not verified

COCO's annotation licence (the page renders through JavaScript); the archive licences of WISDM
and PAMAP2; the Mendeley driver-behaviour licence (extracted, not re-checked); the 6.36 KB figure
for state of charge (abstract only); sampling rates of CWRU and UCI HAR; the NXP eIQ, Espressif
and Silicon Labs zoos; the APIs of IEEE DataPort, TFDS, MLCommons; MCU figures for CAN intrusion
detection; the VL53L5CX rate per mode; HM01B0 8-bit output; PPG and other sensors listed in D; the
u-blox M10 navigation rate; TFLM's handling of dynamic shapes; what the index's geodata entries
contain.

## Sources

Applications and hardware:
[MLPerf Tiny (arXiv 2106.07597)](https://arxiv.org/pdf/2106.07597) ·
[mlcommons/tiny](https://github.com/mlcommons/tiny) ·
[STM32 model zoo](https://stm32ai.st.com/model-zoo/) ·
[STM32 model zoo on GitHub](https://github.com/STMicroelectronics/stm32ai-modelzoo) ·
[Arm ML Embedded Evaluation Kit](https://gitlab.arm.com/artificial-intelligence/ethos-u/ml-embedded-evaluation-kit) ·
[FOMO, Edge Impulse docs](https://docs.edgeimpulse.com/docs/edge-impulse-studio/learning-blocks/object-detection/fomo-object-detection-for-constrained-devices) ·
[TinyML survey 2403.19076](https://arxiv.org/html/2403.19076v2) ·
[MCUNetV2](https://arxiv.org/abs/2110.15352) ·
[detection survey 2508.08352](https://arxiv.org/pdf/2508.08352) ·
[µYOLO 2408.15865](https://arxiv.org/pdf/2408.15865) (preprint) ·
[TinyML/TinyDL survey 2506.18927](https://arxiv.org/pdf/2506.18927) (secondary) ·
[NXP blog on NPUs](https://nxp.com/company/about-nxp/smarter-world-blog/BL-ML-ACCELERATION-RACE-TO-THE-TOP-AND-BOTTOM) ·
[Linaro, Ethos-U65 on i.MX 93](https://www.linaro.org/blog/direct-kernel-access-to-ethos-u65-npu-on-i-mx9-benchmarks-using-latest-kernel-and-mesa-support/) ·
[RidgeRun, i.MX 8M Plus](https://revistas.tec.ac.cr/index.php/tec_marcha/article/download/6487/6313?inline=1) ·
[state of charge on STM32 (Polimi)](https://re.public.polimi.it/retrieve/223925a8-3bb8-4f1a-a083-e349be2d497d/electronics-13-01964-v2.pdf) ·
[TFLM micro_interpreter.h](https://github.com/tensorflow/tflite-micro/blob/main/tensorflow/lite/micro/micro_interpreter.h)

Datasets:
[Speech Commands (Google)](https://research.google/blog/launching-the-speech-commands-dataset/) ·
[MIMII](https://zenodo.org/records/3384388) ·
[ToyADMOS](https://zenodo.org/records/3351307) and its [LICENSE.pdf](https://zenodo.org/records/3351307/files/LICENSE.pdf) ·
[MIMII DUE](https://zenodo.org/records/4740355) ·
[DCASE 2020 T2](https://zenodo.org/records/3678171) ·
[DCASE 2023 T2](https://zenodo.org/records/7882613) ·
[UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones) ·
[WISDM](https://archive.ics.uci.edu/dataset/507/wisdm+smartphone+and+smartwatch+activity+and+biometrics+dataset) ·
[PAMAP2](https://archive.ics.uci.edu/dataset/231/pamap2+physical+activity+monitoring) ·
[MIT-BIH](https://physionet.org/content/mitdb/1.0.0/) ·
[PTB-XL](https://physionet.org/content/ptb-xl/1.0.3/) ·
[CWRU](https://engineering.case.edu/bearingdatacenter/welcome) ·
[NASA PCoE](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) ·
[CALCE](https://calce.umd.edu/battery-data) ·
[CIFAR](https://cave.cs.toronto.edu/kriz/cifar.html) ·
[COCO benchmark paper 2403.18819](https://arxiv.org/pdf/2403.18819) ·
[ROAD](https://zenodo.org/records/10462796) and its [paper](https://arxiv.org/pdf/2012.14600) ·
[HCRL Car-Hacking](https://ocslab.hksecurity.net/Datasets/car-hacking-dataset) ·
[Mendeley Driver Behavior](https://data.mendeley.com/datasets/9vr83n7z5j/2) ·
[GeoLife user guide](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/User20Guide-1.2.pdf) ·
[SHL dataset](http://www.shl-dataset.org/dataset/) and [download/licence](http://www.shl-dataset.org/download/) ·
[SHL on IEEE DataPort](https://ieee-dataport.org/documents/sussex-huawei-locomotion-and-transportation-dataset)

Sensors:
[Bosch BMI270](https://www.bosch-sensortec.com/products/motion-sensors/imus/bmi270/) ·
[ST AN on PDM decoding](https://www.st.com/resource/en/application_note/dm00040808-pdm-audio-software-decoding-on-stm32-microcontrollers-stmicroelectronics.pdf) ·
[Nordic PDM (nRF52840)](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/pdm.html) ·
[TI PDM decimation (SPRAC51)](https://ti.com/lit/pdf/sprac51) ·
[HM01B0 at SparkFun](https://www.sparkfun.com/himax-cmos-imaging-camera-hm01b0-monochrome.html) ·
[HM01B0 at Arducam](https://www.arducam.com/blog/product/arducam-hm01b0-qvga-cmos-mocochrome-camera-module-for-rp2040-arduino/) ·
[esp32-camera driver](https://components.espressif.com/components/espressif/esp32-camera) ·
[VL53L5CX at SparkFun](https://www.sparkfun.com/products/18642) ·
[MLX90640 datasheet](https://www.melexis.com/-/media/files/documents/datasheets/mlx90640-datasheet-melexis.pdf) ·
[BGT60TR13C datasheet](https://www.infineon.com/dgdl/Infineon-BGT60TR13C-DataSheet-v02_49-EN.pdf?fileId=8ac78c8c7d718a49017d94bac88e5d43) ·
[TI E2E, IWR6843 output](https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/847278/iwr6843aopevm-out-of-box-demo-data-struct) (forum) ·
[Bosch BME688](https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme688/) ·
[UBX-NAV-PVT, ROS](https://docs.ros.org/en/kinetic/api/ublox_msgs/html/msg/NavPVT.html) ·
[UBX-NAV-PVT, Zephyr](https://docs.zephyrproject.org/latest/doxygen/html/structubx__nav__pvt.html) ·
[transport mode detection without GPS](https://research.buaa.edu.cn/en/publications/detecting-transportation-modes-with-low-power-consumption-sensors/) ·
[Sentiance, on-device transport mode](https://sentiance.com/transport-mode-classification-on-device-and-near-real-time) (vendor)

Metadata and aggregators:
[Croissant](https://github.com/mlcommons/croissant) ·
[Croissant RAI](https://docs.mlcommons.org/croissant/docs/croissant-rai-spec.html) ·
[schema.org Dataset](https://schema.org/Dataset) ·
[DCAT 2 (arXiv 2303.08883)](https://arxiv.org/pdf/2303.08883) ·
[ucimlrepo](https://github.com/uci-ml-repo/ucimlrepo) ·
[Edge Impulse public projects API](https://docs.edgeimpulse.com/apis/studio/projects/list-public-projects.md) ·
[Papers with Code sunset (hyper.ai)](https://hyper.ai/en/news/42900) (secondary) ·
[HF forum on the migration](https://discuss.huggingface.co/t/missing-dataset-after-paperswithcode-migration/167174) (forum)
