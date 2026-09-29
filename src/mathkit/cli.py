"""Command-line entry point: render | serve | check | validate | schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from mathkit import __version__
from mathkit.core.certificate import canonical_json

PENDING = ("serve", "check", "validate")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mathkit")
    parser.add_argument("--version", action="version", version=f"mathkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="render Math IR or Scene JSON to SVG or Scene JSON")
    render.add_argument("input", type=Path, help="mathkit.ir/1 or mathkit.scene/1 JSON file")
    render.add_argument("-o", "--output", type=Path, help="output file (default: stdout)")
    render.add_argument(
        "-f", "--format", choices=("svg", "json"), help="default: from -o suffix, else svg"
    )
    render.add_argument("--view", default="default", help="compile view (Math IR input only)")
    render.add_argument("--layout", help="override the layout engine (fixed, circular, tutte)")

    schema = sub.add_parser("schema", help="print or write the JSON Schemas")
    schema.add_argument("which", nargs="?", choices=("ir", "scene"), default="scene")
    schema.add_argument(
        "--out-dir", type=Path, help="write ir.schema.json and scene.schema.json here"
    )

    for name in PENDING:
        sub.add_parser(name, help="not implemented yet (see docs/PLAN.md)")

    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            return _render(args)
        if args.command == "schema":
            return _schema(args)
    except (OSError, ValueError) as exc:  # includes IR, scene, compile and layout errors
        parser.exit(1, f"mathkit {args.command}: {type(exc).__name__}: {exc}\n")
    parser.exit(2, f"mathkit {args.command}: not implemented yet (see docs/PLAN.md)\n")


def _render(args: argparse.Namespace) -> int:
    from mathkit import ir, scene
    from mathkit.compile import compile_visual
    from mathkit.domains import load_domains
    from mathkit.layout import apply_layout
    from mathkit.render import RENDERERS

    path: Path = args.input
    data: object = json.loads(path.read_text(encoding="utf-8"))
    header = cast("dict[str, Any]", data) if isinstance(data, dict) else {}
    kind = header.get("schema")
    if kind == ir.SCHEMA_ID:
        domains = load_domains()
        doc = ir.load_document(header, domains.kinds)
        sc = compile_visual(doc, domains.registry, args.view, title=path.stem)
    elif kind == scene.SCHEMA_ID:
        sc = scene.load_scene(header)
    else:
        raise ValueError(f"{path}: expected schema {ir.SCHEMA_ID!r} or {scene.SCHEMA_ID!r}")
    sc = apply_layout(sc, args.layout)

    output: Path | None = args.output
    fmt = args.format or ("json" if output is not None and output.suffix == ".json" else "svg")
    _emit(RENDERERS[fmt](sc), output)
    return 0


def _schema(args: argparse.Namespace) -> int:
    from mathkit.ir.schema import ir_schema
    from mathkit.scene.schema import scene_schema

    schemas = {"ir": ir_schema(), "scene": scene_schema()}
    out_dir: Path | None = args.out_dir
    if out_dir is None:
        _emit(canonical_json(schemas[args.which]), None)
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, value in schemas.items():
        _emit(canonical_json(value), out_dir / f"{name}.schema.json")
    return 0


def _emit(text: str, output: Path | None) -> None:
    """Write UTF-8 with ``\\n`` newlines on every platform, so bytes stay deterministic."""
    data = text.encode("utf-8")
    if output is None:
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
    else:
        output.write_bytes(data)


if __name__ == "__main__":
    raise SystemExit(main())
