"""JSON Schema for ``mathkit.scene/1``; the viewer's TypeScript types are generated from it."""

from typing import Any

from mathkit.scene.model import CLASSES, LAYER_KINDS, SCHEMA_ID

_ORIGIN = {"type": "array", "items": {"type": "string"}}


def scene_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "mathkit Scene",
        "type": "object",
        "required": ["schema", "title", "evidence", "provenance", "nodes", "edges", "layers",
                     "layout"],
        "additionalProperties": False,
        "properties": {
            "schema": {"const": SCHEMA_ID},
            "title": {"type": "string"},
            "evidence": {"type": "string"},
            "provenance": {"type": "object", "additionalProperties": {"type": "string"}},
            "nodes": {"type": "array", "items": {"$ref": "#/$defs/node"}},
            "edges": {"type": "array", "items": {"$ref": "#/$defs/edge"}},
            "layers": {"type": "array", "items": {"$ref": "#/$defs/layer"}},
            "layout": {"$ref": "#/$defs/layout"},
        },
        "$defs": {
            "class": {"enum": list(CLASSES)},
            "node": {
                "type": "object",
                "required": ["id", "label", "class", "pos", "origin"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "class": {"$ref": "#/$defs/class"},
                    "pos": {
                        "oneOf": [
                            {"type": "null"},
                            {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        ]
                    },
                    "origin": _ORIGIN,
                },
            },
            "edge": {
                "type": "object",
                "required": ["id", "u", "v", "class", "origin"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "u": {"type": "string"},
                    "v": {"type": "string"},
                    "class": {"$ref": "#/$defs/class"},
                    "origin": _ORIGIN,
                },
            },
            "layer": {
                "type": "object",
                "required": ["id", "kind", "values", "origin"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "kind": {"enum": list(LAYER_KINDS)},
                    "values": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "origin": _ORIGIN,
                },
            },
            "layout": {
                "type": "object",
                "required": ["engine", "outer", "version", "exact"],
                "additionalProperties": False,
                "properties": {
                    "engine": {"type": ["string", "null"]},
                    "outer": {"type": "array", "items": {"type": "string"}},
                    "version": {"type": ["integer", "null"]},
                    "exact": {"type": ["boolean", "null"]},
                },
            },
        },
    }
