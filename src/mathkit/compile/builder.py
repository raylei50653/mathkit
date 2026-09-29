"""Mutable accumulator rules write into; produces an immutable :class:`Scene`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from mathkit.ir import MathDocument
from mathkit.scene import Edge, Layer, Layout, Node, Scene


class CompileError(ValueError):
    """A rule met IR it cannot lower (e.g. a boundary cycle whose edge is missing)."""


@dataclass
class _Draft:
    id: str
    cls: str
    origin: list[str]
    label: str = ""
    u: str = ""
    v: str = ""


@dataclass
class SceneBuilder:
    """Scene elements are keyed by the IR element they draw, so later rules can find them."""

    doc: MathDocument
    _nodes: dict[str, _Draft] = field(default_factory=dict[str, _Draft])
    _edges: dict[str, _Draft] = field(default_factory=dict[str, _Draft])
    _layers: list[Layer] = field(default_factory=list[Layer])
    _outer: tuple[str, ...] | None = None
    _outer_origin: str = ""

    def add_node(
        self, key: str, label: str, origin: Iterable[str] = (), cls: str = "default"
    ) -> str:
        if key in self._nodes:
            raise CompileError(f"{key!r} drawn twice as a node")
        draft = _Draft(f"n{len(self._nodes)}", cls, _dedupe(origin), label=label)
        self._nodes[key] = draft
        return draft.id

    def add_edge(
        self, key: str, u: str, v: str, origin: Iterable[str] = (), cls: str = "default"
    ) -> str:
        """Edge between the nodes drawn for IR elements ``u`` and ``v``."""
        if key in self._edges:
            raise CompileError(f"{key!r} drawn twice as an edge")
        draft = _Draft(f"s{len(self._edges)}", cls, _dedupe(origin), u=self.node(u), v=self.node(v))
        self._edges[key] = draft
        return draft.id

    def node(self, key: str) -> str:
        try:
            return self._nodes[key].id
        except KeyError:
            raise CompileError(f"no node drawn for {key!r}") from None

    def edge(self, key: str) -> str:
        try:
            return self._edges[key].id
        except KeyError:
            raise CompileError(f"no edge drawn for {key!r}") from None

    def mark(self, key: str, cls: str | None = None, origin: Iterable[str] = ()) -> None:
        """Restyle the node or edge drawn for ``key`` and record extra origins."""
        draft = self._nodes.get(key) or self._edges.get(key)
        if draft is None:
            raise CompileError(f"nothing drawn for {key!r}")
        if cls is not None:
            draft.cls = cls
        draft.origin = _dedupe([*draft.origin, *origin])

    def add_layer(self, kind: str, values: Mapping[str, int], origin: Iterable[str]) -> str:
        """``values`` is keyed by IR element; it is translated to scene node ids."""
        layer_id = f"l{len(self._layers)}"
        translated = {self.node(k): c for k, c in values.items()}
        self._layers.append(Layer(layer_id, kind, translated, tuple(_dedupe(origin))))
        return layer_id

    def set_outer(self, keys: Iterable[str], origin: str) -> None:
        if self._outer is not None:
            raise CompileError(f"outer face claimed by both {self._outer_origin!r} and {origin!r}")
        self._outer = tuple(self.node(k) for k in keys)
        self._outer_origin = origin

    def build(self, title: str = "") -> Scene:
        nodes = tuple(
            Node(d.id, d.label, d.cls, None, tuple(d.origin)) for d in self._nodes.values()
        )
        edges = tuple(Edge(d.id, d.u, d.v, d.cls, tuple(d.origin)) for d in self._edges.values())
        return Scene(
            title,
            self.doc.evidence,
            dict(self.doc.provenance),
            nodes,
            edges,
            tuple(self._layers),
            Layout(outer=self._outer or ()),
        )


def _dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))
