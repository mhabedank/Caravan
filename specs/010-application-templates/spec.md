# Feature Specification: Templates for the Application Classes

**Feature Branch**: `010-application-templates`

**Created**: 2026-10-29

**Status**: Draft — scope decided 2026-10-29

**Input**: User description: "wir hatten bereits eine analyse gemacht, welche use cases es gibt,
richtig? das war ne ganze menge. lass uns mal daraus entwickeln welche templates wir brauchen und
diese dann implementieren" — *we already analysed which use cases exist, quite a lot of them. Let us
derive from it which templates we need, and then implement them.*

## Context

The analysis is the research note of 2026-10-23,
[`docs/research/2026-10-23-mcu-ml-landscape.md`](../../docs/research/2026-10-23-mcu-ml-landscape.md),
Part A: twelve application classes that are shown to run on microcontrollers, each with its input,
its output, a reference size and the hardware. The owner made it the scope of Caravan the same day
(owner decision D5), and constitution Principle X accepts such a documented application class as a
template's justification, beside a named model.

Caravan has two templates today. `mlp` is a dense decider over a window, `conv1d` a convolutional
one. Both take a window of rows, each row the channels of the declared input features, and both end
in a head for a `category`, `binary` or `number` output.

### Which template each application class needs

| # | Application class | Input, as Caravan sees it | Output | Template | Status |
|---|---|---|---|---|---|
| 1 | Activity recognition (HAR), hand posture | IMU window, rows × channels | class | `conv1d`, `mlp` | **covered** (`pace-cnn`) |
| 2 | Arc fault detection | current, rows × channels | class | `conv1d` | **covered** |
| 3 | Battery state of charge | voltage, current, temperature | value | `mlp` (`number` output) | **covered** |
| 4 | CAN intrusion detection | event sequence, one row per frame | class | `mlp`, `conv1d` | **covered** (`picket-mlp`) |
| 5 | ECG | 1–12 leads | class, often several at once | `conv1d` | template **covered**; multi-label output is a gap of the output types, not of the templates |
| 6 | Machine anomaly from sound or vibration | feature frames, e.g. 5 × 40 log-mel (`hum-fan`), 5 × 128 (MLPerf Tiny) | **reconstruction → anomaly score** | — | **gap: an autoencoder** |
| 7 | Keyword spotting | feature frames, 49 × 10 MFCC | class | — | **gap: a two-dimensional convolution over frames × coefficients** |
| 8 | Person present (Visual Wake Words) | image 96 × 96 | class | the same two-dimensional convolution | template gap as in 7; **also needs an image input type** |
| 9 | Image classification | image 32 × 32 | class | the same | as in 8; the reference ResNet needs residual connections, which stay out |
| 10 | Object detection | image 96–128 px | grid or boxes | a detection head | needs an image input and a grid output; M7 or NPU class |
| 11 | Pose, segmentation, depth, face | image | dense, several heads | — | MCU with NPU; no output kind for it |
| 12 | Audio events, noise suppression | audio | class, or a **signal** | — | signal output; M55 with NPU |

Two literature figures sit beside the table without a row of their own: recurrent networks for
battery health (a CNN-LSTM of 8,961 parameters, 35 KB flash on an ST SPC58) and for CAN intrusion
detection (an LSTM autoencoder of 6,272 parameters), both recorded in the zoo's model-ideas research
of 2026-10-11. They make a recurrent template a candidate, not a need: rows 3 and 4 are already
served, and the ESP32's accelerated library has no recurrent kernel (`esp-nn`, read 2026-10-22).

**What follows.** Five of twelve classes are served by the two templates that exist. Two templates
are missing for classes that fit the data Caravan already reads — a window of rows with numeric
columns: an **autoencoder** for anomaly detection (row 6) and a **two-dimensional convolution** over
the window as a plane of rows × columns (row 7). The same two-dimensional template is what the image
classes (rows 8 and 9) will need once an image input type exists. Rows 10 to 12 need output kinds
and hardware classes Caravan does not have, and no template alone would serve them.

## Scope Decision

Decided by the owner on 2026-10-29 (option D of four): this feature builds

1. the **anomaly template**, an autoencoder (row 6, driven by `hum-fan`);
2. the **two-dimensional convolution** (row 7, keyword spotting);
3. the **`image` input type**, so that rows 8 and 9 run end to end through the two-dimensional
   template.

Not chosen: a recurrent template (no model needs one today, and the ESP32's accelerated library has
no kernel for it), and the smaller scopes without images. Rows 10 to 12 stay out.

Together the three take Caravan from five of the twelve application classes to nine.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect anomalies from normal data alone (Priority: P1)

An author has recordings of a machine in normal condition — a fan, a bearing, a pump — and a few
recordings of faults, labelled in a column. They want a model that learns what normal sounds or
feels like and says how unusual a window is, because faults are rare, varied and mostly unseen at
training time. They name the anomaly template and the column that tells normal from abnormal; the
pipeline trains on normal windows only, chooses an alarm threshold, judges the int8 model by how
well it separates normal from abnormal, and exports a model whose output is the anomaly score.

**Why this priority**: It is the one gap a named model needs today: `hum-fan` is published in the
zoo, was built by hand, and is exactly this architecture. It also covers MLPerf Tiny's anomaly task
and the zoo's bearing idea (`hum-bearing`).

**Independent Test**: Write a manifest naming the anomaly template on a committed synthetic fixture
with normal and abnormal windows, run the pipeline to export, and read the exported score, threshold
and separation figures.

**Acceptance Scenarios**:

1. **Given** a manifest naming the anomaly template, a condition column and which value of it means
   normal, **When** it is validated, **Then** it is accepted and the resolved manifest shows the
   encoder widths, the code size, the decoder widths and the threshold rule with their defaults.
2. **Given** that manifest, **When** the model is trained, **Then** only windows labelled normal are
   used for training, and the report states how many windows of each condition each split held.
3. **Given** the trained model, **When** it is evaluated, **Then** the report gives how well the
   score separates normal from abnormal windows on the test part, and the threshold chosen from
   normal windows of the validation part, with the rule that chose it.
4. **Given** the int8 model, **When** the quantization gate runs, **Then** it compares the
   separation of the int8 model with that of the float model and fails the run when the drop
   exceeds the budget the manifest states.
5. **Given** the exported model, **When** a firmware passes a raw window, **Then** the model's
   output is the anomaly score itself, and the interface contract states the threshold and that a
   score at or above it means abnormal — the firmware computes nothing around the model.

---

### User Story 2 - Classify a plane of feature frames (Priority: P1)

An author has audio already turned into feature frames — one row per frame, one column per
coefficient, as in keyword spotting — or any other window whose columns are neighbours of each other
the way rows are. They want a convolution that slides over both axes, because a pattern in a
spectrogram has extent in time *and* frequency, and the one-dimensional template treats the columns
as unrelated channels. They name the two-dimensional template; the pipeline builds, trains,
quantizes and exports it as it does the others.

**Why this priority**: Keyword spotting is the one MLPerf Tiny task whose data is cleanly usable
commercially (Speech Commands v2, CC BY 4.0), and its reference architecture is small enough for
every built-in board. The same template is the foundation the image classes will build on.

**Independent Test**: Write a manifest naming the template on a committed synthetic fixture of
feature frames, run the pipeline to export, and check the export's operator set and coverage.

**Acceptance Scenarios**:

1. **Given** a manifest naming the two-dimensional template with blocks of standard and separable
   convolutions, **When** it is validated, **Then** it is accepted and the resolved manifest shows
   every block with its defaults.
2. **Given** that manifest, **When** the model is built, **Then** the window is treated as a plane of
   rows by input columns, and the report names the layers, the input and output shapes and the
   parameter count.
3. **Given** a configuration that expresses the MLPerf Tiny keyword-spotting reference architecture,
   **When** it is built at 49 frames × 10 coefficients with 12 labels, **Then** its parameter count
   matches the count computed independently from that architecture.
4. **Given** an exported model, **When** the export record is read, **Then** every operator the
   template produces is mapped to the runtime's resolver, and each has a coverage verdict on every
   built-in board.
5. **Given** a kernel or stride that does not fit the plane on either axis, **When** the manifest is
   validated or the model is built, **Then** it is refused, naming the axis, the block, the size left
   when that block was reached, and what would fit.

---

### User Story 3 - Classify images (Priority: P2)

An author has a folder of small images — frames of a doorway from a low-power camera, thermal
snapshots — and a table that names each image file and its class, the way Ludwig reads images. They
declare one image input; the pipeline reads and resizes the images for training, builds the pixel
scaling into the model, checks against the boards whether such a model can fit at all, and exports a
model that takes raw pixels at the declared size.

**Why this priority**: The owner put image processing in scope (decision D5: "definitiv gibt es
Bildverarbeitung auf kleinen Controllern"), and two of MLPerf Tiny's four tasks are images. It is P2
and not P1 because it builds on the two-dimensional template of User Story 2 and adds the largest
new surface: a second way of reading data.

**Independent Test**: On a committed fixture of small generated images with a label table, run a
manifest with an image input and the two-dimensional template from validation to export, and read the
interface contract.

**Acceptance Scenarios**:

1. **Given** a manifest with an image input naming its column, **When** it is validated, **Then** it
   is accepted, and the resolved manifest of a run shows the height, width, channels and resize
   method used — stated by the author or taken from the data.
2. **Given** a table whose image column names files relative to the dataset, **When** the pipeline
   reads it, **Then** every image is read, converted to the declared channels and brought to the
   declared size, and the report counts the images read and how many had to be resized.
3. **Given** a record whose image file is missing or cannot be decoded, **When** the data is read,
   **Then** the run is refused, naming the record, the file and what was wrong — no image is dropped
   silently.
4. **Given** the exported model, **When** a firmware passes a frame of the declared size as raw 8-bit
   pixels, **Then** the model scales them itself, and the interface contract states the height, the
   width, the channels and their order, the pixel element type, and that the frame must already have
   the declared size.
5. **Given** an image model whose lower bounds exceed a board's memory, **When** the fit check runs,
   **Then** the run stops before training with the floors and the board's figures; and an image is
   counted at one byte per pixel, so a model that fits is not refused for a float copy it will
   never have.
6. **Given** an image input beside other inputs, an image input with a window, or an image input
   with the anomaly template, **When** the manifest is validated, **Then** it is refused, naming the
   combination and what is accepted.

---

### User Story 4 - See which application each template serves (Priority: P2)

An author arrives with a problem — "detect a worn bearing", "recognise a wake word" — not with a
template name. They need to find out which template fits their problem, what data shape it expects
and which applications Caravan does not serve yet, without reading the source.

**Why this priority**: The derivation above is the analysis the owner asked for; it is worth only
as much as the author can find of it. It is documentation, and it rides with the templates.

**Independent Test**: Open the documentation and, for each of the twelve application classes, find
which template serves it or why none does.

**Acceptance Scenarios**:

1. **Given** the documentation, **When** an author looks up an application class, **Then** they find
   the template that serves it, the shape of data it expects, and an example manifest, or the reason
   it is not served and what it would need.
2. **Given** the template listing command, **When** it runs, **Then** each template shows a one-line
   summary that names the kind of problem it is for.
3. **Given** the roadmap, **When** it is read after this feature, **Then** the templates built here
   are delivered, and the deferred ones are recorded with their reason.

---

### User Story 5 - Add templates without touching the core (Priority: P3)

Two more templates are two more tests of the registry's promise: a template is a parameter half in
the core, a builder half behind the training extra, and a registration, with no central list edited
and no stage carrying a special case.

**Why this priority**: The promise was proven once, by `conv1d`. An autoencoder is the first template
whose output is not one of the existing heads, and the two-dimensional template is the first that
takes either a window or an image, so together they test where a template ends and a feature type
begins.

**Independent Test**: List the templates in an installation without the training extra; validate a
manifest for each; search the stages for a branch on a template identifier.

**Acceptance Scenarios**:

1. **Given** the new templates, **When** the core is imported without a training framework, **Then**
   their parameters validate and nothing fails.
2. **Given** the stages, **When** they handle a model of any template, **Then** none branches on the
   template's identifier; what differs for anomaly detection is decided by the output type, and
   what differs for images by the input type.

---

### Edge Cases

- An anomaly manifest whose test part holds no abnormal window: the separation cannot be measured,
  so the gate cannot decide, and the run fails with a message naming the split and the counts —
  unknown is not within budget (Principle V).
- An anomaly manifest whose training part holds no normal window: refused before training, naming the
  normal value and the values found.
- A condition column with more than two values: every value other than the stated normal one counts
  as abnormal, and the report lists the counts per value.
- The anomaly template with an output type other than the anomaly one, or the anomaly output with a
  template that does not reconstruct its input: refused at validation, naming both.
- An anomaly model on inputs with a `category` feature: the reconstruction target is the input as the
  model sees it after preprocessing, so it is valid; the report says what the target was.
- A two-dimensional configuration that fits the time axis but not the column axis, for example a
  kernel of 4 columns on 3 input columns: refused, naming the column axis — the failure the
  one-dimensional template could not have.
- A `category` input with one-hot encoding feeding the two-dimensional template: its channels become
  columns of the plane, which a convolution would treat as neighbours. Valid, and the documentation
  says why it is rarely what an author wants.
- Separable blocks with a dropout of zero: no dropout layer appears, as in the existing templates.
- A two-dimensional head that reduces over the plane: recorded with its operator and coverage like
  `conv1d`'s, so the author sees whether it is accelerated.
- Images of different sizes and no size stated: refused, naming the sizes found and the keys that
  would settle it. Images of one size and no size stated: that size is taken and recorded.
- A colour image where one channel is declared, or the reverse: converted, and the report counts
  the conversions.
- An image column naming a path outside the dataset directory: refused, because a manifest may not
  reach files outside its declared fields (Principle I).
- An image file in a format the pipeline does not read: refused with the formats it does read.
- The image fixture's size is far below the reference shapes: the reference shapes are checked by
  building and by the fit check, not by training, as `conv1d` did for `pace-cnn`.

## Out of Scope

- Rows 10 to 12 of the table: detection, segmentation, pose, signal outputs. They need output kinds
  and, mostly, NPU-class hardware that Caravan has no board for.
- Resizing, cropping or decoding images on the device: the camera or the firmware delivers frames
  at the declared size as raw pixels; JPEG decoding stays the firmware's.
- Image augmentation, pretrained weights, transfer learning.
- An image input combined with other inputs, and anomaly detection on images.
- Multi-label output for ECG (row 5): an output type, a separate feature.
- A recurrent template (not chosen in the scope decision).
- Feature extraction inside Caravan: turning audio into MFCC or log-mel frames, vibration into
  spectra. The author's data arrives as frames, one row per frame, as `hum-fan`'s does today; where
  that extraction should live is the open question the research note recorded (Part F).
- The port of `hum-fan` itself, and any accuracy claim for a real dataset: that happens in the zoo,
  where the data is. No dataset enters this repository (Principle VI).
- Residual connections, attention, dilation, and every architectural option no named model or
  documented application needs (Principle X). So the image classification reference (ResNet-8 on
  32 × 32) is not expressible; row 9 is served by plain and separable stacks.

## Requirements *(mandatory)*

### Functional Requirements

**The derivation, recorded**

- **FR-001**: The project MUST record, for each of the twelve application classes of the research
  note, which template serves it, or why none does and what it would need, with the source of the
  classification.
- **FR-002**: Every template built by this feature MUST name its justification in this specification:
  a named model, an application class of the research note, or both (Principle X).

**The anomaly template** (User Story 1)

- **FR-003**: The project MUST provide a template that reconstructs its input through a narrower
  code: a sequence of encoder widths, a code size, and a sequence of decoder widths, each validated
  individually by the template.
- **FR-004**: The template MUST express `hum-fan`'s architecture — 200 inputs from 5 × 40 frames,
  encoder [64, 64], code 8, decoder [64, 64] — and the MLPerf Tiny anomaly reference's shape of
  5 × 128 frames.
- **FR-005**: The project MUST provide an output type for anomaly detection, declared in the manifest
  by the column that tells normal from abnormal and the value that means normal.
- **FR-006**: Training MUST use only windows whose condition is normal, and the report MUST give the
  number of windows of each condition value in each split.
- **FR-007**: The anomaly score MUST be the reconstruction error of a window, computed in the model,
  so that the exported model's output is the score.
- **FR-008**: The pipeline MUST choose the alarm threshold from the normal windows of the validation
  part by a rule with a documented default, which the author MAY state instead; the run report and
  the resolved manifest MUST record the rule and the threshold.
- **FR-009**: The evaluation MUST report how well the score separates normal from abnormal windows on
  the test part, and the detection rates at the chosen threshold.
- **FR-010**: The quantization gate for the anomaly output MUST compare the separation of the int8
  model with that of the float model against a budget stated in the manifest, and MUST fail the run
  when the budget is exceeded or cannot be determined.
- **FR-011**: The interface contract in the export MUST state the score output, the threshold, and
  that a score at or above the threshold means abnormal.
- **FR-012**: The anomaly template and the anomaly output type MUST each refuse to be combined with a
  counterpart that cannot serve them, naming both, at validation.

**The two-dimensional template** (User Story 2)

- **FR-013**: The project MUST provide a convolutional template that treats the window as a plane of
  rows by input columns, with one channel.
- **FR-014**: Its parameters MUST express a sequence of blocks, each either a standard convolution or
  a depthwise-separable one, with a filter count, a kernel and a stride per axis, padding, optional
  normalisation, optional pooling and optional dropout.
- **FR-015**: Its parameters MUST express a head choice of at least reducing over the plane and
  flattening, as `conv1d` does.
- **FR-016**: It MUST express the MLPerf Tiny keyword-spotting reference architecture at 49 × 10 with
  12 labels.
- **FR-017**: A configuration that does not fit the plane on either axis MUST be refused before
  training with the axis, the block, the size left there, and a fitting alternative.
- **FR-018**: Every operator the template can produce MUST be mapped to a resolver method and have a
  coverage verdict on every built-in board, asserted by a test.
- **FR-019**: It MUST end in the existing heads for `category`, `binary` and `number` outputs, with no
  head of its own beyond what FR-015 names.

**The image input type** (User Story 3)

- **FR-020**: The project MUST provide an `image` input type, in Ludwig's name, declared by the
  column that names each record's image file, relative to the dataset directory.
- **FR-021**: The height, the width and the number of channels (one or three) MAY be stated; a value
  not stated MUST be taken from the data when all images agree on it, recorded in the resolved
  manifest, and refused naming the values found when they do not.
- **FR-022**: The pipeline MUST read at least PNG and JPEG files, convert each image to the declared
  channels and resize it to the declared size by a documented default method, and report how many
  images were converted or resized.
- **FR-023**: A missing, unreadable or out-of-directory image MUST refuse the run, naming the record
  and the file.
- **FR-024**: The model's image input MUST take raw 8-bit pixels at the declared size; the scaling of
  pixel values MUST be inside the model.
- **FR-025**: An image input MUST be the model's only input, each record MUST be one sample, and a
  window MUST NOT be stated; the two-dimensional template MUST take the image as its plane, with its
  channels.
- **FR-026**: The interface contract MUST state the image input's height, width, channels and their
  order, its element type, and that frames are passed at the declared size.
- **FR-027**: The fit check before training, the stage cache, the splits and the test windows of the
  export MUST work for image models as for windowed ones; a test window of an image model is one
  image with the host's answer.
- **FR-028**: The dataset's identity for the stage cache MUST cover the image files a table names, so
  that changing an image invalidates what was built from it.

**Both templates, in the pipeline**

- **FR-029**: Each template MUST be a parameter half in the core and a builder half behind the
  training extra, registered without editing a central list, and listed with a one-line summary
  naming its kind of problem.
- **FR-030**: No stage MAY branch on a template identifier; behaviour that differs for anomaly
  detection MUST follow from the output type.
- **FR-031**: Each template MUST run end to end — validate, render, build, train, quantize, export —
  on a committed synthetic fixture, with its gate able to pass and to fail.
- **FR-032**: The fit check before training MUST apply to both templates, counting what they add:
  depthwise convolutions as convolutions, and an image input at one byte per pixel.
- **FR-033**: The stage cache MUST apply: a changed parameter produces a new model, an unread field
  does not.
- **FR-034**: The dependency count, the extras and the default installation's size MUST be unchanged.

**Documentation** (User Story 3)

- **FR-035**: The documentation MUST carry the application-class table of FR-001, an example manifest
  for each new template, and the manifest reference for each new parameter and output key.
- **FR-036**: The roadmap MUST record the templates delivered by this feature, and each deferred
  candidate with its date and reason.

### Key Entities

- **Image input**: one column naming an image file per record, with height, width and channels,
  stated or taken from the data, and the resize method.
- **Application class**: a use shown to run on microcontrollers, with its input, output, reference
  size and hardware, from the research note; the justification a template may cite.
- **Anomaly template parameters**: encoder widths, code size, decoder widths, dropout.
- **Anomaly output**: the condition column, its normal value, the threshold rule and the threshold it
  produced, and the separation budget.
- **Plane**: what the two-dimensional template convolves — a window seen as rows by input columns
  with one channel, or an image with its channels.
- **Convolution block (two-dimensional)**: standard or separable, filters, kernel and stride per
  axis, padding, normalisation, pooling, dropout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the twelve application classes has an entry in the documentation that names its
  template, or the reason it has none and what it would need.
- **SC-002**: A manifest for each new template runs from validation to export on its committed
  fixture, with the gate passing; a run whose int8 model loses more than the budget fails the gate
  and leaves no model. (On the fixtures int8 loses nothing, so the loss is injected at the
  measurement seam, as feature 003's gate test does.)
- **SC-003**: The anomaly template built at `hum-fan`'s architecture has exactly 35,280 parameters,
  the count of the zoo's hand-built model.
- **SC-004**: On the anomaly fixture, the exported int8 model's score separates normal from abnormal
  test windows, and the report states the float and int8 separation and the drop between them.
- **SC-005**: An exported anomaly model gives a firmware its decision from one comparison of the
  output with the threshold in the contract; no other arithmetic around the model is needed.
- **SC-006**: The two-dimensional template built at the keyword-spotting reference shape has the
  parameter count computed independently from that reference architecture.
- **SC-007**: 100% of the operators either template can produce have a resolver mapping and a
  coverage verdict on all three built-in boards.
- **SC-008**: Every refusal named in the edge cases names the field or axis, the value, and what is
  accepted.
- **SC-009**: The parameter halves validate manifests in an installation without the training
  extra, asserted in that installation.
- **SC-010**: No stage contains a branch on a template identifier.
- **SC-011**: Dependencies, extras and the default installation's size are unchanged.
- **SC-012**: A manifest with an image input and the two-dimensional template runs from validation to
  export on a committed fixture of generated images, with the gate passing.
- **SC-013**: The two-dimensional template built at the Visual Wake Words reference — MobileNetV1 at
  width 0.25, 96 × 96 × 3, two labels — has the parameter count computed independently from that
  architecture. (Measured 2026-10-29: its working-memory floor, 55,296 bytes, is below even the
  s32k144's 65,536, so the fit check passes it on every built-in board; a floor is a lower bound,
  and the figure a board needs comes from emulation or the board. An image model whose floor does
  exceed a board is refused before training, tested separately.)
- **SC-014**: Every missing, unreadable or out-of-directory image in a test fixture is refused with
  its record and file named; none is dropped silently.
- **SC-015**: Changing one image file of a dataset invalidates the cached stages that read it, and
  changing none does not.
- **SC-016**: Nine of the twelve application classes have a template and input type that serve them,
  as the documentation's table states.

## Assumptions

- **Feature frames arrive as rows.** Both templates read the window Caravan already builds: one row
  per frame, one column per coefficient. That is how `hum-fan`'s 5 × 40 log-mel frames and keyword
  spotting's 49 × 10 MFCC frames look once extracted, so no new input type is needed for rows 6
  and 7.
- **Labels are required for anomaly detection.** Training needs only normal windows, but the gate
  must judge separation, and a gate that cannot decide fails (Principle V). So the condition column
  is required, as it is in MLPerf Tiny's and DCASE's evaluation protocols and in `hum-fan`'s.
- **The score is computed inside the model.** Owner decision D7: the user writes nothing around the
  model. The plan measures what this costs in operators and coverage, and whether the int8 score
  keeps the separation; if it does not, the plan records the alternative.
- **The threshold rule defaults to a percentile of validation normals.** `hum-fan` uses the 95th
  percentile; that is the default unless the plan's research finds a better-founded one.
- **The separation measure is the area under the ROC curve**, as in MLPerf Tiny's anomaly task and
  DCASE. Its exact budget key is a plan decision.
- **The two-dimensional template is named for what the author describes**, as `conv1d` is: a
  convolution over two axes. The roadmap's working name `smallcnn` is replaced.
- **Separable convolution is offered here and was not in `conv1d`.** The keyword-spotting reference
  needs it, and feature 005 measured that its depthwise operator is accelerated on both built-in
  libraries.
- **Adding an output type and two templates is additive.** A manifest written before this feature
  keeps its meaning; whether the schema version changes is a plan decision under Principle IX.
- **Synthetic fixtures only.** Each template gets a small generated fixture: frames with
  class-dependent patterns for the two-dimensional template, normal windows and perturbed abnormal
  ones for the autoencoder, and a few hundred small generated images with simple class-dependent
  shapes for the image type. No recording and no photograph enters the repository.
- **Images are read as Ludwig reads them.** A table column holds the image file's path; the label
  and the split are other columns of the same table. That keeps one dataset form for every input
  type, and lets the existing splits, including a fixed split from a column, apply unchanged.
- **Image size is the author's decision about the device, not a fact of the data.** The camera
  delivers a fixed frame; the model must take that frame. So the size may be stated, and is taken
  from the data only when the data leaves no doubt (Principle I: what the data says is not asked).
- **Resizing happens on the host, for training only.** On a microcontroller the camera crops and
  bins (the HM01B0 delivers 320 × 240 windows and 2 × 2 binning, research note Part D); a resize
  operator in the model would spend memory the image already strains. The contract says the frame
  must arrive at the declared size.
- **The device passes 8-bit pixels.** A 96 × 96 × 3 frame is 27,648 bytes as 8-bit values and four
  times that as 32-bit floats; on boards with 64 KB to 1 MB of memory that difference decides what
  fits. How the 8-bit input reaches the quantized model is a plan decision.
- **Image decoding adds no dependency.** It is needed only where training happens, and the training
  extra already brings a framework that decodes PNG and JPEG; the plan confirms this before relying
  on it (Principle XII).

## Constitution Check

- **Principle I**: the templates are chosen by identifier with parameters; the anomaly output and
  the image input are declared feature types, every new key is read by a stage, and an image size
  the data already states is not asked again.
- **Principle IV**: no accuracy or latency is claimed for a real dataset; parameter counts are
  checked against independently computed figures.
- **Principle V**: the anomaly output brings its own gate, which fails when it cannot decide.
- **Principle VII**: both templates register by discovery; no central list is edited.
- **Principle VIII**: the anomaly score and threshold are in the interface contract.
- **Principle X**: the autoencoder is justified by `hum-fan` and by the anomaly application class;
  the two-dimensional template by the keyword-spotting application class, with Speech Commands v2
  (CC BY 4.0) as its public dataset; the image input type by the Visual Wake Words and image
  classification classes (MLPerf Tiny) and owner decision D5. Deferred candidates are recorded with
  their reason.
- **Principle XII**: no dependency, no extra; the parameter halves stay framework-free, and image
  decoding lives where training lives.
