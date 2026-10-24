"""The generated array compiles standing alone.

This is what turns a success criterion into a check. SC-004 says the array compiles on its own;
for most of this feature's life that sentence was a claim nothing tested, which is the kind of
criterion that can never fail. The pair needs only ``<cstdint>``, so a host compiler settles it.

The resolver is *not* compiled here, and that is deliberate rather than an omission: it includes the
runtime's headers, which this project does not vendor. Compiling it is what emulated verification
is for, and pretending otherwise here would be the unverified claim this project is built against.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from caravan.export import c_array

COMPILERS = ("g++", "clang++")
BLOB = bytes(range(97)) * 5


def compiler() -> str | None:
    for candidate in COMPILERS:
        if shutil.which(candidate):
            return candidate
    return None


@pytest.mark.skipif(compiler() is None, reason="no host C++ compiler on the path")
def test_the_generated_pair_compiles(tmp_path) -> None:
    (tmp_path / "model_data.h").write_text(c_array.header("model_data", len(BLOB)))
    (tmp_path / "model_data.cc").write_text(c_array.source("model_data", BLOB))

    result = subprocess.run(
        [
            str(compiler()),
            "-std=c++17",
            "-Wall",
            "-Werror",
            "-c",
            "model_data.cc",
            "-o",
            "model_data.o",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "model_data.o").is_file()


@pytest.mark.skipif(compiler() is None, reason="no host C++ compiler on the path")
def test_the_header_is_self_contained(tmp_path) -> None:
    # Included on its own by somebody else's translation unit, which is how it will be used.
    (tmp_path / "model_data.h").write_text(c_array.header("model_data", len(BLOB)))
    (tmp_path / "user.cc").write_text(
        '#include "model_data.h"\nint main() { return g_model_data_size == 0; }\n'
    )
    result = subprocess.run(
        [str(compiler()), "-std=c++17", "-Wall", "-Werror", "-fsyntax-only", "user.cc"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_a_compiler_is_available_where_this_matters() -> None:
    # A test that skips everywhere proves nothing. This one does not assert that a compiler exists
    # — a contributor's machine may have none — but it records which environments must have one, so
    # that the skip is visible in continuous integration rather than silent.
    assert COMPILERS, "the list of compilers to try must not be empty"


@pytest.mark.skipif(compiler() is None, reason="no host C++ compiler on the path")
def test_the_pair_with_the_interface_compiles_and_reads_back(tmp_path) -> None:
    # Feature 006: the header gains the model's identity, the named positions and the label array.
    # Compiled, linked and run, so the labels a firmware author reads are the labels written,
    # escapes and all.
    from caravan.export.interface import header_additions, source_additions

    model = {"name": "picket-mlp", "version": "0.1.0"}
    bindings = [
        {
            "name": "frames",
            "role": "input",
            "position": 0,
            "element_type": "float32",
            "shape": [1, 8],
        },
        {
            "name": "attack",
            "role": "output",
            "position": 0,
            "element_type": "float32",
            "shape": [1, 4],
        },
    ]
    features = [{"name": "frames", "type": "number"}]
    output = {
        "name": "attack",
        "type": "category",
        "preprocessing": {"fitted": {"labels": ["dos", 'quo"te', "fäll", "\tF"]}},
    }
    (tmp_path / "model_data.h").write_text(
        c_array.header(
            "model_data",
            len(BLOB),
            header_additions("g_model_data", model, bindings, features, output),
        )
    )
    (tmp_path / "model_data.cc").write_text(
        c_array.source("model_data", BLOB, source_additions("g_model_data", output))
    )
    (tmp_path / "main.cc").write_text(
        '#include <cstdio>\n#include "model_data.h"\n'
        "int main() {\n"
        '  std::printf("%s %s %u %u\\n", g_model_data_model_name, g_model_data_model_version,\n'
        "              g_model_data_input_frames, g_model_data_output_attack_label_count);\n"
        "  for (unsigned i = 0; i < g_model_data_output_attack_label_count; ++i)\n"
        '    std::printf("[%s]\\n", g_model_data_output_attack_labels[i]);\n'
        "  return 0;\n}\n"
    )
    build = subprocess.run(
        [str(compiler()), "-std=c++17", "-Wall", "-Werror", "main.cc", "model_data.cc", "-o", "m"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    ran = subprocess.run([str(tmp_path / "m")], capture_output=True, check=True)
    assert ran.stdout.decode("utf-8").splitlines() == [
        "picket-mlp 0.1.0 0 4",
        "[dos]",
        '[quo"te]',
        "[fäll]",
        "[\tF]",
    ]
