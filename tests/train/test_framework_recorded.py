"""FR-022: the framework and its version are in the report of any run that used one.

Which wheel ran is part of why a number came out as it did, so the Python version is recorded with
it. When this window closes and the extra moves to a Python the framework publishes for, these are
the fields that will show it.
"""

from __future__ import annotations

import json
import platform

from caravan.cli.main import EXIT_OK, main
from tests.train.conftest import latest_run


def test_the_report_names_the_framework_keras_and_the_interpreter(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    assert (
        main(
            [
                "train",
                str(fixture_manifest),
                "--runs-dir",
                str(runs),
                "--cache-dir",
                str(cache),
            ]
        )
        == EXIT_OK
    )
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    training = report["training"]

    assert training["framework"]["name"] == "tensorflow"
    assert training["framework"]["version"].startswith("2.")
    assert training["keras_version"].startswith("3.")
    assert training["python"] == platform.python_version()


def test_the_built_model_records_it_too(fixture_manifest, workspace) -> None:
    # The build stage used the framework as much as the train stage did, and its artifact is the
    # one the next feature converts — so its provenance has to travel with it.
    runs, cache = workspace
    main(["build", str(fixture_manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    description = json.loads(
        (latest_run(runs) / "model" / "built.json").read_text(encoding="utf-8")
    )
    assert description["framework"]["name"] == "tensorflow"
    assert description["python"] == platform.python_version()
