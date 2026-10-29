# The `trainer` section

| Field | Type | Default |
|---|---|---|
| {mf}`trainer.epochs` | integer | `50` |
| {mf}`trainer.batch_size` | integer | `256` |
| {mf}`trainer.learning_rate` | number | `0.001` |
| {mf}`trainer.optimizer.type` | string | `adam` |
| {mf}`trainer.early_stop` | integer | `5` |

:::{manifest-field} trainer.epochs
**Type** `integer` · **Default** `50` · at least 1 · read by **train**

**Does** — the maximum number of passes over the training part. {mf}`trainer.early_stop` ends training
sooner when the validation loss stops improving, and the best checkpoint is kept rather than the last.

**Default** — `50`, enough for a small model on a small dataset to converge.

**Change it** — raise it when training is still improving when it stops; lower it to iterate faster
while you are still deciding on columns and types.

**Extremes** — too few and the model never converges; too many costs time but little else, because
the best checkpoint is what is kept.
:::

:::{manifest-field} trainer.batch_size
**Type** `integer` · **Default** `256` · at least 1 · read by **train**

**Does** — how many windows the model sees before each weight update.

**Default** — `256`, which trains quickly on a dataset of a few thousand windows.

**Change it** — lower it when you have few windows, so there are enough updates per epoch to learn
anything. A dataset of 80 windows and a batch of 256 gets one update per epoch.

**Extremes** — very small batches train slowly and noisily; very large ones on a small dataset
barely train at all.
:::

:::{manifest-field} trainer.learning_rate
**Type** `number` · **Default** `0.001` · greater than 0 · read by **train**

**Does** — how far the weights move at each update.

**Default** — `0.001`, the conventional starting point for the default optimizer.

**Change it** — lower it when the loss jumps around or diverges; raise it when training is
converging far too slowly to wait for.

**Extremes** — too high and the loss diverges or oscillates and never settles; too low and training
ends on `epochs` long before it has learned anything ({rule}`DS-10`).
:::

:::{manifest-field} trainer.optimizer.type
**Type** `string` · **Default** `adam` · `adam`, `sgd` or `adamw` · read by **train**

**Does** — chooses the algorithm that applies the updates.

**Default** — `adam`, which needs the least tuning and is why the default learning rate works
without being thought about.

**Change it** — `adamw` when the model overfits and you want weight decay as well as `dropout`;
`sgd` only when you are deliberately reproducing a recipe that asks for it.

**Extremes** — `sgd` at the learning rate chosen for `adam` trains badly: the two want
different rates, so changing the optimizer means revisiting `learning_rate`.
:::

:::{manifest-field} trainer.early_stop
**Type** `integer` · **Default** `5` · epochs without an improvement in validation loss before stopping; `-1`
never stops · read by **train**

**Does** — stops training when the validation loss has not improved for this many epochs, and keeps
the best checkpoint rather than the last.

**Default** — `5`, patient enough to ride out a noisy epoch and short enough not to waste minutes.

**Change it** — raise it when your validation loss is noisy on a small validation part; set `-1`
when you want all `epochs` regardless.

**Extremes** — `1` stops on the first bad epoch, which on a small validation part is luck rather
than evidence. `-1` with large `epochs` is only slower, since the best checkpoint still wins.
:::
