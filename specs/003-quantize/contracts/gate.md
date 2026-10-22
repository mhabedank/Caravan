# Contract: The Accuracy Gate

Date: 2026-10-22 · Feature: 003 · Decisions: R6, R7 in [research.md](../research.md)

This is the project's first budget in the constitution's sense: a number the author writes that
decides whether a run produces an artifact. Principle V governs it completely, so this document is
mostly that principle made concrete.

## The three numbers, and which two the gate judges

| Figure | Measured with | Answers |
|---|---|---|
| `trained` | the training framework | what training achieved |
| `converted` | the runtime, on the unquantized conversion | what **conversion** cost |
| `quantized` | the runtime, on the deployed model | what the deployed model does |

```text
conversion_drop   = trained   - converted      # recorded
quantization_drop = converted - quantized      # judged
verdict           = quantization_drop <= export.accuracy_drop_max
```

The gate judges the second difference because `accuracy_drop_max` is "the maximum accuracy loss
accepted from quantization" (Principle V), and that is the loss from quantization. The first
difference is recorded next to it so a loss caused by conversion cannot hide inside a passing gate:
with one baseline the two are a single number, and a threshold on their sum either fails runs for
the wrong reason or passes them while conversion quietly cost something.

All three are measured on the **test split**, against the same dataset version, in the same run.
None is read from an earlier run's report — that would compare a measurement with a memory.

## The arithmetic, exactly

- The threshold is an **absolute difference**. `accuracy_drop_max: 0.02` means two points of
  accuracy, not two percent of the accuracy.
- **The comparison is made on the numbers as recorded**, to six decimals. This is not cosmetic:
  `0.90 - 0.88` is `0.020000000000000018` in binary floating point, so an unrounded comparison
  would fail a run whose report says the drop was `0.020000` against a threshold of `0.02` — the
  document would contradict its own verdict, and a reader recomputing it would get the other
  answer. The verdict a report carries must be the verdict its numbers produce.
- The comparison is `<=`: a drop exactly equal to the threshold **passes**. The author wrote the
  number they accept, and a number you accept is one you accept. One consequence is worth stating
  because it is surprising: a threshold of `0.0` does **not** fail a run whose quantization cost
  nothing, since `0.000 <= 0.000`. On the committed fixture that is exactly what happens, which is
  why the failure path is exercised by constructing the arithmetic rather than by tightening a
  threshold and hoping.
- A **negative** drop — the quantized model scoring higher — passes, and is recorded as negative
  rather than clamped to zero. Clamping would hide a measurement worth looking at.
- `resolution = 1 / samples` is recorded with the verdict. On the committed fixture that is 1/12 ≈
  0.083 against a threshold of 0.02, which means that split cannot resolve the threshold, and the
  message says so. A verdict whose resolution is coarser than its threshold is still the verdict —
  the author's number decides — but it is reported with the fact that makes it readable.

## What a failure does

1. The run fails with exit **1** and a machine-readable reason: rule `Q-4`, a finding naming
   `export.accuracy_drop_max`, and an entry in the report's `gates` list with both numbers.
2. **No quantized model survives.** The stage writes into a private directory that is only
   published when it finishes, so a failed gate leaves nothing behind — the same mechanism feature
   002 used for a diverged training run. A failed gate must leave no publishable artifact, and the
   way to guarantee that is to never have moved one into place.
3. **The per-layer error table is emitted** — into `quantization-error.csv` and into the report —
   because the constitution requires a failed gate to emit what is needed to act on it, not only a
   verdict.

## The per-layer table

Columns, from the debugger's own output plus one computed value:

```text
op_name, tensor_name, num_elements, rmse, scale, rmse_over_scale, max_abs_error
```

Ordered by `rmse_over_scale` descending — worst first, because the author is looking for the layer
that cost them the accuracy.

Reported with the table, every time:

> The reference is `1 / sqrt(12)` ≈ 0.289: a tensor whose `rmse / scale` is near it quantizes well,
> and the larger the value the less well it quantized. The LiteRT quantization-debugger guide's own
> example flags layers above 0.7 as candidates for keeping in float.

**Neither number is a gate.** The gate is the author's threshold. These are evidence, and the
difference matters: a project that invented its own per-layer cutoff would be gating on a heuristic
nobody wrote in the manifest.

The table costs a second, instrumented conversion and one inference per calibration sample, which
is why it is produced on failure only. A cost paid on every successful run would be paid by
everyone to serve nobody.

## What cannot silence it

- No command-line option. The whole option surface is asserted against a list of forbidden
  substrings, inherited from feature 001 and extended here.
- No environment variable, no configuration file: the threshold is read from the manifest's
  resolved form and from nowhere else, which the stage's declared read set enforces by
  construction.
- `--fresh` recomputes; it does not bypass. A fresh run runs the same gate.
- **Unknown is not within budget**: if the comparison cannot be measured — a model that will not
  load, a split with no samples — the run fails (`Q-5`) rather than passing with an unknown.

## Where the verdict appears

| Place | Form |
|---|---|
| exit code | 0 on pass, 1 on fail |
| standard error | the human summary, with both numbers, the threshold and the resolution |
| `report.json` → `gates` | `{"name": "accuracy", "result": "pass", "detail": "quantization cost 0.000, accepted 0.020"}` |
| `report.json` → `findings` | on failure, a finding with rule `Q-4` naming `export.accuracy_drop_max` |
| `report.json` → `quantization` | the whole record, including all three accuracies |
| `quantization.json` | the same record, as the artifact the report is built from |

The gate entry and the finding are one event seen twice: by a person reading a summary, and by a
continuous integration job reading a document.
