"""``compile_visual``: Math IR -> Scene, with Math IR <-> Scene integrity enforced."""

import warnings

from mathkit.compile.builder import CompileError, SceneBuilder
from mathkit.compile.registry import DEFAULT_VIEW, Registry
from mathkit.ir import MathDocument, dependency_order, resolves, validate_document
from mathkit.scene import Scene, SceneError, validate_scene


class CompileWarning(UserWarning):
    """An IR object was skipped because no rule handles its kind."""


class OriginError(ValueError):
    """A Scene element's ``origin`` does not resolve into the Math IR (integrity rule 4)."""


def compile_visual(
    doc: MathDocument, registry: Registry, view: str = DEFAULT_VIEW, title: str = ""
) -> Scene:
    """Lower ``doc`` to a Scene; objects are visited so referenced objects are drawn first."""
    builder = SceneBuilder(doc)
    for obj in dependency_order(doc):
        rule = registry.lookup(obj.kind, view)
        if rule is None:
            warnings.warn(
                f"no compile rule for kind {obj.kind!r} (object {obj.id!r}); skipped",
                CompileWarning,
                stacklevel=2,
            )
            continue
        rule(obj, builder)
    scene = builder.build(title)
    try:
        validate_origins(doc, scene)
    except (SceneError, OriginError) as exc:
        raise CompileError(f"compiled scene violates integrity: {exc}") from exc
    return scene


def validate_origins(doc: MathDocument, scene: Scene) -> None:
    """Check all eight Math IR <-> Scene integrity rules (ARCHITECTURE §3)."""
    validate_document(doc)
    validate_scene(scene)
    by_id = {obj.id: obj for obj in doc.objects}
    for elem in (*scene.nodes, *scene.edges, *scene.layers):
        for ref in elem.origin:
            if not resolves(doc, ref, by_id):
                raise OriginError(f"{elem.id!r}: dangling origin {ref!r}")
