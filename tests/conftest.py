import json
from pathlib import Path
from typing import Any

import pytest

from mathkit.domains import Domains, load_domains
from mathkit.ir import MathDocument, load_document

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
GOLDEN = Path(__file__).resolve().parent / "golden"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def domains() -> Domains:
    return load_domains()


@pytest.fixture
def c5_data() -> dict[str, Any]:
    return read_json(EXAMPLES / "c5.ir.json")


@pytest.fixture
def c5_doc(c5_data: dict[str, Any], domains: Domains) -> MathDocument:
    return load_document(c5_data, domains.kinds)
