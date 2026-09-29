"""Use the positions the Scene already carries (hand placement stays reproducible)."""

from collections.abc import Mapping

from mathkit.scene import Pos, Scene


class LayoutError(ValueError):
    """The requested layout cannot be applied to this Scene."""


def fixed(scene: Scene) -> tuple[Mapping[str, Pos], bool]:
    pos: dict[str, Pos] = {}
    for n in scene.nodes:
        if n.pos is None:
            raise LayoutError(f"fixed layout: node {n.id!r} has no pos")
        pos[n.id] = n.pos
    return pos, True
