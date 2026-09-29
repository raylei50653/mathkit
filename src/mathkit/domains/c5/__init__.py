"""C5 boundary-colouring domain pack for the ``math`` research repository."""

from mathkit.domains import DomainPack
from mathkit.domains.c5.ir_kinds import BoundaryCycle
from mathkit.domains.c5.rules import RULES


def plugin() -> DomainPack:
    """Entry point: the IR kinds and compile rules this pack contributes."""
    return DomainPack(name="c5", kinds={"c5.boundary_cycle": BoundaryCycle.from_json}, rules=RULES)
