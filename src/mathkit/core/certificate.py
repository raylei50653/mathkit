"""Deterministic serialization, input fingerprints, and replay descriptions.

Nothing here records timestamps, host names, or absolute paths (ARCHITECTURE §6): paths are
kept exactly as the caller spells them, so pass repository-relative ones.
"""

import hashlib
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import mathkit

EVIDENCE = "computation"


def canonical_json(value: Any) -> str:
    """Byte-stable JSON text: sorted keys, 2-space indent, UTF-8, trailing newline."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fingerprint(paths: Iterable[str | Path]) -> dict[str, str]:
    """``{path as given: sha256}`` for each input file."""
    return {str(p): sha256_file(p) for p in sorted(paths, key=str)}


def dump(value: Any, path: str | Path) -> None:
    """Write :func:`canonical_json` of ``value`` with ``\\n`` newlines on every platform."""
    Path(path).write_bytes(canonical_json(value).encode("utf-8"))


def replay(command: Sequence[str], inputs: Iterable[str | Path] = ()) -> dict[str, Any]:
    """How to reproduce a result: the command, input fingerprints, and the evidence level.

    Mathkit output is computational evidence; it never raises a claim's evidence level.
    """
    return {
        "command": list(command),
        "evidence": EVIDENCE,
        "inputs": fingerprint(inputs),
        "mathkit": mathkit.__version__,
    }
