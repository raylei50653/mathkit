"""Kempe chains: components of the subgraph induced by two colours, swaps, and Kempe classes.

Chains are vertex bitmasks. Uncoloured vertices (``UNCOLORED``) belong to no chain.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Sequence

from mathkit.core.coloring import UNCOLORED, Coloring, normalize_colors
from mathkit.core.graph import Graph


def color_mask(col: Sequence[int], a: int, b: int) -> int:
    """Vertices coloured ``a`` or ``b``."""
    return sum(1 << v for v, c in enumerate(col) if c != UNCOLORED and c in (a, b))


def chain(g: Graph, col: Sequence[int], v: int, a: int, b: int) -> int:
    """The ``{a, b}``-Kempe chain containing ``v`` (``v`` must be coloured ``a`` or ``b``)."""
    allowed = color_mask(col, a, b)
    if not allowed >> v & 1:
        raise ValueError(f"vertex {v} has colour {col[v]}, not {a} or {b}")
    comp, frontier = 1 << v, 1 << v
    while frontier:
        low = frontier & -frontier
        frontier ^= low
        new = g.adj[low.bit_length() - 1] & allowed & ~comp
        comp |= new
        frontier |= new
    return comp


def chains(g: Graph, col: Sequence[int], a: int, b: int) -> list[int]:
    """All ``{a, b}``-Kempe chains, ordered by lowest vertex."""
    rest = color_mask(col, a, b)
    out: list[int] = []
    while rest:
        v = (rest & -rest).bit_length() - 1
        comp = chain(g, col, v, a, b)
        out.append(comp)
        rest &= ~comp
    return out


def swap(col: Sequence[int], mask: int, a: int, b: int) -> Coloring:
    """Exchange colours ``a`` and ``b`` on the vertices of ``mask``.

    Swapping a whole Kempe chain keeps a proper colouring proper.
    """
    out = list(col)
    for v in range(len(out)):
        if mask >> v & 1:
            if out[v] == a:
                out[v] = b
            elif out[v] == b:
                out[v] = a
    return tuple(out)


def kempe_class(
    g: Graph,
    col: Sequence[int],
    colors: Iterable[int] | None = None,
    *,
    up_to_permutation: bool = False,
    limit: int = 100_000,
) -> tuple[Coloring, ...]:
    """Colourings reachable from ``col`` by single-chain Kempe swaps, sorted.

    ``colors`` is the palette swaps may use (default: colours present in ``col``; including an
    absent colour allows recolouring a vertex to it). With ``up_to_permutation`` each colouring
    is replaced by :func:`normalize_colors` of it. Raises ``OverflowError`` past ``limit``.
    """
    pal = sorted(set(colors) if colors is not None else {c for c in col if c != UNCOLORED})
    pairs = [(a, b) for i, a in enumerate(pal) for b in pal[i + 1 :]]
    canon: Callable[[Sequence[int]], Coloring] = normalize_colors if up_to_permutation else _as_is
    start = tuple(col)
    seen = {canon(start)}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        for a, b in pairs:
            for ch in chains(g, cur, a, b):
                nxt = swap(cur, ch, a, b)
                key = canon(nxt)
                if key not in seen:
                    if len(seen) >= limit:
                        raise OverflowError(f"Kempe class exceeds {limit} colourings")
                    seen.add(key)
                    queue.append(nxt)
    return tuple(sorted(seen))


def _as_is(col: Sequence[int]) -> Coloring:
    return tuple(col)
