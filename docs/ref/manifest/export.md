# The `export` section

| Field | Type | Default |
|---|---|---|
| {mf}`export.targets` | list of strings | — required |
| {mf}`export.quantization` | string | `int8` |
| {mf}`export.formats` | list of strings | `[flatbuffer, c_array]` |
| {mf}`export.representative_samples` | integer | — required for `int8` |
| {mf}`export.test_windows` | integer | `0` |

:::{manifest-field} export.targets
**Type** `list of strings` · **Default** none — required · board identifiers from `caravan boards`, each at most once · read by
**build (the fit check), export**

**Does** — names the boards the model must fit. Before training, the fit check compares the model's
weights and a floor on its working memory against each board and fails if one cannot possibly hold
it. It also decides which runner skeletons the export writes.

**Default** — none. A model for a microcontroller without a named microcontroller has no budget,
and the budget is the reason this project exists.

**Change it** — when the hardware changes. Naming more than one board is normal and the check runs
against all of them.

**Extremes** — an unknown identifier is refused ({rule}`B-1`). A model far too large fails
the fit check in seconds with the exact shortfall, before training ({rule}`F-1`) — a
passing check is not a promise that it fits, because its figures are `estimated` lower bounds.
:::

:::{manifest-field} export.quantization
**Type** `string` · **Default** `int8` · `int8`, `float16` or `none` · read by **build (the fit check),
quantize, export**

**Does** — the numeric format the model is converted to.

**Default** — `int8`. It is what makes a model fit and run on a microcontroller, so it is the
format rather than an optimisation applied at the end.

**Change it** — rarely. `float16` or `none` exist for comparison and for hardware with a usable
floating-point unit, and both make the model larger.

**Extremes** — away from `int8` the accuracy gate has little to measure, and the model may stop
fitting the boards you named. `int8` requires `export.representative_samples`
({rule}`Q-3`).
:::

:::{manifest-field} export.formats
**Type** `list of strings` · **Default** `[flatbuffer, c_array]` · `flatbuffer`, `c_array` · read by **export**

**Does** — which forms of the model are written. `flatbuffer` is `model.tflite`; `c_array` is the
`.h` and `.cc` pair your firmware compiles.

**Default** — both, because you almost always want both: the file to inspect and the array to
build.

**Change it** — drop `c_array` if nothing will compile the model, and keep in mind that
`export.test_windows` needs it.

**Extremes** — `onnx` is refused rather than silently ignored ({rule}`X-1`).
:::

:::{manifest-field} export.representative_samples
**Type** `integer` · **Default** none — required for `int8` · at least 100 · read by **quantize**

**Does** — how many training windows are run through the model to learn the range of every tensor,
which is what int8 conversion needs in order to choose its scales.

**Default** — none, and it is required for `int8`, because a calibration set chosen for you is a
silent accuracy decision.

**Change it** — raise it when the gate fails and you suspect calibration rather than the model.
When the training part holds fewer windows than you ask for, all of them are used and the report
says so.

**Extremes** — too few and the scales are set by an unrepresentative sample, which costs accuracy
in exactly the way the gate then catches. Very many only costs conversion time
({rule}`CF-4`).
:::

:::{manifest-field} export.test_windows
**Type** `integer` · **Default** `0` · 0 to 64; above 0 needs `c_array` in `export.formats` · read by **export**

**Does** — writes `model/test_windows.h`: that many windows of the test part as raw values, every
class in turn, together with what the data says and what the int8 model answered on your computer.
A [board run](../../intro/tutorial03.md) compares the board's answers with these.

**Default** — `0`, which writes none. Your data enters an export only when you ask it to, and that
default is the safe one.

**Change it** — set it to 16 before [part 3 of the tutorial](../../intro/tutorial03.md). Without it, "the board works" can only mean "the board
did not crash".

**Extremes** — when the test part holds fewer windows than you ask for, all of them are written and
`export.json` says so. The upper bound of 64 keeps the generated header readable and the board run
short. Remember that these windows are **your data, in a header file**: it is a file to keep out of
anything you publish.
:::
