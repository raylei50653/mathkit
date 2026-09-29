"""Math IR: mathematical objects and their relations, no geometry or style (ADR-0005)."""

from mathkit.ir.model import (
    CORE_KINDS,
    EVIDENCE,
    SCHEMA_ID,
    ColoringObject,
    GraphEdge,
    GraphObject,
    IRError,
    IRObject,
    KindParser,
    MathDocument,
    RawObject,
    dependency_order,
    load_document,
    resolves,
    validate_document,
)

__all__ = [
    "CORE_KINDS",
    "EVIDENCE",
    "SCHEMA_ID",
    "ColoringObject",
    "GraphEdge",
    "GraphObject",
    "IRError",
    "IRObject",
    "KindParser",
    "MathDocument",
    "RawObject",
    "dependency_order",
    "load_document",
    "resolves",
    "validate_document",
]
