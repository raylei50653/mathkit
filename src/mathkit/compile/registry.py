"""``(kind, view) -> rule`` registry. Duplicate claims fail closed (ARCHITECTURE §3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mathkit.ir import IRObject

if TYPE_CHECKING:
    from mathkit.compile.builder import SceneBuilder

Rule = Callable[[IRObject, "SceneBuilder"], None]
DEFAULT_VIEW = "default"


class RuleConflictError(ValueError):
    """Two sources claimed the same ``(kind, view)``."""


@dataclass(frozen=True, slots=True)
class RuleSpec:
    kind: str
    view: str
    rule: Rule


@dataclass(frozen=True, slots=True)
class _Entry:
    rule: Rule
    source: str


class Registry:
    """Build once, then :meth:`freeze`; lookups are only allowed on a frozen registry."""

    def __init__(self) -> None:
        self._rules: dict[tuple[str, str], _Entry] = {}
        self._frozen = False

    def register(self, spec: RuleSpec, source: str) -> None:
        if self._frozen:
            raise RuntimeError("registry is frozen")
        key = (spec.kind, spec.view)
        existing = self._rules.get(key)
        if existing is not None:
            raise RuleConflictError(
                f"rule for kind={spec.kind!r} view={spec.view!r} claimed by both "
                f"{existing.source!r} and {source!r}"
            )
        self._rules[key] = _Entry(spec.rule, source)

    def freeze(self) -> Registry:
        self._frozen = True
        return self

    @property
    def frozen(self) -> bool:
        return self._frozen

    def lookup(self, kind: str, view: str) -> Rule | None:
        """The rule for ``(kind, view)``, falling back to ``(kind, "default")``."""
        if not self._frozen:
            raise RuntimeError("freeze the registry before compiling")
        entry = self._rules.get((kind, view)) or self._rules.get((kind, DEFAULT_VIEW))
        return None if entry is None else entry.rule
