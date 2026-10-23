# Quickstart: validating Release 0.1.0

Each scenario states its command and what must be true. Figures marked *to be measured* are filled
in from the actual run, never from expectation.

## 1. The console shows Caravan, the log keeps the rest

```bash
caravan export examples/picket-mlp.yaml
```

Expected:
- at most 25 lines on the console;
- no line starting with `I0000`, `W0000`, `E0000`, `Saved artifact`, `TensorSpec` or
  `fully_quantize`;
- the run directory holds `framework.log`, which contains those lines;
- `caravan export examples/picket-mlp.yaml --json | python -m json.tool` succeeds.

## 2. The switch brings the framework back

```bash
caravan export examples/picket-mlp.yaml --fresh --framework-output
```

Expected: the framework's lines appear on the console, and no `framework.log` is written.

## 3. A fixed split

```bash
pytest tests/unit/test_fixed_split.py tests/train/test_fixed_split_run.py
caravan validate tests/fixtures/manifests/invalid/cf-12-split-column-with-fractions.yaml   # exit 1, CF-12
caravan validate tests/fixtures/manifests/invalid/cf-13-split-column-as-input.yaml         # exit 1, CF-13
```

Expected:
- every window lands in the part its records name;
- a window whose records name two parts is counted in `windows_discarded_mixed_split`;
- a value such as `holdout` stops the run with DS-13, naming file, line and value.

## 4. The guide, as written

```bash
pytest tests/train/test_try_it_guide.py
```

It runs `docs/try-it.md`'s `run` blocks unchanged. The release workflow later runs every block,
including `fetch` and `install`, against the published release.

## 5. The version

```bash
pytest tests/unit/test_version.py
caravan --version          # caravan-ml 0.1.0rc1 on the candidate
```

## 6. The port (after `v0.1.0rc1`)

```bash
python ports/pace-cnn/convert.py <path to UCI HAR archive> <output dir outside the repository>
caravan export ports/pace-cnn/pace-cnn.yaml   # with dataset.source pointing at the output dir
```

Expected:
- the converter refuses an archive whose hash differs from the zoo's benchmark manifest;
- it writes 7,352 training and 2,947 test windows of 128 records each, with three training subjects
  marked `val`;
- the export either succeeds or stops at a gate with a finding that is the model's.

Numbers to record, *to be measured*:
- float and int8 accuracy on the 2,947 test windows;
- model file size;
- operators;
- the fit floors.

They are compared with the published `pace-cnn` 0.1.0, which reported 0.9230 int8 accuracy and a
14,472-byte file, and the comparison is labelled as such.

## 7. Release gate

On a candidate tag, the workflow `release.yml` must run green end to end. The release note lists the
run for each gate item.
