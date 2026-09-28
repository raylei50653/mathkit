import importlib

import pytest

from mathkit import __version__
from mathkit.cli import main

LAYERS = ["core", "scene", "layout", "render", "adapters", "domains", "domains.c5", "cli"]


def test_version() -> None:
    assert __version__


@pytest.mark.parametrize("name", LAYERS)
def test_layers_import(name: str) -> None:
    importlib.import_module(f"mathkit.{name}")


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
