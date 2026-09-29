"""Math IR document model, core kinds, and referential integrity (ARCHITECTURE §3)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from mathkit.core.graph import Graph

SCHEMA_ID = "mathkit.ir/1"
EVIDENCE = ("computation", "paper", "lean")

_NAME = re.compile(r"[A-Za-z0-9_.:\-]+")


class IRError(ValueError):
    """Malformed or referentially inconsistent Math IR."""


class IRObject(Protocol):
    """One IR object. Element ids are ``"<object id>/<element>"``."""

    @property
    def id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    def elements(self) -> tuple[str, ...]:
        """Local names of the sub-elements this object defines."""
        ...

    def refs(self) -> tuple[str, ...]:
        """Ids of other objects this object depends on."""
        ...

    def element_refs(self) -> tuple[str, ...]:
        """Full element ids (``obj/elem``) of other objects this object mentions."""
        ...

    def to_json(self) -> dict[str, Any]: ...


KindParser = Callable[[Mapping[str, Any]], IRObject]


def check_name(value: object, what: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise IRError(f"{what}: expected a name matching {_NAME.pattern}, got {value!r}")
    return value


def expect_keys(
    data: Mapping[str, Any], required: set[str], optional: frozenset[str] = frozenset()
) -> None:
    missing = required - data.keys()
    extra = data.keys() - required - optional
    where = f"object {data.get('id')!r}"
    if missing:
        raise IRError(f"{where}: missing {sorted(missing)}")
    if extra:
        raise IRError(f"{where}: unknown fields {sorted(extra)}")


def expect_list(value: object, what: str) -> list[Any]:
    if not isinstance(value, list):
        raise IRError(f"{what}: expected a list")
    return value  # pyright: ignore[reportUnknownVariableType]


def expect_dict(value: object, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IRError(f"{what}: expected an object")
    return value  # pyright: ignore[reportUnknownVariableType]


# --------------------------------------------------------------------------- core kinds


@dataclass(frozen=True, slots=True)
class GraphEdge:
    id: str
    u: str
    v: str


@dataclass(frozen=True, slots=True)
class GraphObject:
    """Simple undirected graph with named vertices and named edges."""

    id: str
    vertices: tuple[str, ...]
    edges: tuple[GraphEdge, ...]
    kind: str = field(default="graph", init=False)

    def __post_init__(self) -> None:
        vs = set(self.vertices)
        if len(vs) != len(self.vertices):
            raise IRError(f"graph {self.id!r}: duplicate vertex")
        seen: set[frozenset[str]] = set()
        for e in self.edges:
            if e.u not in vs or e.v not in vs:
                raise IRError(f"graph {self.id!r}: edge {e.id!r} has an unknown endpoint")
            if e.u == e.v:
                raise IRError(f"graph {self.id!r}: edge {e.id!r} is a self-loop")
            pair = frozenset((e.u, e.v))
            if pair in seen:
                raise IRError(f"graph {self.id!r}: edge {e.id!r} is parallel to another edge")
            seen.add(pair)
        names = self.elements()
        if len(set(names)) != len(names):
            raise IRError(f"graph {self.id!r}: vertex and edge ids must be distinct")

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> GraphObject:
        expect_keys(data, {"id", "kind", "vertices", "edges"})
        oid = check_name(data["id"], "graph id")
        vertices = tuple(
            check_name(v, f"graph {oid!r} vertex")
            for v in expect_list(data["vertices"], f"graph {oid!r} vertices")
        )
        edges: list[GraphEdge] = []
        for raw in expect_list(data["edges"], f"graph {oid!r} edges"):
            e = expect_dict(raw, f"graph {oid!r} edge")
            expect_keys(e, {"id", "u", "v"})
            edges.append(
                GraphEdge(
                    check_name(e["id"], f"graph {oid!r} edge id"),
                    check_name(e["u"], f"graph {oid!r} edge endpoint"),
                    check_name(e["v"], f"graph {oid!r} edge endpoint"),
                )
            )
        return cls(oid, vertices, tuple(edges))

    def elements(self) -> tuple[str, ...]:
        return self.vertices + tuple(e.id for e in self.edges)

    def refs(self) -> tuple[str, ...]:
        return ()

    def element_refs(self) -> tuple[str, ...]:
        return ()

    def edge_between(self, u: str, v: str) -> GraphEdge | None:
        for e in self.edges:
            if {e.u, e.v} == {u, v}:
                return e
        return None

    def to_core(self) -> Graph:
        """The underlying :class:`Graph`; vertex ``i`` is ``self.vertices[i]``."""
        index = {v: i for i, v in enumerate(self.vertices)}
        return Graph.from_edges(len(self.vertices), ((index[e.u], index[e.v]) for e in self.edges))

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "vertices": list(self.vertices),
            "edges": [{"id": e.id, "u": e.u, "v": e.v} for e in self.edges],
        }


@dataclass(frozen=True, slots=True)
class ColoringObject:
    """Assignment of integer colours to (some of) a graph's vertices. Not necessarily proper."""

    id: str
    graph: str
    values: Mapping[str, int]
    kind: str = field(default="coloring", init=False)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> ColoringObject:
        expect_keys(data, {"id", "kind", "graph", "values"})
        oid = check_name(data["id"], "coloring id")
        values: dict[str, int] = {}
        for v, c in expect_dict(data["values"], f"coloring {oid!r} values").items():
            if not isinstance(c, int) or isinstance(c, bool):
                raise IRError(f"coloring {oid!r}: colour of {v!r} must be an integer")
            values[check_name(v, f"coloring {oid!r} vertex")] = c
        return cls(oid, check_name(data["graph"], f"coloring {oid!r} graph"), values)

    def elements(self) -> tuple[str, ...]:
        return ()

    def refs(self) -> tuple[str, ...]:
        return (self.graph,)

    def element_refs(self) -> tuple[str, ...]:
        return tuple(f"{self.graph}/{v}" for v in sorted(self.values))

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "graph": self.graph,
            "values": {v: self.values[v] for v in sorted(self.values)},
        }


@dataclass(frozen=True, slots=True)
class RawObject:
    """An object of a kind no loaded pack understands; kept verbatim, never referenced into."""

    id: str
    kind: str
    data: Mapping[str, Any]

    def elements(self) -> tuple[str, ...]:
        return ()

    def refs(self) -> tuple[str, ...]:
        return ()

    def element_refs(self) -> tuple[str, ...]:
        return ()

    def to_json(self) -> dict[str, Any]:
        return dict(self.data)


CORE_KINDS: Mapping[str, KindParser] = {
    "graph": GraphObject.from_json,
    "coloring": ColoringObject.from_json,
}


# --------------------------------------------------------------------------- document


@dataclass(frozen=True, slots=True)
class MathDocument:
    evidence: str
    provenance: Mapping[str, str]
    objects: tuple[IRObject, ...]

    def get(self, oid: str) -> IRObject:
        for obj in self.objects:
            if obj.id == oid:
                return obj
        raise KeyError(oid)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "evidence": self.evidence,
            "provenance": {k: self.provenance[k] for k in sorted(self.provenance)},
            "objects": [obj.to_json() for obj in self.objects],
        }


def load_document(data: object, kinds: Mapping[str, KindParser] = CORE_KINDS) -> MathDocument:
    """Parse and validate a ``mathkit.ir/1`` JSON value. Unknown kinds become :class:`RawObject`."""
    doc = expect_dict(data, "document")
    if doc.get("schema") != SCHEMA_ID:
        raise IRError(f"expected schema {SCHEMA_ID!r}, got {doc.get('schema')!r}")
    expect_keys(doc, {"schema", "evidence", "objects"}, frozenset({"provenance"}))
    if doc["evidence"] not in EVIDENCE:
        raise IRError(f"evidence must be one of {EVIDENCE}")
    provenance = expect_dict(doc.get("provenance", {}), "provenance")
    if not all(isinstance(v, str) for v in provenance.values()):
        raise IRError("provenance values must be strings")
    objects: list[IRObject] = []
    for raw in expect_list(doc["objects"], "objects"):
        obj = expect_dict(raw, "object")
        kind = obj.get("kind")
        if not isinstance(kind, str):
            raise IRError(f"object {obj.get('id')!r}: missing kind")
        parser = kinds.get(kind)
        if parser is None:
            objects.append(RawObject(check_name(obj.get("id"), "object id"), kind, obj))
        else:
            objects.append(parser(obj))
    result = MathDocument(doc["evidence"], dict(provenance), tuple(objects))
    validate_document(result)
    return result


def validate_document(doc: MathDocument) -> None:
    """Integrity rules 1-3: unique ids, unique elements, all references resolve, no cycles."""
    by_id: dict[str, IRObject] = {}
    for obj in doc.objects:
        check_name(obj.id, "object id")
        if obj.id in by_id:
            raise IRError(f"duplicate object id {obj.id!r}")
        names = obj.elements()
        if len(set(names)) != len(names):
            raise IRError(f"object {obj.id!r}: duplicate element id")
        by_id[obj.id] = obj
    for obj in doc.objects:
        for ref in obj.refs():
            if ref not in by_id:
                raise IRError(f"object {obj.id!r}: reference to unknown object {ref!r}")
        for ref in obj.element_refs():
            if not resolves(doc, ref, by_id):
                raise IRError(f"object {obj.id!r}: reference to unknown element {ref!r}")
    dependency_order(doc)


def resolves(doc: MathDocument, ref: str, by_id: Mapping[str, IRObject] | None = None) -> bool:
    """Whether ``ref`` names an object (``G``) or an element (``G/e0``) of ``doc``."""
    table = by_id if by_id is not None else {o.id: o for o in doc.objects}
    oid, sep, elem = ref.partition("/")
    obj = table.get(oid)
    if obj is None:
        return False
    return not sep or elem in obj.elements()


def dependency_order(doc: MathDocument) -> tuple[IRObject, ...]:
    """Objects ordered so every object follows those it refers to; ties keep document order."""
    position = {obj.id: i for i, obj in enumerate(doc.objects)}
    state: dict[str, int] = {}  # 1 = visiting, 2 = done
    out: list[IRObject] = []

    def visit(obj: IRObject) -> None:
        mark = state.get(obj.id)
        if mark == 2:
            return
        if mark == 1:
            raise IRError(f"reference cycle through {obj.id!r}")
        state[obj.id] = 1
        for ref in sorted(set(obj.refs()), key=position.__getitem__):
            visit(doc.objects[position[ref]])
        state[obj.id] = 2
        out.append(obj)

    for obj in doc.objects:
        visit(obj)
    return tuple(out)
