"""The ``mlp`` template: a feature-based decider over a window of samples.

The only template registered in this feature, because it is the only one the pilot model needs
(Principle X). The registry's extensibility is proven by a test that registers a second template,
not by shipping one nobody uses.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from caravan.targets.fit import dense_record
from caravan.templates.registry import TemplateParameterSpec, TemplateStarter


class MlpParameters(BaseModel):
    """Parameters of the ``mlp`` template, validated by the template itself (FR-021)."""

    model_config = ConfigDict(extra="forbid")

    #: Validated per element, so a rejection names which width is wrong, not just the list.
    hidden: list[Annotated[int, Field(gt=0)]] = Field(min_length=1)
    dropout: float = Field(default=0.0, ge=0.0, lt=1.0)


def layers(params: BaseModel, steps: int, channels: int) -> tuple[list[object], int]:
    """The dense layers ``builders/mlp.py`` makes, as fit records (feature 013, research R13)."""
    assert isinstance(params, MlpParameters)
    records: list[object] = []
    width = steps * channels
    for position, units in enumerate(params.hidden, start=1):
        records.append(dense_record(f"hidden_{position}", width, units))
        width = units
    return records, width


SPEC = TemplateParameterSpec(
    identifier="mlp",
    parameters=MlpParameters,
    consumes_window=True,
    layers=layers,
    summary="Feature-based decider over a window of samples; hidden layer widths and dropout",
    # examples/picket-mlp.yaml's parameters (feature 013, research R7).
    starter=TemplateStarter(
        params={"hidden": [32, 16], "dropout": 0.1},
        window=64,
        rank=0,
        note="dense layers over the whole window: small and quick; a start for most tables",
    ),
)
