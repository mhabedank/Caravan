"""What a model file says about itself, read with the runtime and nothing else."""

from __future__ import annotations

from caravan.runtime.inspect import INTEGER_DTYPES, inspect_model


def test_an_int8_model_is_fully_integer(int8_model) -> None:
    inspection = inspect_model(int8_model)
    assert inspection.fully_integer
    assert inspection.floating_tensors() == ()
    assert set(inspection.dtype_counts) <= INTEGER_DTYPES
    assert inspection.size_bytes == int8_model.stat().st_size


def test_an_int8_model_carries_quantization_parameters(int8_model) -> None:
    inspection = inspect_model(int8_model)
    assert inspection.input.dtype == "int8"
    assert inspection.output.dtype == "int8"
    # Without a scale and a zero point there is no defined way to feed the model, so their
    # presence is not a detail — it is what makes the measurement possible at all.
    assert inspection.input.scale is not None and inspection.input.scale > 0
    assert inspection.input.zero_point is not None


def test_a_float_model_is_not_fully_integer(float_model) -> None:
    inspection = inspect_model(float_model)
    assert not inspection.fully_integer
    assert inspection.floating_tensors()
    assert inspection.input.dtype == "float32"
    # A float tensor has no scale: the runtime reports zero, and zero is not a scale.
    assert inspection.input.scale is None


def test_the_record_is_serialisable_and_says_what_it_read(int8_model) -> None:
    record = inspect_model(int8_model).as_dict()
    assert record["fully_integer"] is True
    assert record["dtype_counts"]
    assert record["input"]["scale"] > 0
    assert len(record["tensors"]) == sum(record["dtype_counts"].values())


def test_int32_counts_as_integer_because_biases_are_int32(int8_model) -> None:
    # "Every tensor is int8" would be the wrong test: a fully int8 graph keeps its biases in
    # int32, so a check that demanded int8 everywhere would reject every real int8 model.
    counts = inspect_model(int8_model).dtype_counts
    assert "int32" in counts and "int8" in counts
    assert "int32" in INTEGER_DTYPES
