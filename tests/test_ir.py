import copy
from typing import Any

import pytest

from mathkit.domains import Domains
from mathkit.domains.c5.ir_kinds import BoundaryCycle
from mathkit.ir import (
    CORE_KINDS,
    GraphObject,
    IRError,
    MathDocument,
    RawObject,
    dependency_order,
    load_document,
)


def test_example_loads(c5_doc: MathDocument) -> None:
    assert [o.kind for o in c5_doc.objects] == ["graph", "c5.boundary_cycle", "coloring"]
    graph = c5_doc.get("G")
    assert isinstance(graph, GraphObject)
    core = graph.to_core()
    assert core.n == 6 and core.edge_count() == 10
    assert isinstance(c5_doc.get("B"), BoundaryCycle)


def test_round_trip(c5_data: dict[str, Any], c5_doc: MathDocument) -> None:
    assert c5_doc.to_json() == c5_data


def test_without_pack_domain_kind_is_raw(c5_data: dict[str, Any]) -> None:
    doc = load_document(c5_data, CORE_KINDS)
    assert isinstance(doc.get("B"), RawObject)
    assert doc.to_json() == c5_data


def _mutated(data: dict[str, Any], index: int, **changes: Any) -> dict[str, Any]:
    out = copy.deepcopy(data)
    out["objects"][index].update(changes)
    return out


@pytest.mark.parametrize(
    ("index", "changes", "message"),
    [
        (2, {"id": "G"}, "duplicate object id"),
        (2, {"graph": "H"}, "unknown object 'H'"),
        (2, {"values": {"nope": 1}}, "unknown element 'G/nope'"),
        (1, {"cycle": ["b_0", "b_1", "b_2", "b_3", "x"]}, "unknown element 'G/x'"),
        (1, {"cycle": ["b_0", "b_1", "b_2", "b_3"]}, "5 distinct"),
        (0, {"vertices": ["b_0", "b_0"]}, "duplicate vertex"),
        (0, {"edges": [{"id": "b_0", "u": "b_0", "v": "b_1"}]}, "must be distinct"),
        (0, {"edges": [{"id": "e", "u": "b_0", "v": "b_0"}]}, "self-loop"),
        (0, {"id": "G/x"}, "expected a name"),
        (2, {"values": {"b_0": True}}, "must be an integer"),
        (2, {"extra": 1}, "unknown fields"),
    ],
)
def test_integrity_violations(
    c5_data: dict[str, Any], domains: Domains, index: int, changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(IRError, match=message):
        load_document(_mutated(c5_data, index, **changes), domains.kinds)


def test_bad_header(c5_data: dict[str, Any]) -> None:
    with pytest.raises(IRError, match="schema"):
        load_document({**c5_data, "schema": "mathkit.ir/2"})
    with pytest.raises(IRError, match="evidence"):
        load_document({**c5_data, "evidence": "vibes"})


def test_dependency_order_puts_referenced_first(
    c5_data: dict[str, Any], domains: Domains
) -> None:
    data = copy.deepcopy(c5_data)
    data["objects"].reverse()
    doc = load_document(data, domains.kinds)
    assert [o.id for o in dependency_order(doc)] == ["G", "col", "B"]
