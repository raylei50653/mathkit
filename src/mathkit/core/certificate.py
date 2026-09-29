"""Deterministic serialization. Fingerprints and replay descriptions arrive in M2."""

import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Byte-stable JSON text: sorted keys, 2-space indent, UTF-8, trailing newline."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
