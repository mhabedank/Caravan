"""The command line's own contract: exit codes and the separation of the two streams."""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_INTERNAL, EXIT_OK, EXIT_RULE, EXIT_USAGE, build_parser, main
from tests.support import INVALID, PILOT, PILOT_FIXTURE


def test_a_valid_manifest_exits_zero(tmp_path, capsys) -> None:
    assert main(["validate", str(PILOT), "--runs-dir", str(tmp_path)]) == EXIT_OK


def test_a_rule_saying_no_exits_one(tmp_path, capsys) -> None:
    code = main(["validate", str(INVALID / "cf-1-split-sum.yaml"), "--runs-dir", str(tmp_path)])
    assert code == EXIT_RULE


def test_a_usage_error_exits_two(capsys) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["validate", "--not-an-option"])
    assert caught.value.code == EXIT_USAGE


def test_no_command_prints_help_and_exits_two(capsys) -> None:
    assert main([]) == EXIT_USAGE
    assert "usage: caravan" in capsys.readouterr().err


def test_an_unreadable_path_exits_two(capsys) -> None:
    assert main(["validate", "no/such/manifest.yaml", "--no-report"]) == EXIT_USAGE
    assert "no such file" in capsys.readouterr().err


def test_a_defect_in_the_tool_exits_three(monkeypatch, capsys) -> None:
    # The boundary that turns an unexpected failure into exit code 3 rather than into a verdict
    # about the manifest.
    import caravan.cli.validate as validate_command

    def explode(*_args, **_kwargs):
        raise RuntimeError("synthetic defect")

    monkeypatch.setattr(validate_command, "load_manifest", explode)
    assert main(["validate", str(PILOT), "--no-report"]) == EXIT_INTERNAL
    err = capsys.readouterr().err
    assert "defect in caravan itself" in err


def test_the_answer_goes_to_stdout_and_messages_to_stderr(tmp_path, capsys) -> None:
    # A current-form manifest, so there is nothing to say: a migrated one says what changed, on
    # stderr (feature 006, test below).
    main(["render", str(PILOT_FIXTURE), "--stdout"])
    captured = capsys.readouterr()
    assert captured.out.startswith("apiVersion:")
    assert captured.err == ""


def test_json_puts_nothing_but_the_document_on_stdout(tmp_path, capsys) -> None:
    main(
        ["validate", str(INVALID / "b-1-unknown-board.yaml"), "--json", "--runs-dir", str(tmp_path)]
    )
    captured = capsys.readouterr()
    json.loads(captured.out)  # parses, so nothing else was written there
    assert captured.err == ""


def test_quiet_leaves_stderr_empty_on_success(tmp_path, capsys) -> None:
    assert main(["validate", str(PILOT), "--quiet", "--runs-dir", str(tmp_path)]) == EXIT_OK
    assert capsys.readouterr().err == ""


def test_the_listings_exist_because_the_messages_promise_them(capsys) -> None:
    from caravan.targets.registry import default_registry as boards
    from caravan.templates.registry import default_registry as templates

    assert main(["templates"]) == EXIT_OK
    listed = {line.split("\t")[0] for line in capsys.readouterr().out.splitlines()}
    assert listed == set(templates().identifiers)

    assert main(["boards"]) == EXIT_OK
    listed = {line.split("\t")[0] for line in capsys.readouterr().out.splitlines()}
    assert listed == set(boards().identifiers)


def test_version_is_available_without_a_subcommand(capsys) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    assert caught.value.code == 0
    assert "caravan-ml" in capsys.readouterr().out


def test_validate_and_render_agree_on_the_same_manifest(tmp_path, capsys) -> None:
    manifest = INVALID / "cf-4-calibration-samples.yaml"
    main(["validate", str(manifest), "--json", "--runs-dir", str(tmp_path / "a")])
    from_validate = json.loads(capsys.readouterr().out)
    main(["render", str(manifest), "--json", "--runs-dir", str(tmp_path / "b")])
    from_render = json.loads(capsys.readouterr().out)
    assert from_validate["findings"] == from_render["findings"]
    assert from_validate["unresolved"] == from_render["unresolved"]
    assert from_validate["schema_version"] == from_render["schema_version"]


def test_the_parser_exposes_only_the_documented_commands() -> None:
    parser = build_parser()
    actions = [a for a in parser._subparsers._group_actions if hasattr(a, "choices")]
    # Principle XII fixes the verb set, so this is where the set is written down and the second
    # of only two assertions each pipeline feature changes. The stage verbs need no amendment: the
    # constitution's pipeline contract already names them as stages, and a stage must be
    # separately invocable. A verb that is not in this set does not exist.
    assert set(actions[0].choices) == {
        "validate",
        "render",
        "build",
        "train",
        "quantize",
        "export",
        "templates",
        "boards",
    }


# --- feature 006, constitution 4.0.0: no migration before 1.0.0, removed fields ------------------


def test_the_previous_form_is_refused_with_the_change_note(capsys) -> None:
    code = main(["validate", str(INVALID / "v-1-previous-version.yaml"), "--no-report"])
    assert code == EXIT_RULE
    err = capsys.readouterr().err
    assert "apiVersion" in err
    assert "caravan/v0.1" in err
    assert "docs/manifest-changes.md" in err


def test_a_manifest_without_a_version_is_refused_not_read_as_some_version(capsys) -> None:
    code = main(["validate", str(INVALID / "v-1-no-version.yaml"), "--json", "--no-report"])
    assert code == EXIT_RULE
    document = json.loads(capsys.readouterr().out)
    assert document["schema_version"] is None
    (finding,) = document["findings"]
    assert finding["rule"] == "V-1"
    assert finding["path"] == "apiVersion"
    assert "no schema version declared" in finding["problem"]


def test_a_valid_manifest_prints_one_line(capsys) -> None:
    assert main(["validate", str(PILOT_FIXTURE), "--no-report"]) == EXIT_OK
    assert capsys.readouterr().err.splitlines() == ["picket-mlp-fixture.yaml: valid"]


def test_a_removed_field_in_the_new_form_is_refused_at_its_path(capsys) -> None:
    code = main(["validate", str(INVALID / "removed-compliance.yaml"), "--no-report"])
    assert code == EXIT_RULE
    err = capsys.readouterr().err
    assert "compliance — removed in caravan/v0.1: Caravan carries no compliance layer" in err


def test_render_to_stdout_writes_only_the_document(capsys) -> None:
    assert main(["render", str(PILOT), "--stdout"]) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("apiVersion: caravan/v0.1\n")
