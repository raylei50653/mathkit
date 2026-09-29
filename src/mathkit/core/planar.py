"""Combinatorial planar embeddings: rotation systems, faces, and the LR planarity test.

A rotation system lists each vertex's neighbours in counter-clockwise order. Faces are traced
with the face on the left: after the dart ``u -> v`` comes ``v -> w``, where ``w`` is the
neighbour following ``u`` clockwise around ``v``. Bounded faces therefore come out
counter-clockwise.

:func:`embed` defaults to the self-contained LR (left-right) algorithm of Brandes,
"The Left-Right Planarity Test" (2009), whose structure follows the networkx implementation;
``backend="networkx"`` delegates to ``networkx.check_planarity`` for cross-checking.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, cast

from mathkit.core.graph import Graph

Dart = tuple[int, int]


class NotPlanarError(ValueError):
    """A rotation system that is not a planar embedding (Euler's formula fails)."""


@dataclass(frozen=True, slots=True)
class Embedding:
    """A planar embedding of ``graph``; ``rotation[v]`` is ``v``'s neighbours counter-clockwise.

    Each rotation starts at its smallest neighbour, so equal embeddings compare equal.
    """

    graph: Graph
    rotation: tuple[tuple[int, ...], ...]

    @classmethod
    def from_rotation(cls, g: Graph, rotation: Sequence[Sequence[int]]) -> Embedding:
        """Validate ``rotation`` against ``g`` and check Euler's formula per component."""
        if len(rotation) != g.n:
            raise ValueError(f"rotation has {len(rotation)} entries for {g.n} vertices")
        rot: list[tuple[int, ...]] = []
        for v, order in enumerate(rotation):
            order = tuple(order)
            if len(set(order)) != len(order) or set(order) != set(g.neighbors(v)):
                raise ValueError(f"rotation at {v} is not a permutation of its neighbours")
            rot.append(_start_at_min(order))
        emb = cls(g, tuple(rot))
        emb._check_euler()
        return emb

    def mirror(self) -> Embedding:
        flipped = (_start_at_min(tuple(reversed(r))) for r in self.rotation)
        return Embedding(self.graph, tuple(flipped))

    def faces(self) -> tuple[tuple[int, ...], ...]:
        """Boundary walks as vertex sequences (tails of darts), canonical and sorted.

        A vertex repeats on a face whose boundary is not a simple cycle.
        """
        return tuple(sorted(_canonical_walk(f) for f in self._dart_faces()))

    def _dart_faces(self) -> list[list[Dart]]:
        index = [{u: i for i, u in enumerate(r)} for r in self.rotation]
        seen: set[Dart] = set()
        faces: list[list[Dart]] = []
        for u, v in _darts(self.graph):
            if (u, v) in seen:
                continue
            face: list[Dart] = []
            dart = (u, v)
            while dart not in seen:
                seen.add(dart)
                face.append(dart)
                a, b = dart
                around = self.rotation[b]
                dart = (b, around[(index[b][a] - 1) % len(around)])
            if dart != (u, v):
                raise NotPlanarError("rotation does not define a permutation of darts")
            faces.append(face)
        return faces

    def _check_euler(self) -> None:
        g = self.graph
        f = len(self._dart_faces())
        edged = [c for c in components(g) if len(c) > 1]
        vertices_in_edged = sum(len(c) for c in edged)
        # For each component with an edge: V - E + F = 2.
        if vertices_in_edged - g.edge_count() + f != 2 * len(edged):
            raise NotPlanarError("rotation system has positive genus (Euler's formula fails)")


def components(g: Graph) -> list[list[int]]:
    """Connected components, each sorted, ordered by smallest vertex."""
    seen = 0
    out: list[list[int]] = []
    for s in range(g.n):
        if seen >> s & 1:
            continue
        comp, frontier = 1 << s, 1 << s
        while frontier:
            low = frontier & -frontier
            frontier ^= low
            new = g.adj[low.bit_length() - 1] & ~comp
            comp |= new
            frontier |= new
        seen |= comp
        out.append([v for v in range(g.n) if comp >> v & 1])
    return out


def is_planar(g: Graph) -> bool:
    return embed(g) is not None


def embed(g: Graph, backend: str = "lr") -> Embedding | None:
    """A planar embedding of ``g``, or ``None`` if ``g`` is not planar."""
    if backend == "lr":
        rotation = _LR(g).run()
    elif backend == "networkx":
        rotation = _networkx_rotation(g)
    else:
        raise ValueError(f"unknown planarity backend {backend!r}")
    return None if rotation is None else Embedding.from_rotation(g, rotation)


def _darts(g: Graph) -> Iterator[Dart]:
    for u, v in g.edges():
        yield u, v
        yield v, u


def _start_at_min(order: tuple[int, ...]) -> tuple[int, ...]:
    if not order:
        return order
    i = order.index(min(order))
    return order[i:] + order[:i]


def _canonical_walk(face: list[Dart]) -> tuple[int, ...]:
    walk = [u for u, _ in face]
    return min(tuple(walk[i:] + walk[:i]) for i in range(len(walk)))


def _networkx_rotation(g: Graph) -> list[list[int]] | None:
    nx: Any = importlib.import_module("networkx")  # optional extra [nx]

    planar, emb = cast(tuple[bool, Any], nx.check_planarity(g.to_networkx()))
    if not planar:
        return None
    return [
        list(reversed(list(emb.neighbors_cw_order(v)))) if g.degree(v) else [] for v in range(g.n)
    ]


# --------------------------------------------------------------------------- LR algorithm


class _NonPlanar(Exception):
    pass


class _Interval:
    __slots__ = ("high", "low")

    def __init__(self, low: Dart | None = None, high: Dart | None = None) -> None:
        self.low = low
        self.high = high

    def empty(self) -> bool:
        return self.low is None and self.high is None

    def copy(self) -> _Interval:
        return _Interval(self.low, self.high)


class _Pair:
    """Conflict pair; compared by identity (``stack_bottom`` remembers exact stack entries)."""

    __slots__ = ("left", "right")

    def __init__(self, left: _Interval | None = None, right: _Interval | None = None) -> None:
        self.left = left or _Interval()
        self.right = right or _Interval()

    def swap(self) -> None:
        self.left, self.right = self.right, self.left


def _drive(start: Iterator[int], step: Callable[[int], Iterator[int]]) -> None:
    """Run a recursive DFS written as generators (each ``yield w`` recurses into ``w``)."""
    stack = [start]
    while stack:
        child = next(stack[-1], None)
        if child is None:
            stack.pop()
        else:
            stack.append(step(child))


class _Rotation:
    """Doubly linked cyclic neighbour lists plus a 'leftmost' marker, as the LR embedding needs."""

    def __init__(self, n: int) -> None:
        self.cw: list[dict[int, int]] = [{} for _ in range(n)]
        self.ccw: list[dict[int, int]] = [{} for _ in range(n)]
        self.leftmost: list[int | None] = [None] * n

    def _sole(self, s: int, e: int) -> None:
        self.cw[s][e] = self.ccw[s][e] = e
        self.leftmost[s] = e

    def add_cw_of(self, s: int, e: int, ref: int | None) -> None:
        """Insert ``e`` right after ``ref`` going clockwise (networkx ``ccw=ref``)."""
        if ref is None:
            self._sole(s, e)
            return
        nxt = self.cw[s][ref]
        self.cw[s][ref], self.ccw[s][e], self.cw[s][e], self.ccw[s][nxt] = e, ref, nxt, e

    def add_ccw_of(self, s: int, e: int, ref: int) -> None:
        """Insert ``e`` right after ``ref`` going counter-clockwise (networkx ``cw=ref``)."""
        prv = self.ccw[s][ref]
        self.ccw[s][ref], self.cw[s][e], self.ccw[s][e], self.cw[s][prv] = e, ref, prv, e
        if ref == self.leftmost[s]:
            self.leftmost[s] = e

    def add_first(self, s: int, e: int) -> None:
        ref = self.leftmost[s]
        if ref is None:
            self._sole(s, e)
        else:
            self.add_ccw_of(s, e, ref)

    def ccw_order(self, s: int) -> list[int]:
        if not self.ccw[s]:
            return []
        start = min(self.ccw[s])
        out, v = [start], self.ccw[s][start]
        while v != start:
            out.append(v)
            v = self.ccw[s][v]
        return out


class _LR:
    def __init__(self, g: Graph) -> None:
        n = g.n
        self.g = g
        self.height: list[int | None] = [None] * n
        self.parent_edge: list[Dart | None] = [None] * n
        self.lowpt: dict[Dart, int] = {}
        self.lowpt2: dict[Dart, int] = {}
        self.nesting: dict[Dart, int] = {}
        self.out: list[list[int]] = [[] for _ in range(n)]
        self.oriented: set[Dart] = set()
        self.ref: dict[Dart, Dart | None] = {}
        self.side: dict[Dart, int] = {}
        self.stack: list[_Pair] = []
        self.stack_bottom: dict[Dart, _Pair | None] = {}
        self.lowpt_edge: dict[Dart, Dart] = {}
        self.left_ref: list[int] = [0] * n
        self.right_ref: list[int] = [0] * n
        self.rot = _Rotation(n)
        self.roots: list[int] = []

    def run(self) -> list[list[int]] | None:
        g = self.g
        if g.n > 2 and g.edge_count() > 3 * g.n - 6:
            return None
        for v in range(g.n):
            if self.height[v] is None:
                self.height[v] = 0
                self.roots.append(v)
                _drive(self._orient(v), self._orient)
        for v in range(g.n):
            self.out[v].sort(key=lambda w, v=v: self.nesting[(v, w)])
        try:
            for v in self.roots:
                _drive(self._test(v), self._test)
        except _NonPlanar:
            return None
        for v in range(g.n):
            for w in self.out[v]:
                self.nesting[(v, w)] *= self._sign((v, w))
        for v in range(g.n):
            self.out[v].sort(key=lambda w, v=v: self.nesting[(v, w)])
            prev: int | None = None
            for w in self.out[v]:
                self.rot.add_cw_of(v, w, prev)
                prev = w
        for v in self.roots:
            _drive(self._embed(v), self._embed)
        return [self.rot.ccw_order(v) for v in range(g.n)]

    def _h(self, v: int) -> int:
        h = self.height[v]
        assert h is not None
        return h

    # Phase 1: DFS orientation, lowpoints, nesting depth.
    def _orient(self, v: int) -> Iterator[int]:
        e = self.parent_edge[v]
        hv = self._h(v)
        for w in self.g.neighbors(v):
            if (v, w) in self.oriented or (w, v) in self.oriented:
                continue
            vw = (v, w)
            self.oriented.add(vw)
            self.out[v].append(w)
            self.lowpt[vw] = self.lowpt2[vw] = hv
            hw = self.height[w]
            if hw is None:  # tree edge
                self.parent_edge[w] = vw
                self.height[w] = hv + 1
                yield w
            else:  # back edge
                self.lowpt[vw] = hw
            self.nesting[vw] = 2 * self.lowpt[vw] + (1 if self.lowpt2[vw] < hv else 0)
            if e is not None:
                lo, lo_e = self.lowpt[vw], self.lowpt[e]
                if lo < lo_e:
                    self.lowpt2[e] = min(lo_e, self.lowpt2[vw])
                    self.lowpt[e] = lo
                elif lo > lo_e:
                    self.lowpt2[e] = min(self.lowpt2[e], lo)
                else:
                    self.lowpt2[e] = min(self.lowpt2[e], self.lowpt2[vw])

    # Phase 2: LR partition test.
    def _test(self, v: int) -> Iterator[int]:
        e = self.parent_edge[v]
        hv = self._h(v)
        first = self.out[v][0] if self.out[v] else None
        for w in self.out[v]:
            ei = (v, w)
            self.stack_bottom[ei] = self.stack[-1] if self.stack else None
            if ei == self.parent_edge[w]:
                yield w
            else:
                self.lowpt_edge[ei] = ei
                self.stack.append(_Pair(right=_Interval(ei, ei)))
            if self.lowpt[ei] < hv:
                assert e is not None  # a root has height 0, so nothing returns below it
                if w == first:
                    self.lowpt_edge[e] = self.lowpt_edge[ei]
                else:
                    self._add_constraints(ei, e)
        if e is not None:
            self._remove_back_edges(e)

    def _conflicting(self, iv: _Interval, b: Dart) -> bool:
        return not iv.empty() and self.lowpt[_some(iv.high)] > self.lowpt[b]

    def _lowest(self, p: _Pair) -> int:
        if p.left.empty():
            return self.lowpt[_some(p.right.low)]
        if p.right.empty():
            return self.lowpt[_some(p.left.low)]
        return min(self.lowpt[_some(p.left.low)], self.lowpt[_some(p.right.low)])

    def _add_constraints(self, ei: Dart, e: Dart) -> None:
        s, p = self.stack, _Pair()
        while True:  # merge return edges of ei into p.right
            q = s.pop()
            if not q.left.empty():
                q.swap()
            if not q.left.empty():
                raise _NonPlanar
            if self.lowpt[_some(q.right.low)] > self.lowpt[e]:
                if p.right.empty():
                    p.right = q.right.copy()
                else:
                    self.ref[_some(p.right.low)] = q.right.high
                p.right.low = q.right.low
            else:
                self.ref[_some(q.right.low)] = self.lowpt_edge[e]
            if (s[-1] if s else None) is self.stack_bottom[ei]:
                break
        # merge conflicting return edges of earlier siblings into p.left
        while s and (self._conflicting(s[-1].left, ei) or self._conflicting(s[-1].right, ei)):
            q = s.pop()
            if self._conflicting(q.right, ei):
                q.swap()
            if self._conflicting(q.right, ei):
                raise _NonPlanar
            self.ref[_some(p.right.low)] = q.right.high
            if q.right.low is not None:
                p.right.low = q.right.low
            if p.left.empty():
                p.left = q.left.copy()
            else:
                self.ref[_some(p.left.low)] = q.left.high
            p.left.low = q.left.low
        if not (p.left.empty() and p.right.empty()):
            s.append(p)

    def _remove_back_edges(self, e: Dart) -> None:
        s, u = self.stack, e[0]
        hu = self._h(u)
        while s and self._lowest(s[-1]) == hu:  # drop pairs returning only to u
            p = s.pop()
            if p.left.low is not None:
                self.side[p.left.low] = -1
        if s:  # trim one more pair
            p = s.pop()
            while p.left.high is not None and p.left.high[1] == u:
                p.left.high = self.ref.get(p.left.high)
            if p.left.high is None and p.left.low is not None:
                self.ref[p.left.low] = p.right.low
                self.side[p.left.low] = -1
                p.left.low = None
            while p.right.high is not None and p.right.high[1] == u:
                p.right.high = self.ref.get(p.right.high)
            if p.right.high is None and p.right.low is not None:
                self.ref[p.right.low] = p.left.low
                self.side[p.right.low] = -1
                p.right.low = None
            s.append(p)
        if self.lowpt[e] < hu:  # side of e follows its highest return edge
            hl, hr = s[-1].left.high, s[-1].right.high
            if hl is not None and (hr is None or self.lowpt[hl] > self.lowpt[hr]):
                self.ref[e] = hl
            else:
                self.ref[e] = hr

    def _sign(self, e: Dart) -> int:
        """Resolve relative sides along the ``ref`` chain into absolute ones."""
        chain = [e]
        while (nxt := self.ref.get(chain[-1])) is not None:
            chain.append(nxt)
        for a, b in zip(reversed(chain[:-1]), reversed(chain[1:]), strict=True):
            self.side[a] = self.side.get(a, 1) * self.side.get(b, 1)
            self.ref[a] = None
        return self.side.get(e, 1)

    # Phase 3: build the rotation system.
    def _embed(self, v: int) -> Iterator[int]:
        for w in self.out[v]:
            ei = (v, w)
            if ei == self.parent_edge[w]:
                self.rot.add_first(w, v)
                self.left_ref[v] = self.right_ref[v] = w
                yield w
            elif self.side.get(ei, 1) == 1:
                self.rot.add_cw_of(w, v, self.right_ref[w])
            else:
                self.rot.add_ccw_of(w, v, self.left_ref[w])
                self.left_ref[w] = v


def _some(d: Dart | None) -> Dart:
    assert d is not None
    return d
