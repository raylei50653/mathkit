import hashlib
from pathlib import Path

import pytest

import mathkit
from mathkit.core.certificate import canonical_json, dump, fingerprint, replay


def test_canonical_json_is_stable() -> None:
    expected = '{\n  "a": [\n    1,\n    "é"\n  ],\n  "b": 1\n}\n'
    assert canonical_json({"b": 1, "a": [1, "é"]}) == expected
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


def test_dump_uses_lf(tmp_path: Path) -> None:
    out = tmp_path / "x.json"
    dump({"k": [1, 2]}, out)
    assert b"\r" not in out.read_bytes()
    assert out.read_bytes() == canonical_json({"k": [1, 2]}).encode()


def test_fingerprint_and_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("b.json").write_bytes(b"{}")
    Path("a.json").write_bytes(b"[]")
    fp = fingerprint(["b.json", "a.json"])
    assert list(fp) == ["a.json", "b.json"]
    assert fp["a.json"] == hashlib.sha256(b"[]").hexdigest()
    record = replay(["mathkit", "check", "a.json"], ["a.json"])
    assert record == {
        "command": ["mathkit", "check", "a.json"],
        "evidence": "computation",
        "inputs": {"a.json": fp["a.json"]},
        "mathkit": mathkit.__version__,
    }
    assert not any(Path(p).is_absolute() for p in record["inputs"])
