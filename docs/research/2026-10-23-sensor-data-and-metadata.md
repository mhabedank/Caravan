# Sensor data on microcontrollers: form, delivery, quality, metadata

Date: 2026-10-23 · Status: research note, input to the manifest's input model, to the dataset
contract, and to the zoo's resource index. It continues Part D of
[`2026-10-23-mcu-ml-landscape.md`](2026-10-23-mcu-ml-landscape.md) and takes over from it.

The question: which sensors sit next to microcontrollers and small SoCs, what their data look
like, how the data arrive, in what quality, and which metadata come with them, including the
observability of the device itself. The scope is domain-agnostic.

**Method.** A second deep-research workflow (106 agents) extracted 89 claims and put 25 through
three adversarial votes each: 22 confirmed, 3 refuted. Its verified claims, with votes and
evidence, are in [`2026-10-23-sensor-data-and-metadata.claims.json`](2026-10-23-sensor-data-and-metadata.claims.json).
The verified set covered few sensor classes and none of the standards, so the runtime fields and
the standards were then checked by hand against the defining source text: RFC 8428, the
`common_interfaces` message files of ROS 2, Zephyr's `sensor_data_types.h`, CEVA's
`sh2_SensorValue.h` (BNO08x), ST's VL53L5CX driver header, the `ublox_msgs` NAV-PVT definition,
AOSP's `sensors-base.h`, the Linux `sysfs-bus-iio` ABI, the W3C SSN recommendation, and the
Memfault and ASAM pages. Rows marked **(interim)** come from datasheets read for the landscape
note. The status of every claim is stated next to it.

## Summary

- **Sensors deliver counts, not units.** Physical values exist only once the host applies
  configuration: reference voltage and gain, measurement range, a conversion formula. The
  configuration is therefore part of the data, not a detail of the firmware.
- **The way data arrive varies as much as the data.** There is slow polling with read-once
  buffers, data-ready pins, and FIFO batches behind a watermark interrupt. FIFO formats differ
  even inside one part: one FIFO describes itself, its neighbour carries bare numbers.
- **Time is often reconstructed, not measured.** Common pipelines stamp a batch with host uptime
  and spread it across the samples. Which clock a timestamp came from is a fact the recording
  must carry.
- **Quality has a datasheet vocabulary**, and its figures are typical values at 25 °C, depend on
  the configured range, and are looser for derived quantities than for the raw measurement.
- **Many parts report quality per sample at runtime**: electrode contact, diagnostic flags,
  calibration accuracy, per-zone ranging status, GNSS fix type and accuracy estimates. The
  common pipelines and formats **drop most of it**: Zephyr's decoded format has no accuracy
  field, SenML carries no static metadata, ROS's IMU message has covariances but no model,
  configuration or calibration, and Memfault aggregates hourly integers.
- **For ML this matters measurably.** Differences between devices and small shifts in placement
  degrade activity recognition substantially. The device, its configuration, its placement and
  its timing are minimum metadata for a usable recording.

---

## 1. Sensor classes and what they deliver

| Class | Part | Raw form | To physical units | Timing | Status of the source |
|---|---|---|---|---|---|
| ECG front end | TI ADS1292 | 24-bit two's complement per channel, MSB first; clips at 7FFFFFh / 800000h; each read is preceded by a 24-bit status word (72 bits per read on the ADS1292R) | 1 LSB = VREF / (2²³ − 1); input-referred also ÷ PGA gain. VREF is internal 2.42 V or 4.033 V, or external | periodic, configured data rate | datasheet, 3–0; the PGA term was added from memory by a verifier |
| Current, voltage, power | TI INA228 | 20-bit delta-sigma; shunt ±163.84 mV or ±40.96 mV (bit ADCRANGE); bus 0–85 V | register scaling depends on ADCRANGE | periodic, conversion time configurable | datasheet and product page, 3–0 |
| CO₂, temperature, humidity | Sensirion SCD4x | three unsigned 16-bit words, each followed by an 8-bit CRC | CO₂ ppm = word; T = −45 + 175·w/(2¹⁶−1); RH = 100·w/(2¹⁶−1) | update every 5 s (periodic) or ~30 s (low power); SCD41 also single shot (5 s) | datasheet v1.5, 3–0 |
| IMU, FIFO | Bosch BMI088 | accel FIFO: self-describing frames (7-byte data frame, 1 header byte with type and interrupt tags); gyro FIFO: up to 100 frames of three 16-bit words, no header | range-dependent scale | periodic, FIFO with watermark | application note BST-MIS-AN005 (2018, "preliminary"), 3–0 |
| Precision IMU | ADI ADIS16470 | 16- or 32-bit words; gyro 10 LSB/(°/s) (16-bit), accel 800 LSB/g (16-bit) | fixed scale per format | internal 2000 SPS ± 3 %; decimation; four external sync modes | datasheet via mirror (Rev. A/C), 3–0 and 2–1 |
| IMU with on-chip fusion | CEVA/Hillcrest BNO08x (SH-2) | sensor reports with sequence number, status byte, timestamp in µs, delay | report-specific Q points | per report, configurable | `sh2_SensorValue.h`, checked by hand |
| IMU **(interim)** | Bosch BMI270 | 3-axis accel + gyro, 16-bit counts | full scale ±2…16 g, ±125…2000 dps | accel 12.5 Hz–1.6 kHz, gyro 25 Hz–6.4 kHz | product page |
| MEMS microphone **(interim)** | PDM parts | 1-bit stream at 1–3.25 MHz | decimate (CIC/FIR) to 16-bit PCM | 16 kHz PCM after decimation by 64 or 80 | ST and TI application notes, Nordic docs |
| Camera **(interim)** | Himax HM01B0; OV2640 | 320×320 mono (1/4/8-bit bus, 8-bit disputed); OV2640: YUV, RGB565, JPEG, raw up to 1600×1200 | JPEG must be decoded; colour conversion | frames, up to 60/120 fps (HM01B0) | vendor and driver pages |
| Multizone ToF | ST VL53L5CX | per zone (4×4 or 8×8): `distance_mm` (int16), `range_sigma_mm`, `target_status`, `nb_target_detected`, signal and ambient rate per SPAD, reflectance, motion indicator | distance already in mm | 15 or 60 Hz (source inconsistent per mode) | driver header, checked by hand; rates from a retailer page |
| Thermal array **(interim)** | Melexis MLX90640 | 32×24 raw IR plus Ta and VDD in RAM | temperatures computed on the host from EEPROM calibration | 0.5–64 Hz | datasheet |
| FMCW radar, raw **(interim)** | Infineon BGT60TR13C | 1 TX, 3 RX, three 12-bit ADCs up to 4 MSps, FIFO 8192 × 24 bit | all radar processing on the host | chirps and frames | datasheet |
| FMCW radar, processed **(interim)** | TI IWR6843 | TLV packets with a variable number of detected points (range, Doppler, x, y, z) | as delivered | per frame | forum-level sources |
| Gas **(interim)** | Bosch BME688 | T, p, RH, gas scan; IAQ and equivalents through BSEC | through BSEC | a standard gas scan takes 10.8 s | product page |
| GNSS | u-blox, UBX-NAV-PVT | lat/lon int32 in 1e-7°, height mm, ground speed mm/s, heading 1e-5° | fixed scale | navigation rate not checked | `ublox_msgs` definition, checked by hand |
| Vehicle bus **(interim)** | CAN / CAN FD | frames: timestamp, ID, DLC, data bytes | signals through a DBC: bit position, length, byte order, sign, factor, offset, unit | event-driven | dataset pages, cantools docs (partial) |

Not covered by any checked source: PPG (MAX30102, MAX86150), other ECG front ends (MAX30003),
EDA, load cells (HX711), strain, ultrasonic, LiDAR, event cameras, Grid-EYE, SPS30, ICM-42688,
ST's LSM6DSV machine-learning core.

## 2. How the data arrive

**Three delivery patterns.**

1. **Slow polling.** The SCD4x answers with NACK when no new value exists. A value can be read
   only once, because reading empties the buffer. `get_data_ready_status` tells the host whether
   a value is waiting (the lower 11 bits are 0 when none is).
2. **Data-ready.** The ADIS16470 has a data-ready pin and an internal clock of 2000 SPS with an
   initial accuracy of 3 %.
3. **FIFO batches behind a watermark interrupt.** Zephyr starts a stream once with
   `sensor_stream()`. From then on the stream keeps itself running through
   `SENSOR_TRIG_FIFO_WATERMARK`; the sample uses 64 samples per batch.

**FIFO formats are part-specific.** The BMI088 accelerometer FIFO interleaves data frames with
metadata frames:
- a skip frame: the number of frames lost to overflow, saturating at 0xFF;
- a sensortime frame: 24 bits, and only when the FIFO runs empty during a burst read;
- an input-config frame when range, filter or downsampling changed;
- a sample-drop frame for samples that may be invalid after reconfiguration.

The gyroscope FIFO of the same part has none of that. Overflow shows only as an overrun flag, and
an external event tag (for example camera frame sync) overwrites the least significant bit of the
z axis. The host needs a parser per part. Gaps, configuration changes and the time base can be
reconstructed only where the sensor reports them.

The same application note also limits the usable gyroscope rate by bus speed when the FIFO is
used: every filter mode at 400 kHz I²C, ≤ 1 kHz at 200 kHz, ≤ 400 Hz at 100 kHz. This was
extracted from the voted document, but the claim itself was not voted.

**Integrity information, where it exists.**
- The SCD4x protects each 16-bit word with a CRC.
- A burst read of the ADIS16470 returns `DIAG_STAT`, three gyro and three accel axes,
  `TEMP_OUT`, the sample counter `DATA_CNTR` and a checksum. The checksum is a plain byte sum,
  not a CRC. In scaled-sync mode `DATA_CNTR` is replaced by `TIME_STMP`.
- The BNO08x numbers its reports with a sequence counter.

**Time.**
- Zephyr's decoded format carries one 64-bit base timestamp per block, taken from
  `k_uptime_ticks` (host uptime, not sensor time), and a 32-bit delta per reading.
- Linux IIO names the POSIX clock used for buffered samples in `current_timestamp_clock`.
- A July 2026 patch to IIO's InvenSense timestamp helper derives the sample period from interrupt
  timestamps, clamps it to the chip's jitter tolerance, and back-calculates the first sample of a
  batch from the nominal period. The patch is not confirmed as merged.
- Sensor time exists only where the part provides it: the BMI088 sensortime frame, the BNO08x
  timestamp, ADIS16470's `TIME_STMP` in scaled-sync mode.

## 3. Quality

**Vocabulary.** The quality figures on a datasheet are typical values, often 1σ at 25 °C, and
not guaranteed limits. The ADIS16470 shows the full set for an inertial sensor:

| Parameter | Gyroscope | Accelerometer |
|---|---|---|
| Range, sensitivity (16-bit) | ±2000 °/s, 10 LSB/(°/s) | ±40 g, 800 LSB/g |
| In-run bias stability | 8 °/h | 13 µg |
| Random walk | ARW 0.34 °/√h | VRW 0.037 m/s/√h |
| Noise density | 0.008 °/s/√Hz rms | 100 µg/√Hz |
| Nonlinearity | ±0.25 % FS | **0.02 % FS at ±10 g, 0.4 % at ±20 g, 1.5 % at ±40 g** |
| Misalignment between axes | ±0.1° | — |
| Sensitivity error over −10…+75 °C | ±0.25 % | — |
| Bandwidth | 550 Hz | — |

The SSN recommendation names the same dimensions as classes: Accuracy, Precision, Resolution,
Latency, Frequency, MeasurementRange, Drift, Sensitivity, Selectivity, DetectionLimit and
ResponseTime.

**Four patterns.**

1. **Quality depends on configuration.** The ADIS16470's nonlinearity grows 75-fold from the ±10 g
   to the ±40 g range.
2. **Derived quantities are looser.** The INA228 specifies offset ±1 µV, offset drift
   ±0.01 µV/°C, gain error ±0.05 %, gain drift ±20 ppm/°C and CMRR ≥ 154 dB for its
   measurement. Power is specified at 0.5 % FS, and energy and charge at 1.0 % FS. A model that
   uses energy as a feature or label works with a wider error band than the raw current. These
   are different metrics, so the comparison is indicative.
3. **Accuracy and repeatability come apart.** The SCD40 is accurate to ±(50 ppm + 5 % of
   reading) at 400–2000 ppm, the SCD41 to ±(50 ppm + 2.5 %) at 400–1000 ppm. Repeatability is
   typically ±10 ppm.
4. **Calibration can depend on context.** The SCD4x's automatic self-calibration (ASC) is on by
   default:
   - it assumes the sensor sees 400 ppm air weekly, and readings below 400 ppm with ASC active
     can degrade accuracy;
   - its five-year drift with ASC is typically ±(5 ppm + 0.5 %);
   - transport and mounting degrade accuracy temporarily, and recovery by ASC or forced
     recalibration (FRC) is possible no earlier than 5 days after mounting;
   - FRC returns its correction as `word − 0x8000` ppm, or `0xffff` on failure.

**Factory calibration and self-test.** Each ADIS16470 is calibrated over −10…+75 °C for
sensitivity, bias, alignment, the effect of linear acceleration on gyro bias, and point of
percussion. On demand it runs a sensor self-test (14 ms; result in `DIAG_STAT`), a flash test, and
a restore of the factory calibration.

**How quality reaches the model.**
- **Device differences.** A study of 36 phones and watches (13 models, 4 makers, 9 users) found
  that differences in sensors and in how they are handled — sampling, OS pipeline — degrade
  activity recognition substantially, and below published research results. How much depends on
  device and method (Stisen et al. 2015; only the abstract was checked).
- **Placement.** A small study with IMUs moved a few centimetres within the same body part saw
  accelerometer-based recognition fall from 100 % to 33 % and gyroscope-based from 65 % to 43 %.
  A scheme combining both recovered 78 %, or 85 % with two training positions. Only 2 subjects
  took part, and the paper's own text gives other figures (63 %/24 %) than its table; a claim
  built on those was refuted. Read it as an illustration, not a benchmark.
- **Why placement matters physically.** Gyroscope signals are the same everywhere on a rigid
  segment; accelerometer signals are not, and the gravity component depends on orientation.

## 4. Runtime quality metadata the parts deliver

| Part or stack | Field | Meaning | Source |
|---|---|---|---|
| ADS1292 | lead-off bits in the status word | electrode contact | datasheet, 3–0 |
| ADIS16470 | `DIAG_STAT` | clock error, memory failure, sensor failure after self-test, standby (VDD < 2.8 V), SPI error, flash update failure, data-path overrun | datasheet, extracted, not voted |
| BMI088 | skip frame, overrun flag, sample-drop frame, input-config frame | loss, invalid samples, configuration change | application note, 3–0 |
| BNO08x (SH-2) | `status` bits 1–0 | accuracy: 0 unreliable, 1 low, 2 medium, 3 high | `sh2_SensorValue.h` |
| VL53L5CX | `target_status`, `range_sigma_mm`, `nb_target_detected` per zone | validity and uncertainty per zone | driver header (meaning of the status codes not checked) |
| u-blox NAV-PVT | `fix_type` 0–5 (none, dead reckoning, 2D, 3D, GNSS + DR, time only); flags `gnssFixOK`, `diffSoln`; `h_acc`, `v_acc` (mm), `s_acc` (mm/s), `head_acc`, `p_dop`, `num_sv` | fix quality and accuracy estimates | `ublox_msgs` definition |
| SCD4x | ASC status, FRC correction; mounting date (recorded by the operator) | calibration state | datasheet, 3–0 |
| Android sensor HAL | `status`: −1 no contact, 0 unreliable, 1 low, 2 medium, 3 high | accuracy per event | AOSP `sensors-base.h` |

## 5. Standards and tooling: what they carry, what they lack

| Standard or tool | Carries | Lacks | Source |
|---|---|---|---|
| IETF SenML (RFC 8428) | name, unit (IANA registry, unprefixed SI), one value, time. Times below 2²⁸ are relative to "now", above it absolute. Base fields compress packs. **Update Time `ut`** detects failed sensors or paths. | **No static metadata** ("assumed … carried out of band") | RFC text |
| W3C SSN/SOSA | Observation with `madeBySensor`, `observedProperty`, `hasResult`; **`phenomenonTime` versus `resultTime`**; SystemCapability with accuracy, precision, drift and others under conditions; Platform and Deployment for mounting | a concrete encoding for per-sample status bits | W3C recommendation |
| ROS 2 `sensor_msgs` | SI units; a 3×3 covariance per quantity; **all zeros = unknown, element 0 = −1 = not provided**; header with timestamp and frame. `NavSatFix` has a covariance type 0–3 (unknown, approximated, diagonal known, known). | sensor model, configuration, calibration state | `common_interfaces` jazzy |
| Android sensor HAL | per-event accuracy, −1 to 3 | static description | AOSP |
| Linux IIO | `_raw` plus `_offset` and `_scale` give SI units (accel in m/s²); `calibbias`, `calibscale`; **`mount_matrix`**; `sampling_frequency`; `current_timestamp_clock`; `hwfifo_watermark` | per-sample accuracy | `sysfs-bus-iio` |
| Zephyr sensor API | q31 fixed point with a shift per block; unit fixed per channel; host base timestamp plus a delta per reading; raw read and decode as separate steps (RTIO) | **any accuracy, calibration or quality field** | `sensor_data_types.h`, docs (the API is called "quickly stabilizing") |
| IEEE 1451.4 TEDS | identity (manufacturer, model, version, serial); templates per transducer type; calibration templates (table, polynomial segments, frequency response); Virtual TEDS as a file | — | National Instruments overview (secondary) |
| ASAM MDF 4.3.0 | raw values **with their conversion formulas**, signal grouping, events, attachments, alternative compression | the specification is free for members only; details not checked | ASAM page |
| DBC (via cantools) | per signal: start bit, length, byte order, sign, scale, offset, minimum, maximum, unit, multiplexing, value names | — | cantools docs (field order inferred from an example) |
| Memfault | device health per heartbeat (default 1 h): reboots, operational hours, CPU temperature, battery, heap and stack, connectivity, dropped log lines, location accuracy on nRF91. Types: int32, timer, string; unset integers send no data point (SDK ≥ 0.42.0). | **sensor data quality** (custom metrics needed); it is not a data path for samples | Memfault docs |

Not checked: OGC SensorThings API, CANopen device profiles, OpenTelemetry for MCUs, Golioth.

## 6. A classification

This is a synthesis of the sections above, not an independently verified result.

| Class | Data shape | Timing | Host processing | Dominant quality dimensions | Runtime metadata available |
|---|---|---|---|---|---|
| Environment, gas, CO₂ | scalar | slow periodic, seconds; polled | formula scaling, CRC check | accuracy vs repeatability, long-term drift, self-calibration | calibration status |
| Electrical | scalar per channel | periodic | scaling by range | offset, gain error, derived-quantity error | range setting |
| Inertial | vector series (3/6/9 axes) | periodic, Hz–kHz; FIFO batches | scaling, FIFO parsing, timestamp reconstruction, fusion | noise density, bias stability, nonlinearity, misalignment, placement | accuracy level, diagnostics, overrun/skip, sample counter |
| Biosignal | vector series (1–12 channels) | periodic, 100–500 Hz | VREF/gain scaling | noise, contact | lead-off |
| Audio | scalar series at kHz; 1-bit stream before decimation | periodic | decimation, then features | SNR, dynamic range | rarely any |
| Image, thermal, ToF | 2D frame | periodic frames | decode, colour conversion, calibration (thermal) | resolution, NETD, ranging uncertainty | per-zone status and sigma (ToF) |
| Radar | data cube (raw) or set (points) | frames | FFTs (raw); variable-length sets (points) | — (not checked) | — |
| GNSS | record of scalars | periodic, low rate | relative coordinates before int8 | CEP, DOP, fix type | fix type, accuracy estimates, satellite count |
| Vehicle bus | event sequence | event-driven, irregular | DBC decoding | — | bus errors (not checked) |

## 7. Minimum metadata for a recording to be usable for ML

The list below follows from the verified findings. It names where each item can come from. It is
knowledge about data quality, **not a requirement Caravan places on its users** (see Section 8).

| Item | Why | Where it comes from |
|---|---|---|
| Sensor model, revision, firmware | device differences shift the distribution | the device, the driver |
| Configuration: range, rate, filter or decimation, reference and gain | counts become units only with it; quality depends on range | the driver; MDF and IIO carry it, SenML and Zephyr do not |
| Calibration state: factory, self-calibration, forced recalibration, self-test result | drift and recovery windows | the part (some), the operator |
| Placement and orientation | placement changes the signal | the deployment record; IIO `mount_matrix`, SSN Platform/Deployment |
| Timestamp source and clock tolerance | host time is often reconstructed | the stack (IIO names the clock; Zephyr uses uptime) |
| Gaps, overruns, integrity | windows across gaps are not samples | the part (skip frames, overrun flags, counters, CRC) |
| Per-sample status | con## 8. What this means for Caravan

**Decided by the owner on 2026-10-23.** Caravan requires neither units nor a metadata record. It
cannot know a user's data situation, and a tool that demands this kind of bookkeeping up front is
not adopted. A metadata and compliance layer is a candidate for a separate, paid offering on top of
Caravan, not part of its feature set.

Units were also the wrong lever. A model trained on counts works on the same counts; what breaks
it is a different representation on the device, for example the same IMU at ±8 g instead of the
±4 g it was trained at. Units in the manifest would not catch that. What remains are proposals
that cost the user nothing:

- **Caravan computes the input scaling from the training data and exports it.** Today there is no
  input normalisation at all. The export states what the model expects — channel order, window,
  the scaling applied — so firmware can feed the representation the model was trained on. Units
  stay optional documentation.
- **Caravan reports what it can see in the data itself**: the measured sample rate and gaps where
  a time column exists, the range of each channel, values pinned at a limit (clipping), constant
  channels. Report only.
- **A window that crosses a detected gap is discarded and counted**, as mixed windows are today.
- **Splits by device or placement** are possible where the data has such a column; never
  required.
- The zoo's resource index may still take the fields of Section 7 for the datasets it lists; that
  is the zoo's decision, not Caravan's.

ment.
- **The zoo's `content.sensor` block** proposed in the landscape note should take these fields.

## Not verified

The meaning of the VL53L5CX status codes; PPG and the other parts listed at the end of
Section 1; the bus-speed limit on BMI088 gyro rates (extracted, not voted); `DIAG_STAT`'s bit list
(extracted, not voted); OGC SensorThings, CANopen, OpenTelemetry for MCUs, Golioth; the details of
MDF4; whether the IIO timestamp patch was merged; the u-blox navigation rate; independent
measurements of any datasheet figure.

**Refuted** (not to be used): a claim about convergence of the old InvenSense timestamp logic
(0–3); an output rate of 15 Hz inferred from the Zephyr sample's printed output (1–2); the
placement study's in-text figures 63 %/24 % (0–3).

## Sources

Datasheets and application notes:
[TI ADS1292](https://www.ti.com/document-viewer/ADS1292/datasheet/data-format-sbas4598878) ·
[TI INA228 datasheet](https://ti.com/document-viewer/INA228/datasheet) and [product page](https://www.ti.com/product/INA228) ·
[Sensirion SCD4x v1.5](https://cdn.sparkfun.com/assets/9/7/5/7/0/Sensirion_SCD4x_Datasheet.pdf) (SparkFun mirror) ·
[Bosch BST-MIS-AN005 (BMI08x FIFO)](https://www.bosch-sensortec.com/media/boschsensortec/downloads/application_notes_1/bst-mis-an005.pdf) ·
[ADI ADIS16470](https://wcm-cce.cldnet.analog.com/media/en/technical-documentation/data-sheets/ADIS16470.pdf) (checked through a mirror)

Source code and message definitions:
[CEVA SH-2 `sh2_SensorValue.h`](https://github.com/ceva-dsp/sh2/blob/main/sh2_SensorValue.h) ·
[ST VL53L5CX driver header (SparkFun library)](https://github.com/sparkfun/SparkFun_VL53L5CX_Arduino_Library/blob/main/src/vl53l5cx_api.h) ·
[`ublox_msgs` NavPVT](https://github.com/KumarRobotics/ublox/blob/ros2/ublox_msgs/msg/NavPVT.msg) ·
[ROS 2 `Imu.msg`](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg) and [`NavSatFix.msg`](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/NavSatFix.msg) ·
[Zephyr `sensor_data_types.h`](https://github.com/zephyrproject-rtos/zephyr/blob/main/include/zephyr/drivers/sensor_data_types.h) ·
[AOSP `sensors-base.h`](https://android.googlesource.com/platform/hardware/libhardware/+/refs/heads/main/include_all/hardware/sensors-base.h) ·
[Linux `sysfs-bus-iio`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/ABI/testing/sysfs-bus-iio) ·
[IIO InvenSense timestamp patch (LKML, July 2026)](https://lkml.iu.edu/2607.2/03571.html)

Documentation and standards:
[Zephyr FIFO streaming sample](https://docs.zephyrproject.org/latest/samples/sensor/6dof_fifo_stream/README.html) ·
[Zephyr read and decode](https://docs.zephyrproject.org/latest/hardware/peripherals/sensor/read_and_decode.html) ·
[RFC 8428 (SenML)](https://www.rfc-editor.org/rfc/rfc8428) ·
[W3C SSN/SOSA](https://www.w3.org/TR/vocab-ssn/) ·
[NI on IEEE 1451.4 TEDS](https://www.ni.com/en/support/documentation/supplemental/06/ieee-1451-4-sensor-templates-overview.html) (secondary) ·
[ASAM MDF](https://www.asam.net/standards/detail/mdf/) ·
[cantools](https://cantools.readthedocs.io/en/latest/) ·
[Memfault metrics API](https://docs.memfault.com/docs/mcu/metrics-api) ·
[Memfault built-in metrics](https://docs.memfault.com/docs/mcu/mcu-builtin-metrics)

Studies:
[Stisen et al., SenSys 2015](https://www.doi.org/10.1145/2809695.2809718) (abstract only) ·
[Kunze & Lukowicz, IEEE Pervasive Computing 2014](https://www-live.dfki.de/fileadmin/user_upload/import/7846_Sensor_Placement_Variations_in_Wearable_Activity_Recognition.pdf) ·
[survey on data heterogeneity in wearable HAR (arXiv 2304.06489)](https://mdsoar.org/handle/11603/27921) (secondary)

Sources from the interim rows are listed in the landscape note.
