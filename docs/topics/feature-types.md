# Feature types: `number`, `category`, `binary`, `image` and `anomaly`

:::{admonition} You will learn
:class: learn
- the one question that decides a column's type;
- what `number`, `category` and `binary` each learn from your data;
- what an `image` input is, and why the device passes the camera's bytes unchanged;
- what an `anomaly` output answers, and where its threshold comes from;
- what your firmware passes for each type;
- why the preprocessing lives inside the model.
:::

Every column the model reads is declared with a **{term}`feature type`**. The type decides three things: what the
model is told about that column, what preprocessing is learned from your data, and what your
firmware passes at run time.

The names follow [Ludwig](https://ludwig.ai)'s, because Caravan borrowed the idea of declaring a
type per column from it rather than inventing a vocabulary. Only the types that can run inside a
model on a microcontroller exist here.

## The one decision that matters

**Is 2 between 1 and 3?**

- **Yes** → `number`. A temperature, a voltage, a count, a duty cycle. The distance between values
  means something.
- **No** → `category`. A CAN identifier, a gear position, a device id, an error code, a mode name.
  The values are labels that happen to be written down somehow.
- **Exactly two values** → `binary`. Open or closed, present or absent, ok or fault.

One column is not a reading at all: a column that names an **image file** per record is `image`,
and it gets its own section below.

The mistake worth naming: **a column written as numbers can still be a category.** CAN id 0x201 is
not "between" 0x200 and 0x202 in any sense that matters to the model. Declaring it `number` tells
the model to interpolate between device identities, and it will — producing a model that works on
your test split and makes no sense on a bus with one new device.

## `number`

**Passed as:** `float32`, one value per column per time step.

**What is learned from your data:** a shift and a scale, the {term}`normalization`, from the
{term}`training part` only, so that the model sees values around zero rather than around 40.0 or
0.002. Which shift and scale depends on
{mf}`normalization <input_features[].preprocessing.normalization>`:

| `normalization` | Learns | Reach for it when |
|---|---|---|
| `zscore` (default) | the mean and the standard deviation | the column is bell-shaped |
| `minmax` | the minimum and the range | the column has hard physical limits |
| `iq` | the median and the interquartile range | the column has outliers you do not want setting the scale |
| `null` | nothing; the value is passed through | the column is already in a sane range and you want no surprises |

**A missing reading** — an empty cell — is filled with
{mf}`fill_value <input_features[].preprocessing.fill_value>`, which defaults to `0.0`. With
{mf}`missing_value_strategy <input_features[].preprocessing.missing_value_strategy>`:
`fill_with_mean` it is filled with the training part's mean instead, the better answer for a
sensor, because zero is a real temperature.

## `category`

**Passed as:** `int32` — a code, not the text.

**What is learned from your data:** a {term}`vocabulary`. The
{mf}`most_common <input_features[].preprocessing.most_common>` most frequent values in the
{term}`training part` (default 32), ordered by frequency and then alphabetically. Everything else, including
anything your board sees that was never in your data, becomes a single "unknown" entry. That entry
is the reason an unfamiliar device id does not crash the model.

**What your firmware passes:**

- for a column that is already integers, the integer itself;
- for a column of text, the code that `model/interface.json`, the {term}`interface contract`,
  lists for each value. Your firmware
  does the lookup, and the run writes the table for it.

**{mf}`encoder.type <input_features[].encoder.type>`** decides how the model represents the code
internally: `dense` (the default) gives
each value a short learned vector — an *embedding* — and `onehot` gives it one position per value.
`dense` is smaller as soon as the vocabulary is more than a handful, and `embedding_size` defaults
to the smaller of the vocabulary size and 4.

**Pinning the vocabulary.** Give {mf}`vocab <input_features[].preprocessing.vocab>` a list and that order is fixed, which matters
when the model's codes must stay stable across retrains — because your firmware has the old table
compiled into it.

## `binary`

**Passed as:** `int32`, 0 or 1.

Ludwig's spellings are recognised without being told: `yes`/`no`, `true`/`false`, `1`/`0`,
`on`/`off` and the like.

**For two spellings of your own** — `ok`/`fault`, `open`/`closed` — the one that sorts second
becomes true unless you say otherwise. That rule is arbitrary, so say otherwise with
{mf}`fallback_true_label <input_features[].preprocessing.fallback_true_label>`:

```yaml
preprocessing: {fallback_true_label: fault}
```

## `image`

**Passed as:** `uint8`, the raw pixels at the declared size, rows then columns then channels — the
camera's bytes as they arrive, with a scale of 1 and a zero point of 0.

**What the data looks like:** one record per image. The column holds a file name relative to the
dataset directory, the way Ludwig reads images, and another column holds the label. PNG,
JPEG, BMP and GIF files are read.

**What is learned from your data:** the size. When every image has the same height, width and number
of channels, those are taken from the images; when they differ, state
{mf}`height <input_features[].preprocessing.height>`,
{mf}`width <input_features[].preprocessing.width>` and
{mf}`num_channels <input_features[].preprocessing.num_channels>` — the size the device's camera, or
the firmware's crop, delivers. Images of another size are brought to it for training by
{mf}`resize_method <input_features[].preprocessing.resize_method>`. The model itself does not
resize: the device passes frames of exactly the declared size.

**What it changes about the rest of the manifest:**

- an image is the model's **only** input — no other column beside it ({rule}`CF-19`);
- one record is one sample, so there is no {mf}`preprocessing.window_size`;
- the template is `conv2d`, the one that takes an image ([Templates](templates.md)).

Scaling the pixels to the range the network trained on happens inside the model, exactly as for a
`number`. That is why the firmware passes bytes and not floats: no scaling code to port, and no
float copy of the frame in the board's working memory.

## `anomaly`, an output type

The types above are what a model *reads*. An output is declared the same way, with `category`,
`binary` or `number` for a model that names a class, says yes or no, or gives a value. `anomaly`
exists only on the output side.

**What it answers:** how unusual a window is — the {term}`anomaly score`, one number per window. It is
the `autoencoder` template's output and only that template's ([Templates](templates.md)).

**What the column holds:** the label that tells normal windows from abnormal ones.
{mf}`normal_label <output_features[].preprocessing.normal_label>` names the value that means normal
(default `normal`), and every other value is abnormal. Training uses the normal windows of the
training part only; the abnormal ones are there so the run can measure how well the score separates
the two.

**What is learned from your data:** the **threshold**. After quantization, the run scores the
validation part's normal windows with the int8 model and takes the
{mf}`threshold_percentile <output_features[].threshold_percentile>`-th percentile, 95 by default: at
95, about one normal window in twenty raises an alarm. `quantization.json` records the threshold
with the detection and false alarm rates it gives on the test part, and `model/interface.json`
states it, so your firmware compares one number with another: abnormal when the score is at or
above the threshold.

**Its {term}`budget`** is {mf}`auc_drop_max <output_features[].auc_drop_max>`, how much of the area
under the ROC (receiver operating characteristic) curve 8-bit may cost.
[Budgets and gates](budgets-and-gates.md) says what that area measures.

## Where the preprocessing lives

**Inside the model.** This is what makes the export portable.

The scaling of a number and the lookup of a category are not Python that you have to port to C.
They are learned from the training part and then built into the model as layers, so the exported
`.tflite` and its C array take **raw sensor values** and do the rest themselves.

That matters for a reason that is easy to miss until it bites: a preprocessing step that lives
outside the model is a second implementation. Your computer scales with one line of Python, your
firmware scales with one line of C, the two round differently, and the board quietly disagrees with
your test results. There is nothing to disagree about here.

What each column learned is written to `data/preprocessing.json` in every run, so you can read the
numbers rather than trust them.

## Columns you do not name

A column no feature names is ignored, and every run lists it under `ignored_columns`. There is no
`exclude` list to maintain: naming a column is how you opt it in.

:::{seealso}
Every field of a feature, with its default and when to change it:
[the input features](../ref/manifest/input-features.md),
[the output features](../ref/manifest/output-features.md) and
[the `defaults` section](../ref/manifest/defaults.md).
:::
