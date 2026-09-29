from dataclasses import replace

import pytest

from mathkit.compile import compile_visual
from mathkit.domains import Domains
from mathkit.ir import MathDocument
from mathkit.layout import GRID, LAYOUT_VERSION, LayoutError, apply_layout
from mathkit.layout.circular import circular
from mathkit.render import render_json, render_svg
from mathkit.scene import Edge, Node, Scene, load_scene


def _bare(n: int) -> Scene:
    nodes = tuple(Node(f"n{i}", str(i), origin=(f"G/{i}",)) for i in range(n))
    return Scene("t", "computation", {}, nodes, ())


def test_circular_square_is_exact_grid() -> None:
    pos, exact, _ = circular(_bare(4))
    assert exact
    half = GRID // 2
    assert dict(pos) == {"n0": (half, GRID), "n1": (0, half), "n2": (half, 0), "n3": (GRID, half)}


def test_c5_layout(c5_doc: MathDocument, domains: Domains) -> None:
    scene = apply_layout(compile_visual(c5_doc, domains.registry))
    assert scene.layout.engine == "tutte" and scene.layout.exact
    assert scene.layout.version == LAYOUT_VERSION
    pos = {n.label: n.pos for n in scene.nodes}
    assert pos["v"] == (GRID // 2, GRID // 2)
    assert pos["b_0"] == (GRID // 2, GRID)
    # b_1 at 90 + 72 degrees: (5000 + 5000 cos 162°, 5000 + 5000 sin 162°)
    assert pos["b_1"] == (245, 6545)
    # mirror symmetry of the regular pentagon survives quantization
    for a, b in (("b_1", "b_4"), ("b_2", "b_3")):
        (xa, ya), (xb, yb) = pos[a], pos[b]  # type: ignore[misc]
        assert xa + xb == GRID and ya == yb


def test_inner_ring_when_several_inner_nodes() -> None:
    scene = replace(_bare(6), layout=replace(_bare(0).layout, outer=("n0", "n1", "n2")))
    pos = {n.id: n.pos for n in apply_layout(scene).nodes}
    assert pos["n3"] == (GRID // 2, GRID * 3 // 4)
    assert len(set(pos.values())) == 6


def test_fixed_layout() -> None:
    scene = _bare(2)
    with pytest.raises(LayoutError, match="no pos"):
        apply_layout(scene, "fixed")
    placed = replace(scene, nodes=tuple(replace(n, pos=(i, -i)) for i, n in enumerate(scene.nodes)))
    out = apply_layout(placed)
    assert out.layout.engine == "fixed" and out.nodes[1].pos == (1, -1)
    with pytest.raises(LayoutError, match="unknown layout engine"):
        apply_layout(placed, "spring")


def test_svg_needs_positions() -> None:
    with pytest.raises(ValueError, match="laid-out"):
        render_svg(_bare(1))


def test_svg_contents(c5_doc: MathDocument, domains: Domains) -> None:
    scene = apply_layout(compile_visual(c5_doc, domains.registry, title="c5 & friends"))
    svg = render_svg(scene)
    assert svg.startswith("<svg ") and svg.endswith("</svg>\n")
    assert "<title>c5 &amp; friends</title>" in svg
    assert 'data-evidence="paper"' in svg
    assert svg.count('<line class="mk-edge mk-outer"') == 5
    assert svg.count('<g class="mk-node mk-') == 6
    assert "prefers-color-scheme:dark" in svg and "var(" not in svg
    assert "b<tspan" in svg


def test_scene_json_round_trip(c5_doc: MathDocument, domains: Domains) -> None:
    scene = apply_layout(compile_visual(c5_doc, domains.registry))
    import json

    again = load_scene(json.loads(render_json(scene)))
    assert again == scene
    assert render_svg(again) == render_svg(scene)


def test_load_scene_rejects_bad_edges() -> None:
    scene = replace(_bare(1), edges=(Edge("s0", "n0", "n9", origin=("G/e",)),))
    from mathkit.scene import SceneError

    with pytest.raises(SceneError, match="endpoint"):
        load_scene(scene.to_json())
