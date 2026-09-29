import copy
import warnings
from dataclasses import replace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mathkit.compile import (
    CompileError,
    CompileWarning,
    OriginError,
    Registry,
    RuleConflictError,
    RuleSpec,
    SceneBuilder,
    compile_visual,
    register_core_rules,
    validate_origins,
)
from mathkit.domains import DomainPack, Domains, discover, load_domains
from mathkit.domains.c5 import plugin as c5_plugin
from mathkit.ir import ColoringObject, GraphEdge, GraphObject, IRObject, MathDocument, load_document
from mathkit.scene import Node, SceneError


def _noop(obj: IRObject, b: SceneBuilder) -> None:
    pass


def test_c5_scene(c5_doc: MathDocument, domains: Domains) -> None:
    scene = compile_visual(c5_doc, domains.registry)
    by_label = {n.label: n for n in scene.nodes}
    assert by_label["b_0"].cls == "outer" and by_label["b_0"].origin == ("G/b_0", "B")
    assert by_label["v"].cls == "default" and by_label["v"].origin == ("G/v",)
    outer_edges = [e for e in scene.edges if e.cls == "outer"]
    assert len(outer_edges) == 5 and all(e.origin[1] == "B" for e in outer_edges)
    assert scene.layout.outer == tuple(by_label[f"b_{i}"].id for i in range(5))
    (layer,) = scene.layers
    assert layer.kind == "vertex-color" and layer.origin == ("col",)
    assert layer.values[by_label["v"].id] == 4
    assert scene.evidence == "paper" and scene.provenance == c5_doc.provenance
    validate_origins(c5_doc, scene)


def test_compile_is_deterministic(c5_doc: MathDocument, domains: Domains) -> None:
    assert compile_visual(c5_doc, domains.registry) == compile_visual(c5_doc, domains.registry)


def test_c5_pack_is_discovered() -> None:
    assert [p.name for p in discover()] == ["c5"]


def test_duplicate_rule_fails_closed() -> None:
    registry = Registry()
    register_core_rules(registry)
    with pytest.raises(RuleConflictError, match=r"'mathkit.compile' and 'domain:x'"):
        registry.register(RuleSpec("graph", "default", _noop), "domain:x")


def test_packs_cannot_override_each_other() -> None:
    clash = DomainPack("zz", rules=(RuleSpec("c5.boundary_cycle", "default", _noop),))
    with pytest.raises(RuleConflictError, match="domain:c5"):
        load_domains([c5_plugin(), clash])
    with pytest.raises(RuleConflictError, match="loaded twice"):
        load_domains([c5_plugin(), c5_plugin()])
    kind_clash = DomainPack("zz", kinds={"graph": GraphObject.from_json})
    with pytest.raises(RuleConflictError, match="IR kind 'graph'"):
        load_domains([kind_clash])


def test_registry_must_be_frozen() -> None:
    registry = Registry()
    with pytest.raises(RuntimeError, match="freeze"):
        registry.lookup("graph", "default")
    registry.freeze()
    with pytest.raises(RuntimeError, match="frozen"):
        registry.register(RuleSpec("graph", "default", _noop), "late")


def test_view_falls_back_to_default(c5_doc: MathDocument, domains: Domains) -> None:
    assert compile_visual(c5_doc, domains.registry, view="kempe:1-3") == compile_visual(
        c5_doc, domains.registry
    )


def test_unknown_kind_warns_and_skips(c5_data: dict[str, Any], domains: Domains) -> None:
    data = copy.deepcopy(c5_data)
    data["objects"].append({"id": "Q", "kind": "other.thing", "x": 1})
    doc = load_document(data, domains.kinds)
    with pytest.warns(CompileWarning, match="other.thing"):
        scene = compile_visual(doc, domains.registry)
    assert len(scene.nodes) == 6


def test_domain_kind_without_pack_is_skipped(c5_data: dict[str, Any]) -> None:
    core_only = load_domains([])
    doc = load_document(c5_data, core_only.kinds)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        scene = compile_visual(doc, core_only.registry)
    assert [str(w.message).split("'")[1] for w in caught] == ["c5.boundary_cycle"]
    assert all(n.cls == "default" for n in scene.nodes) and scene.layout.outer == ()


def test_boundary_cycle_needs_its_edges(c5_data: dict[str, Any], domains: Domains) -> None:
    data = copy.deepcopy(c5_data)
    data["objects"][1]["cycle"] = ["b_0", "b_2", "b_1", "b_3", "b_4"]
    doc = load_document(data, domains.kinds)
    with pytest.raises(CompileError, match="no edge b_0-b_2"):
        compile_visual(doc, domains.registry)


def test_validate_origins_rejects_dangling(c5_doc: MathDocument, domains: Domains) -> None:
    scene = compile_visual(c5_doc, domains.registry)
    bad = replace(scene, nodes=(replace(scene.nodes[0], origin=("G/zz",)), *scene.nodes[1:]))
    with pytest.raises(OriginError, match="G/zz"):
        validate_origins(c5_doc, bad)
    empty = replace(scene, nodes=(replace(scene.nodes[0], origin=()), *scene.nodes[1:]))
    with pytest.raises(SceneError, match="empty origin"):
        validate_origins(c5_doc, empty)
    legend = Node("legend", "key", "decoration")
    validate_origins(c5_doc, replace(scene, nodes=(*scene.nodes, legend)))


@pytest.mark.filterwarnings("ignore::mathkit.compile.CompileWarning")
def test_bad_rule_output_is_caught(c5_doc: MathDocument) -> None:
    def dangling(obj: IRObject, b: SceneBuilder) -> None:
        b.add_node(f"{obj.id}/ghost", "?", origin=(f"{obj.id}/ghost",))

    registry = Registry()
    registry.register(RuleSpec("graph", "default", dangling), "test")
    with pytest.raises(CompileError, match="dangling origin"):
        compile_visual(c5_doc, registry.freeze())


@st.composite
def documents(draw: st.DrawFn) -> MathDocument:
    n = draw(st.integers(1, 8))
    names = [f"v{i}" for i in range(n)]
    pairs = [(u, v) for i, u in enumerate(names) for v in names[i + 1 :]]
    chosen = draw(st.lists(st.sampled_from(pairs), unique=True)) if pairs else []
    graph = GraphObject(
        "G", tuple(names), tuple(GraphEdge(f"e{i}", u, v) for i, (u, v) in enumerate(chosen))
    )
    colored = draw(st.lists(st.sampled_from(names), unique=True))
    values = {v: draw(st.integers(0, 9)) for v in colored}
    return MathDocument("computation", {}, (graph, ColoringObject("col", "G", values)))


@given(documents())
def test_origins_hold_for_all_compile_outputs(doc: MathDocument) -> None:
    registry = load_domains([]).registry
    scene = compile_visual(doc, registry)
    validate_origins(doc, scene)
    assert len(scene.nodes) == len(doc.get("G").elements()) - len(scene.edges)
