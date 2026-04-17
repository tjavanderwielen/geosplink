import pytest
from geosplink.geo_comparison_level_library import (
    GeoNullLevel,
    GeoExactOverlapLevel,
    GeoAnyOverlapLevel,
    GeoOverlapLevel,
    GeoJaccardLevel,
    GeoSizeExactLevel,
    GeoSizeRatioLevel,
)

# WKT test geometries with precomputed bounding boxes
_UNIT_SQUARE = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"  # area=1
_UNIT_BBOX = (0.0, 0.0, 1.0, 1.0)

_RIGHT_HALF = (
    "POLYGON((0.5 0, 1.5 0, 1.5 1, 0.5 1, 0.5 0))"  # area=1, 50% overlap with unit
)
_RIGHT_HALF_BBOX = (0.5, 0.0, 1.5, 1.0)

_FAR_SQUARE = "POLYGON((2 0, 3 0, 3 1, 2 1, 2 0))"  # area=1, no overlap with unit
_FAR_BBOX = (2.0, 0.0, 3.0, 1.0)

_LARGE_SQUARE = "POLYGON((0 0, 4 0, 4 4, 0 4, 0 0))"  # area=16, contains unit
_LARGE_BBOX = (0.0, 0.0, 4.0, 4.0)

_SMALL_SQUARE = (
    "POLYGON((0.1 0.1, 0.5 0.1, 0.5 0.5, 0.1 0.5, 0.1 0.1))"  # area=0.16, inside unit
)
_SMALL_BBOX = (0.1, 0.1, 0.5, 0.5)


def _eval(con, level, wkt_l, bbox_l, wkt_r, bbox_r):
    """Evaluate a level's SQL against two WKT geometries, returning the boolean result."""
    sql = level.create_sql(None)
    minx_l, miny_l, maxx_l, maxy_l = bbox_l
    minx_r, miny_r, maxx_r, maxy_r = bbox_r
    query = f"""
        SELECT ({sql}) AS result
        FROM (
            SELECT
                '{wkt_l}' AS geometry_l, '{wkt_r}' AS geometry_r,
                {minx_l} AS bbox_minx_l, {miny_l} AS bbox_miny_l,
                {maxx_l} AS bbox_maxx_l, {maxy_l} AS bbox_maxy_l,
                {minx_r} AS bbox_minx_r, {miny_r} AS bbox_miny_r,
                {maxx_r} AS bbox_maxx_r, {maxy_r} AS bbox_maxy_r
        )
    """
    return con.execute(query).fetchone()[0]


def _eval_null(con, level, wkt_l, wkt_r):
    """Evaluate a level's SQL where either geometry may be NULL (no bbox needed)."""
    sql = level.create_sql(None)
    l = f"'{wkt_l}'" if wkt_l is not None else "NULL"
    r = f"'{wkt_r}'" if wkt_r is not None else "NULL"
    return con.execute(
        f"SELECT ({sql}) FROM (SELECT {l} AS geometry_l, {r} AS geometry_r)"
    ).fetchone()[0]


class TestGeoNullLevel:
    def test_label(self):
        assert GeoNullLevel("geometry").create_label_for_charts() == "Null"

    def test_is_null_level(self):
        assert GeoNullLevel("geometry").is_null_level is True

    def test_sql_references_col(self):
        sql = GeoNullLevel("geom").create_sql(None)
        assert "geom_l IS NULL" in sql
        assert "geom_r IS NULL" in sql

    def test_matches_left_null(self, duckdb_spatial):
        assert (
            _eval_null(duckdb_spatial, GeoNullLevel("geometry"), None, _UNIT_SQUARE)
            is True
        )

    def test_matches_right_null(self, duckdb_spatial):
        assert (
            _eval_null(duckdb_spatial, GeoNullLevel("geometry"), _UNIT_SQUARE, None)
            is True
        )

    def test_matches_both_null(self, duckdb_spatial):
        assert _eval_null(duckdb_spatial, GeoNullLevel("geometry"), None, None) is True

    def test_no_match_both_present(self, duckdb_spatial):
        assert (
            _eval_null(
                duckdb_spatial, GeoNullLevel("geometry"), _UNIT_SQUARE, _UNIT_SQUARE
            )
            is False
        )


class TestGeoExactOverlapLevel:
    def test_label(self):
        assert (
            GeoExactOverlapLevel("geometry").create_label_for_charts()
            == "Exact overlap"
        )

    def test_sql_uses_st_equals(self):
        sql = GeoExactOverlapLevel("geometry").create_sql(None)
        assert "ST_Equals" in sql

    def test_sql_uses_bbox_prefilter(self):
        sql = GeoExactOverlapLevel("geometry").create_sql(None)
        assert "bbox_maxx_l" in sql

    def test_matches_identical_geometries(self, duckdb_spatial):
        level = GeoExactOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _UNIT_SQUARE,
                _UNIT_BBOX,
            )
            is True
        )

    def test_no_match_different_shape(self, duckdb_spatial):
        level = GeoExactOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is False
        )

    def test_no_match_non_overlapping(self, duckdb_spatial):
        level = GeoExactOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoAnyOverlapLevel:
    def test_label(self):
        assert GeoAnyOverlapLevel("geometry").create_label_for_charts() == "Any overlap"

    def test_sql_uses_st_intersects(self):
        sql = GeoAnyOverlapLevel("geometry").create_sql(None)
        assert "ST_Intersects" in sql

    def test_sql_uses_bbox_prefilter(self):
        sql = GeoAnyOverlapLevel("geometry").create_sql(None)
        assert "bbox_maxx_l" in sql

    def test_matches_partially_overlapping(self, duckdb_spatial):
        level = GeoAnyOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is True
        )

    def test_matches_identical(self, duckdb_spatial):
        level = GeoAnyOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _UNIT_SQUARE,
                _UNIT_BBOX,
            )
            is True
        )

    def test_no_match_non_overlapping(self, duckdb_spatial):
        level = GeoAnyOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoOverlapLevel:
    def test_label(self):
        assert (
            GeoOverlapLevel("geometry", 0.9).create_label_for_charts()
            == ">=90% overlap"
        )
        assert (
            GeoOverlapLevel("geometry", 0.5).create_label_for_charts()
            == ">=50% overlap"
        )
        assert (
            GeoOverlapLevel("geometry", 0.75).create_label_for_charts()
            == ">=75% overlap"
        )

    def test_sql_embeds_threshold(self):
        sql = GeoOverlapLevel("geometry", 0.6).create_sql(None)
        assert "0.6" in sql

    def test_sql_uses_intersection_and_min(self):
        sql = GeoOverlapLevel("geometry", 0.5).create_sql(None)
        assert "ST_Intersection" in sql
        assert "LEAST" in sql
        assert "NULLIF" in sql

    def test_identical_passes_high_threshold(self, duckdb_spatial):
        # intersection/min = 1/1 = 1.0
        level = GeoOverlapLevel("geometry", 0.9)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _UNIT_SQUARE,
                _UNIT_BBOX,
            )
            is True
        )

    def test_half_overlap_passes_at_threshold(self, duckdb_spatial):
        # unit vs right_half: intersection=0.5, min(1,1)=1 → ratio=0.5
        level = GeoOverlapLevel("geometry", 0.5)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is True
        )

    def test_half_overlap_fails_above_threshold(self, duckdb_spatial):
        level = GeoOverlapLevel("geometry", 0.9)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is False
        )

    def test_small_inside_large_passes_asymmetric(self, duckdb_spatial):
        # small fully inside unit: intersection=area(small), min=area(small) → 1.0
        level = GeoOverlapLevel("geometry", 0.9)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _SMALL_SQUARE,
                _SMALL_BBOX,
                _UNIT_SQUARE,
                _UNIT_BBOX,
            )
            is True
        )

    def test_non_overlapping_fails(self, duckdb_spatial):
        level = GeoOverlapLevel("geometry", 0.1)
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoJaccardLevel:
    def test_label(self):
        assert (
            GeoJaccardLevel("geometry", 0.9).create_label_for_charts()
            == ">=90% Jaccard similarity"
        )
        assert (
            GeoJaccardLevel("geometry", 0.5).create_label_for_charts()
            == ">=50% Jaccard similarity"
        )

    def test_sql_embeds_threshold(self):
        sql = GeoJaccardLevel("geometry", 0.75).create_sql(None)
        assert "0.75" in sql

    def test_sql_uses_intersection_and_union(self):
        sql = GeoJaccardLevel("geometry", 0.5).create_sql(None)
        assert "ST_Intersection" in sql
        assert "ST_Union" in sql
        assert "NULLIF" in sql

    def test_identical_passes(self, duckdb_spatial):
        # IoU = 1/1 = 1.0
        level = GeoJaccardLevel("geometry", 0.9)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _UNIT_SQUARE,
                _UNIT_BBOX,
            )
            is True
        )

    def test_half_overlap_jaccard_below_half(self, duckdb_spatial):
        # unit vs right_half: intersection=0.5, union=1.5 → IoU≈0.333
        level_pass = GeoJaccardLevel("geometry", 0.3)
        assert (
            _eval(
                duckdb_spatial,
                level_pass,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is True
        )

        level_fail = GeoJaccardLevel("geometry", 0.5)
        assert (
            _eval(
                duckdb_spatial,
                level_fail,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is False
        )

    def test_non_overlapping_fails(self, duckdb_spatial):
        level = GeoJaccardLevel("geometry", 0.1)
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoSizeExactLevel:
    def test_label(self):
        assert (
            GeoSizeExactLevel("geometry").create_label_for_charts()
            == "Exact size match"
        )

    def test_sql_uses_st_area(self):
        sql = GeoSizeExactLevel("geometry").create_sql(None)
        assert "ST_Area" in sql

    def test_matches_same_area_different_shape(self, duckdb_spatial):
        # unit and right_half both have area=1, non-overlapping shapes
        level = GeoSizeExactLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is True
        )

    def test_matches_identical(self, duckdb_spatial):
        level = GeoSizeExactLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _UNIT_SQUARE,
                _UNIT_BBOX,
            )
            is True
        )

    def test_no_match_different_area(self, duckdb_spatial):
        level = GeoSizeExactLevel("geometry")
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _LARGE_SQUARE,
                _LARGE_BBOX,
            )
            is False
        )


class TestGeoSizeRatioLevel:
    def test_label(self):
        assert (
            GeoSizeRatioLevel("geometry", 0.5).create_label_for_charts()
            == ">=50% size ratio"
        )
        assert (
            GeoSizeRatioLevel("geometry", 0.25).create_label_for_charts()
            == ">=25% size ratio"
        )

    def test_sql_embeds_threshold(self):
        sql = GeoSizeRatioLevel("geometry", 0.75).create_sql(None)
        assert "0.75" in sql

    def test_sql_uses_least_greatest_nullif(self):
        sql = GeoSizeRatioLevel("geometry", 0.5).create_sql(None)
        assert "LEAST" in sql
        assert "GREATEST" in sql
        assert "NULLIF" in sql

    def test_equal_area_passes_high_threshold(self, duckdb_spatial):
        # unit and right_half: min(1,1)/max(1,1) = 1.0
        level = GeoSizeRatioLevel("geometry", 0.9)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _RIGHT_HALF,
                _RIGHT_HALF_BBOX,
            )
            is True
        )

    def test_unit_vs_large_fails_threshold(self, duckdb_spatial):
        # unit(1) vs large(16): ratio=1/16=0.0625, fails 0.25
        level = GeoSizeRatioLevel("geometry", 0.25)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _UNIT_SQUARE,
                _UNIT_BBOX,
                _LARGE_SQUARE,
                _LARGE_BBOX,
            )
            is False
        )

    def test_small_vs_large_fails_low_threshold(self, duckdb_spatial):
        # small(0.16) vs large(16): ratio≈0.01, fails 0.5
        level = GeoSizeRatioLevel("geometry", 0.5)
        assert (
            _eval(
                duckdb_spatial,
                level,
                _SMALL_SQUARE,
                _SMALL_BBOX,
                _LARGE_SQUARE,
                _LARGE_BBOX,
            )
            is False
        )
