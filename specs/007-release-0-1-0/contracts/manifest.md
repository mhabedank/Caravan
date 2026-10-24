# Contract: the fixed split

Schema version stays `caravan/v0.1`. The addition is optional, so every existing manifest keeps
validating, and no version change or change note is needed (constitution 4.0.0, Principle IX: a new
optional field is not a breaking change).

```yaml
dataset:
  source: data/
  split:
    column: split
```

Each record's `split` value is `train`, `val` or `test`. In order:

1. **Validation** refuses the manifest when:
   - fractions or `stratified` are stated with `column` (CF-12): "a fixed split takes its parts from
     the column `split`; fractions and stratified would be ignored, so they are not accepted";
   - the column is the output column or a stated input column (CF-13).
2. **The data stage** reads the column like the label column. Rule DS-13 fires when it is missing,
   or when a record holds another value; the finding names the file, the line and the value.
3. **Derived input columns** leave the split column out, as they leave out the output column.
4. **Windows.**
   - A window whose records name one part goes to that part.
   - A window whose records name different parts is discarded and counted.
   - A window whose records disagree on the label is discarded as before. When both apply, it
     counts as mixed by label.
5. **Empty parts.** A part with no window fails with the existing empty-split rule, naming the
   column.
6. **Calibration** draws `representative_samples` from the training part only, as before.

`caravan render` prints the split as written. The run report records `split_source` and the
discarded count.
