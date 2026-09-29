import importlib
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mathkit.core.coloring import (
    UNCOLORED,
    extensions,
    first_extension,
    is_proper,
    normalize_colors,
    palette,
)
from mathkit.core.graph import Graph
from mathkit.core.kempe import chain, chains, kempe_class, swap

from .test_coloring import small_graphs

nx: Any = importlib.import_module("networkx")

C6 = Graph.from_edges(6, [(i, (i + 1) % 6) for i in range(6)])


def test_chain_on_cycle() -> None:
    col = (0, 1, 0, 2, 0, 2)  # vertex 4 is cut off from 0-1-2 by colour-2 neighbours
    assert chains(C6, col, 0, 1) == [0b000111, 0b010000]
    assert chain(C6, col, 1, 0, 1) == 0b000111
    with pytest.raises(ValueError, match="not 0 or 1"):
        chain(C6, col, 3, 0, 1)


def test_swap_skips_other_colours_and_uncoloured() -> None:
    assert swap((0, 1, 2, UNCOLORED), 0b1111, 0, 1) == (1, 0, 2, UNCOLORED)


def test_absent_colour_allows_recolouring() -> None:
    path = Graph.from_edges(2, [(0, 1)])
    assert kempe_class(path, (0, 1)) == ((0, 1), (1, 0))
    assert set(kempe_class(path, (0, 1), colors=[0, 1, 2])) == {
        c for c in extensions(path, palette(3))
    }


def test_limit() -> None:
    empty = Graph.from_edges(6, [])
    with pytest.raises(OverflowError):
        kempe_class(empty, (0,) * 6, colors=range(3), limit=10)


@st.composite
def coloured(draw: st.DrawFn, max_n: int = 8) -> tuple[Graph, tuple[int, ...]]:
    g = draw(small_graphs(max_n=max_n))
    return g, first_extension(g, palette(4)) or tuple(range(g.n))  # 5+ colours: all distinct


@settings(max_examples=200)
@given(coloured(), st.integers(0, 3), st.integers(0, 3))
def test_chains_match_networkx_components(
    gc: tuple[Graph, tuple[int, ...]], a: int, b: int
) -> None:
    g, col = gc
    if a == b:
        return
    sub = g.to_networkx().subgraph([v for v, c in enumerate(col) if c in (a, b)])
    expected = sorted(sum(1 << v for v in comp) for comp in nx.connected_components(sub))
    got = chains(g, col, a, b)
    assert sorted(got) == expected
    for ch in got:  # swapping any chain keeps the colouring proper
        assert is_proper(g, swap(col, ch, a, b))


@settings(max_examples=100, deadline=None)
@given(coloured(max_n=5))  # classes can be exponential: an edgeless graph has 4^n
def test_kempe_class_is_closed_and_proper(gc: tuple[Graph, tuple[int, ...]]) -> None:
    g, col = gc
    cls = kempe_class(g, col, colors=range(4))
    assert col in cls and all(is_proper(g, c) for c in cls)
    assert kempe_class(g, cls[-1], colors=range(4)) == cls  # equivalence class
    canon = kempe_class(g, col, colors=range(4), up_to_permutation=True)
    assert set(canon) == {normalize_colors(c) for c in cls}
