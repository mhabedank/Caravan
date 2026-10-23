# Owner decisions after the first from-zero run — 2026-10-23

Status: record of decisions and open proposals from a working session. Nothing here is
implemented yet. The decisions bind the next specs; the constitution has not been amended yet,
and where a decision contradicts it, the amendment is listed as work to do.

The owner tried Caravan from an empty folder and reviewed the manifest, the CLI and the run
directories. His words are quoted in the original German, followed by a translation. Everything
marked **proposal** is Claude's, not decided.

## Decided

### D1. Compliance is not part of Caravan

> "warum license und permitted use. wir wollen compliance nicht drin haben, das soll ein leanes
> produkt sein und compliance sollte nicht teil des features sets sein" — "compliance komplett
> raus."

*Why license and permitted use. We don't want compliance in it; this should be a lean product,
and compliance should not be part of the feature set. Compliance out completely.*

- The `compliance` section of the manifest goes, and with it `dataset.license` and
  `dataset.permitted_use`.
- Work to do: **amend Principle VI** ("Compliance Is Enforced by the Schema"). That is a MAJOR
  amendment of the constitution (2.4.0 → 3.0.0). Rules CF-3, CF-5 and CF-8 and the compliance
  parts of `resolve.py` go with it.

### D2. No units and no metadata record required of users

> "Metadaten-Record: Können wir nicht garantieren, wir kennen die Datenlage der Nutzer nicht. Und
> ein Tool, das zu viel Compliance einfordert, wird nie genutzt — zumindest nicht am Anfang. Das
> wäre was für eine paid Version, die einen Compliance-Layer drauf packt."

*We cannot guarantee a metadata record; we don't know users' data situation. A tool that demands
too much compliance will never be used, at least not at first. That would be something for a paid
version that adds a compliance layer.*

- Caravan requires neither units nor a metadata record. A metadata and compliance layer is a
  candidate for a separate, paid offering on top of Caravan.
- Recorded in Section 8 of
  [`../research/2026-10-23-sensor-data-and-metadata.md`](../research/2026-10-23-sensor-data-and-metadata.md).

### D3. `render` and `validate` write to the shell

> "render validate sollten einfach ins shell schreiben und nicht in eine datei"

*Render and validate should simply write to the shell, not to a file.*

- Both commands can already do this (`render --stdout`, `validate --no-report`); the default
  flips, and writing a file becomes the opt-in.

### D4. Inputs and outputs are declared, Ludwig-style, and there can be several

> "da geht es um input und output feature. ich finde das viel besser. dadurch wird viel klarer was
> das modell machen soll. warum haben wir das nicht so?"

*Ludwig has input and output features. I find that much better; it makes much clearer what the
model is meant to do. Why don't we have it that way?*

> "Ich verstehe noch nicht ganz die Argumentation, warum wir nicht mehrere In- und Outputs haben
> können. Wenn das von TFLite (oder was auch immer wir als Base nutzen) unterstützt wird, dann
> machen wir das auch. Ob das dann aufs Board passt oder nicht, müssen wir dann eben evaluieren,
> Caravan sollte das unterstützen. Da es ja die Boards kennt, könnte es das easy tun, bevor wir
> trainieren."

*I don't quite follow why we can't have several inputs and outputs. If TFLite (or whatever we use
as the base) supports it, we do it. Whether it then fits the board is something we evaluate;
Caravan should support it. Since it knows the boards, it could easily do that before we train.*

- The manifest declares inputs and outputs with a type each, and the output type says what the
  model does.
- **Several inputs and several outputs** are supported wherever the runtime supports them. TFLM
  does: `inputs_size()`, `input(i)`, `outputs_size()`, `output(i)`.
- **Whether the model fits the board is checked before training**, from the board descriptions
  (flash, RAM), the parameter count and the working-memory floor of the built model.
- An earlier argument for a single input, that the builders take one input shape, was wrong. It
  described what had been built, not what the base can do.

### D5. The scope is broad

> "es muss ja typische Einsätze geben, und im Übrigen gehört da auch Bildverarbeitung dazu.
> Vielleicht nicht auf dem ESP32, aber definitiv gibt es Bildverarbeitung auf kleinen
> Controllern … zudem gibt es das auch, dass man mehrere Inputs hat, zum Beispiel CAN-Messages im
> Ganzen mit Timestamp usw. Dann gibt es Modelle, die eben ein laufendes Fenster analysieren." —
> "dieses Tool ist nicht ausschließlich für Mobility, das ist nur unser Einsatzzweck."

*There must be typical applications, and image processing belongs to them too — perhaps not on
the ESP32, but definitely on small controllers. There are also several inputs, for example whole
CAN messages with timestamps. And there are models that analyse a running window. This tool is
not only for mobility; that is only our use.*

- Image input, event sequences such as CAN, and running-window models are in scope. Mobility is
  one domain among several.
- The applications and their input and output kinds are in
  [`../research/2026-10-23-mcu-ml-landscape.md`](../research/2026-10-23-mcu-ml-landscape.md).

### D6. Run directories must be findable

> "generell sind die Run-Ordner Mist, es ist die komplette Zeit drin, sodass ich für alle Schritte
> einen extra Ordner habe. Wie macht Ludwig das? Ich finde es bei so langen Namen schwer,
> überhaupt zu sehen, welche Daten ich mir angucken möchte (20261023T070450Z-6f9e7964)"

*The run directories are bad in general: the full time is in the name, so I get an extra folder
for every step. How does Ludwig do it? With such long names it is hard even to see which data I
want to look at.*

- Decided: the current naming goes. The scheme is open (see P6).
- Clarified fact: one invocation already makes one directory (`pipeline.py`). The folder per step
  came from the tutorial running each stage as its own command; `caravan export` alone runs them
  all into one directory.

## Raised by the owner, direction given, details open

### R1. `topic` and `task`

> "warum brauche ich topic und task?" — *Why do I need topic and task?*

No stage reads either field; they exist only in the schema and in `resolve.py`. **Proposal:**
remove both. D4 makes `task` redundant: the output type says it.

### R2. Labels come from the data

> "warum muss ich die labels hinschreiben, sollte die sich nicht aus dem Datensatz ergeben, in dem
> man die Label-Spalte angibt, bzw. Y"

*Why do I have to write the labels down; shouldn't they follow from the dataset, by naming the
label column, or Y?*

**Proposal:** derive the labels from the named output column, sorted, and record them in the
resolved manifest. An explicit list stays optional to pin the order. Fail when a later run sees a
different set.

### R3. `representative_samples`

The owner asked what it means: it is the calibration set for int8 quantization. **Proposal:**
rename it `calibration_samples`, give it a default capped at the training split, and keep it
optional.

### R4. Visualising models

**Answered, no feature:** Netron opens `.keras` and `.tflite` files and shows each tensor's type,
scale and zero point; `model.summary()` and `keras.utils.plot_model` are the in-code options.

## Open proposals (Claude's, not decided)

- **P1. Input kinds.** Regular series (with an optional sample rate as documentation), event
  sequences (window = N events, Δt as a feature), images, scalars, and variable-length sets in a
  fixed form.
- **P2. Output kinds.** Class (single or multi-label), value, reconstruction with an anomaly
  score, grid, signal. Each kind brings its loss, metric and its own accuracy gate.
- **P3. Architecture.** One branch per input (template plus parameters), a combiner, one head per
  output. A single input and output remain the short form. The board fit check (D4) is what keeps
  the architecture decision with the author.
- **P4. Windows and splits.** Allow overlapping training windows (window size plus stride), and
  prevent leakage by splitting before windowing, by file or contiguous block. Use the splits a
  dataset ships with where they exist (speaker- or patient-disjoint).
- **P5. The input contract in the export.** Caravan computes input scaling from the training data
  (today there is none) and exports channel order, window, scaling, label order and the
  input/output names. The names matter because the TFLite converter does not reliably keep input
  and output order. Today the C header carries only the byte array: label order is not exported.
- **P6. Run directory naming.** `runs/<model name>/<n>/` with a `latest` link, the manifest digest
  moving into `report.json`, and a `caravan runs` listing. For comparison, Ludwig uses
  `results/<experiment>_<model>_<n>`, and `run_<n>` without names.
- **P7. Data observations, report only.** Measured sample rate and gaps where a time column
  exists, per-channel range, clipping, constant channels. Windows across a detected gap are
  discarded and counted, as mixed windows are today.
