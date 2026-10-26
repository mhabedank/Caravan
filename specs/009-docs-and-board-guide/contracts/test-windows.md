# Contract: `model/test_windows.h`

What the export writes when `export.test_windows > 0`, and what a firmware may rely on. The board
guide's firmware (`examples/lora32/src/main.cc`) uses only what is listed here. That is why it
works unchanged for any model exported with test windows (spec, Story 4, scenario 2).

## Includes

```c++
#include "model_data.h"                 // the named positions and label names (features 004, 006, 008)
#include "tensorflow/lite/micro/micro_interpreter.h"
```

Everything below lives in `namespace caravan_windows`. Every array is `static const`, because the
header is included from exactly one translation unit. The header says so in a comment.

## Constants

| Name | Type | Meaning |
|---|---|---|
| `kCount` | `int` | windows in this header (`N`, ≥ 1) |
| `kOutputCount` | `int` | elements of the output tensor (classes for a category, 1 for binary and number) |
| `kOutputType` | `enum OutputType { kCategory, kBinary, kNumber }` | the output feature's type |
| `kScoreStep` | `float` | one quantization step of the output, in output units |
| `kModelName`, `kModelVersion` | `const char*` | aliases of the header's model name and version |

## Data

| Name | Shape | Meaning |
|---|---|---|
| `k<Input>` for each input feature | `[kCount][elements]` of the input's boundary C type | raw values, as a sensor would give them |
| `kExpected` | `[kCount]` `int` (category, binary) or `float` (number) | what the data says |
| `kHostScores` | `[kCount][kOutputCount]` `float` | the int8 model's output on the host |
| `kHostDecision` | `[kCount]` `int` or `float` | the host's decision under `Decide` |

## Functions

```c++
// Copies window i into every input tensor, by the named positions of model_data.h.
// Returns false when an input's type or size is not what the header was generated for.
inline bool FillWindow(tflite::MicroInterpreter& interpreter, int i);

// The decision under the output's rule: argmax (category), threshold from model_data.h (binary),
// the value itself (number). The same rule the host applied to kHostScores.
inline float Decide(const float* scores);

// A short printable name for a decision: the label for category and binary, the value for number.
// Writes into buf (at least 24 bytes) and returns it.
inline const char* DecisionName(float decision, char* buf);
```

## Agreement, as the firmware computes it

| Output type | Agrees when |
|---|---|
| category, binary | `Decide(board) == kHostDecision[i]` |
| number | `fabs(Decide(board) - kHostDecision[i]) <= kScoreStep` |

For every type, the largest `|board − host|` over all scores, in units of `kScoreStep`, is reported
as `max_score_diff_steps`. SC-002 requires agreement on every window and
`max_score_diff_steps ≤ 1`.

## Provenance comment

The header's first comment states:
- the model name and version;
- the run directory name;
- the dataset version;
- `split: test`;
- the selection rule (round-robin by class, or test order);
- the windows asked for, written and available;
- that the host reference is the int8 model run by the measurement runtime, with its version.

## Not in this header

- The interpreter, the arena, the resolver call or any output handling. Those are the firmware's.
- Any timing (FR-006).
- Any preprocessing. The model does it (feature 008).
