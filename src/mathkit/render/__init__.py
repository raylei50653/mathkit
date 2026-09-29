"""Scene renderers: svg, tikz, json. Output must be byte-deterministic."""

from mathkit.core.certificate import canonical_json
from mathkit.render.svg import render_svg
from mathkit.scene import Scene


def render_json(scene: Scene) -> str:
    return canonical_json(scene.to_json())


RENDERERS = {"svg": render_svg, "json": render_json}

__all__ = ["RENDERERS", "render_json", "render_svg"]
