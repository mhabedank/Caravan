# Contract: The Exported Set

**Feature**: 004 · **Date**: 2026-10-22

What a firmware author receives, and what each file promises. Everything here is a standard format
usable without Caravan, which is the whole of Principle VIII.

## The files

```text
<run>/model/model.tflite        the serialised model — the bytes the accuracy gate measured
<run>/model/model_data.cc       the same bytes as a C array
<run>/model/model_data.h        its declaration and its length
<run>/model/resolver.h          an operator resolver holding exactly this model's operators
<run>/runner/<target>/main.cc   a runner skeleton per target board
<run>/export.json               what was written, what was read, and where every number came from
```

The first four do not depend on the target. The skeleton does, because the runtime and the
accelerated library come from the board description.

## The C array

Emitted the way the runtime's own generator emits it (research R3), so that an author who has seen
one before sees nothing new:

```c
/* model_data.cc */
#include <cstdint>
#include "model_data.h"

alignas(16) const unsigned char g_model_data[] = {0x1c, 0x00, 0x00, 0x00, /* … */};
```

```c
/* model_data.h */
#include <cstdint>

constexpr unsigned int g_model_data_size = 7856;
extern const unsigned char g_model_data[];
```

- **`alignas(16)` is required**, not stylistic: the runtime needs the model buffer aligned and an
  unaligned one fails at initialisation on the target, far from this machine.
- **The bytes are the model's bytes.** A test reads the array back out of the generated source and
  compares it with the file. Equality is checked on the bytes, not on the length (FR-004).
- **The file is deterministic**: no timestamp, no path, no host name. Exporting the same model twice
  gives identical bytes, and a test asserts it by exporting twice (FR-005).

## The resolver

```c
/* resolver.h — generated; 3 operators, 4 nodes */
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"

inline tflite::MicroMutableOpResolver<3> CaravanResolver() {
  tflite::MicroMutableOpResolver<3> resolver;
  resolver.AddReshape();          /* RESHAPE v1, 1 node */
  resolver.AddFullyConnected();   /* FULLY_CONNECTED v4, 2 nodes */
  resolver.AddSoftmax();          /* SOFTMAX v2, 1 node */
  return resolver;
}
```

- The template argument is the number of distinct operators, which is what the runtime's class
  requires and what makes "one too many" cost flash.
- The method names come from an explicit table, not from a naming rule. `AddConv2D` is not
  `AddConv2d`, and the generic `AddBuiltin` is private, so an operator with no public method
  refuses the run (`X-4`) rather than generating code that fails at the author's compiler
  (research R4).
- A custom operator is emitted as `AddCustom` with its name, and the comment states that the author
  must supply the registration.

## The runner skeleton

Per target, naming the runtime that board declares, referencing the two generated headers, and
carrying the working-memory floor as a named constant:

```c
/* runner/stm32h743/main.cc — skeleton; runtime: tflm; accel: cmsis-nn */
constexpr int kArenaBytes = 2048;  /* floor 648 bytes, computed from the model file.
                                      Not the figure this board needs: the runtime adds scratch
                                      buffers and bookkeeping. Raise until init succeeds, or
                                      measure it — see the note in export.json. */
```

The skeleton is emitted and **not compiled**. Nothing in this feature cross-compiles it, so nothing
claims it builds (FR-027, research R7).

## The report

`export.json` carries the artifact list with sizes and digests, the operator records, the coverage
verdicts with their sources and dates, the two memory figures with their methods, and the cache
verdict. Every number names what it was computed from. No number describes a target's behaviour.

## What the next features read

- **Footprint analysis** reads `model.tflite` and the operator records; it adds the figures this
  stage refuses to state, because it can measure them.
- **Emulated verification** reads the skeleton and the resolver, builds them, and replaces the
  working-memory floor with a measured figure.
- **The model card** reads `export.json` for the operator set and the artifact digests.
