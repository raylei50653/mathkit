"""Compile rules for ``c5.*`` kinds."""

from mathkit.compile import DEFAULT_VIEW, CompileError, RuleSpec, SceneBuilder
from mathkit.domains.c5.ir_kinds import BoundaryCycle
from mathkit.ir import GraphObject, IRObject


def boundary_cycle_rule(obj: IRObject, b: SceneBuilder) -> None:
    """Style the cycle as ``outer`` and pin it as the outer face of a Tutte layout."""
    if not isinstance(obj, BoundaryCycle):
        raise CompileError(f"{obj.id!r}: boundary rule got kind {obj.kind!r}")
    graph = b.doc.get(obj.graph)
    if not isinstance(graph, GraphObject):
        raise CompileError(f"{obj.id!r}: {obj.graph!r} is not a graph")
    keys = [f"{graph.id}/{v}" for v in obj.cycle]
    for key in keys:
        b.mark(key, "outer", (obj.id,))
    for u, v in zip(obj.cycle, obj.cycle[1:] + obj.cycle[:1], strict=True):
        edge = graph.edge_between(u, v)
        if edge is None:
            raise CompileError(f"{obj.id!r}: no edge {u}-{v} in graph {graph.id!r}")
        b.mark(f"{graph.id}/{edge.id}", "outer", (obj.id,))
    b.set_outer(keys, obj.id, engine="tutte")


RULES = (RuleSpec("c5.boundary_cycle", DEFAULT_VIEW, boundary_cycle_rule),)
