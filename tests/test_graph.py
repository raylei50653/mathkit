from typing import Any, cast

import networkx as nx
import pytest
from hypothesis import given
from hypothesis import strategies as st

from mathkit.core.graph import Graph


def test_from_edges_basics() -> None:
    g = Graph.from_edges(4, [(2, 1), (0, 1), (3, 0)])
    assert g.n == 4
    assert list(g.edges()) == [(0, 1), (0, 3), (1, 2)]
    assert g.edge_count() == 3
    assert g.has_edge(1, 0) and not g.has_edge(2, 3)
    assert g.neighbors(0) == (1, 3)
    assert g.degree(1) == 2


@pytest.mark.parametrize(
    "edges", [[(0, 0)], [(0, 1), (1, 0)], [(0, 5)], [(-1, 0)]], ids=["loop", "dup", "hi", "lo"]
)
def test_from_edges_rejects(edges: list[tuple[int, int]]) -> None:
    with pytest.raises(ValueError):
        Graph.from_edges(3, edges)


def test_constructor_rejects_asymmetric() -> None:
    with pytest.raises(ValueError, match="asymmetric"):
        Graph((0b10, 0))


def test_induced_relabels_in_order() -> None:
    cycle = Graph.from_edges(5, [(i, (i + 1) % 5) for i in range(5)])
    path = cycle.induced(0b01110)  # vertices 1, 2, 3
    assert list(path.edges()) == [(0, 1), (1, 2)]


def test_graph_is_hashable_key() -> None:
    a = Graph.from_edges(3, [(0, 1)])
    b = Graph.from_edges(3, [(1, 0)])
    assert a == b and len({a, b}) == 1


def test_from_networkx_requires_range_nodes() -> None:
    h = cast(Any, nx.Graph())
    h.add_edge("a", "b")
    with pytest.raises(ValueError):
        Graph.from_networkx(h)


@st.composite
def graphs(draw: st.DrawFn) -> Graph:
    n = draw(st.integers(0, 9))
    pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
    chosen = draw(st.lists(st.sampled_from(pairs), unique=True)) if pairs else []
    return Graph.from_edges(n, chosen)


@given(graphs())
def test_networkx_round_trip(g: Graph) -> None:
    h = g.to_networkx()
    assert h.number_of_nodes() == g.n and h.number_of_edges() == g.edge_count()
    assert Graph.from_networkx(h) == g
    for v in range(g.n):
        assert sorted(h.neighbors(v)) == list(g.neighbors(v))
