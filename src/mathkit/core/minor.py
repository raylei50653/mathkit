"""Minor models: verify branch sets, and extract a K5 / K3,3 model from a non-planar graph.

A *minor model* of ``H`` in ``G`` assigns vertex ``i`` of ``H`` a branch set ``B_i`` of ``G`` such
that the sets are non-empty, pairwise disjoint and each induces a connected subgraph, and every
edge ``ij`` of ``H`` is realised by some edge of ``G`` between ``B_i`` and ``B_j``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from mathkit.core.graph import Graph
from mathkit.core.planar import is_planar

K5 = Graph.from_edges(5, [(u, v) for u in range(5) for v in range(u + 1, 5)])
#: Sides ``{0, 1, 2}`` and ``{3, 4, 5}``.
K33 = Graph.from_edges(6, [(u, v) for u in range(3) for v in range(3, 6)])


@dataclass(frozen=True, slots=True)
class MinorCheck:
    """Truthy iff the model is valid; ``reason`` explains the first failure."""

    ok: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


def check_minor(g: Graph, branch_sets: Sequence[int | Iterable[int]], h: Graph) -> MinorCheck:
    """Verify that ``branch_sets`` (bitmasks or vertex iterables) is a model of ``h`` in ``g``."""
    sets = [b if isinstance(b, int) else sum(1 << v for v in set(b)) for b in branch_sets]
    if len(sets) != h.n:
        return MinorCheck(False, f"{len(sets)} branch sets for {h.n} vertices of H")
    full = (1 << g.n) - 1
    used = 0
    for i, b in enumerate(sets):
        if b <= 0:
            return MinorCheck(False, f"branch set {i} is empty")
        if b & ~full:
            return MinorCheck(False, f"branch set {i} has a vertex outside 0..{g.n - 1}")
        if b & used:
            return MinorCheck(False, f"branch set {i} overlaps an earlier one")
        used |= b
        if not _connected_within(g, b):
            return MinorCheck(False, f"branch set {i} is not connected")
    for i, j in h.edges():
        if not any(g.adj[v] & sets[j] for v in _bits(sets[i])):
            return MinorCheck(False, f"no edge between branch sets {i} and {j}")
    return MinorCheck(True)


@dataclass(frozen=True, slots=True)
class Kuratowski:
    """A certificate of non-planarity: ``graph`` is ``"K5"`` or ``"K33"``."""

    graph: str
    branch_sets: tuple[int, ...]

    @property
    def h(self) -> Graph:
        return K5 if self.graph == "K5" else K33


def kuratowski(g: Graph) -> Kuratowski | None:
    """A K5 or K3,3 minor model of ``g``, or ``None`` if ``g`` is planar.

    Deletes edges while the graph stays non-planar, leaving a subdivision of K5 or K3,3; each
    subdivided path is then absorbed into the branch set of one endpoint. The result is
    re-verified with :func:`check_minor`. Deterministic; O(m) planarity tests.
    """
    if is_planar(g):
        return None
    edges = list(g.edges())
    keep = set(edges)
    for e in edges:
        keep.discard(e)
        if is_planar(Graph.from_edges(g.n, sorted(keep))):
            keep.add(e)
    sub = Graph.from_edges(g.n, sorted(keep))
    branch = [v for v in range(g.n) if sub.degree(v) >= 3]
    sets = {v: 1 << v for v in branch}
    links: set[tuple[int, int]] = set()
    for s in branch:
        for first in sub.neighbors(s):
            prev, cur, path = s, first, 0
            while sub.degree(cur) == 2:
                path |= 1 << cur
                prev, cur = cur, next(w for w in sub.neighbors(cur) if w != prev)
            if s < cur:  # each path once, absorbed into its smaller endpoint
                sets[s] |= path
                links.add((s, cur))
    if len(branch) == 5:
        model = Kuratowski("K5", tuple(sets[v] for v in branch))
    elif len(branch) == 6:
        side = _two_colour(branch, links)
        order = [v for v in branch if side[v] == 0] + [v for v in branch if side[v] == 1]
        model = Kuratowski("K33", tuple(sets[v] for v in order))
    else:  # pragma: no cover - Kuratowski's theorem
        raise AssertionError(f"minimal non-planar subgraph has {len(branch)} branch vertices")
    check = check_minor(g, model.branch_sets, model.h)
    assert check, check.reason
    return model


def _two_colour(vertices: list[int], links: set[tuple[int, int]]) -> dict[int, int]:
    side = {vertices[0]: 0}
    changed = True
    while changed:
        changed = False
        for u, v in sorted(links):
            for a, b in ((u, v), (v, u)):
                if a in side and b not in side:
                    side[b] = 1 - side[a]
                    changed = True
    return side


def _connected_within(g: Graph, mask: int) -> bool:
    start = mask & -mask
    comp, frontier = start, start
    while frontier:
        low = frontier & -frontier
        frontier ^= low
        new = g.adj[low.bit_length() - 1] & mask & ~comp
        comp |= new
        frontier |= new
    return comp == mask


def _bits(mask: int) -> Iterable[int]:
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low
