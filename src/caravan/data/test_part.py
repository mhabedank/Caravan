"""The samples and their split, formed once for every stage that measures or ships a test part.

Core-importable: ``numpy`` is reached only through ``reader_bridge``, inside functions. Shared
rather than repeated because two stages must agree to the window on what the test part is: the
quantize stage measures its accuracy gate on it, and the export stage (feature 009) hands windows
of it to a board as the reference the board is compared against. If the two formed it separately,
a board run could agree with a host reference the gate never saw.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from caravan.data.reader_bridge import assemble_samples, select
from caravan.data.windows import SplitPlan, WindowPlan, plan_windows, split_for


def split_labels(output_type: str, plan_labels: Sequence[str]) -> tuple[str, ...]:
    """What a stratified split draws per, and what its counts are reported by.

    A ``number`` output has no classes, so its split is drawn as one pool and counted as one.
    """
    if output_type == "number":
        return ()
    return tuple(sorted(set(plan_labels)))


@dataclass(frozen=True)
class Parts:
    """Every sample of a run, with the split that divides them."""

    plan: WindowPlan
    split: SplitPlan
    #: The model's inputs, keyed by feature name, one row per sample.
    features: dict[str, Any]
    #: The targets, one per sample, in the encoding the gate scores against.
    targets: Any

    def test(self) -> tuple[dict[str, Any], Any]:
        """The test part, in split order: inputs and targets."""
        indices = list(self.split.test)
        return select(self.features, indices), self.targets[indices]


def form_parts(records: Any, inputs: Mapping[str, Any], output: Mapping[str, Any]) -> Parts:
    """Windows, samples and split, exactly as the quantize stage has always formed them.

    ``inputs`` is a stage projection holding ``preprocessing.window_size``,
    ``preprocessing.split``, ``random_seed`` and ``input_features``; ``output`` is the output
    feature as ``caravan.stages.quantize.output_of`` describes it.
    """
    plan = plan_windows(records.labels, inputs["preprocessing.window_size"], parts=records.parts)
    split = split_for(
        plan,
        inputs["preprocessing.split"],
        seed=int(inputs["random_seed"]),
        labels=split_labels(output["type"], plan.labels),
    )
    features, targets = assemble_samples(records, plan, inputs["input_features"], output)
    return Parts(plan=plan, split=split, features=features, targets=targets)
