"""Domain packs, discovered via the ``mathkit.domains`` entry point group (ADR-0004).

Packs load in entry-point-name order; a duplicate pack name, IR kind, or ``(kind, view)`` rule
is an error, never a silent override.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from importlib.metadata import entry_points

from mathkit.compile import Registry, RuleConflictError, RuleSpec, register_core_rules
from mathkit.ir import CORE_KINDS, KindParser

GROUP = "mathkit.domains"


@dataclass(frozen=True, slots=True)
class DomainPack:
    """What a pack contributes. Adapters and checkers arrive with M3."""

    name: str
    kinds: Mapping[str, KindParser] = field(default_factory=dict[str, KindParser])
    rules: tuple[RuleSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class Domains:
    packs: tuple[DomainPack, ...]
    kinds: Mapping[str, KindParser]
    registry: Registry


def discover() -> tuple[DomainPack, ...]:
    """Load every installed pack, sorted by entry point name."""
    eps = sorted(entry_points(group=GROUP), key=lambda ep: ep.name)
    packs: list[DomainPack] = []
    for ep in eps:
        pack = ep.load()()
        if not isinstance(pack, DomainPack):
            raise TypeError(f"entry point {ep.name!r} did not return a DomainPack")
        if pack.name != ep.name:
            raise ValueError(f"entry point {ep.name!r} returned pack named {pack.name!r}")
        packs.append(pack)
    return tuple(packs)


def load_domains(packs: Iterable[DomainPack] | None = None) -> Domains:
    """Combine core kinds and rules with ``packs`` (default: :func:`discover`) and freeze."""
    chosen = tuple(discover() if packs is None else packs)
    kinds: dict[str, KindParser] = dict(CORE_KINDS)
    kind_source = dict.fromkeys(CORE_KINDS, "mathkit.ir")
    registry = Registry()
    register_core_rules(registry)
    seen: set[str] = set()
    for pack in chosen:
        if pack.name in seen:
            raise RuleConflictError(f"domain pack {pack.name!r} loaded twice")
        seen.add(pack.name)
        source = f"domain:{pack.name}"
        for kind, parser in sorted(pack.kinds.items()):
            if kind in kinds:
                raise RuleConflictError(
                    f"IR kind {kind!r} claimed by both {kind_source[kind]!r} and {source!r}"
                )
            kinds[kind] = parser
            kind_source[kind] = source
        for spec in pack.rules:
            registry.register(spec, source)
    return Domains(chosen, kinds, registry.freeze())


__all__ = ["GROUP", "DomainPack", "Domains", "discover", "load_domains"]
