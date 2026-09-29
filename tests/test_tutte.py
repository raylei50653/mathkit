"""Tutte layout: semantic + byte goldens on planar graph classes, and a no-crossing property.

Regenerate goldens after an intentional change with
``MATHKIT_UPDATE_GOLDEN=1 uv run pytest tests/test_tutte.py`` (and bump LAYOUT_VERSION).
"""

import hashlib
import importlib
import json
import os
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from itertools import combinations
from typing import Any

import pytest
from hypothesis import given, settings

from mathkit.core.graph import Graph
from mathkit.core.planar import embed
from mathkit.layout import GRID, LayoutError, apply_layout
from mathkit.layout.circular import ring
from mathkit.layout.tutte import EXACT_MAX_INTERIOR, barycentric, choose_outer
from mathkit.render import render_json

from .conftest import GOLDEN
from .planar_graphs import scene_of, triangulations

nx: Any = importlib.import_module("networkx")

CLASSES: dict[str, Any] = {
    "wheel8": nx.wheel_graph(8),
    "cube": nx.cubical_graph(),
    "octahedron": nx.octahedral_graph(),
    "prism5": nx.circular_ladder_graph(5),
    "dodecahedron": nx.dodecahedral_graph(),
    "icosahedron": nx.icosahedral_graph(),
}


def _semantic(g: Graph) -> dict[str, Any]:
    emb = embed(g)
    assert emb is not None
    return {
        "n": g.n,
        "m": g.edge_count(),
        "faces": sorted(sorted(f) for f in emb.faces()),
        "outer": choose_outer(g),
    }


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_planar_class_goldens(name: str) -> None:
    g = Graph.from_networkx(CLASSES[name])
    scene = apply_layout(scene_of(g, title=name), "tutte")
    assert scene.layout.exact
    digest = hashlib.sha256(render_json(scene).encode()).hexdigest()
    record = {**_semantic(g), "scene_sha256": digest}
    path = GOLDEN / "planar" / f"{name}.json"
    if os.environ.get("MATHKIT_UPDATE_GOLDEN"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    golden = json.loads(path.read_text(encoding="utf-8"))
    semantic = {k: v for k, v in record.items() if k != "scene_sha256"}
    assert semantic == {k: v for k, v in golden.items() if k != "scene_sha256"}  # all platforms
    assert record["scene_sha256"] == golden["scene_sha256"]  # exact path => byte-identical


def test_auto_outer_is_recorded() -> None:
    scene = apply_layout(scene_of(Graph.from_networkx(nx.cubical_graph())), "tutte")
    assert len(scene.layout.outer) == 4
    corners = {n.pos for n in scene.nodes if n.id in scene.layout.outer}
    assert corners == {(GRID // 2, GRID), (0, GRID // 2), (GRID // 2, 0), (GRID, GRID // 2)}


def test_large_interior_falls_back_to_float() -> None:
    grid = Graph.from_networkx(nx.convert_node_labels_to_integers(nx.grid_2d_graph(12, 12)))
    scene = apply_layout(scene_of(grid), "tutte")
    assert len(grid.adj) - len(scene.layout.outer) > EXACT_MAX_INTERIOR
    assert scene.layout.exact is False
    assert all(0 <= c <= GRID for n in scene.nodes for c in n.pos or ())


def test_layout_errors() -> None:
    with pytest.raises(LayoutError, match="planar"):
        apply_layout(scene_of(Graph.from_networkx(nx.complete_graph(5))), "tutte")
    with pytest.raises(LayoutError, match="simple cycle"):
        apply_layout(scene_of(Graph.from_edges(3, [(0, 1), (1, 2)])), "tutte")
    tri_plus = scene_of(Graph.from_edges(4, [(0, 1), (1, 2), (2, 0)]))
    pinned = replace(tri_plus, layout=replace(tri_plus.layout, outer=("n0", "n1", "n2")))
    with pytest.raises(LayoutError, match="not connected"):
        apply_layout(pinned, "tutte")


def _orient(p: Any, q: Any, r: Any) -> int:
    d = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (d > 0) - (d < 0)


def _crosses(a: Any, b: Any, c: Any, d: Any) -> bool:
    """Proper crossing of segments ab and cd (no shared endpoint)."""
    return _orient(a, b, c) * _orient(a, b, d) < 0 and _orient(c, d, a) * _orient(c, d, b) < 0


def _overlaps(a: Any, b: Any, c: Any) -> bool:
    """Segments ab and ac, sharing endpoint a, lie on top of each other."""
    same_dir = (b[0] - a[0]) * (c[0] - a[0]) + (b[1] - a[1]) * (c[1] - a[1]) > 0
    return _orient(a, b, c) == 0 and same_dir


@settings(max_examples=60, deadline=None)
@given(triangulations(max_n=16))
def test_tutte_on_triangulations_has_no_crossings(g: Graph) -> None:
    outer = choose_outer(g)
    fixed = dict(ring(outer, Decimal(GRID) / 2))
    pos: dict[int, tuple[Fraction, Fraction]] = {
        v: (Fraction(x), Fraction(y)) for v, (x, y) in fixed.items()
    }
    pos.update(barycentric(g, fixed))
    assert len(set(pos.values())) == g.n
    edges = list(g.edges())
    for (a, b), (c, d) in combinations(edges, 2):
        shared = {a, b} & {c, d}
        if not shared:
            assert not _crosses(pos[a], pos[b], pos[c], pos[d]), ((a, b), (c, d))
        else:
            (s,) = shared
            x, y = ({a, b} - shared).pop(), ({c, d} - shared).pop()
            assert not _overlaps(pos[s], pos[x], pos[y]), ((a, b), (c, d))
