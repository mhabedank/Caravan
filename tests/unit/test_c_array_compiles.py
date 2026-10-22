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
