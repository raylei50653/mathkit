import importlib
from itertools import product
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mathkit.core.coloring import (
    UNCOLORED,
    chromatic_number,
    conflicts,
    count_extensions,
    extensions,
    first_extension,
    is_colorable,
    is_proper,
    normalize_colors,
    palette,
)
from mathkit.core.graph import Graph

nx: Any = importlib.import_module("networkx")

C5 = Graph.from_edges(5, [(i, (i + 1) % 5) for i in range(5)])


@st.composite
def small_graphs(draw: st.DrawFn, max_n: int = 7) -> Graph:
    n = draw(st.integers(0, max_n))
    pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
    return Graph.from_edges(n, [e for e in pairs if draw(st.booleans())])


def _brute(g: Graph, lists: list[int], fixed: dict[int, int]) -> set[tuple[int, ...]]:
    """Independent reference: filter the full product of the lists."""
    choices = [[c for c in range(8) if lists[v] >> c & 1] for v in range(g.n)]
    return {
        col
        for col in product(*choices)
        if all(col[u] != col[v] for u, v in g.edges())
        and all(col[v] == c for v, c in fixed.items())
    }


def test_cycle_counts() -> None:
    # chromatic polynomial of C_n at k: (k-1)^n + (-1)^n (k-1)
    assert count_extensions(C5, palette(3)) == 2**5 - 2
    assert chromatic_number(C5) == 3
    assert not is_colorable(C5, 2)


def test_petersen() -> None:
    petersen = Graph.from_networkx(nx.petersen_graph())
    assert chromatic_number(petersen) == 3
    assert count_extensions(petersen, palette(3)) == 120


def test_fixed_and_lists() -> None:
    assert first_extension(C5, palette(3), {0: 0, 1: 0}) is None  # adjacent clash
    assert first_extension(C5, palette(3), {0: 5}) is None  # outside the list
    cols = list(extensions(C5, [0b001, 0b110, 0b011, 0b110, 0b110]))
    assert cols and all(c[0] == 0 and is_proper(C5, c) for c in cols)
    with pytest.raises(ValueError, match="lists"):
        list(extensions(C5, [1, 1]))
    with pytest.raises(ValueError, match="outside"):
        list(extensions(C5, palette(3), {9: 0}))


def test_conflicts_ignore_uncoloured() -> None:
    assert conflicts(C5, (0, 0, UNCOLORED, UNCOLORED, 1)) == [(0, 1)]
    assert is_proper(C5, (UNCOLORED,) * 5)
    with pytest.raises(ValueError):
        is_proper(C5, (0,))


def test_normalize_colors() -> None:
    assert normalize_colors((3, 1, 3, UNCOLORED, 0)) == (0, 1, 0, UNCOLORED, 2)


@settings(max_examples=200)
@given(small_graphs(), st.data())
def test_extensions_match_brute_force(g: Graph, data: st.DataObject) -> None:
    lists = [data.draw(st.integers(1, 15)) for _ in range(g.n)]
    fixed_vs = data.draw(st.lists(st.integers(0, max(g.n - 1, 0)), max_size=2)) if g.n else []
    fixed = {v: data.draw(st.integers(0, 3)) for v in fixed_vs}
    got = list(extensions(g, lists, fixed))
    assert len(got) == len(set(got))  # no duplicates
    assert set(got) == _brute(g, lists, fixed)
    assert list(extensions(g, lists, fixed)) == got  # deterministic order


@given(small_graphs(max_n=9))
def test_chromatic_number_vs_networkx_greedy(g: Graph) -> None:
    chi = chromatic_number(g)
    greedy = nx.greedy_color(g.to_networkx(), strategy="largest_first")
    assert chi <= (max(greedy.values()) + 1 if greedy else 0)
    col = first_extension(g, palette(chi))
    assert col is not None and is_proper(g, col)
    assert chi == 0 or not is_colorable(g, chi - 1)
