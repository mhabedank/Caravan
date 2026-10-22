"""A model with more than one subgraph refuses the run.

Tested against a graph record rather than against a file, and the reason is worth stating: a
genuine two-subgraph int8 model needs control flow in the template, which is a feature of its own.
What is being checked here is the stage's *check* — that it looks at the subgraph count and refuses
— and that is exactly what the record expresses. A seam, declared as one, not a shortcut.

Why it matters at all: a resolver generated for the first subgraph of several would link kernels for
one graph while the runtime executes another, and nothing downstream of here would notice.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from caravan.manifest.errors import RULE_MULTIPLE_SUBGRAPHS, RunRuleFailure
from caravan.stages.export import check_single_subgraph


@dataclass
class Graph:
    subgraphs: int


def test_a_single_subgraph_model_passes() -> None:
    check_single_subgraph(Graph(subgraphs=1))


@pytest.mark.parametrize("count", [2, 3, 7])
def test_more_than_one_subgraph_refuses(count: int) -> None:
    with pytest.raises(RunRuleFailure) as raised:
        check_single_subgraph(Graph(subgraphs=count))
    assert raised.value.finding.rule == RULE_MULTIPLE_SUBGRAPHS
    assert str(count) in raised.value.finding.problem


def test_the_message_says_why_rather_than_only_what() -> None:
    with pytest.raises(RunRuleFailure) as raised:
        check_single_subgraph(Graph(subgraphs=2))
    assert "wrong kernels" in raised.value.finding.problem
