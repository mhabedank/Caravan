"""No stage knows which template it runs (feature 010, FR-030, SC-010).

What differs for an autoencoder is decided by the ``anomaly`` output type, and what differs for an
image by the ``image`` input type; what a template can do is a field of its parameter spec
(``output_types``, ``takes_images``, ``plane_fit``). So outside ``caravan/templates/`` no module
names a template, and adding one stays two files and a registration.
"""

from __future__ import annotations

import re
from pathlib import Path

import caravan
from caravan.templates.registry import default_registry

SOURCE = Path(caravan.__file__).parent
TEMPLATES = SOURCE / "templates"


def test_four_templates_are_listed_with_their_summaries() -> None:
    registry = default_registry()
    assert registry.identifiers == ("autoencoder", "conv1d", "conv2d", "mlp")
    for spec in registry:
        assert spec.summary and len(spec.summary) < 120


def test_no_module_outside_the_templates_names_a_template() -> None:
    identifiers = default_registry().identifiers
    alternatives = "|".join(map(re.escape, identifiers))
    pattern = re.compile(rf"""["']({alternatives})["']""")
    offenders = []
    for path in sorted(SOURCE.rglob("*.py")):
        if TEMPLATES in path.parents:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(SOURCE)}:{number}: {line.strip()}")
    assert not offenders, "a template identifier outside caravan/templates/:\n" + "\n".join(
        offenders
    )
