"""Hand-written, byte-deterministic SVG with a light palette and a dark-mode override.

Only the first ``vertex-color`` layer is drawn; choosing among several is the view's job.
"""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape, quoteattr

from mathkit.core.certificate import canonical_json
from mathkit.scene import Node, Scene

MARGIN = 500
NODE_R = 360
FONT = 320
PX_PER_UNIT = 25  # 10 000 grid units -> 400 px

LIGHT = {
    "bg": "#ffffff", "fg": "#1f2328", "edge": "#6e7781", "outer": "#0550ae",
    "emph": "#cf222e", "muted": "#afb8c1",
    "c": ("#ffd8a8", "#a5d8ff", "#b2f2bb", "#ffc9c9", "#d0bfff", "#ffec99", "#99e9f2", "#eebefa"),
}
DARK = {
    "bg": "#0d1117", "fg": "#e6edf3", "edge": "#8b949e", "outer": "#58a6ff",
    "emph": "#ff7b72", "muted": "#484f58",
    "c": ("#9a5b13", "#1f6feb", "#2b7a3d", "#a4363a", "#6e40c9", "#8a6d00", "#1b7c83", "#8e3a9e"),
}
PALETTE_SIZE = len(LIGHT["c"])

_LAYOUT_CSS = """\
.mk-edge{stroke-width:40;stroke-linecap:round}
.mk-edge.mk-outer,.mk-edge.mk-emphasis{stroke-width:70}
.mk-edge.mk-dashed{stroke-dasharray:120 90}
.mk-node circle{stroke-width:40}
.mk-node.mk-outer circle,.mk-node.mk-emphasis circle{stroke-width:70}
.mk-node.mk-dashed circle{stroke-dasharray:90 60}
.mk-node text{font-family:serif;font-style:italic;text-anchor:middle;dominant-baseline:central}
"""


def _colors(p: dict[str, Any]) -> str:
    """Colour rules as literals, not CSS variables, so non-browser SVG consumers render them."""
    rules = [
        f".mk-bg{{fill:{p['bg']}}}",
        f".mk-edge{{stroke:{p['edge']}}}",
        f".mk-edge.mk-outer{{stroke:{p['outer']}}}",
        f".mk-edge.mk-emphasis{{stroke:{p['emph']}}}",
        f".mk-edge.mk-muted{{stroke:{p['muted']}}}",
        f".mk-node circle{{fill:{p['bg']};stroke:{p['fg']}}}",
        f".mk-node.mk-outer circle{{stroke:{p['outer']}}}",
        f".mk-node.mk-emphasis circle{{stroke:{p['emph']}}}",
        f".mk-node.mk-muted circle{{stroke:{p['muted']}}}",
        f".mk-node text{{fill:{p['fg']}}}",
        *(f".mk-node circle.mk-c{i}{{fill:{c}}}" for i, c in enumerate(p["c"])),
    ]
    return "\n".join(rules) + "\n"


_STYLE = (
    _LAYOUT_CSS
    + _colors(LIGHT)
    + "@media (prefers-color-scheme:dark){\n"
    + _colors(DARK)
    + "}\n"
)

def render_svg(scene: Scene) -> str:
    if any(n.pos is None for n in scene.nodes):
        raise ValueError("render_svg needs a laid-out scene (run mathkit.layout.apply_layout)")
    pos = {n.id: _pos(n) for n in scene.nodes}
    xs = [p[0] for p in pos.values()] or [0]
    ys = [p[1] for p in pos.values()] or [0]
    min_x, max_y = min(xs), max(ys)
    width = max(xs) - min_x + 2 * MARGIN
    height = max_y - min(ys) + 2 * MARGIN

    def at(node_id: str) -> tuple[int, int]:
        x, y = pos[node_id]
        return x - min_x + MARGIN, max_y - y + MARGIN  # flip: scene y points up

    colors: dict[str, int] = {}
    for layer in scene.layers:
        if layer.kind == "vertex-color":
            colors = dict(layer.values)
            break

    meta = canonical_json(
        {
            "evidence": scene.evidence,
            "provenance": dict(scene.provenance),
            "layout": scene.layout.to_json(),
        }
    )
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width // PX_PER_UNIT}" height="{height // PX_PER_UNIT}" '
        f'data-evidence={quoteattr(scene.evidence)} role="img">',
        f"<title>{escape(scene.title)}</title>",
        f"<metadata>{escape(meta)}</metadata>",
        f"<style>\n{_STYLE}</style>",
        f'<rect class="mk-bg" width="{width}" height="{height}"/>',
        '<g class="mk-edges">',
    ]
    for e in scene.edges:
        (x1, y1), (x2, y2) = at(e.u), at(e.v)
        out.append(
            f'<line class="mk-edge mk-{e.cls}" data-id={quoteattr(e.id)} '
            f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
        )
    out.append("</g>")
    out.append('<g class="mk-nodes">')
    for n in scene.nodes:
        x, y = at(n.id)
        fill = f' class="mk-c{colors[n.id] % PALETTE_SIZE}"' if n.id in colors else ""
        out.append(f'<g class="mk-node mk-{n.cls}" data-id={quoteattr(n.id)}>')
        out.append(f'<circle{fill} cx="{x}" cy="{y}" r="{NODE_R}"/>')
        if n.label:
            out.append(f'<text x="{x}" y="{y}" font-size="{FONT}">{_label(n.label)}</text>')
        out.append("</g>")
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _pos(n: Node) -> tuple[int, int]:
    assert n.pos is not None
    return n.pos


def _label(label: str) -> str:
    """``b_0`` renders as b with subscript 0; everything else is literal text."""
    base, sep, sub = label.partition("_")
    if not sep or not base or not sub:
        return escape(label)
    return (
        f'{escape(base)}<tspan font-size="{FONT * 7 // 10}" dy="{FONT // 4}" '
        f'font-style="normal">{escape(sub)}</tspan>'
    )
