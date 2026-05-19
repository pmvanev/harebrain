from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


DATA_DIR = Path(__file__).parent.parent / "data"
PDF_PATH = DATA_DIR / "IA Employee Handbook 050826.pdf"


@pytest.fixture
def pdf_path() -> Path:
    return PDF_PATH


def unit(values: list[float]) -> np.ndarray:
    v = np.array(values, dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def make_unit():
    return unit
