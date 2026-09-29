"""End-to-end CLI tests, including the M1a byte goldens.

Regenerate goldens after an intentional output change with
``MATHKIT_UPDATE_GOLDEN=1 uv run pytest tests/test_cli.py`` and bump LAYOUT_VERSION
if positions moved.
"""

import hashlib
import os
from pathlib import Path

import jsonschema
import pytest

from mathkit.cli import main
from mathkit.ir.schema import ir_schema
from mathkit.scene.schema import scene_schema

from .conftest import EXAMPLES, GOLDEN, ROOT, read_json

C5 = EXAMPLES / "c5.ir.json"


def _run(*argv: str) -> int:
    try:
        return main(list(argv))
    except SystemExit as exc:
        return int(exc.code or 0)


def _check_golden(produced: Path, name: str) -> None:
    golden = GOLDEN / name
    if os.environ.get("MATHKIT_UPDATE_GOLDEN"):
        golden.parent.mkdir(exist_ok=True)
        golden.write_bytes(produced.read_bytes())
    assert produced.read_bytes() == golden.read_bytes(), f"{name} differs from golden"


def test_render_svg_matches_golden(tmp_path: Path) -> None:
    out = tmp_path / "c5.svg"
    assert _run("render", str(C5), "-o", str(out)) == 0
    _check_golden(out, "c5.svg")


def test_render_twice_same_sha256(tmp_path: Path) -> None:
    a, b = tmp_path / "a.svg", tmp_path / "b.svg"
    _run("render", str(C5), "-o", str(a))
    _run("render", str(C5), "-o", str(b))
    assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()


def test_scene_json_golden_and_rerender(tmp_path: Path) -> None:
    scene_path = tmp_path / "c5.scene.json"
    assert _run("render", str(C5), "-o", str(scene_path)) == 0
    _check_golden(scene_path, "c5.scene.json")
    jsonschema.validate(read_json(scene_path), scene_schema())
    svg = tmp_path / "c5.svg"
    assert _run("render", str(scene_path), "-o", str(svg)) == 0
    assert svg.read_bytes() == (GOLDEN / "c5.svg").read_bytes()


def test_example_matches_ir_schema() -> None:
    jsonschema.validate(read_json(C5), ir_schema())


def test_committed_schemas_are_current(tmp_path: Path) -> None:
    assert _run("schema", "--out-dir", str(tmp_path)) == 0
    for name in ("ir.schema.json", "scene.schema.json"):
        assert (tmp_path / name).read_bytes() == (ROOT / "schemas" / name).read_bytes(), (
            f"schemas/{name} is stale; run `uv run mathkit schema --out-dir schemas`"
        )


def test_schemas_are_valid_json_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(ir_schema())
    jsonschema.Draft202012Validator.check_schema(scene_schema())


def test_render_errors_exit_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema": "nope"}', encoding="utf-8")
    assert _run("render", str(bad)) == 1
    assert "expected schema" in capsys.readouterr().err


def test_pending_commands_say_so(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run("serve") == 2
    assert "not implemented" in capsys.readouterr().err
