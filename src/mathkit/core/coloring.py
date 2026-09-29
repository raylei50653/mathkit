"""Proper and list colourings by bitmask backtracking.

A colouring is a tuple of ints, one per vertex; ``UNCOLORED`` (-1) marks a vertex without a
colour. Colour lists are int bitmasks (bit ``c`` set = colour ``c`` allowed), so hot loops never
touch Python sets (ADR-0003).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

from mathkit.core.graph import Graph

UNCOLORED = -1
Coloring = tuple[int, ...]


def palette(k: int) -> int:
    """The list ``{0, ..., k-1}`` as a bitmask."""
    return (1 << k) - 1


def is_proper(g: Graph, col: Sequence[int]) -> bool:
    """No edge joins two vertices of the same colour (uncoloured vertices never conflict)."""
    return not conflicts(g, col)


def conflicts(g: Graph, col: Sequence[int]) -> list[tuple[int, int]]:
    """Monochromatic edges ``(u, v)``, ``u < v``, in order."""
    _check_length(g, col)
    return [(u, v) for u, v in g.edges() if col[u] != UNCOLORED and col[u] == col[v]]


def extensions(
    g: Graph, lists: Sequence[int] | int, fixed: Mapping[int, int] | None = None
) -> Iterator[Coloring]:
    """Every proper colouring with ``col[v]`` in ``lists[v]`` that agrees with ``fixed``.

    ``lists`` is one bitmask per vertex, or a single bitmask shared by all (``palette(k)`` for
    ordinary k-colouring). The enumeration order is deterministic but unspecified; the search
    branches on the vertex with the fewest remaining colours (ties: lowest index).
    """
    domains = [lists] * g.n if isinstance(lists, int) else list(lists)
    if len(domains) != g.n:
        raise ValueError(f"{len(domains)} lists for {g.n} vertices")
    col = [UNCOLORED] * g.n
    for v, c in sorted((fixed or {}).items()):
        if not 0 <= v < g.n:
            raise ValueError(f"fixed vertex {v} outside 0..{g.n - 1}")
        if c < 0 or not domains[v] >> c & 1:
            return  # the precolouring itself is outside the lists: no extension
        if not _assign(g, domains, col, v, c):
            return
    yield from _search(g, domains, col)


def first_extension(
    g: Graph, lists: Sequence[int] | int, fixed: Mapping[int, int] | None = None
) -> Coloring | None:
    return next(extensions(g, lists, fixed), None)


def count_extensions(
    g: Graph, lists: Sequence[int] | int, fixed: Mapping[int, int] | None = None
) -> int:
    return sum(1 for _ in extensions(g, lists, fixed))


def is_colorable(g: Graph, k: int) -> bool:
    return first_extension(g, palette(k)) is not None


def chromatic_number(g: Graph) -> int:
    k = 0
    while not is_colorable(g, k):
        k += 1
    return k


def normalize_colors(col: Sequence[int]) -> Coloring:
    """Rename colours ``0, 1, 2, ...`` in order of first appearance (colour-permutation canon)."""
    names: dict[int, int] = {}
    return tuple(
        UNCOLORED if c == UNCOLORED else names.setdefault(c, len(names)) for c in col
    )


def _check_length(g: Graph, col: Sequence[int]) -> None:
    if len(col) != g.n:
        raise ValueError(f"colouring has {len(col)} entries for {g.n} vertices")


def _assign(g: Graph, domains: list[int], col: list[int], v: int, c: int) -> bool:
    """Colour ``v`` and prune ``c`` from its uncoloured neighbours; False on a wipe-out or clash."""
    if col[v] != UNCOLORED:
        return col[v] == c
    col[v] = c
    domains[v] = 1 << c
    bit = ~(1 << c)
    rest = g.adj[v]
    while rest:
        low = rest & -rest
        rest ^= low
        u = low.bit_length() - 1
        if col[u] == c:
            return False
        if col[u] == UNCOLORED:
            domains[u] &= bit
            if not domains[u]:
                return False
    return True


def _search(g: Graph, domains: list[int], col: list[int]) -> Iterator[Coloring]:
    best, best_size = -1, 1 << 30
    for v in range(g.n):
        if col[v] == UNCOLORED:
            size = domains[v].bit_count()
            if size < best_size:
                best, best_size = v, size
    if best < 0:
        yield tuple(col)
        return
    options = domains[best]
    while options:
        low = options & -options
        options ^= low
        saved_domains, saved_col = domains[:], col[:]
        if _assign(g, domains, col, best, low.bit_length() - 1):
            yield from _search(g, domains, col)
        domains[:], col[:] = saved_domains, saved_col
