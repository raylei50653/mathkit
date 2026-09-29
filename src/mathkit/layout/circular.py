"""Outer nodes on a regular polygon, inner nodes at the centre or on a smaller ring.

Trigonometry runs in ``decimal`` at fixed precision rather than through the platform libm,
so the quantized output is byte-identical everywhere (``exact = True``).
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal, localcontext

from mathkit.layout.grid import GRID, quantize
from mathkit.scene import Pos, Scene

_PREC = 40
_PI = Decimal("3.14159265358979323846264338327950288419716939937510")
_HALF = Decimal(GRID) / 2


def circular(scene: Scene) -> tuple[Mapping[str, Pos], bool, tuple[str, ...]]:
    outer = list(scene.layout.outer) or [n.id for n in scene.nodes]
    on_outer = set(outer)
    inner = [n.id for n in scene.nodes if n.id not in on_outer]
    pos = dict(ring(outer, _HALF))
    if len(inner) == 1:
        pos[inner[0]] = (GRID // 2, GRID // 2)
    else:
        pos.update(ring(inner, _HALF / 2))
    return pos, True, scene.layout.outer


def ring[K](ids: Sequence[K], radius: Decimal) -> list[tuple[K, Pos]]:
    """Regular polygon centred in the grid box: first id at the top, then counter-clockwise."""
    out: list[tuple[K, Pos]] = []
    with localcontext() as ctx:
        ctx.prec = _PREC
        for k, node in enumerate(ids):
            theta = _PI / 2 + 2 * _PI * k / len(ids)
            cos, sin = _cos_sin(theta)
            out.append((node, (quantize(_HALF + radius * cos), quantize(_HALF + radius * sin))))
    return out


def _cos_sin(theta: Decimal) -> tuple[Decimal, Decimal]:
    """Taylor series after reducing ``theta`` into ``[-pi, pi]``."""
    two_pi = 2 * _PI
    theta -= two_pi * (theta / two_pi).to_integral_value()
    cos, sin = Decimal(0), Decimal(0)
    term, i = Decimal(1), 0  # term = theta**i / i!
    eps = Decimal(10) ** -(_PREC - 2)
    while abs(term) > eps or i < 2:
        if i % 4 == 0:
            cos += term
        elif i % 4 == 1:
            sin += term
        elif i % 4 == 2:
            cos -= term
        else:
            sin -= term
        i += 1
        term = term * theta / i
    return cos, sin
