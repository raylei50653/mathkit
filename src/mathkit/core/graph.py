"""Immutable small graphs: vertices ``0..n-1``, adjacency as one int bitmask per vertex."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class Graph:
    """Simple undirected graph. ``adj[v]`` has bit ``u`` set iff ``uv`` is an edge."""

    adj: tuple[int, ...]

    def __post_init__(self) -> None:
        n = len(self.adj)
        full = (1 << n) - 1
        for v, row in enumerate(self.adj):
            if row & ~full:
                raise ValueError(f"vertex {v}: neighbour outside 0..{n - 1}")
            if row >> v & 1:
                raise ValueError(f"vertex {v}: self-loop")
            for u in _bits(row):
                if not self.adj[u] >> v & 1:
                    raise ValueError(f"asymmetric adjacency between {v} and {u}")

    @classmethod
    def from_edges(cls, n: int, edges: Iterable[tuple[int, int]]) -> Graph:
        if n < 0:
            raise ValueError("n must be non-negative")
        adj = [0] * n
        for u, v in edges:
            if not (0 <= u < n and 0 <= v < n):
                raise ValueError(f"edge ({u}, {v}) outside 0..{n - 1}")
            if u == v:
                raise ValueError(f"self-loop at {u}")
            if adj[u] >> v & 1:
                raise ValueError(f"duplicate edge ({u}, {v})")
            adj[u] |= 1 << v
            adj[v] |= 1 << u
        return cls(tuple(adj))

    @property
    def n(self) -> int:
        return len(self.adj)

    def edges(self) -> Iterator[tuple[int, int]]:
        """Edges ``(u, v)`` with ``u < v``, in lexicographic order."""
        for u, row in enumerate(self.adj):
            for v in _bits(row >> (u + 1) << (u + 1)):
                yield u, v

    def edge_count(self) -> int:
        return sum(row.bit_count() for row in self.adj) // 2

    def has_edge(self, u: int, v: int) -> bool:
        return bool(self.adj[u] >> v & 1)

    def neighbors(self, v: int) -> tuple[int, ...]:
        return tuple(_bits(self.adj[v]))

    def degree(self, v: int) -> int:
        return self.adj[v].bit_count()

    def induced(self, mask: int) -> Graph:
        """Subgraph induced by the vertices in ``mask``, relabelled ``0..k-1`` in order."""
        keep = list(_bits(mask & ((1 << self.n) - 1)))
        index = {v: i for i, v in enumerate(keep)}
        adj = tuple(
            sum(1 << index[u] for u in _bits(self.adj[v] & mask)) for v in keep
        )
        return Graph(adj)

    def to_networkx(self) -> Any:
        import networkx as nx  # optional extra [nx]

        g = cast(Any, nx.Graph())
        g.add_nodes_from(range(self.n))
        g.add_edges_from(self.edges())
        return g

    @classmethod
    def from_networkx(cls, g: Any) -> Graph:
        """Convert a networkx graph whose nodes are exactly ``0..n-1``."""
        n = g.number_of_nodes()
        if set(g.nodes) != set(range(n)):
            raise ValueError("networkx graph nodes must be exactly 0..n-1")
        return cls.from_edges(n, ((int(u), int(v)) for u, v in g.edges))


def _bits(mask: int) -> Iterator[int]:
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low
