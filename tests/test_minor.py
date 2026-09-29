import importlib
from typing import Any, cast

from hypothesis import given, settings
from hypothesis import strategies as st

from mathkit.core.graph import Graph
from mathkit.core.minor import K5, K33, check_minor, kuratowski
from mathkit.core.planar import is_planar

nx: Any = importlib.import_module("networkx")

PETERSEN = Graph.from_networkx(nx.petersen_graph())


def test_identity_models() -> None:
    assert check_minor(K5, [1 << i for i in range(5)], K5)
    assert check_minor(K33, [[i] for i in range(6)], K33)


def test_petersen_contains_k5_by_contracting_spokes() -> None:
    # networkx labels: outer 0-4, inner 5-9, spokes i -- i+5
    model = [[i, i + 5] for i in range(5)]
    assert check_minor(PETERSEN, model, K5)


def test_failures_are_explained() -> None:
    cases = {
        "4 branch sets": [[0], [1], [2], [3]],
        "empty": [[0], [1], [2], [3], []],
        "overlaps": [[0, 5], [1], [2], [3], [0]],
        "not connected": [[0, 7], [1], [2], [3], [4]],
        "outside": [[0], [1], [2], [3], [99]],
        "no edge between branch sets 0 and 2": [[0], [1], [2], [3], [4]],
    }
    for reason, model in cases.items():
        check = check_minor(PETERSEN, model, K5)
        assert not check and reason in check.reason, (reason, check.reason)


def test_kuratowski_classics() -> None:
    assert kuratowski(Graph.from_networkx(nx.icosahedral_graph())) is None
    k5 = kuratowski(K5)
    assert k5 is not None and k5.graph == "K5"
    petersen = kuratowski(PETERSEN)
    assert petersen is not None and check_minor(PETERSEN, petersen.branch_sets, petersen.h)


@st.composite
def dense_graphs(draw: st.DrawFn) -> Graph:
    n = draw(st.integers(5, 10))
    pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
    return Graph.from_edges(n, [e for e in pairs if draw(st.floats(0, 1)) < 0.6])


@settings(max_examples=150, deadline=None)
@given(dense_graphs())
def test_kuratowski_certifies_non_planarity(g: Graph) -> None:
    model = kuratowski(g)
    assert (model is None) == is_planar(g)
    if model is not None:
        assert check_minor(g, model.branch_sets, model.h)


@settings(max_examples=150)
@given(dense_graphs(), st.data())
def test_check_minor_matches_networkx_quotient(g: Graph, data: st.DataObject) -> None:
    """Random partitions: valid model iff connected parts and quotient contains K3,3/K5."""
    labels = [data.draw(st.integers(0, 5)) for _ in range(g.n)]
    parts = [[v for v in range(g.n) if labels[v] == i] for i in range(6)]
    if any(not p for p in parts):
        return
    h = g.to_networkx()
    connected = all(nx.is_connected(h.subgraph(p)) for p in parts)
    quotient = nx.quotient_graph(h, [set(p) for p in parts], relabel=True)
    realised = all(cast(bool, quotient.has_edge(u, v)) for u, v in K33.edges())
    assert bool(check_minor(g, parts, K33)) == (connected and realised)
