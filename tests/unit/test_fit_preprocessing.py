"""Fitting each feature's preprocessing on the training part (feature 008, ``caravan.data.fit``).

Pure Python, so these run on every Python in the matrix. The numbers are chosen by hand: each case
says what Ludwig's definition gives and asserts exactly that.
"""

from __future__ import annotations

import math

import pytest

from caravan.data.fit import (
    SCALE_ZERO_NOTE,
    UNKNOWN_INDEX,
    apply_number,
    binary_code,
    by_frequency,
    category_code,
    fit_binary,
    fit_category,
    fit_number,
    fit_output_binary,
    fit_output_category,
    fit_output_number,
)
from caravan.manifest.errors import (
    RULE_BINARY_SPELLINGS,
    RULE_CLASS_OUTSIDE_TRAIN,
    RULE_DATASET_LABELS,
    RULE_TOO_FEW_CLASSES,
    RunRuleFailure,
)

NAN = float("nan")


# --- number ------------------------------------------------------------------------------------


def number(values, normalization="zscore", strategy="fill_with_const", fill=0.0):
    return fit_number(values, normalization=normalization, strategy=strategy, fill_value=fill)


def test_zscore_is_the_mean_and_the_population_deviation() -> None:
    fitted = number([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert fitted["shift"] == pytest.approx(5.0)
    assert fitted["scale"] == pytest.approx(2.0)
    assert apply_number(7.0, fitted) == pytest.approx(1.0)


def test_minmax_is_the_minimum_and_the_range() -> None:
    fitted = number([3.0, 7.0, 5.0], normalization="minmax")
    assert (fitted["shift"], fitted["scale"]) == (3.0, 4.0)


def test_iq_is_the_median_and_the_interquartile_range() -> None:
    fitted = number([1.0, 2.0, 3.0, 4.0, 5.0], normalization="iq")
    # Linear interpolation, numpy's default: q1 = 2, q3 = 4.
    assert (fitted["shift"], fitted["scale"]) == (3.0, 2.0)


def test_no_normalization_is_shift_zero_and_scale_one() -> None:
    fitted = number([3.0, 7.0], normalization=None)
    assert (fitted["shift"], fitted["scale"]) == (0.0, 1.0)


def test_a_constant_column_gets_scale_one_and_a_note() -> None:
    fitted = number([4.0, 4.0, 4.0])
    assert fitted["scale"] == 1.0
    assert fitted["note"] == SCALE_ZERO_NOTE


def test_a_missing_reading_is_filled_with_the_constant_before_the_statistics() -> None:
    fitted = number([2.0, NAN, 4.0], normalization="minmax", fill=0.0)
    assert fitted["fill"] == 0.0
    assert (fitted["shift"], fitted["scale"]) == (0.0, 4.0)


def test_fill_with_mean_fills_with_the_mean_of_the_present_values() -> None:
    fitted = number([2.0, NAN, 4.0], strategy="fill_with_mean")
    assert fitted["fill"] == 3.0
    assert fitted["shift"] == pytest.approx(3.0)


# --- category ------------------------------------------------------------------------------------


def test_the_vocabulary_is_by_frequency_then_by_text() -> None:
    assert by_frequency({"b": 2, "a": 2, "c": 5}) == ["c", "a", "b"]


def test_an_integer_column_keeps_its_integers_as_codes() -> None:
    fitted = fit_category(["7", "7", "3", "9", "3", "7"], most_common=32, fill_value="<UNK>")
    assert fitted["vocab"] == [7, 3, 9]
    assert fitted["codes"] == [7, 3, 9]
    assert fitted["text_codes"] is None
    assert fitted["unknown_index"] == UNKNOWN_INDEX == 0
    assert fitted["cut"] == 0
    # A missing reading is passed as an integer that is in no vocabulary.
    assert fitted["missing"] < 0 and fitted["missing"] not in fitted["codes"]


def test_most_common_caps_the_vocabulary_and_counts_what_it_cut() -> None:
    fitted = fit_category(["a", "a", "a", "b", "b", "c", "d"], most_common=2, fill_value="<UNK>")
    assert fitted["vocab"] == ["a", "b"]
    assert fitted["cut"] == 2


def test_a_text_column_gets_codes_one_to_v_in_vocabulary_order() -> None:
    fitted = fit_category(["park", "drive", "drive"], most_common=32, fill_value="<UNK>")
    assert fitted["vocab"] == ["drive", "park"]
    assert fitted["codes"] == [1, 2]
    assert fitted["text_codes"] == {"drive": 1, "park": 2}
    assert fitted["missing"] == 0
    assert category_code("park", fitted) == 2
    assert category_code("reverse", fitted) == 0  # unseen: unknown
    assert category_code("", fitted) == 0


def test_a_pinned_vocabulary_is_kept_in_its_order() -> None:
    fitted = fit_category(
        ["a", "b", "b"], most_common=32, fill_value="<UNK>", pinned=["b", "a", "z"]
    )
    assert fitted["vocab"] == ["b", "a", "z"]
    assert fitted["text_codes"] == {"b": 1, "a": 2, "z": 3}


def test_an_explicit_fill_value_is_a_value_of_its_own() -> None:
    fitted = fit_category(["a", "", "", ""], most_common=32, fill_value="none")
    assert fitted["vocab"] == ["none", "a"]
    assert fitted["missing"] == fitted["text_codes"]["none"]


def test_fitting_reads_only_the_values_it_is_given() -> None:
    # The data stage passes the training part's values; nothing else can enter the vocabulary.
    train = ["1", "1", "2"]
    fitted = fit_category(train, most_common=32, fill_value="<UNK>")
    assert fitted["vocab"] == [1, 2]
    assert category_code("3", fitted) == 3  # passed as itself, lands in "unknown" in the model


# --- binary --------------------------------------------------------------------------------------


def test_ludwigs_spellings_are_read_as_such() -> None:
    fitted = fit_binary(["yes", "no", "Yes"], fallback_true_label=None, path="p")
    assert fitted["spellings"] == {"Yes": 1, "no": 0, "yes": 1}
    assert binary_code("TRUE", fitted["spellings"]) == 1


def test_a_fallback_true_label_decides() -> None:
    fitted = fit_binary(["open", "closed", "ajar"], fallback_true_label="open", path="p")
    assert fitted["spellings"] == {"ajar": 0, "closed": 0, "open": 1}
    assert fitted["true_spelling"] == "open"


def test_two_unusual_spellings_take_the_second_as_true_with_a_note() -> None:
    fitted = fit_binary(["low", "high"], fallback_true_label=None, path="p")
    assert fitted["spellings"] == {"high": 0, "low": 1}
    assert "fallback_true_label" in fitted["note"]


def test_more_than_two_unusual_spellings_are_ds_15() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        fit_binary(
            ["a", "b", "c"], fallback_true_label=None, path="input_features[2].preprocessing"
        )
    assert caught.value.finding.rule == RULE_BINARY_SPELLINGS
    assert caught.value.finding.path == "input_features[2].preprocessing"


def test_a_missing_binary_reading_is_its_fill_value() -> None:
    assert fit_binary(["on", "off"], fallback_true_label=None, path="p")["missing"] == 0
    assert fit_binary(["1"], fallback_true_label=None, path="p", fill_value=True)["missing"] == 1


# --- outputs -------------------------------------------------------------------------------------


def test_output_labels_are_by_frequency_in_the_training_part() -> None:
    fitted = fit_output_category(
        ["b", "a", "b", "c"], ["a", "b", "c", "a", "a"], pinned=None, path="output_features[0]"
    )
    assert fitted["labels"] == ["b", "a", "c"]
    assert fitted["labels_source"] == "derived"


def test_a_class_outside_the_training_part_is_ds_14() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        fit_output_category(["a", "b"], ["a", "b", "c"], pinned=None, path="output_features[0]")
    assert caught.value.finding.rule == RULE_CLASS_OUTSIDE_TRAIN
    assert caught.value.finding.found == ["c"]


def test_a_pinned_output_order_must_name_every_class_and_only_those() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        fit_output_category(["a", "b"], ["a", "b"], pinned=["a"], path="output_features[0]")
    assert caught.value.finding.rule == RULE_DATASET_LABELS
    with pytest.raises(RunRuleFailure):
        fit_output_category(["a", "b"], ["a", "b"], pinned=["a", "b", "z"], path="o")
    kept = fit_output_category(["a", "b"], ["a", "b"], pinned=["b", "a"], path="o")
    assert kept["labels"] == ["b", "a"] and kept["labels_source"] == "stated"


def test_one_class_is_ds_11() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        fit_output_category(["a"], ["a"], pinned=None, path="output_features[0]")
    assert caught.value.finding.rule == RULE_TOO_FEW_CLASSES


def test_a_binary_output_needs_both_classes_in_the_training_part() -> None:
    fitted = fit_output_binary(
        ["no", "yes"], ["no", "yes", "no"], fallback_true_label=None, path="o"
    )
    assert fitted["true_spelling"] == "yes"
    with pytest.raises(RunRuleFailure) as caught:
        fit_output_binary(["no", "no"], ["no", "yes"], fallback_true_label=None, path="o")
    assert caught.value.finding.rule == RULE_CLASS_OUTSIDE_TRAIN


def test_a_number_output_is_fitted_only_when_normalized() -> None:
    assert fit_output_number([1.0, 3.0], normalization=None) == {
        "normalization": None,
        "shift": 0.0,
        "scale": 1.0,
    }
    fitted = fit_output_number([1.0, 3.0], normalization="zscore")
    assert (fitted["shift"], fitted["scale"]) == (2.0, 1.0)
    assert not math.isnan(fitted["scale"])
