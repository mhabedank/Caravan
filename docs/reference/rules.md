# Rules

Every refusal Caravan makes carries a rule identifier. The finding names:
- the rule;
- the field path it is reported at;
- what was wrong;
- what is accepted.

Search this page for the identifier to find what it checks and how to fix it.

**Where each group comes from.**
- **On the manifest alone:** V, T, B and CF. `caravan validate` reports these.
- **On a run, when the data or a measurement disagrees with the manifest:** DS, F, Q and X. The
  run stops with exit code `1` and writes its report, but no exportable model.
- **On a board description:** E and S, for whoever adds a board.

Retired identifiers are never reused.

## Schema version

### V-1

**Checks:** the manifest declares the schema version this build reads, `apiVersion: caravan/v0.2`.

**Reported at:** `apiVersion`.

**Fix:** write the manifest in the current form. A `caravan/v0.1` manifest is refused as a whole.
[Manifest changes](../manifest-changes.md) lists each key that moved and where it went. A manifest
with no `apiVersion` is refused too, rather than guessed at.

### V-2 (retired)

Read a manifest without a version as the oldest known one. Retired by constitution 4.0.0: an
undeclared version is now V-1.

## Templates and boards

### T-1

**Checks:** `model.template` names a registered template.

**Reported at:** `model.template`.

**Fix:** use one of the names `caravan templates` lists: `mlp` or `conv1d`.

### T-2

**Checks:** `model.params` holds exactly the parameters the template accepts, with valid values.

**Reported at:** `model.params.<parameter>`.

**Fix:** see the template's parameters in the [manifest reference](manifest.md#model). Unknown or
misspelled parameters are refused, never ignored.

### B-1

**Checks:** every entry of `export.targets` is a known board.

**Reported at:** `export.targets[<index>]`.

**Fix:** use one of the names `caravan boards` lists. A board is added by a description file, not
by code ([compatibility](../compatibility.md)).

## Manifest consistency

### CF-1

**Checks:** `preprocessing.split.probabilities` has three parts, each above zero, summing to 1.

**Reported at:** `preprocessing.split.probabilities`.

**Fix:** for example `[0.7, 0.15, 0.15]`. Every part must be able to hold a window.

### CF-2

**Checks:** no board appears twice in `export.targets`.

**Reported at:** `export.targets`.

**Fix:** name each board once. Duplicates are refused, never silently removed.

### CF-3 (retired)

Personal data against a risk class: part of a compliance layer Caravan no longer carries
(constitution 3.0.0, Principle VI).

### CF-4

**Checks:** an `int8` export states `export.representative_samples`, at least 100. Calibration
data decides the quantized ranges, and too few samples are a known cause of accuracy collapse.

**Reported at:** `export.representative_samples`.

**Fix:** set it to 100 or more. When the training part holds fewer windows, all are used, and the
report says so.

### CF-5 (retired)

Publication needed a compliance block. Retired with the compliance layer (constitution 3.0.0).

### CF-6

**Checks:** a template that consumes a time window has `preprocessing.window_size`, and the window
is long enough for its layers. Both templates consume one.

**Reported at:** `preprocessing.window_size`.

**Fix:** set the window. For `conv1d`, the finding says which block the window ran out at, and the
smallest window that works.

### CF-7 (retired)

Every target needed an emulator. Retired: a board without emulator support says so in its
description and is verified on the next rung (constitution 3.0.0).

### CF-8 (retired)

Benchmark-only data could not be published. Retired with the compliance layer (constitution 3.0.0).

### CF-9

**Checks:** each feature name has the form `[a-z][a-z0-9_]{0,31}`, and no column is named twice.
The name is what a firmware binds by, in C and in the model's signature.

**Reported at:** `input_features[<index>].name` or `output_features[0].name`.

**Fix:** rename the column in your data to that form, or name it once.

### CF-10 (retired)

Allowed exactly one input and one output. Retired by `caravan/v0.2`: any number of input features
is allowed, and exactly one output is CF-17.

### CF-11

**Checks:** no input feature reads the output's column. A model would be trained on its own answer.

**Reported at:** `input_features[<index>].name`.

**Fix:** remove that column from `input_features`.

### CF-12

**Checks:** for `preprocessing.split.type: fixed`:
- `column` is given;
- `probabilities` is not, because the data decides the parts and the fractions would be silently
  overridden.

**Reported at:** `preprocessing.split.column` or `preprocessing.split.probabilities`.

**Fix:** a fixed split takes `{type: fixed, column: <column>}` and nothing else.

### CF-13

**Checks:** the split column is neither an input feature nor the output. A model would learn which
part a sample is in.

**Reported at:** `preprocessing.split.column`.

**Fix:** take the column out of `input_features`, or split on another column.

### CF-14

**Checks:** each feature's `type` is one this build implements:
- inputs `number`, `category`, `binary`;
- outputs `category`, `binary`, `number`.

Each type brings its preprocessing into the model, and only types with a path to the device exist.

**Reported at:** `input_features[<index>].type` or `output_features[0].type`.

**Fix:** use one of the implemented types. [Compatibility](../compatibility.md) says why Ludwig's
other types are absent.

### CF-15

**Checks:** `stratify` splits by the output's classes: its `column` is the output's column, and
the output is not a `number`.

**Reported at:** `preprocessing.split.column` or `preprocessing.split.type`.

**Fix:** leave `column` out (it defaults to the output's), or use `random` for a `number` output.

### CF-16

**Checks:** the int8 budget matches the output type, and is given:
- `accuracy_drop_max` for `category` and `binary`;
- `mae_increase_max` for `number`.

**Reported at:** `output_features[0].accuracy_drop_max` or `output_features[0].mae_increase_max`.

**Fix:** state the budget that fits the type ([budgets](../budgets.md)).

### CF-17

**Checks:** exactly one output feature.

**Reported at:** `output_features`.

**Fix:** list one output. A model that answers two questions is two models.

## Data

These fire when a run reads the data. The manifest can be valid while the data disagrees with it.

### DS-1

**Checks:** `dataset` points at something readable:
- a directory whose own files are the data;
- or a single `.csv`, `.tsv` or `.txt` file.

**Reported at:** `dataset`.

**Fix:** point at the directory or file, relative to the manifest.

### DS-2

**Checks:** each data file has a header row and at least one record, and the output's column
appears in it exactly once.

**Reported at:** `dataset` or `output_features[0].name`.

**Fix:** add the header row, or name the output by a column the header has.

### DS-3

**Checks:** every file of one dataset carries the same header. They are read as one sequence.

**Reported at:** `dataset`.

**Fix:** make the headers identical, or keep different files in different datasets.

### DS-4

**Checks:** every cell is readable:
- a number column holds numbers;
- every record has as many values as the header.

**Reported at:** `dataset`, naming the file, the record and the column.

**Fix:** correct that cell or record. An empty cell is a missing reading, which `fill_value`
handles.

### DS-5

**Checks:** a pinned `output_features[0].preprocessing.vocab` names every class of the data, and
only those.

**Reported at:** `output_features[0].preprocessing.vocab`.

**Fix:** add the classes the finding names, or remove the ones the data does not have. Or leave
`vocab` out, and the order is derived.

### DS-6

**Checks:** the data forms at least one window: enough records, and windows whose records agree on
the output.

**Reported at:** `preprocessing.window_size`.

**Fix:** a smaller window, or more data. The report counts discarded windows.

### DS-7 (reserved)

DS-7 can never fire: the feature width comes from the data, so nothing can disagree with it. Kept
reserved rather than renumbering.

### DS-8

**Checks:** each part of the split (train, validation, test) receives at least one window.

**Reported at:** `preprocessing.split.probabilities`.

**Fix:** more data, a smaller window, or larger fractions for the empty part.

### DS-9 (retired)

Training not permitted by a data declaration. Retired with the compliance layer (constitution
3.0.0).

### DS-10

**Checks:** training did not diverge. The loss stayed finite.

**Reported at:** `trainer.learning_rate`.

**Fix:** a smaller learning rate. The finding names the epoch and the loss.

### DS-11

**Checks:** the output column holds at least two distinct values: something to classify.

**Reported at:** `output_features[0].name`.

**Fix:** a dataset with more than one class, or a `number` output.

### DS-12

**Checks:** every feature names a column of the data.

**Reported at:** `input_features[<index>].name`.

**Fix:** the finding lists the columns the data has. Use one of them, spelled exactly.

### DS-13

**Checks:** for a `fixed` split, every file has the split column, and every record names its part
as `train`, `validation` or `test`, or as `0`, `1` or `2`.

**Reported at:** `preprocessing.split.column`.

**Fix:** correct the record the finding names.

### DS-14

**Checks:** every class of the output occurs in the training part. A class only in validation or
test could not be learned.

**Reported at:** `output_features[0]`, naming the classes.

**Fix:** with a `fixed` split, move some of that class's records into training. Otherwise, use more
data or `stratify`.

### DS-15

**Checks:** a `binary` column has at most two spellings that are not Ludwig's standard ones, or
states which one is true.

**Reported at:** the feature's `preprocessing`.

**Fix:** set `preprocessing.fallback_true_label` to the spelling that means true, or clean the
column.

## Fit check

### F-1

**Checks:** before training, the model's computed lower bounds on flash and working memory fit
every target board. A lower bound that exceeds the board means no training can make the model fit.

**Reported at:** `export.targets`.

**Fix:** a smaller model (fewer or narrower layers, a smaller embedding), or a larger board. The
finding gives each bound against each board.

## Quantization

### Q-1

**Checks:** the trained model of the run can be read.

**Reported at:** the trained model's path.

**Fix:** run again with `--fresh` to rebuild it.

### Q-2

**Checks:** the conversion to the stated quantization succeeded.

**Reported at:** `export.quantization`.

**Fix:** the finding carries the converter's error. A layer the converter cannot handle is a
template defect: report it.

### Q-3

**Checks:** an `int8` result is integer inside, read from the model file's tensors, not from the
converter's word. Only the boundary may be float: raw values in, the answer out.

**Reported at:** `export.quantization`.

**Fix:** none on your side. The finding names the floating tensors. Report it as a defect.

### Q-4

**Checks:** the accuracy gate. Quantization cost no more than the budget on the test part:
- accuracy, against `accuracy_drop_max`;
- or the mean absolute error, against `mae_increase_max`.

**Reported at:** `output_features[0].accuracy_drop_max` or `output_features[0].mae_increase_max`.

**Fix:** read the per-layer error table the run wrote. It shows which layer lost the accuracy. Then:
- more `representative_samples`;
- or a model that quantizes better.

Raising the budget is a decision about the model, and the report records it.

### Q-5

**Checks:** the test part has samples, so the gate can be measured at all.

**Reported at:** `preprocessing.split.probabilities`.

**Fix:** more data or a larger test fraction.

## Export

### X-1

**Checks:** every format in `export.formats` is one Caravan can produce: `flatbuffer`, `c_array`.

**Reported at:** `export.formats`.

**Fix:** remove the format. Nothing is written when one is refused.

### X-2

**Checks:** the run has a quantized model to export.

**Reported at:** `export.formats`.

**Fix:** run `caravan quantize` first. A failed accuracy gate leaves nothing exportable.

### X-3

**Checks:** the model has a single subgraph.

**Reported at:** `export.formats`.

**Fix:** none on your side: report it as a defect.

### X-4

**Checks:** every operator of the model has a public registration method in TensorFlow Lite Micro.

**Reported at:** `export.formats`, naming the operator.

**Fix:** none on your side. Caravan refuses the run rather than writing a resolver that would not
compile. Report it.

### X-5 (reserved)

X-5 can never fire: board descriptions admit only accelerator libraries with sourced coverage data.
Kept reserved.

### X-6

**Checks:** every declared input and output name is in the converted model's signature. The
firmware binds by these names.

**Reported at:** the feature's name.

**Fix:** none on your side: report it as a defect.

## Board descriptions

For whoever adds a board under `src/caravan/targets/boards/`.

### E-1

**Checks:** a board's emulator platform is one that exists, or `null` with the reason in
`sources`.

**Reported at:** `<board>.emulator.platform`.

**Fix:** name a real platform, or state `emulator: null` and why.

### S-1

**Checks:** every value of a board description carries a source a reader can check.

**Reported at:** `<board>.sources`.

**Fix:** add the missing citations.

## Informational

### D-1

**Records:** that the dataset reference was deliberately not resolved, because `validate` does not
read data. It refuses nothing.
