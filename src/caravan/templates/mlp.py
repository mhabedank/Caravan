"""The ``mlp`` template: a feature-based decider over a window of samples.

The only template registered in this feature, because it is the only one the pilot model needs
(Principle X). The registry's extensibility is proven by a test that registers a second template,
not by shipping one nobody uses.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from caravan.templates.registry import TemplateParameterSpec


class MlpParameters(BaseModel):
    """Parameters of the ``mlp`` template, validated by the template itself (FR-021)."""

    model_config = ConfigDict(extra="forbid")

    #: Validated per element, so a rejection names which width is wrong, not just the list.
    hidden: list[Annotated[int, Field(gt=0)]] = Field(min_length=1)
    dropout: float = Field(default=0.0, ge=0.0, lt=1.0)


SPEC = TemplateParameterSpec(
    identifier="mlp",
    parameters=MlpParameters,
    consumes_window=True,
    summary="Feature-based decider over a window of samples; hidden layer widths and dropout",
)
