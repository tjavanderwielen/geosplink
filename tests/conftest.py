# tests/conftest.py
import csv
from pathlib import Path

import pytest
import geosplink

_CSV_PATH = Path(__file__).parent / "data" / "sample_geometries.csv"
_GEOMETRIES_DIR = Path(__file__).parent / "data" / "geometries"


def _load_geometries() -> dict:
    result = {}
    with open(_CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            bbox = None
            if row["minx"]:
                bbox = (
                    float(row["minx"]),
                    float(row["miny"]),
                    float(row["maxx"]),
                    float(row["maxy"]),
                )
            result[row["name"]] = {"wkt": row["wkt"], "bbox": bbox}
    return result


_GEOMETRIES = _load_geometries()


def load_wkt(name: str) -> str:
    return _GEOMETRIES[name]["wkt"]


def load_bbox(name: str) -> tuple:
    return _GEOMETRIES[name]["bbox"]


@pytest.fixture(scope="session")
def geometries() -> dict:
    return _GEOMETRIES


@pytest.fixture
def duckdb_spatial():
    db_api = geosplink.DuckDBAPI()
    yield db_api._con
    db_api._con.close()
