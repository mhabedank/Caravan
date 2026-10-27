# What a run leaves behind

Every `caravan export` writes one directory, `runs/<time>-<digest>/`, and never touches an earlier
one. Re-running does not overwrite; it adds. The digest is of the manifest as resolved, so two runs
with the same inputs are recognisable as such.

You do not need most of these files. They are listed so that when you do need one, you know it
exists.

## The four you will actually open

**`model/model_data.h` and `model/model_data.cc`** — your model as a C array, with its length. This
is what your firmware compiles. The header names a position for every input and the output, each
with its element type, and the label names.

**`model/interface.json`** — the contract. Every input by name, with its position in the converted
model, its shape, its element type, its quantization scale and zero point, what was learned for it,
and what to pass when a reading is missing; and what the output means. Bind by **name**, never by
position: the converter does not promise to keep your declared order.

**`quantization.json`** — what making the model 8-bit cost, and the gate's verdict.

**`metrics.json`** — the trained model's accuracy and confusion matrix on the test part.

## The rest, by what you would want it for

| File | Answers |
|---|---|
| `report.json` | "What happened in this run?" Every stage, the data, the metrics with what they were measured on, the fit check, the gate's verdict, the interface |
| `resolved-manifest.yaml` | "What did the pipeline actually use?" Your manifest with every default filled in and everything learned from the data written down |
| `data/schema.json` | "Which columns were read, and which ignored?" Also how the windows were split |
| `data/preprocessing.json` | "What did each column learn?" The shift and scale of a number, the vocabulary of a category, the order of the labels |
| `export.json` | "Which operators does this model need, and does each board accelerate them?" And the model's size |
| `model/model.tflite` | The int8 model as a file, for anything that reads TensorFlow Lite |
| `model/resolver.h` | Exactly the operators this model needs, for the microcontroller runtime — so the firmware carries those kernels and not the whole set |
| `model/fit.json` | The lower bounds on flash and RAM against each board, labelled <span class="prov estimated">estimated</span> |
| `model/test_windows.h` | Windows of the test part as raw values, with what the int8 model answered on your computer — for a board to run and compare |
| `runner/<board>/main.cc` | A starting point for firmware on each board you named, filling every input by name |
| `framework.log` | What the training framework printed, kept here rather than on your console |

## Two that exist for a specific reason

**`model/test_windows.h`** is how you find out whether your board agrees with your computer. It
holds real windows and the answers your machine gave for them, so firmware can run the same inputs
and compare. Without it, "the board works" means "the board did not crash". Leg 3 of the route uses
it. It is written only when `export.test_windows` asks for it.

**`model/resolver.h`** exists because the microcontroller runtime can either carry every operator it
knows or exactly the ones your model uses, and the difference is flash you do not have. The file is
generated from the model, so it cannot drift from it.

## What is not here

**Your data.** Caravan reads it and records its digest; it does not copy it into the run directory,
and nothing it writes contains your rows. Keeping the data out of anything you publish is your
decision to make, and Caravan does not take it away from you by quietly duplicating the file.

**Credentials.** A stage fails if it finds one in the repository, in a manifest or in a board
description, and never writes one into a report, a log or an exported artifact.

## Why they are kept

Every number Caravan reports about hardware carries one of
<span class="prov estimated">estimated</span>, <span class="prov emulated">emulated</span> or
<span class="prov measured">measured</span>, and the run directory is where that provenance lives.
A figure in a report you can trace is worth something; the same figure in a chat message is not.
