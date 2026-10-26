"""``test_windows.h`` compiles, and does on the host what a board will do (feature 009, T008).

In the train suite because the header needs a real export. The runtime's headers are not vendored,
so the one declaration the header uses — ``MicroInterpreter::input`` returning a ``TfLiteTensor`` —
is stubbed with exactly the members contracts/test-windows.md names. The stub is not the runtime:
it proves the header is well-formed C++ and that its logic (fill by named position, decide, name)
reproduces the host's decisions, which is everything the board adds on top is the runtime itself.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.stages.export import ARRAY_HEADER, ARRAY_SOURCE, INTERFACE, TEST_WINDOWS
from tests.train.conftest import latest_run
from tests.train.test_test_windows import manifest_with

pytest.importorskip("ai_edge_litert")

COMPILER = shutil.which("g++") or shutil.which("clang++")
pytestmark = pytest.mark.skipif(COMPILER is None, reason="no host C++ compiler on the path")

STUB = """#pragma once
#include <cstddef>
#include <cstdint>
typedef enum { kTfLiteFloat32 = 1, kTfLiteInt32 = 2, kTfLiteInt8 = 9 } TfLiteType;
typedef union { float* f; int32_t* i32; int8_t* int8; } TfLitePtrUnion;
typedef struct { TfLiteType type; TfLitePtrUnion data; size_t bytes; } TfLiteTensor;
namespace tflite {
class MicroInterpreter {
 public:
  TfLiteTensor* input(size_t index) { return index < count ? &tensors[index] : nullptr; }
  TfLiteTensor tensors[16];
  size_t count = 0;
};
}  // namespace tflite
"""

TYPES = {"float32": ("kTfLiteFloat32", "float", "f"), "int32": ("kTfLiteInt32", "int32_t", "i32")}


def harness(interface: dict) -> str:
    """A host program: tensors laid out as the interface says, every window filled and decided."""
    inputs = list(interface["inputs"])
    setup = []
    for entry in inputs:
        tflite_type, c_type, member = TYPES[entry["dtype"]]
        count = 1
        for dim in entry["shape"]:
            count *= dim
        position = entry["position"]
        setup.append(
            f"  static {c_type} buffer_{entry['name']}[{count}];\n"
            f"  interpreter.tensors[{position}].type = {tflite_type};\n"
            f"  interpreter.tensors[{position}].data.{member} = buffer_{entry['name']};\n"
            f"  interpreter.tensors[{position}].bytes = sizeof(buffer_{entry['name']});"
        )
    nl = "\n"
    return f"""#include "test_windows.h"
using namespace caravan_windows;
int main() {{
  tflite::MicroInterpreter interpreter;
  interpreter.count = {len(inputs)};
{nl.join(setup)}
  int agreed = 0;
  for (int i = 0; i < kCount; ++i) {{
    const char* failed = nullptr;
    if (!FillWindow(interpreter, i, &failed)) {{
      std::printf("fill failed: %s\\n", failed);
      return 1;
    }}
    char name[24];
    const float decision = Decide(kHostScores[i]);
    std::printf("%d %s\\n", i, DecisionName(decision, name));
    if (decision == kHostDecision[i]) ++agreed;
  }}
  std::printf("agreed %d/%d\\n", agreed, kCount);
  return agreed == kCount ? 0 : 2;
}}
"""


def test_the_header_compiles_and_reproduces_the_host_decisions(workspace, tmp_path) -> None:
    runs, cache = workspace
    manifest = manifest_with(tmp_path, 8)
    code = main(["export", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    assert code == EXIT_OK
    run = latest_run(runs)

    build = tmp_path / "build"
    (build / "tensorflow" / "lite" / "micro").mkdir(parents=True)
    (build / "tensorflow" / "lite" / "micro" / "micro_interpreter.h").write_text(STUB)
    for relative in (ARRAY_HEADER, ARRAY_SOURCE, TEST_WINDOWS):
        shutil.copy(run / relative, build / Path(relative).name)
    interface = json.loads((run / INTERFACE).read_text(encoding="utf-8"))
    (build / "harness.cc").write_text(harness(interface))

    compiled = subprocess.run(
        [
            str(COMPILER),
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I.",
            "harness.cc",
            "model_data.cc",
            "-o",
            "harness",
        ],
        cwd=build,
        capture_output=True,
        text=True,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr

    ran = subprocess.run(
        [str(build / "harness")], cwd=build, capture_output=True, text=True, check=False
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    lines = ran.stdout.strip().splitlines()
    assert lines[-1] == "agreed 8/8"
    names = {line.split(" ", 1)[1] for line in lines[:-1]}
    assert names == {"dos", "fuzzy", "normal", "replay"}
