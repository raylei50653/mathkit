"""Deterministic layouts on the canonical integer grid (ADR-0006).

Coordinates are integers in ``[0, GRID]``, y pointing up. ``LAYOUT_VERSION`` is written into
every Scene; changing any engine's output bumps it.
"""

from collections.abc import Callable, Mapping

from mathkit.layout.circular import circular
from mathkit.layout.fixed import LayoutError, fixed
from mathkit.layout.grid import GRID
from mathkit.scene import Layout as LayoutInfo
from mathkit.scene import Pos, Scene

LAYOUT_VERSION = 1

#: engine -> (positions, exact). ``exact`` means byte-identical output on every platform.
Engine = Callable[[Scene], tuple[Mapping[str, Pos], bool]]
ENGINES: Mapping[str, Engine] = {"fixed": fixed, "circular": circular}


def apply_layout(scene: Scene, engine: str | None = None) -> Scene:
    """Fill every node's ``pos``. ``engine`` overrides the compiler's hint.

    Without either, scenes whose nodes all carry positions use ``fixed``, others ``circular``.
    """
    name = engine or scene.layout.engine
    if name is None:
        name = "fixed" if all(n.pos is not None for n in scene.nodes) else "circular"
    run = ENGINES.get(name)
    if run is None:
        raise LayoutError(f"unknown layout engine {name!r}; available: {sorted(ENGINES)}")
    pos, exact = run(scene)
    info = LayoutInfo(name, scene.layout.outer, LAYOUT_VERSION, exact)
    return scene.with_positions(pos, info)


__all__ = ["ENGINES", "GRID", "LAYOUT_VERSION", "LayoutError", "apply_layout"]
