"""Tutte barycentric layout: outer cycle pinned to a regular polygon, each inner node at the
average of its neighbours.

For a 3-connected planar graph whose outer cycle is a face, the result is a planar straight-line
drawing with convex faces (Tutte 1963). Up to ``EXACT_MAX_INTERIOR`` inner nodes the linear
system is solved in ``fractions.Fraction`` and rounded half-to-even, so the output is
byte-identical on every platform (``exact = True``); larger systems use numpy floats.
Changing this threshold changes output and must bump ``LAYOUT_VERSION`` (ADR-0006).
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from fractions import Fraction

from mathkit.core.graph import Graph
from mathkit.core.planar import embed
from mathkit.layout.circular import ring
from mathkit.layout.fixed import LayoutError
from mathkit.layout.grid import GRID
from mathkit.scene import Pos, Scene

EXACT_MAX_INTERIOR = 64

Point = tuple[Fraction, Fraction]


def tutte(scene: Scene) -> tuple[Mapping[str, Pos], bool, tuple[str, ...]]:
    ids = [n.id for n in scene.nodes]
    index = {k: i for i, k in enumerate(ids)}
    pairs = {(min(index[e.u], index[e.v]), max(index[e.u], index[e.v])) for e in scene.edges}
    g = Graph.from_edges(len(ids), sorted(p for p in pairs if p[0] != p[1]))
    outer = [index[k] for k in scene.layout.outer] if scene.layout.outer else choose_outer(g)
    if len(outer) < 3:
        raise LayoutError("tutte layout needs an outer cycle of at least 3 nodes")
    fixed = dict(ring(outer, Decimal(GRID) / 2))
    interior = g.n - len(fixed)
    if interior <= EXACT_MAX_INTERIOR:
        solved = {v: (round(x), round(y)) for v, (x, y) in barycentric(g, fixed).items()}
        exact = True
    else:
        solved = _barycentric_float(g, fixed)
        exact = False
    pos = {ids[v]: p for v, p in {**solved, **fixed}.items()}
    return pos, exact, tuple(ids[i] for i in outer)


def choose_outer(g: Graph) -> list[int]:
    """Largest face bounded by a simple cycle; ties go to the smallest sorted vertex set.

    Faces are compared as vertex sets and the cycle is oriented canonically, so for
    3-connected graphs (unique embedding up to mirroring) the choice does not depend on
    which embedding the planarity test returned.
    """
    emb = embed(g)
    if emb is None:
        raise LayoutError("tutte layout without layout.outer needs a planar graph")
    simple = [f for f in emb.faces() if len(f) >= 3 and len(set(f)) == len(f)]
    if not simple:
        raise LayoutError("tutte layout: no face is bounded by a simple cycle; use circular")
    face = min(simple, key=lambda f: (-len(f), sorted(f)))
    i = face.index(min(face))
    cycle = list(face[i:] + face[:i])
    if cycle[-1] < cycle[1]:  # walk towards the smaller neighbour of the minimum
        cycle = [cycle[0], *reversed(cycle[1:])]
    return cycle


def barycentric(g: Graph, fixed: Mapping[int, Pos]) -> dict[int, Point]:
    """Exact positions of the non-fixed vertices (Gaussian elimination over the rationals)."""
    inner, row = _inner(g, fixed)
    k = len(inner)
    # Augmented rows [L | bx | by]; L is symmetric positive definite, so no pivoting is needed.
    m: list[list[Fraction]] = []
    for v in inner:
        r = [Fraction(0)] * (k + 2)
        r[row[v]] = Fraction(g.degree(v))
        for u in g.neighbors(v):
            if u in row:
                r[row[u]] -= 1
            else:
                r[k] += fixed[u][0]
                r[k + 1] += fixed[u][1]
        m.append(r)
    for c in range(k):
        pivot = m[c][c]
        for r in range(c + 1, k):
            f = m[r][c] / pivot
            if f:
                mr, mc = m[r], m[c]
                for j in range(c, k + 2):
                    mr[j] -= f * mc[j]
    sol: list[Point] = [(Fraction(0), Fraction(0))] * k
    for c in reversed(range(k)):
        x, y = m[c][k], m[c][k + 1]
        for j in range(c + 1, k):
            if m[c][j]:
                x -= m[c][j] * sol[j][0]
                y -= m[c][j] * sol[j][1]
        sol[c] = (x / m[c][c], y / m[c][c])
    return {v: sol[row[v]] for v in inner}


def _barycentric_float(g: Graph, fixed: Mapping[int, Pos]) -> dict[int, Pos]:
    import numpy as np

    inner, row = _inner(g, fixed)
    k = len(inner)
    a = np.zeros((k, k))
    b = np.zeros((k, 2))
    for v in inner:
        a[row[v], row[v]] = g.degree(v)
        for u in g.neighbors(v):
            if u in row:
                a[row[v], row[u]] -= 1
            else:
                b[row[v]] += fixed[u]
    sol = np.linalg.solve(a, b)
    return {v: (round(float(sol[row[v], 0])), round(float(sol[row[v], 1]))) for v in inner}


def _inner(g: Graph, fixed: Mapping[int, Pos]) -> tuple[Sequence[int], dict[int, int]]:
    """Non-fixed vertices, after checking each can reach a fixed one (else L is singular)."""
    reach = 0
    frontier = sum(1 << v for v in fixed)
    while frontier:
        reach |= frontier
        low = frontier & -frontier
        frontier ^= low
        frontier |= g.adj[low.bit_length() - 1] & ~reach
    inner = [v for v in range(g.n) if v not in fixed]
    stranded = [v for v in inner if not reach >> v & 1]
    if stranded:
        raise LayoutError(f"tutte layout: {len(stranded)} node(s) not connected to the outer cycle")
    return inner, {v: i for i, v in enumerate(inner)}
