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


class TestGeoDistance:
    def test_single_threshold_normalised_to_list(self):
        assert gcl.GeoDistance("geometry", 100).thresholds == [100]

    def test_list_thresholds_preserved(self):
        assert gcl.GeoDistance("geometry", [100, 500]).thresholds == [100, 500]

    def test_output_column_name(self):
        assert gcl.GeoDistance("my_geom", 100).create_output_column_name() == "my_geom"

    def test_level_count_single_threshold(self):
        # null + exact + 1 threshold + else = 4
        assert len(gcl.GeoDistance("geometry", 100).create_comparison_levels()) == 4

    def test_level_count_two_thresholds(self):
        # null + exact + 2 thresholds + else = 5
        assert (
            len(gcl.GeoDistance("geometry", [100, 500]).create_comparison_levels()) == 5
        )

    def test_first_level_is_null(self):
        levels = gcl.GeoDistance("geometry", 100).create_comparison_levels()
        assert isinstance(levels[0], gcll.GeoNullLevel)

    def test_second_level_is_distance_exact(self):
        levels = gcl.GeoDistance("geometry", 100).create_comparison_levels()
        assert isinstance(levels[1], gcll.GeoDistanceExactLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = gcl.GeoDistance("geometry", [100, 500]).create_comparison_levels()
        assert isinstance(levels[2], gcll.GeoDistanceLevel)
        assert levels[2].threshold == 100
        assert isinstance(levels[3], gcll.GeoDistanceLevel)
        assert levels[3].threshold == 500

    def test_no_any_overlap_level(self):
        levels = gcl.GeoDistance("geometry", 100).create_comparison_levels()
        assert not any(isinstance(l, gcll.GeoAnyOverlapLevel) for l in levels)

    def test_last_level_label_uses_highest_threshold(self):
        levels = gcl.GeoDistance("geometry", [100, 500]).create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "> 500 distance"

    def test_use_centroid_passed_to_levels(self):
        levels = gcl.GeoDistance(
            "geometry", 100, use_centroid=True
        ).create_comparison_levels()
        assert levels[1].use_centroid is True
        assert levels[2].use_centroid is True

    def test_use_centroid_false_by_default(self):
        levels = gcl.GeoDistance("geometry", 100).create_comparison_levels()
        assert levels[1].use_centroid is False
        assert levels[2].use_centroid is False

    def test_unsupported_distance_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported distance type"):
            gcl.GeoDistance(
                "geometry", 100, distance_type="haversine"
            ).create_comparison_levels()
