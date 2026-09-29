"""JSON Schema for ``mathkit.ir/1``. Domain kinds are checked by their pack, not here."""

from typing import Any

from mathkit.ir.model import EVIDENCE, SCHEMA_ID

_NAME = {"type": "string", "pattern": r"^[A-Za-z0-9_.:\-]+$"}


def ir_schema() -> dict[str, Any]:
    core = {
        "graph": {
            "type": "object",
            "required": ["id", "kind", "vertices", "edges"],
            "additionalProperties": False,
            "properties": {
                "id": {"$ref": "#/$defs/name"},
                "kind": {"const": "graph"},
                "vertices": {"type": "array", "items": {"$ref": "#/$defs/name"}},
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "u", "v"],
                        "additionalProperties": False,
                        "properties": {
                            "id": {"$ref": "#/$defs/name"},
                            "u": {"$ref": "#/$defs/name"},
                            "v": {"$ref": "#/$defs/name"},
                        },
                    },
                },
            },
        },
        "coloring": {
            "type": "object",
            "required": ["id", "kind", "graph", "values"],
            "additionalProperties": False,
            "properties": {
                "id": {"$ref": "#/$defs/name"},
                "kind": {"const": "coloring"},
                "graph": {"$ref": "#/$defs/name"},
                "values": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "mathkit Math IR",
        "type": "object",
        "required": ["schema", "evidence", "objects"],
        "additionalProperties": False,
        "properties": {
            "schema": {"const": SCHEMA_ID},
            "evidence": {"enum": list(EVIDENCE)},
            "provenance": {"type": "object", "additionalProperties": {"type": "string"}},
            "objects": {"type": "array", "items": {"$ref": "#/$defs/object"}},
        },
        "$defs": {
            "name": _NAME,
            "object": {
                "type": "object",
                "required": ["id", "kind"],
                "properties": {"id": {"$ref": "#/$defs/name"}, "kind": {"type": "string"}},
                "allOf": [
                    {
                        "if": {"properties": {"kind": {"const": kind}}},
                        "then": {"$ref": f"#/$defs/{kind}"},
                    }
                    for kind in core
                ],
            },
            **core,
        },
    }
