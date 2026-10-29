"""The ``autoencoder`` template: anomaly detection from normal data.

Feature 010. A window goes in, through a narrower code, and is reconstructed; how badly it is
reconstructed is the anomaly score, computed inside the model so the device receives the score
itself (research R8). Trained on normal windows only, it reconstructs what it has seen and fails on
what it has not.

Two justifications (Principle X): ``hum-fan``, published in the zoo and built by hand with exactly
this architecture — encoder 64, 64, code 8, decoder 64, 64 over 5 x 40 log-mel frames, 35,280
parameters — and MLPerf Tiny's anomaly task, whose reference is the same shape at 5 x 128.

It answers the ``anomaly`` output and no other (``output_types``): its last layer is a
reconstruction, not a head, and only the anomaly output knows what to do with one (CF-18).

The parameter half is here, in the core, and imports no framework. The builder half is
``caravan/templates/builders/autoencoder.py``.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from caravan.templates.registry import TemplateParameterSpec

Width = Annotated[int, Field(gt=0)]


class AutoencoderParameters(BaseModel):
    """Parameters of the ``autoencoder`` template, validated by the template itself."""

    model_config = ConfigDict(extra="forbid")

    #: Dense widths from the input towards the code, each followed by a ReLU.
    encoder: list[Width] = Field(min_length=1)
    #: The bottleneck's width. Linear, because a rectified code would discard half its range.
    code: Width
    #: Dense widths from the code back out. Left out, the encoder reversed — the usual mirror,
    #: and ``hum-fan``'s.
    decoder: list[Width] | None = None
    dropout: float = Field(default=0.0, ge=0.0, lt=1.0)

    def decoder_widths(self) -> list[int]:
        return list(self.decoder) if self.decoder is not None else list(reversed(self.encoder))

    def model_post_init(self, _context: object) -> None:
        # The resolved manifest shows the effective value, never an implicit one (FR-010 of 005).
        if self.decoder is None:
            self.decoder = list(reversed(self.encoder))


SPEC = TemplateParameterSpec(
    identifier="autoencoder",
    parameters=AutoencoderParameters,
    consumes_window=True,
    summary=(
        "Anomaly detection from normal data: reconstructs a window and scores how unusual it is"
    ),
    output_types=("anomaly",),
)
