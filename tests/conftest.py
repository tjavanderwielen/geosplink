# tests/conftest.py
import pytest
import duckdb


@pytest.fixture
def duckdb_spatial():
    con = duckdb.connect(":memory:")
    con.execute("INSTALL spatial; LOAD spatial;")
    yield con
    con.close()