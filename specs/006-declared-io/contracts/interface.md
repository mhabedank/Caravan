# Contract: the interface contract in the export

Two files carry it: `model/interface.json` for any reader, and the existing C header and source
for a runner. Both are written by the export stage. Both are byte-identical across two exports of
the same quantized model (FR-027), and both are listed in `export.json` with size and digest.

Every number about a tensor is **read from the converted model file**, never taken from the manifest
(FR-023). A declaration and a file that disagree are a defect, not something to reconcile.

## `model/interface.json`

```json
{
  "contract_version": 1,
  "model": {"name": "picket-mlp", "version": "0.1.0"},
  "model_file": "model/model.tflite",
  "runtime_binding": "by position in subgraph 0: interpreter.input(position) / interpreter.output(position)",
  "inputs": [
    {
      "name": "frames",
      "position": 0,
      "tensor_index": 0,
      "tensor_name": "serving_default_frames:0",
      "shape": [1, 64, 5],
      "element_type": "int8",
      "scale": 0.0123,
      "zero_point": -128,
      "transformation": {
        "kind": "series",
        "columns": ["can_id", "dlc", "b0", "b1", "b2"],
        "window": 64,
        "stride": 64,
        "scaling": "none"
      }
    }
  ],
  "outputs": [
    {
      "name": "attack",
      "position": 0,
      "tensor_index": 7,
      "tensor_name": "StatefulPartitionedCall_1:0",
      "shape": [1, 4],
      "element_type": "int8",
      "scale": 0.00390625,
      "zero_point": -128,
      "interpretation": {
        "kind": "class",
        "labels": ["dos", "fuzzy", "normal", "replay"],
        "decision": "argmax"
      }
    }
  ]
}
```

The numbers shown are illustrative; the fields and their meaning are the contract.

- `model` is the manifest's `model.name` and `model.version`, so the contract says which model it
  describes; the export stage reads both fields for this (Principle I).
- `position` is what the microcontroller runtime takes: `MicroInterpreter::input(size_t)` indexes
  subgraph 0's input list by position (research R5, tflite-micro `f7ed40d`). It is found from the
  SignatureDef entry named `name`, by locating its tensor index in that list.
- `tensor_index` and `tensor_name` are for desktop readers, who can also bind through the
  signature.
- `scale` and `zero_point` are `null` for a float tensor (`quantization: none`).
- `columns` is the order in which a record's values go into the last axis of the input. `window`
  is the number of consecutive records along the axis before it, and is `null` with no window.
- `scaling: "none"` is stated, not omitted, because Principle VIII requires every transformation to
  be stated and "none" is a statement.
- A feature that adds an input kind, an output kind or scaling increments `contract_version`.

Format: UTF-8, keys sorted, two-space indentation, one trailing newline, no timestamp and no path
outside the export directory.

## The C header, `model_data.h`, additions

```c
/* Interface — positions for interpreter.input(i) / interpreter.output(i), read from the model
 * file's signature, not from the manifest. Bind by these names, never by a literal index: the
 * converter does not guarantee to keep the declared order. */
/* Which model this is: the manifest's model.name and model.version. */
constexpr char g_model_data_model_name[] = "picket-mlp";
constexpr char g_model_data_model_version[] = "0.1.0";

constexpr unsigned int g_model_data_input_frames = 0;
constexpr unsigned int g_model_data_output_attack = 0;

/* Class labels of output "attack", in output-unit order. */
constexpr unsigned int g_model_data_output_attack_label_count = 4;
extern const char* const g_model_data_output_attack_labels[];
```

## The C source, `model_data.cc`, additions

```c
const char* const g_model_data_output_attack_labels[] = {
    "dos",
    "fuzzy",
    "normal",
    "replay",
};
```

The identifiers are `<array name>_model_name`, `<array name>_model_version`,
`<array name>_input_<name>`, `<array name>_output_<name>`,
`<array name>_output_<name>_label_count` and `<array name>_output_<name>_labels`. The array name
comes from feature 004, and the declared name's pattern makes every identifier valid C (research R2).

Label literals: every byte outside printable ASCII, and every `"` and `\`, is written as `\xNN`. A
literal is closed and reopened after such an escape (`"a\xc3" "\xa4b"`), because a C hex escape
continues for as long as hex digits follow (research R7).

## The runner skeleton

Feature 004's skeleton (`runner/<board>/main.cc`) calls `interpreter.input(0)` and
`interpreter.output(0)` today. It changes to `interpreter.input(g_model_data_input_frames)` and
`interpreter.output(g_model_data_output_attack)`. The skeleton is a runner, and Principle VIII in
3.0.0 says a runner binds by name. Shipping a literal index in the one runner Caravan writes
itself would teach the opposite.

## What the contract does not claim

- It does not claim that the runner skeleton builds, that a kernel is selected, or what the arena
  is. Feature 004's statements stand unchanged.
- It does not claim that raw data in a unit or a range other than the training data's will work.
  The transformation is what Caravan did, not a description of the sensor.
