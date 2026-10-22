"""The C array: the bytes, the alignment, and the promise that two exports are one file.

The round-trip is the test that matters. A generator that emitted a plausible-looking array with
one byte wrong would pass every other check here and produce firmware that loads a corrupt model.
"""

from __future__ import annotations

from caravan.export import c_array

BLOB = bytes(range(256)) * 3 + b"\x00\xff\x10"


def test_the_array_round_trips_to_the_exact_bytes() -> None:
    assert c_array.read_back(c_array.source("model_data", BLOB)) == BLOB


def test_the_header_declares_the_same_length() -> None:
    header = c_array.header("model_data", len(BLOB))
    assert f"g_model_data_size = {len(BLOB)};" in header
    assert "extern const unsigned char g_model_data[];" in header


def test_the_array_is_aligned_because_the_runtime_requires_it() -> None:
    # Not stylistic: an unaligned model buffer fails at initialisation on the target.
    assert f"alignas({c_array.ALIGNMENT}) const unsigned char g_model_data[]" in c_array.source(
        "model_data", BLOB
    )


def test_two_generations_of_one_model_are_identical() -> None:
    assert c_array.source("model_data", BLOB) == c_array.source("model_data", BLOB)
    assert c_array.header("model_data", 7) == c_array.header("model_data", 7)


def test_nothing_about_this_machine_leaks_into_the_files() -> None:
    # What would make two exports of one model differ: a date, a path, a host name, a user name.
    import getpass
    import socket

    text = c_array.source("model_data", BLOB) + c_array.header("model_data", len(BLOB))
    for leak in (socket.gethostname(), getpass.getuser(), "/home/", "2026-10-22T"):
        assert leak not in text, f"the generated source carries {leak!r}"


def test_the_name_does_not_repeat_the_stem() -> None:
    # The runtime's generator derives g_<stem>_model_data from <stem>.tflite; here the stem is
    # already model_data, so appending the suffix again would give g_model_data_data.
    assert c_array.array_name("model_data") == "g_model_data"
    assert c_array.array_name("odd-name.v2") == "g_odd_name_v2"


def test_an_empty_model_is_still_valid_source() -> None:
    # Not a case the pipeline produces, but a generator that emitted `= {\n\n};` would be a syntax
    # error reaching the author's compiler rather than failing here.
    source = c_array.source("model_data", b"")
    assert "= {" in source and source.rstrip().endswith("};")
    assert c_array.read_back(source) == b""
