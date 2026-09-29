import importlib
from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mathkit.core.graph import Graph
from mathkit.core.planar import Embedding, NotPlanarError, components, embed, is_planar

from .planar_graphs import planar_graphs, triangulations

nx: Any = importlib.import_module("networkx")

K4 = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])


def _nx(g: Any) -> Graph:
    return Graph.from_networkx(g)


def test_from_rotation_k4() -> None:
    # vertex 0 in the centre of triangle 1-2-3 (counter-clockwise)
    emb = Embedding.from_rotation(K4, [(1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1)])
    assert emb.faces() == ((0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2))
    assert emb.mirror().mirror() == emb


def test_from_rotation_rejects_torus_rotation() -> None:
    with pytest.raises(NotPlanarError, match="Euler"):
        Embedding.from_rotation(K4, [(1, 2, 3), (0, 2, 3), (0, 1, 3), (0, 1, 2)])


def test_from_rotation_rejects_non_permutation() -> None:
    with pytest.raises(ValueError, match="permutation"):
        Embedding.from_rotation(K4, [(1, 2), (0, 3, 2), (0, 1, 3), (0, 2, 1)])
    with pytest.raises(ValueError, match="entries"):
        Embedding.from_rotation(K4, [()])


def test_tree_has_one_face_walking_each_edge_twice() -> None:
    star = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3)])
    emb = embed(star)
    assert emb is not None
    (face,) = emb.faces()
    assert len(face) == 6


def test_disconnected_and_isolated() -> None:
    g = Graph.from_edges(7, [(0, 1), (1, 2), (2, 0), (4, 5)])
    assert components(g) == [[0, 1, 2], [3], [4, 5], [6]]
    emb = embed(g)
    assert emb is not None and len(emb.faces()) == 3
    assert embed(Graph.from_edges(0, [])) is not None


@pytest.mark.parametrize(
    "g",
    [nx.complete_graph(5), nx.complete_bipartite_graph(3, 3), nx.petersen_graph()],
    ids=["K5", "K33", "petersen"],
)
def test_classic_non_planar(g: Any) -> None:
    assert not is_planar(_nx(g))


def test_cube_faces() -> None:
    emb = embed(_nx(nx.cubical_graph()))
    assert emb is not None
    assert sorted(len(f) for f in emb.faces()) == [4] * 6


def test_unknown_backend() -> None:
    with pytest.raises(ValueError, match="backend"):
        embed(K4, backend="magic")


@st.composite
def small_graphs(draw: st.DrawFn) -> Graph:
    n = draw(st.integers(0, 10))
    p = draw(st.floats(0.1, 0.9))
    pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
    return Graph.from_edges(n, [e for e in pairs if draw(st.floats(0, 1)) < p])


@settings(max_examples=400)
@given(small_graphs())
def test_lr_agrees_with_networkx(g: Graph) -> None:
    planar = cast(bool, nx.check_planarity(g.to_networkx())[0])
    emb = embed(g)  # a returned embedding is Euler-checked by from_rotation
    assert (emb is not None) == planar
    if emb is not None:
        Embedding.from_rotation(g, emb.mirror().rotation)


@given(planar_graphs())
def test_planar_graphs_are_embedded(g: Graph) -> None:
    assert embed(g) is not None


def _face_sets(e: Embedding) -> list[list[int]]:
    return sorted(sorted(f) for f in e.faces())


@given(triangulations())
def test_three_connected_faces_match_networkx(g: Graph) -> None:
    """Whitney: a 3-connected planar graph has one embedding up to mirroring."""
    ours, theirs = embed(g), embed(g, backend="networkx")
    assert ours is not None and theirs is not None
    assert _face_sets(ours) == _face_sets(theirs)
    assert len(ours.faces()) == 2 * g.n - 4
