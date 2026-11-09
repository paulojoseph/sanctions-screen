from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LISTS = ROOT / "tests" / "fixtures" / "lists"
LISTS_OLD = ROOT / "tests" / "fixtures" / "lists_old"
EXAMPLES = ROOT / "examples"


@pytest.fixture(scope="session")
def lists_dir():
    return LISTS


@pytest.fixture(scope="session")
def examples_dir():
    return EXAMPLES
