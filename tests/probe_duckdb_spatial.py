"""
Diagnostic: what spatial functionality does geosplink.DuckDBAPI provide,
compared to the full duckdb-spatial extension?

Passing = available via geosplink.DuckDBAPI().
Failing = not loaded even after geosplink initialises the connection.

Run explicitly:

    pytest tests/duckdb_spatial.py -v

"""

import re
import urllib.request

import pytest
import geosplink

pytestmark = pytest.mark.spatial_probe

_FUNCTIONS_MD_URL = (
    "https://raw.githubusercontent.com/duckdb/duckdb-spatial/main/docs/functions.md"
)


def _fetch_spatial_functions() -> list[str]:
    with urllib.request.urlopen(_FUNCTIONS_MD_URL, timeout=10) as resp:
        content = resp.read().decode()
    # Match only index entries: [`ST_FunctionName`](#anchor)
    return sorted(set(re.findall(r"\[`(ST_\w+)`\]", content)))


def pytest_generate_tests(metafunc):
    if "fn" in metafunc.fixturenames:
        try:
            functions = _fetch_spatial_functions()
        except Exception as e:
            pytest.skip(f"Could not fetch function list from GitHub: {e}")
            functions = []
        metafunc.parametrize("fn", functions)


@pytest.fixture(scope="module")
def con():
    """DuckDB connection via geosplink.DuckDBAPI."""
    db_api = geosplink.DuckDBAPI()
    yield db_api._con
    db_api._con.close()


def _function_exists(con, name: str) -> bool:
    return (
        con.execute(
            "SELECT count(*) FROM duckdb_functions() WHERE lower(function_name) = ?",
            [name.lower()],
        ).fetchone()[0]
        > 0
    )


def test_function_available(con, fn):
    if not _function_exists(con, fn):
        pytest.fail(f"{fn} not available via geosplink.DuckDBAPI")
