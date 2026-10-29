# Choose a budget

**Goal:** an {mf}`accuracy_drop_max <output_features[].accuracy_drop_max>` for your model that you
can justify from the numbers your own run printed. For a `number` output the same steps choose
{mf}`mae_increase_max <output_features[].mae_increase_max>`, in the column's own unit.

**You need:** a manifest that already runs end to end, as at the end of
[part 2 of the tutorial](../intro/tutorial02.md).

## 1. Decide what a wrong answer costs

The {term}`budget` is a product decision written in a modelling file. Start from what the model
does when it is wrong:

| The model's answer | Start at |
|---|---|
| is checked by a person or a second system | `0.02` to `0.05` |
| acts on its own: a cut-off, an alarm, a refusal | `0.01` or tighter |
| is not yet decided | `0.02` |

## 2. Run once and read what quantization cost

```bash
caravan export manifest.yaml
run=$(ls -td runs/*/ | head -1)
python3 - "$run" <<'PY'
import json, sys
gate = json.load(open(sys.argv[1] + "quantization.json"))["gate"]
print("trained:  ", gate["trained"])
print("int8:     ", gate["quantized"])
print("cost:     ", gate["change"], "against a budget of", gate["budget"])
print("verdict:  ", gate["verdict"])
PY
```

`cost` is what making the model 8-bit took from it on the {term}`test part`. These figures are the
trained and the int8 model run on your computer; they are not figures about a board.

## 3. Set the number

- **The cost is well under your starting point.** Keep the starting point. The model quantizes
  cleanly, and a budget tighter than the cost you need is a gate that refuses for no reason.
- **The cost is above it.** The run failed and wrote `quantization-error.csv`, which names the
  layer that turned 8-bit worst. Change the model, or raise
  {mf}`export.representative_samples` if calibration is the suspect — not the budget, unless step 1
  allows a larger one.
- **A cost of `0.0`.** The decisions sit far from the boundary. Keep the budget from step 1: the
  next dataset may not be as kind.

To try another number, change it and run {cmd}`caravan quantize`. Only the quantize
{term}`stage` reads the budget, so the trained model comes from the cache and the answer arrives in
seconds.

## 4. Write the reason beside it

```yaml
output_features:
  - name: state
    type: binary
    accuracy_drop_max: 0.01   # acts on its own: a false fault stops the line. Cost on 2026-10-29: 0.0
```

## Result

A budget chosen from what a wrong answer costs, checked against what your own run measured, with
the reason in the manifest where the next reader finds it. The
{term}`quantization gate` holds every later run to it (rule {rule}`Q-4`).
[Budgets and gates](../topics/budgets-and-gates.md) explains the gate in full.
