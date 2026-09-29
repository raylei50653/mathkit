"""Domain-free compile rules for the core kinds."""

from mathkit.compile.builder import CompileError, SceneBuilder
from mathkit.compile.registry import DEFAULT_VIEW, Registry, RuleSpec
from mathkit.ir import ColoringObject, GraphObject, IRObject

SOURCE = "mathkit.compile"


def graph_rule(obj: IRObject, b: SceneBuilder) -> None:
    if not isinstance(obj, GraphObject):
        raise CompileError(f"{obj.id!r}: graph rule got kind {obj.kind!r}")
    for v in obj.vertices:
        key = f"{obj.id}/{v}"
        b.add_node(key, v, origin=(key,))
    for e in obj.edges:
        key = f"{obj.id}/{e.id}"
        b.add_edge(key, f"{obj.id}/{e.u}", f"{obj.id}/{e.v}", origin=(key,))


def coloring_rule(obj: IRObject, b: SceneBuilder) -> None:
    if not isinstance(obj, ColoringObject):
        raise CompileError(f"{obj.id!r}: coloring rule got kind {obj.kind!r}")
    values = {f"{obj.graph}/{v}": c for v, c in sorted(obj.values.items())}
    b.add_layer("vertex-color", values, origin=(obj.id,))


CORE_RULES = (
    RuleSpec("graph", DEFAULT_VIEW, graph_rule),
    RuleSpec("coloring", DEFAULT_VIEW, coloring_rule),
)


def register_core_rules(registry: Registry) -> None:
    for spec in CORE_RULES:
        registry.register(spec, SOURCE)
