"""Planar test graphs: hypothesis strategies and a Graph -> Scene helper."""

from hypothesis import strategies as st

from mathkit.compile import compile_visual
from mathkit.core.graph import Graph
from mathkit.domains import load_domains
from mathkit.ir import GraphEdge, GraphObject, MathDocument
from mathkit.scene import Scene


@st.composite
def triangulations(draw: st.DrawFn, max_n: int = 14) -> Graph:
    """Maximal planar graphs (hence 3-connected for n >= 4): stacked insertions + edge flips."""
    n = draw(st.integers(4, max_n))
    faces: list[tuple[int, int, int]] = [(0, 1, 2), (0, 2, 1)]  # both sides of the triangle
    for v in range(3, n):
        a, b, c = faces.pop(draw(st.integers(0, len(faces) - 1)))
        faces += [(a, b, v), (b, c, v), (c, a, v)]
    for _ in range(draw(st.integers(0, 3 * n))):
        _flip(faces, draw(st.integers(0, len(faces) - 1)), draw(st.integers(0, 2)))
    edges = {(min(p), max(p)) for f in faces for p in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))}
    return Graph.from_edges(n, sorted(edges))


def _flip(faces: list[tuple[int, int, int]], i: int, k: int) -> None:
    """Flip edge ``k`` of face ``i`` if the result stays a simple triangulation."""
    f = faces[i]
    a, b, c = f[k], f[(k + 1) % 3], f[(k + 2) % 3]
    j = next(j for j, h in enumerate(faces) if j != i and _has_dart(h, b, a))
    h = faces[j]
    d = next(x for x in h if x not in (a, b))
    if c == d or any({c, d} <= set(g) for g in faces):
        return
    faces[i], faces[j] = (c, a, d), (d, b, c)


def _has_dart(face: tuple[int, int, int], u: int, v: int) -> bool:
    return any(face[m] == u and face[(m + 1) % 3] == v for m in range(3))


@st.composite
def planar_graphs(draw: st.DrawFn, max_n: int = 12) -> Graph:
    """Triangulations with a random subset of edges removed."""
    tri = draw(triangulations(max_n))
    keep = [e for e in tri.edges() if draw(st.booleans())]
    return Graph.from_edges(tri.n, keep)


def scene_of(g: Graph, title: str = "") -> Scene:
    """Compile a bare graph through the normal IR -> Scene path."""
    names = tuple(f"v{i}" for i in range(g.n))
    edges = tuple(GraphEdge(f"e{i}", names[u], names[v]) for i, (u, v) in enumerate(g.edges()))
    doc = MathDocument("computation", {}, (GraphObject("G", names, edges),))
    return compile_visual(doc, load_domains([]).registry, title=title)
