import pytest
from splink import Linker as SplinkLinker, SettingsCreator
from splink.comparison_library import ExactMatch
from splink.internals.comparison_library import CustomComparison
from splink.internals.comparison_level_library import CustomLevel

from geosplink import DuckDBAPI, GeoJaccard, GeoOverlap, GeoSizeRatio, Linker, gcll


@pytest.fixture
def db_api():
    api = DuckDBAPI()
    yield api
    api._con.close()


def _data():
    return {
        "unique_id": [1, 2],
        "geometry": ["POINT (0 0)", "POINT (1 1)"],
        "bounds_minx": [0.0, 1.0],
        "bounds_miny": [0.0, 1.0],
        "bounds_maxx": [0.0, 1.0],
        "bounds_maxy": [0.0, 1.0],
    }


def _settings(comparison, link_type="dedupe_only"):
    return SettingsCreator(
        link_type=link_type,
        comparisons=[comparison],
        blocking_rules_to_generate_predictions=["l.unique_id < r.unique_id"],
    )


@pytest.mark.parametrize("comparison", [GeoOverlap, GeoJaccard])
def test_missing_bbox_columns_identified_for_each_input(db_api, comparison):
    left, right = _data(), _data()
    del left["bounds_minx"]
    del right["bounds_maxy"]
    with pytest.raises(ValueError) as exc:
        Linker(
            [left, right],
            _settings(comparison("geometry", bbox_prefix="bounds"), "link_only"),
            db_api,
            input_table_aliases=["left_data", "right_data"],
        )
    message = str(exc.value)
    assert "left_data" in message and "bounds_minx" in message
    assert "right_data" in message and "bounds_maxy" in message


def test_null_bbox_for_non_null_geometry_is_rejected(db_api):
    data = _data()
    data["bounds_miny"][0] = None
    with pytest.raises(ValueError, match="bounds_miny.*NULL"):
        Linker(data, _settings(GeoOverlap("geometry", bbox_prefix="bounds")), db_api)


@pytest.mark.parametrize(
    "geometry", ["not wkt", "POINT EMPTY", "POLYGON ((0 0,1 1,1 0,0 1,0 0))"]
)
def test_invalid_geometry_is_rejected_before_linkage(db_api, geometry):
    data = _data()
    data["geometry"][0] = geometry
    with pytest.raises(ValueError, match="geometry.*(invalid|empty)"):
        Linker(data, _settings(GeoOverlap("geometry", bbox_prefix="bounds")), db_api)


def test_invalid_geometry_is_rejected_without_bbox(db_api):
    data = _data()
    data["geometry"][0] = "not wkt"
    with pytest.raises(ValueError, match="geometry.*invalid"):
        Linker(data, _settings(GeoSizeRatio("geometry")), db_api)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_non_finite_bbox_is_rejected(db_api, value):
    data = _data()
    data["bounds_minx"][0] = value
    with pytest.raises(ValueError, match="bounds_minx.*(NULL|non-finite)"):
        Linker(data, _settings(GeoOverlap("geometry", bbox_prefix="bounds")), db_api)


def test_non_numeric_bbox_is_rejected(db_api):
    data = _data()
    data["bounds_minx"] = ["0", "1"]
    with pytest.raises(ValueError, match="bounds_minx.*numeric"):
        Linker(data, _settings(GeoOverlap("geometry", bbox_prefix="bounds")), db_api)


def test_null_geometry_may_have_null_bbox(db_api):
    data = _data()
    data["geometry"][0] = None
    for suffix in ("minx", "miny", "maxx", "maxy"):
        data[f"bounds_{suffix}"][0] = None
    linker = Linker(
        data, _settings(GeoOverlap("geometry", bbox_prefix="bounds")), db_api
    )
    assert isinstance(linker, SplinkLinker)
    assert len(linker.inference.predict().as_pandas_dataframe()) == 1


def test_inline_bbox_needs_no_precomputed_columns(db_api):
    data = _data()
    for suffix in ("minx", "miny", "maxx", "maxy"):
        del data[f"bounds_{suffix}"]
    linker = Linker(data, _settings(GeoOverlap("geometry")), db_api)
    assert len(linker.inference.predict().as_pandas_dataframe()) == 1


def test_custom_geo_level_validates_bbox(db_api):
    data = _data()
    del data["bounds_maxx"]
    comparison = CustomComparison(
        comparison_levels=[
            gcll.GeoNullLevel("geometry"),
            gcll.GeoAnyOverlapLevel("geometry", bbox_prefix="bounds"),
            CustomLevel("ELSE"),
        ],
        output_column_name="geometry",
    )
    with pytest.raises(ValueError, match="bounds_maxx"):
        Linker(data, _settings(comparison), db_api)


def test_splink_comparison_still_works(db_api):
    data = {"unique_id": [1, 2], "name": ["Alice", "Alice"]}
    linker = Linker(data, _settings(ExactMatch("name")), db_api)
    assert len(linker.inference.predict().as_pandas_dataframe()) == 1
