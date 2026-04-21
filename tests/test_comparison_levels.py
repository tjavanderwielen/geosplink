import pytest
import geosplink.geo_comparison_level_library as gcll

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
        assert gcll.GeoNullLevel("geometry").create_label_for_charts() == "Null"

    def test_is_null_level(self):
        assert gcll.GeoNullLevel("geometry").is_null_level is True

    def test_sql_references_col(self):
        sql = gcll.GeoNullLevel("geom").create_sql(None)
        assert "geom_l IS NULL" in sql
        assert "geom_r IS NULL" in sql

    def test_matches_left_null(self, duckdb_spatial):
        assert (
            _eval_null(
                duckdb_spatial, gcll.GeoNullLevel("geometry"), None, _UNIT_SQUARE
            )
            is True
        )

    def test_matches_right_null(self, duckdb_spatial):
        assert (
            _eval_null(
                duckdb_spatial, gcll.GeoNullLevel("geometry"), _UNIT_SQUARE, None
            )
            is True
        )

    def test_matches_both_null(self, duckdb_spatial):
        assert (
            _eval_null(duckdb_spatial, gcll.GeoNullLevel("geometry"), None, None)
            is True
        )

    def test_no_match_both_present(self, duckdb_spatial):
        assert (
            _eval_null(
                duckdb_spatial,
                gcll.GeoNullLevel("geometry"),
                _UNIT_SQUARE,
                _UNIT_SQUARE,
            )
            is False
        )


class TestGeoExactOverlapLevel:
    def test_label(self):
        assert (
            gcll.GeoExactOverlapLevel("geometry").create_label_for_charts()
            == "Exact overlap"
        )

    def test_sql_uses_st_equals(self):
        sql = gcll.GeoExactOverlapLevel("geometry").create_sql(None)
        assert "ST_Equals" in sql

    def test_sql_uses_bbox_prefilter(self):
        sql = gcll.GeoExactOverlapLevel("geometry").create_sql(None)
        assert "bbox_maxx_l" in sql

    def test_matches_identical_geometries(self, duckdb_spatial):
        level = gcll.GeoExactOverlapLevel("geometry")
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
        level = gcll.GeoExactOverlapLevel("geometry")
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
        level = gcll.GeoExactOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoAnyOverlapLevel:
    def test_label(self):
        assert (
            gcll.GeoAnyOverlapLevel("geometry").create_label_for_charts()
            == "Any overlap"
        )

    def test_sql_uses_st_intersects(self):
        sql = gcll.GeoAnyOverlapLevel("geometry").create_sql(None)
        assert "ST_Intersects" in sql

    def test_sql_uses_bbox_prefilter(self):
        sql = gcll.GeoAnyOverlapLevel("geometry").create_sql(None)
        assert "bbox_maxx_l" in sql

    def test_matches_partially_overlapping(self, duckdb_spatial):
        level = gcll.GeoAnyOverlapLevel("geometry")
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
        level = gcll.GeoAnyOverlapLevel("geometry")
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
        level = gcll.GeoAnyOverlapLevel("geometry")
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoOverlapLevel:
    def test_label(self):
        assert (
            gcll.GeoOverlapLevel("geometry", 0.9).create_label_for_charts()
            == ">=90% overlap"
        )
        assert (
            gcll.GeoOverlapLevel("geometry", 0.5).create_label_for_charts()
            == ">=50% overlap"
        )
        assert (
            gcll.GeoOverlapLevel("geometry", 0.75).create_label_for_charts()
            == ">=75% overlap"
        )

    def test_sql_embeds_threshold(self):
        sql = gcll.GeoOverlapLevel("geometry", 0.6).create_sql(None)
        assert "0.6" in sql

    def test_sql_uses_intersection_and_min(self):
        sql = gcll.GeoOverlapLevel("geometry", 0.5).create_sql(None)
        assert "ST_Intersection" in sql
        assert "LEAST" in sql
        assert "NULLIF" in sql

    def test_identical_passes_high_threshold(self, duckdb_spatial):
        # intersection/min = 1/1 = 1.0
        level = gcll.GeoOverlapLevel("geometry", 0.9)
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
        level = gcll.GeoOverlapLevel("geometry", 0.5)
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
        level = gcll.GeoOverlapLevel("geometry", 0.9)
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
        level = gcll.GeoOverlapLevel("geometry", 0.9)
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
        level = gcll.GeoOverlapLevel("geometry", 0.1)
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoJaccardLevel:
    def test_label(self):
        assert (
            gcll.GeoJaccardLevel("geometry", 0.9).create_label_for_charts()
            == ">=90% Jaccard similarity"
        )
        assert (
            gcll.GeoJaccardLevel("geometry", 0.5).create_label_for_charts()
            == ">=50% Jaccard similarity"
        )

    def test_sql_embeds_threshold(self):
        sql = gcll.GeoJaccardLevel("geometry", 0.75).create_sql(None)
        assert "0.75" in sql

    def test_sql_uses_intersection_and_union(self):
        sql = gcll.GeoJaccardLevel("geometry", 0.5).create_sql(None)
        assert "ST_Intersection" in sql
        assert "ST_Union" in sql
        assert "NULLIF" in sql

    def test_identical_passes(self, duckdb_spatial):
        # IoU = 1/1 = 1.0
        level = gcll.GeoJaccardLevel("geometry", 0.9)
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
        level_pass = gcll.GeoJaccardLevel("geometry", 0.3)
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

        level_fail = gcll.GeoJaccardLevel("geometry", 0.5)
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
        level = gcll.GeoJaccardLevel("geometry", 0.1)
        assert (
            _eval(
                duckdb_spatial, level, _UNIT_SQUARE, _UNIT_BBOX, _FAR_SQUARE, _FAR_BBOX
            )
            is False
        )


class TestGeoSizeExactLevel:
    def test_label(self):
        assert (
            gcll.GeoSizeExactLevel("geometry").create_label_for_charts()
            == "Exact size match"
        )

    def test_sql_uses_st_area(self):
        sql = gcll.GeoSizeExactLevel("geometry").create_sql(None)
        assert "ST_Area" in sql

    def test_matches_same_area_different_shape(self, duckdb_spatial):
        # unit and right_half both have area=1, non-overlapping shapes
        level = gcll.GeoSizeExactLevel("geometry")
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
        level = gcll.GeoSizeExactLevel("geometry")
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
        level = gcll.GeoSizeExactLevel("geometry")
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
            gcll.GeoSizeRatioLevel("geometry", 0.5).create_label_for_charts()
            == ">=50% size ratio"
        )
        assert (
            gcll.GeoSizeRatioLevel("geometry", 0.25).create_label_for_charts()
            == ">=25% size ratio"
        )

    def test_sql_embeds_threshold(self):
        sql = gcll.GeoSizeRatioLevel("geometry", 0.75).create_sql(None)
        assert "0.75" in sql

    def test_sql_uses_least_greatest_nullif(self):
        sql = gcll.GeoSizeRatioLevel("geometry", 0.5).create_sql(None)
        assert "LEAST" in sql
        assert "GREATEST" in sql
        assert "NULLIF" in sql

    def test_equal_area_passes_high_threshold(self, duckdb_spatial):
        # unit and right_half: min(1,1)/max(1,1) = 1.0
        level = gcll.GeoSizeRatioLevel("geometry", 0.9)
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
        level = gcll.GeoSizeRatioLevel("geometry", 0.25)
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
        level = gcll.GeoSizeRatioLevel("geometry", 0.5)
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


# Points for distance tests — no bbox needed (GeoDistance levels don't use bbox)
_POINT_ORIGIN = "POINT(0 0)"
_POINT_3_4 = "POINT(3 4)"  # distance from origin = 5.0
_POINT_NEAR = "POINT(0.5 0)"  # distance from origin = 0.5


def _eval_distance(con, level, wkt_l, wkt_r):
    sql = level.create_sql(None)
    return con.execute(
        f"SELECT ({sql}) FROM (SELECT '{wkt_l}' AS geometry_l, '{wkt_r}' AS geometry_r)"
    ).fetchone()[0]


_PROJECTED = (
    "EPSG:28992"  # RD New — projected, metres, used throughout to suppress CRS warnings
)
_GEOGRAPHIC = "EPSG:4326"  # WGS 84 — geographic, triggers ST_Transform path


class TestGeoDistanceExactLevel:
    def test_label_geometry(self):
        assert (
            gcll.GeoDistanceExactLevel(
                "geometry",
            ).create_label_for_charts()
            == "Exact location match"
        )

    def test_label_centroid(self):
        assert (
            gcll.GeoDistanceExactLevel(
                "geometry", use_centroid=True
            ).create_label_for_charts()
            == "Exact centroid match"
        )

    def test_sql_uses_st_distance(self):
        sql = gcll.GeoDistanceExactLevel("geometry").create_sql(None)
        assert "ST_Distance" in sql
        assert "= 0" in sql

    def test_sql_uses_centroid_when_requested(self):
        sql = gcll.GeoDistanceExactLevel("geometry", use_centroid=True).create_sql(None)
        assert "ST_Centroid" in sql

    def test_sql_no_centroid_by_default(self):
        sql = gcll.GeoDistanceExactLevel("geometry").create_sql(None)
        assert "ST_Centroid" not in sql

    def test_matches_same_point(self, duckdb_spatial):
        level = gcll.GeoDistanceExactLevel("geometry")
        assert (
            _eval_distance(duckdb_spatial, level, _POINT_ORIGIN, _POINT_ORIGIN) is True
        )

    def test_no_match_different_points(self, duckdb_spatial):
        level = gcll.GeoDistanceExactLevel("geometry")
        assert _eval_distance(duckdb_spatial, level, _POINT_ORIGIN, _POINT_3_4) is False

    def test_centroid_matches_same_polygon(self, duckdb_spatial):
        level = gcll.GeoDistanceExactLevel("geometry", use_centroid=True)
        assert _eval_distance(duckdb_spatial, level, _UNIT_SQUARE, _UNIT_SQUARE) is True

    def test_centroid_no_match_different_polygons(self, duckdb_spatial):
        level = gcll.GeoDistanceExactLevel("geometry", use_centroid=True)
        assert _eval_distance(duckdb_spatial, level, _UNIT_SQUARE, _FAR_SQUARE) is False


class TestGeoDistanceLevel:
    def test_label_projected(self):
        assert (
            gcll.GeoDistanceLevel(
                "geometry", 100, crs=_PROJECTED
            ).create_label_for_charts()
            == "Distance <= 100 m"
        )

    def test_label_geographic(self):
        assert (
            gcll.GeoDistanceLevel(
                "geometry", 100, crs=_GEOGRAPHIC
            ).create_label_for_charts()
            == "Distance <= 100 m"
        )

    def test_label_no_crs_omits_unit(self):
        with pytest.warns(UserWarning):
            level = gcll.GeoDistanceLevel("geometry", 100)
        assert level.create_label_for_charts() == "Distance <= 100"

    def test_label_centroid_projected(self):
        assert (
            gcll.GeoDistanceLevel(
                "geometry", 100, use_centroid=True, crs=_PROJECTED
            ).create_label_for_charts()
            == "Centroid distance <= 100 m"
        )

    def test_sql_embeds_threshold(self):
        sql = gcll.GeoDistanceLevel("geometry", 500, crs=_PROJECTED).create_sql(None)
        assert "500" in sql
        assert "<=" in sql

    def test_sql_uses_centroid_when_requested(self):
        sql = gcll.GeoDistanceLevel(
            "geometry", 100, use_centroid=True, crs=_PROJECTED
        ).create_sql(None)
        assert "ST_Centroid" in sql

    def test_sql_no_centroid_by_default(self):
        sql = gcll.GeoDistanceLevel("geometry", 100, crs=_PROJECTED).create_sql(None)
        assert "ST_Centroid" not in sql

    def test_sql_projected_no_transform(self):
        sql = gcll.GeoDistanceLevel("geometry", 100, crs=_PROJECTED).create_sql(None)
        assert "ST_Transform" not in sql

    def test_sql_geographic_uses_transform(self):
        sql = gcll.GeoDistanceLevel("geometry", 100, crs=_GEOGRAPHIC).create_sql(None)
        assert "ST_Transform" in sql
        assert "4326" in sql
        assert "3857" in sql

    def test_sql_geographic_centroid_applied_before_transform(self):
        # ST_Transform wraps ST_Centroid — centroid is computed in original CRS, then reprojected
        sql = gcll.GeoDistanceLevel(
            "geometry", 100, use_centroid=True, crs=_GEOGRAPHIC
        ).create_sql(None)
        assert "ST_Transform(ST_Centroid(" in sql

    def test_no_crs_warns(self):
        with pytest.warns(UserWarning, match="no CRS supplied"):
            gcll.GeoDistanceLevel("geometry", 100)

    def test_unknown_epsg_warns(self):
        with pytest.warns(UserWarning, match="not in geosplink's known CRS list"):
            gcll.GeoDistanceLevel("geometry", 100, crs="EPSG:9999")

    def test_passes_within_threshold(self, duckdb_spatial):
        # distance from origin to (3,4) = 5.0
        level = gcll.GeoDistanceLevel("geometry", 10, crs=_PROJECTED)
        assert _eval_distance(duckdb_spatial, level, _POINT_ORIGIN, _POINT_3_4) is True

    def test_fails_beyond_threshold(self, duckdb_spatial):
        level = gcll.GeoDistanceLevel("geometry", 3, crs=_PROJECTED)
        assert _eval_distance(duckdb_spatial, level, _POINT_ORIGIN, _POINT_3_4) is False

    def test_passes_at_exact_threshold(self, duckdb_spatial):
        # distance = 5.0, threshold = 5.0
        level = gcll.GeoDistanceLevel("geometry", 5.0, crs=_PROJECTED)
        assert _eval_distance(duckdb_spatial, level, _POINT_ORIGIN, _POINT_3_4) is True

    def test_centroid_distance(self, duckdb_spatial):
        # centroid of unit square = (0.5, 0.5), centroid of far square = (2.5, 0.5), distance = 2.0
        level = gcll.GeoDistanceLevel(
            "geometry", 3.0, use_centroid=True, crs=_PROJECTED
        )
        assert _eval_distance(duckdb_spatial, level, _UNIT_SQUARE, _FAR_SQUARE) is True

    def test_centroid_fails_threshold(self, duckdb_spatial):
        level = gcll.GeoDistanceLevel(
            "geometry", 1.0, use_centroid=True, crs=_PROJECTED
        )
        assert _eval_distance(duckdb_spatial, level, _UNIT_SQUARE, _FAR_SQUARE) is False
