"""Scene IR: purely visual vocabulary. Elements link back to Math IR ids via ``origin``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

SCHEMA_ID = "mathkit.scene/1"

#: Closed visual vocabulary shared by nodes and edges; renderers map each to a style.
CLASSES = ("default", "outer", "emphasis", "muted", "dashed", "decoration")
#: Classes allowed to carry an empty ``origin`` (integrity rule 7).
DECORATIVE_CLASSES = frozenset({"decoration"})
#: Closed layer vocabulary; adding a kind bumps the scene schema minor version.
LAYER_KINDS = ("vertex-color",)

Pos = tuple[int, int]


class SceneError(ValueError):
    """Malformed Scene or a violation of integrity rules 7-8."""


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    label: str
    cls: str = "default"
    pos: Pos | None = None
    origin: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "class": self.cls,
            "pos": None if self.pos is None else list(self.pos),
            "origin": list(self.origin),
        }


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    u: str
    v: str
    cls: str = "default"
    origin: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "u": self.u,
            "v": self.v,
            "class": self.cls,
            "origin": list(self.origin),
        }


@dataclass(frozen=True, slots=True)
class Layer:
    """``vertex-color``: ``values`` maps node id to a colour index."""

    id: str
    kind: str
    values: Mapping[str, int]
    origin: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "values": {k: self.values[k] for k in sorted(self.values)},
            "origin": list(self.origin),
        }


@dataclass(frozen=True, slots=True)
class Layout:
    """Hints from the compiler (``engine``, ``outer``); ``version``/``exact`` set by layout."""

    engine: str | None = None
    outer: tuple[str, ...] = ()
    version: int | None = None
    exact: bool | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "outer": list(self.outer),
            "version": self.version,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class Scene:
    title: str
    evidence: str
    provenance: Mapping[str, str]
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    layers: tuple[Layer, ...] = ()
    layout: Layout = Layout()

    def with_positions(self, pos: Mapping[str, Pos], layout: Layout) -> Scene:
        nodes = tuple(replace(n, pos=pos[n.id]) for n in self.nodes)
        return replace(self, nodes=nodes, layout=layout)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_ID,
            "title": self.title,
            "evidence": self.evidence,
            "provenance": {k: self.provenance[k] for k in sorted(self.provenance)},
            "nodes": [n.to_json() for n in self.nodes],
            "edges": [e.to_json() for e in self.edges],
            "layers": [layer.to_json() for layer in self.layers],
            "layout": self.layout.to_json(),
        }


def validate_scene(scene: Scene) -> None:
    """Scene-internal rules: closed vocabularies, unique ids, edges and layers hit real nodes."""
    ids: set[str] = set()
    for elem in (*scene.nodes, *scene.edges, *scene.layers):
        if elem.id in ids:
            raise SceneError(f"duplicate scene id {elem.id!r}")
        ids.add(elem.id)
    node_ids = {n.id for n in scene.nodes}
    for elem in (*scene.nodes, *scene.edges):
        if elem.cls not in CLASSES:
            raise SceneError(f"{elem.id!r}: unknown class {elem.cls!r}")
        if not elem.origin and elem.cls not in DECORATIVE_CLASSES:
            raise SceneError(f"{elem.id!r}: empty origin on a non-decorative element")
    for e in scene.edges:
        if e.u not in node_ids or e.v not in node_ids:
            raise SceneError(f"edge {e.id!r}: endpoint is not a node")
    for layer in scene.layers:
        if layer.kind not in LAYER_KINDS:
            raise SceneError(f"layer {layer.id!r}: unknown kind {layer.kind!r}")
        if not layer.origin:
            raise SceneError(f"layer {layer.id!r}: empty origin")
        for k in layer.values:
            if k not in node_ids:
                raise SceneError(f"layer {layer.id!r}: {k!r} is not a node")
    for k in scene.layout.outer:
        if k not in node_ids:
            raise SceneError(f"layout.outer: {k!r} is not a node")


def load_scene(data: object) -> Scene:
    """Parse and validate a ``mathkit.scene/1`` JSON value."""
    try:
        return _load_scene(data)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        if isinstance(exc, SceneError):
            raise
        raise SceneError(f"malformed scene: {exc!r}") from exc


def _load_scene(data: Any) -> Scene:
    if data.get("schema") != SCHEMA_ID:
        raise SceneError(f"expected schema {SCHEMA_ID!r}, got {data.get('schema')!r}")

    def pos(p: Any) -> Pos | None:
        if p is None:
            return None
        x, y = p
        if not all(isinstance(c, int) and not isinstance(c, bool) for c in (x, y)):
            raise SceneError("pos must be a pair of integers")
        return (x, y)

    nodes = tuple(
        Node(n["id"], n["label"], n["class"], pos(n["pos"]), tuple(n["origin"]))
        for n in data["nodes"]
    )
    edges = tuple(
        Edge(e["id"], e["u"], e["v"], e["class"], tuple(e["origin"])) for e in data["edges"]
    )
    layers = tuple(
        Layer(ly["id"], ly["kind"], dict(ly["values"]), tuple(ly["origin"]))
        for ly in data.get("layers", [])
    )
    raw_layout = data.get("layout", {})
    layout = Layout(
        raw_layout.get("engine"),
        tuple(raw_layout.get("outer", [])),
        raw_layout.get("version"),
        raw_layout.get("exact"),
    )
    scene = Scene(
        data.get("title", ""),
        data["evidence"],
        dict(data.get("provenance", {})),
        nodes,
        edges,
        layers,
        layout,
    )
    validate_scene(scene)
    return scene
