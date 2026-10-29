# The pipeline and the CLI

:::{admonition} You will learn
:class: learn
- the five stages a manifest goes through, and what each one reads and leaves;
- which command runs which stages;
- why a change to a budget never retrains;
- where in the manifest each stage takes its decisions from.
:::

Caravan is a pipeline of five {term}`stages <stage>`: **data**, **build**, **train**, **quantize**
and **export**. A {term}`manifest` goes in at one end, and the files your firmware compiles come
out at the other. The `caravan` command runs the stages; you never call them yourself.

## The stages

| Stage | Reads from the manifest | Does | Leaves in the run directory |
|---|---|---|---|
| data | {mf}`dataset`, the features, {mf}`preprocessing.window_size`, the split | reads the named columns, cuts windows, splits them, fits each column's preprocessing on the training part | `data/schema.json`, `data/preprocessing.json` |
| build | {mf}`model.template`, {mf}`model.params`, {mf}`export.targets`, {mf}`export.quantization` | builds the model with the preprocessing inside it, then runs the {term}`fit check` | `model/fit.json` |
| train | the [trainer section](../ref/manifest/trainer.md) | trains on the training part, measures on the test part | `metrics.json` |
| quantize | {mf}`export.quantization`, {mf}`export.representative_samples`, each output's budget | converts to int8, proves the result is integer inside, measures it on the test part, runs the {term}`quantization gate` | `model/quantized.tflite`, `quantization.json` |
| export | {mf}`export.formats`, {mf}`export.test_windows` | writes the model, its C array, the operator list and the interface contract | `model/`, `runner/`, `export.json` |

Every run also writes `report.json`, the {term}`run report`, and `resolved-manifest.yaml`, the
manifest with every default and every {term}`derived` value filled in.

**Data** reads only the columns the features name; every other column is ignored and listed as
such. Windows never overlap. Everything learned from the data — a shift and a scale, a
{term}`vocabulary`, the order of the labels — is learned from the {term}`training part` only, so
the test part stays unseen. [Feature types](feature-types.md) says what each type learns.

**Build** turns the {term}`template` and its parameters into a model, with each column's
preprocessing built in as layers. The fit check then compares lower bounds on the model's flash and
RAM with each {term}`target`. A model that cannot fit is refused here, before any training
(rule {rule}`F-1`). [Templates](templates.md) explains the two templates.

**Train** trains for {mf}`trainer.epochs`, stopping early when the validation loss has not improved
for {mf}`trainer.early_stop` epochs, then measures the trained model on the {term}`test part`.

**Quantize** converts the trained model to {term}`int8`, calibrated on
{term}`representative samples`, and reads the result's tensors from the file to prove it is integer
inside. It measures the int8 model on the same test part, and the quantization gate compares the
two against the output's {term}`budget` (rule {rule}`Q-4`).
[Budgets and gates](budgets-and-gates.md) explains both checks.

**Export** writes what a firmware author compiles. The exported model is byte for byte the one the
gate measured. [What a run leaves](what-a-run-leaves.md) lists every file.

## Which command runs which stages

Each stage command runs the stages before it first, reusing whatever is cached:

| Command | Runs |
|---|---|
| {cmd}`caravan validate` | no stage: checks the manifest without reading data |
| {cmd}`caravan render` | no stage: fills in every default, prints `derived` for what only the data can say |
| {cmd}`caravan build` | data, build |
| {cmd}`caravan train` | data, build, train |
| {cmd}`caravan quantize` | data, build, train, quantize |
| {cmd}`caravan export` | all five |

{cmd}`caravan templates` and {cmd}`caravan boards` list what this version registers and run
nothing.

## The cache

Every stage's result is cached under a key made from the manifest fields that stage reads and the
version of the dataset. A stage whose inputs are unchanged is reused, not repeated.

That is why a change only a later stage reads never repeats an earlier one. Change
{mf}`accuracy_drop_max <output_features[].accuracy_drop_max>` and only quantize runs again; the
trained model comes from the cache, and the answer arrives in seconds. Change the window and
everything runs again, because data reads it.

`--fresh` ignores the cache and produces everything again, and the run report records that it did.

## Runs

Every command that runs a stage creates a {term}`run` directory, `runs/<time>-<digest>/`, and never
changes an earlier one. A run that a check refuses still writes its report: what was found, at
which field, under which [rule](../ref/rules.md), and what is accepted. It writes no exportable
model.

:::{seealso}
[The CLI reference](../ref/cli.md) — every command, its options and its exit codes.
:::
