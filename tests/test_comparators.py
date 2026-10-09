import pytest
from splink.internals.comparison_level_library import CustomLevel

import geosplink.geo_comparison_library as gcl
import geosplink.geo_comparison_level_library as gcll


class TestGeoOverlap:
    def test_default_thresholds(self):
        assert gcl.GeoOverlap("geometry").thresholds == [0.9, 0.5]

    def test_single_threshold_normalised_to_list(self):
        assert gcl.GeoOverlap("geometry", 0.75).thresholds == [0.75]

    def test_list_thresholds_preserved(self):
        assert gcl.GeoOverlap("geometry", [0.8, 0.6, 0.3]).thresholds == [0.8, 0.6, 0.3]

    def test_output_column_name(self):
        assert gcl.GeoOverlap("my_geom").create_output_column_name() == "my_geom"

    def test_level_count_default(self):
        # null + exact + 2 thresholds + any + else = 6
        assert len(gcl.GeoOverlap("geometry").create_comparison_levels()) == 6

    def test_level_count_single_threshold(self):
        # null + exact + 1 threshold + any + else = 5
        assert len(gcl.GeoOverlap("geometry", 0.5).create_comparison_levels()) == 5

    def test_level_count_three_thresholds(self):
        # null + exact + 3 thresholds + any + else = 7
        assert (
            len(gcl.GeoOverlap("geometry", [0.9, 0.7, 0.5]).create_comparison_levels())
            == 7
        )

    def test_first_level_is_null(self):
        levels = gcl.GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[0], gcll.GeoNullLevel)

    def test_second_level_is_exact_overlap(self):
        levels = gcl.GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[1], gcll.GeoExactOverlapLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = gcl.GeoOverlap("geometry", [0.9, 0.5]).create_comparison_levels()
        assert isinstance(levels[2], gcll.GeoOverlapLevel)
        assert levels[2].threshold == 0.9
        assert isinstance(levels[3], gcll.GeoOverlapLevel)
        assert levels[3].threshold == 0.5

    def test_second_to_last_is_any_overlap(self):
        levels = gcl.GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[-2], gcll.GeoAnyOverlapLevel)

    def test_last_level_is_else_no_overlap(self):
        levels = gcl.GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "No overlap"


class TestGeoJaccard:
    def test_default_thresholds(self):
        assert gcl.GeoJaccard("geometry").thresholds == [0.9, 0.5]

    def test_single_threshold_normalised_to_list(self):
        assert gcl.GeoJaccard("geometry", 0.75).thresholds == [0.75]

    def test_output_column_name(self):
        assert gcl.GeoJaccard("my_geom").create_output_column_name() == "my_geom"

    def test_level_count_default(self):
        assert len(gcl.GeoJaccard("geometry").create_comparison_levels()) == 6

    def test_first_level_is_null(self):
        levels = gcl.GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[0], gcll.GeoNullLevel)

    def test_second_level_is_exact_overlap(self):
        levels = gcl.GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[1], gcll.GeoExactOverlapLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = gcl.GeoJaccard("geometry", [0.9, 0.5]).create_comparison_levels()
        assert isinstance(levels[2], gcll.GeoJaccardLevel)
        assert levels[2].threshold == 0.9
        assert isinstance(levels[3], gcll.GeoJaccardLevel)
        assert levels[3].threshold == 0.5

    def test_second_to_last_is_any_overlap(self):
        levels = gcl.GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[-2], gcll.GeoAnyOverlapLevel)

    def test_last_level_is_else_no_overlap(self):
        levels = gcl.GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "No overlap"


@pytest.mark.parametrize("cls", [gcl.GeoOverlap, gcl.GeoJaccard])
class TestBBoxPrefix:
    def test_defaults_to_inline(self, cls):
        assert cls("geometry").bbox_prefix is None
        levels = cls("geometry").create_comparison_levels()
        assert all(level.bbox_prefix is None for level in levels[1:-1])

    def test_passed_to_all_bbox_levels(self, cls):
        levels = cls("geometry", bbox_prefix="bbox").create_comparison_levels()
        # exact + thresholds + any overlap sit between the null and else levels
        assert len(levels[1:-1]) == 4
        assert all(level.bbox_prefix == "bbox" for level in levels[1:-1])

    @pytest.mark.parametrize("bad", ["", 5])
    def test_invalid_bbox_prefix_raises(self, cls, bad):
        with pytest.raises(TypeError, match="bbox_prefix"):
            cls("geometry", bbox_prefix=bad)


class TestGeoSizeRatio:
    def test_default_thresholds(self):
        assert gcl.GeoSizeRatio("geometry").thresholds == [0.5, 0.25]

    def test_single_threshold_normalised_to_list(self):
        assert gcl.GeoSizeRatio("geometry", 0.75).thresholds == [0.75]

    def test_output_column_name(self):
        assert gcl.GeoSizeRatio("my_geom").create_output_column_name() == "my_geom"

    def test_level_count_default(self):
        # null + exact_size + 2 thresholds + else = 5
        assert len(gcl.GeoSizeRatio("geometry").create_comparison_levels()) == 5

    def test_first_level_is_null(self):
        levels = gcl.GeoSizeRatio("geometry").create_comparison_levels()
        assert isinstance(levels[0], gcll.GeoNullLevel)

    def test_second_level_is_size_exact(self):
        levels = gcl.GeoSizeRatio("geometry").create_comparison_levels()
        assert isinstance(levels[1], gcll.GeoSizeExactLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = gcl.GeoSizeRatio("geometry", [0.5, 0.25]).create_comparison_levels()
        assert isinstance(levels[2], gcll.GeoSizeRatioLevel)
        assert levels[2].threshold == 0.5
        assert isinstance(levels[3], gcll.GeoSizeRatioLevel)
        assert levels[3].threshold == 0.25

    def test_no_any_overlap_level(self):
        levels = gcl.GeoSizeRatio("geometry").create_comparison_levels()
        assert not any(isinstance(l, gcll.GeoAnyOverlapLevel) for l in levels)

    def test_last_level_label_uses_lowest_threshold(self):
        levels = gcl.GeoSizeRatio("geometry", [0.5, 0.25]).create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "<25% size ratio"

    def test_last_level_label_single_threshold(self):
        levels = gcl.GeoSizeRatio("geometry", 0.75).create_comparison_levels()
        assert levels[-1].create_label_for_charts() == "<75% size ratio"


_PROJECTED = "EPSG:28992"  # RD New — projected, metres


class TestGeoDistance:
    def test_single_threshold_normalised_to_list(self):
        assert gcl.GeoDistance("geometry", 100, crs=_PROJECTED).thresholds == [100]

    def test_list_thresholds_preserved(self):
        assert gcl.GeoDistance("geometry", [100, 500], crs=_PROJECTED).thresholds == [
            100,
            500,
        ]

    def test_output_column_name(self):
        assert (
            gcl.GeoDistance("my_geom", 100, crs=_PROJECTED).create_output_column_name()
            == "my_geom"
        )

    def test_level_count_single_threshold(self):
        # null + exact + 1 threshold + else = 4
        assert (
            len(
                gcl.GeoDistance(
                    "geometry", 100, crs=_PROJECTED
                ).create_comparison_levels()
            )
            == 4
        )

    def test_level_count_two_thresholds(self):
        # null + exact + 2 thresholds + else = 5
        assert (
            len(
                gcl.GeoDistance(
                    "geometry", [100, 500], crs=_PROJECTED
                ).create_comparison_levels()
            )
            == 5
        )

    def test_first_level_is_null(self):
        levels = gcl.GeoDistance(
            "geometry", 100, crs=_PROJECTED
        ).create_comparison_levels()
        assert isinstance(levels[0], gcll.GeoNullLevel)

    def test_second_level_is_distance_exact(self):
        levels = gcl.GeoDistance(
            "geometry", 100, crs=_PROJECTED
        ).create_comparison_levels()
        assert isinstance(levels[1], gcll.GeoDistanceExactLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = gcl.GeoDistance(
            "geometry", [100, 500], crs=_PROJECTED
        ).create_comparison_levels()
        assert isinstance(levels[2], gcll.GeoDistanceLevel)
        assert levels[2].threshold == 100
        assert isinstance(levels[3], gcll.GeoDistanceLevel)
        assert levels[3].threshold == 500

    def test_no_any_overlap_level(self):
        levels = gcl.GeoDistance(
            "geometry", 100, crs=_PROJECTED
        ).create_comparison_levels()
        assert not any(isinstance(l, gcll.GeoAnyOverlapLevel) for l in levels)

    def test_last_level_label_with_known_crs(self):
        levels = gcl.GeoDistance(
            "geometry", [100, 500], crs=_PROJECTED
        ).create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "> 500 m distance"

    def test_last_level_label_no_crs_omits_unit(self):
        with pytest.warns(UserWarning):
            levels = gcl.GeoDistance("geometry", [100, 500]).create_comparison_levels()
        assert levels[-1].create_label_for_charts() == "> 500 distance"

    def test_use_centroid_passed_to_levels(self):
        levels = gcl.GeoDistance(
            "geometry", 100, use_centroid=True, crs=_PROJECTED
        ).create_comparison_levels()
        assert levels[1].use_centroid is True
        assert levels[2].use_centroid is True

    def test_use_centroid_false_by_default(self):
        levels = gcl.GeoDistance(
            "geometry", 100, crs=_PROJECTED
        ).create_comparison_levels()
        assert levels[1].use_centroid is False
        assert levels[2].use_centroid is False

    def test_unsupported_distance_type_raises(self):
        with pytest.raises(ValueError, match="distance_type"):
            gcl.GeoDistance("geometry", 100, distance_type="haversine", crs=_PROJECTED)

    def test_no_crs_warns(self):
        with pytest.warns(UserWarning, match="no CRS supplied"):
            gcl.GeoDistance("geometry", 100)

    def test_geographic_crs_propagates_to_levels(self):
        levels = gcl.GeoDistance(
            "geometry", 100, crs="EPSG:4326"
        ).create_comparison_levels()
        sql = levels[2].create_sql(None)
        assert "ST_Transform" in sql

    def test_projected_crs_no_transform_in_levels(self):
        levels = gcl.GeoDistance(
            "geometry", 100, crs=_PROJECTED
        ).create_comparison_levels()
        sql = levels[2].create_sql(None)
        assert "ST_Transform" not in sql


class _ComparatorValidationMixin:
    """Shared validation tests for ratio-threshold comparator classes."""

    cls = None
    threshold_arg = None  # keyword name for the threshold parameter

    def _make(self, col, threshold):
        return self.cls(col, **{self.threshold_arg: threshold})

    def test_empty_col_name_raises(self):
        with pytest.raises(TypeError, match="col_name"):
            self._make("", 0.5)

    def test_non_string_col_name_raises(self):
        with pytest.raises(TypeError, match="col_name"):
            self._make(None, 0.5)

    def test_empty_threshold_list_raises(self):
        with pytest.raises(ValueError):
            self._make("geometry", [])

    def test_threshold_out_of_range_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            self._make("geometry", 1.5)

    def test_threshold_zero_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            self._make("geometry", 0)

    def test_threshold_in_list_out_of_range_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            self._make("geometry", [0.9, 0.0])


class TestGeoOverlapValidation(_ComparatorValidationMixin):
    cls = gcl.GeoOverlap
    threshold_arg = "overlap_threshold_or_thresholds"


class TestGeoJaccardValidation(_ComparatorValidationMixin):
    cls = gcl.GeoJaccard
    threshold_arg = "score_threshold_or_thresholds"


class TestGeoSizeRatioValidation(_ComparatorValidationMixin):
    cls = gcl.GeoSizeRatio
    threshold_arg = "size_ratio_threshold_or_thresholds"


class TestGeoDistanceValidation:
    def test_empty_col_name_raises(self):
        with pytest.raises(TypeError, match="col_name"):
            gcl.GeoDistance("", 100)

    def test_empty_threshold_list_raises(self):
        with pytest.raises(ValueError):
            gcl.GeoDistance("geometry", [])

    def test_threshold_zero_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            gcl.GeoDistance("geometry", 0)

    def test_threshold_negative_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            gcl.GeoDistance("geometry", -50)

    def test_threshold_in_list_negative_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            gcl.GeoDistance("geometry", [100, -1])

    def test_use_centroid_non_bool_raises(self):
        with pytest.raises(TypeError, match="use_centroid"):
            gcl.GeoDistance("geometry", 100, use_centroid=1, crs=_PROJECTED)

    def test_thresholds_coerced_to_float(self):
        comp = gcl.GeoDistance("geometry", 100, crs=_PROJECTED)
        assert all(type(t) is float for t in comp.thresholds)

    def test_ascending_order_warning(self):
        with pytest.warns(UserWarning, match="ascending"):
            gcl.GeoDistance("geometry", [500, 100], crs=_PROJECTED)

    def test_correct_ascending_order_no_warning(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            gcl.GeoDistance("geometry", [100, 500], crs=_PROJECTED)


class TestThresholdOrderingWarnings:
    """Out-of-order thresholds emit a UserWarning at construction time."""

    def test_overlap_descending_no_warning(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            gcl.GeoOverlap("geometry", [0.9, 0.5])

    def test_overlap_ascending_warns(self):
        with pytest.warns(UserWarning, match="descending"):
            gcl.GeoOverlap("geometry", [0.5, 0.9])

    def test_jaccard_ascending_warns(self):
        with pytest.warns(UserWarning, match="descending"):
            gcl.GeoJaccard("geometry", [0.3, 0.8])

    def test_size_ratio_ascending_warns(self):
        with pytest.warns(UserWarning, match="descending"):
            gcl.GeoSizeRatio("geometry", [0.25, 0.5])

    def test_thresholds_coerced_to_float_overlap(self):
        comp = gcl.GeoOverlap("geometry", [0.9, 0.5])
        assert all(type(t) is float for t in comp.thresholds)

    def test_thresholds_coerced_to_float_jaccard(self):
        comp = gcl.GeoJaccard("geometry", [0.9, 0.5])
        assert all(type(t) is float for t in comp.thresholds)

    def test_thresholds_coerced_to_float_size_ratio(self):
        comp = gcl.GeoSizeRatio("geometry", [0.5, 0.25])
        assert all(type(t) is float for t in comp.thresholds)
