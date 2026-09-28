"""Command-line entry point: render | serve | check | validate | schema."""

import argparse

from mathkit import __version__

COMMANDS = ("render", "serve", "check", "validate", "schema")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mathkit")
    parser.add_argument("--version", action="version", version=f"mathkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        sub.add_parser(name, help="not implemented yet (see docs/PLAN.md)")
    args = parser.parse_args(argv)
    parser.exit(2, f"mathkit {args.command}: not implemented yet (see docs/PLAN.md)\n")


if __name__ == "__main__":
    raise SystemExit(main())
