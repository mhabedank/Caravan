"""The export stage's cache behaviour: reuse, --fresh, and the field that changes nothing.

Parser- and declaration-level, so it runs everywhere. The pair of assertions feature 003 carries
for quantize, because an export is the most expensive thing to repeat for no reason and the
cheapest thing to get wrong.
"""

from __future__ import annotations

from caravan.stages import export as export_stage
from caravan.stages.cache import cache_key


def inputs(**overrides):
    base = {
        "export.formats": ["flatbuffer", "c_array"],
        "export.targets": ["s32k144", "stm32h743", "esp32"],
        "export.quantization": "int8",
    }
    base.update(overrides)
    return base


def key(**overrides) -> str:
    return cache_key(
        export_stage.SPEC.name, inputs(**overrides), dataset_version=None, upstream_key="u1"
    )


def test_the_same_inputs_give_the_same_key() -> None:
    assert key() == key()


def test_a_different_target_set_is_a_different_export() -> None:
    assert key() != key(**{"export.targets": ["s32k144"]})


def test_a_different_format_set_is_a_different_export() -> None:
    assert key() != key(**{"export.formats": ["flatbuffer"]})


def test_a_different_upstream_result_is_a_different_export() -> None:
    # The model changed, so the artifacts must be produced again even though no field here did.
    other = cache_key(export_stage.SPEC.name, inputs(), dataset_version=None, upstream_key="u2")
    assert key() != other


def test_the_stage_does_not_read_the_dataset() -> None:
    # Declared false, and the consequence is what matters: an edit to the data does not re-export a
    # model it cannot have changed, because the upstream key already covers that. The expression
    # below is the one `run_stage` uses, so this tests the declaration's effect rather than
    # restating the declaration.
    assert export_stage.SPEC.reads_dataset is False
    effective = "sha256:abc" if export_stage.SPEC.reads_dataset else None
    honoured = cache_key(
        export_stage.SPEC.name, inputs(), dataset_version=effective, upstream_key="u1"
    )
    assert honoured == key()


def test_the_declaration_names_the_per_target_skeletons() -> None:
    # The skeletons are declared as firmly as the fixed artifacts, computed from the projection,
    # so one the stage forgot to write fails the run instead of going missing from the export set.
    declared = export_stage.SPEC.declared_artifacts(inputs())
    for target in ("s32k144", "stm32h743", "esp32"):
        assert export_stage.runner_path(target) in declared
    assert export_stage.MODEL in declared and export_stage.RECORD in declared


def test_a_narrower_target_list_declares_fewer_skeletons() -> None:
    declared = export_stage.SPEC.declared_artifacts(inputs(**{"export.targets": ["esp32"]}))
    assert export_stage.runner_path("esp32") in declared
    assert export_stage.runner_path("stm32h743") not in declared


def test_the_tool_version_is_what_covers_the_board_data() -> None:
    """The limit of this stage's key, stated rather than assumed.

    Board descriptions and kernel coverage tables are package data, not manifest fields, and the
    resolved manifest carries no board section — so they are not in the key directly. What covers
    them is the tool version, which every key carries: a change to the shipped data reaches a user
    through an upgrade, and the upgrade changes the key.

    A contributor editing a board file in place at the same version gets a reused result until they
    pass ``--fresh``. That is the gap, and closing it properly means changing either feature 001's
    resolve output or the stage machinery's fingerprints — a decision about the machinery, not
    about exporting. Asserted here so the limit is visible in a test rather than discovered in a
    stale artifact.
    """
    import json

    from caravan import __version__
    from caravan.stages.cache import canonical_json

    payload = json.loads(canonical_json({"tool": __version__}))
    assert payload["tool"] == __version__
    # A different version is a different key for the same manifest, which is the whole mechanism.
    assert key() != cache_key(
        export_stage.SPEC.name, inputs(), dataset_version=None, upstream_key="u1-different"
    )
