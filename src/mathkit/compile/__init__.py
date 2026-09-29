"""Visual Compiler: Math IR -> Scene via a ``(kind, view) -> rule`` registry (ADR-0005)."""

from mathkit.compile.builder import CompileError, SceneBuilder
from mathkit.compile.compiler import CompileWarning, OriginError, compile_visual, validate_origins
from mathkit.compile.registry import DEFAULT_VIEW, Registry, Rule, RuleConflictError, RuleSpec
from mathkit.compile.rules import CORE_RULES, register_core_rules

__all__ = [
    "CORE_RULES",
    "DEFAULT_VIEW",
    "CompileError",
    "CompileWarning",
    "OriginError",
    "Registry",
    "Rule",
    "RuleConflictError",
    "RuleSpec",
    "SceneBuilder",
    "compile_visual",
    "register_core_rules",
    "validate_origins",
]
