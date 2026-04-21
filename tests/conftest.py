# tests/conftest.py
import pytest
import geosplink


@pytest.fixture
def duckdb_spatial():
    db_api = geosplink.DuckDBAPI()
    yield db_api._con
    db_api._con.close()