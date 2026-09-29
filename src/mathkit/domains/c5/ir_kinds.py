"""``c5.*`` Math IR kinds. M1a: only the boundary cycle."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from mathkit.ir.model import IRError, check_name, expect_keys, expect_list

BOUNDARY_LENGTH = 5


@dataclass(frozen=True, slots=True)
class BoundaryCycle:
    """The outer 5-cycle ``b0 b1 b2 b3 b4`` of a graph, in cyclic order."""

    id: str
    graph: str
    cycle: tuple[str, ...]
    kind: str = field(default="c5.boundary_cycle", init=False)

    def __post_init__(self) -> None:
        if len(self.cycle) != BOUNDARY_LENGTH or len(set(self.cycle)) != BOUNDARY_LENGTH:
            raise IRError(f"{self.id!r}: boundary cycle needs {BOUNDARY_LENGTH} distinct vertices")

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> BoundaryCycle:
        expect_keys(data, {"id", "kind", "graph", "cycle"})
        oid = check_name(data["id"], "boundary cycle id")
        cycle = tuple(
            check_name(v, f"{oid!r} cycle vertex")
            for v in expect_list(data["cycle"], f"{oid!r} cycle")
        )
        return cls(oid, check_name(data["graph"], f"{oid!r} graph"), cycle)

    def elements(self) -> tuple[str, ...]:
        return ()

    def refs(self) -> tuple[str, ...]:
        return (self.graph,)

    def element_refs(self) -> tuple[str, ...]:
        return tuple(f"{self.graph}/{v}" for v in self.cycle)

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "graph": self.graph, "cycle": list(self.cycle)}
