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


def plan_for(records: Any, inputs: Mapping[str, Any]) -> WindowPlan:
    """The windows every stage forms from these records: one function, so they cannot disagree.

    Feature 014: the recordings come from the reader; the stride and the label rule from the
    resolved manifest (``.get`` because a hand-built projection in an older test may lack them).
    """
    return plan_windows(
        records.labels,
        inputs["preprocessing.window_size"],
        parts=records.parts,
        recordings=getattr(records, "recordings", ()) or None,
        stride=inputs.get("preprocessing.window_stride"),
        rule=inputs.get("preprocessing.window_label") or "all_equal",
        groups=getattr(records, "groups", None),
    )


def window_report(plan: WindowPlan, split: SplitPlan) -> dict[str, Any]:
    """What feature 014 adds to ``data/schema.json``: the windows, the recordings, the split.

    Beside the existing keys, not instead of them: ``split`` stays the count per part that earlier
    readers use (contracts/reports.md).
    """
    return {
        "window": {"size": plan.window, "stride": plan.stride, "label_rule": plan.rule},
        "recordings": [dict(entry) for entry in plan.per_recording],
        "recordings_too_short": list(plan.too_short),
        "windows_dropped": {
            "mixed": plan.discarded_mixed,
            "tied": plan.discarded_tied,
            "mixed_split": plan.discarded_mixed_split,
            "purged": split.purged,
        },
        "split_plan": {
            "type": split.type,
            "derived": split.derived,
            "seed": split.seed,
            "assignment": {name: list(groups) for name, groups in split.assignment.items()},
            "shares": split.shares,
        },
    }


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
    plan = plan_for(records, inputs)
    split = split_for(
        plan,
        inputs["preprocessing.split"],
        seed=int(inputs["random_seed"]),
        labels=split_labels(output["type"], plan.labels),
    )
    features, targets = assemble_samples(records, plan, inputs["input_features"], output)
    return Parts(plan=plan, split=split, features=features, targets=targets)
