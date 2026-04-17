import pytest
from splink.internals.comparison_level_library import CustomLevel

from geosplink import GeoJaccard, GeoOverlap, GeoSizeRatio
from geosplink.geo_comparison_level_library import (
    GeoAnyOverlapLevel,
    GeoExactOverlapLevel,
    GeoJaccardLevel,
    GeoNullLevel,
    GeoOverlapLevel,
    GeoSizeExactLevel,
    GeoSizeRatioLevel,
)


class TestGeoOverlap:
    def test_default_thresholds(self):
        assert GeoOverlap("geometry").thresholds == [0.9, 0.5]

    def test_single_threshold_normalised_to_list(self):
        assert GeoOverlap("geometry", 0.75).thresholds == [0.75]

    def test_list_thresholds_preserved(self):
        assert GeoOverlap("geometry", [0.8, 0.6, 0.3]).thresholds == [0.8, 0.6, 0.3]

    def test_output_column_name(self):
        assert GeoOverlap("my_geom").create_output_column_name() == "my_geom"

    def test_level_count_default(self):
        # null + exact + 2 thresholds + any + else = 6
        assert len(GeoOverlap("geometry").create_comparison_levels()) == 6

    def test_level_count_single_threshold(self):
        # null + exact + 1 threshold + any + else = 5
        assert len(GeoOverlap("geometry", 0.5).create_comparison_levels()) == 5

    def test_level_count_three_thresholds(self):
        # null + exact + 3 thresholds + any + else = 7
        assert (
            len(GeoOverlap("geometry", [0.9, 0.7, 0.5]).create_comparison_levels()) == 7
        )

    def test_first_level_is_null(self):
        levels = GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[0], GeoNullLevel)

    def test_second_level_is_exact_overlap(self):
        levels = GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[1], GeoExactOverlapLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = GeoOverlap("geometry", [0.9, 0.5]).create_comparison_levels()
        assert isinstance(levels[2], GeoOverlapLevel)
        assert levels[2].threshold == 0.9
        assert isinstance(levels[3], GeoOverlapLevel)
        assert levels[3].threshold == 0.5

    def test_second_to_last_is_any_overlap(self):
        levels = GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[-2], GeoAnyOverlapLevel)

    def test_last_level_is_else_no_overlap(self):
        levels = GeoOverlap("geometry").create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "No overlap"


class TestGeoJaccard:
    def test_default_thresholds(self):
        assert GeoJaccard("geometry").thresholds == [0.9, 0.5]

    def test_single_threshold_normalised_to_list(self):
        assert GeoJaccard("geometry", 0.75).thresholds == [0.75]

    def test_output_column_name(self):
        assert GeoJaccard("my_geom").create_output_column_name() == "my_geom"

    def test_level_count_default(self):
        assert len(GeoJaccard("geometry").create_comparison_levels()) == 6

    def test_first_level_is_null(self):
        levels = GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[0], GeoNullLevel)

    def test_second_level_is_exact_overlap(self):
        levels = GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[1], GeoExactOverlapLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = GeoJaccard("geometry", [0.9, 0.5]).create_comparison_levels()
        assert isinstance(levels[2], GeoJaccardLevel)
        assert levels[2].threshold == 0.9
        assert isinstance(levels[3], GeoJaccardLevel)
        assert levels[3].threshold == 0.5

    def test_second_to_last_is_any_overlap(self):
        levels = GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[-2], GeoAnyOverlapLevel)

    def test_last_level_is_else_no_overlap(self):
        levels = GeoJaccard("geometry").create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "No overlap"


class TestGeoSizeRatio:
    def test_default_thresholds(self):
        assert GeoSizeRatio("geometry").thresholds == [0.5, 0.25]

    def test_single_threshold_normalised_to_list(self):
        assert GeoSizeRatio("geometry", 0.75).thresholds == [0.75]

    def test_output_column_name(self):
        assert GeoSizeRatio("my_geom").create_output_column_name() == "my_geom"

    def test_level_count_default(self):
        # null + exact_size + 2 thresholds + else = 5
        assert len(GeoSizeRatio("geometry").create_comparison_levels()) == 5

    def test_first_level_is_null(self):
        levels = GeoSizeRatio("geometry").create_comparison_levels()
        assert isinstance(levels[0], GeoNullLevel)

    def test_second_level_is_size_exact(self):
        levels = GeoSizeRatio("geometry").create_comparison_levels()
        assert isinstance(levels[1], GeoSizeExactLevel)

    def test_threshold_levels_correct_type_and_value(self):
        levels = GeoSizeRatio("geometry", [0.5, 0.25]).create_comparison_levels()
        assert isinstance(levels[2], GeoSizeRatioLevel)
        assert levels[2].threshold == 0.5
        assert isinstance(levels[3], GeoSizeRatioLevel)
        assert levels[3].threshold == 0.25

    def test_no_any_overlap_level(self):
        levels = GeoSizeRatio("geometry").create_comparison_levels()
        assert not any(isinstance(l, GeoAnyOverlapLevel) for l in levels)

    def test_last_level_label_uses_lowest_threshold(self):
        levels = GeoSizeRatio("geometry", [0.5, 0.25]).create_comparison_levels()
        assert isinstance(levels[-1], CustomLevel)
        assert levels[-1].create_label_for_charts() == "<25% size ratio"

    def test_last_level_label_single_threshold(self):
        levels = GeoSizeRatio("geometry", 0.75).create_comparison_levels()
        assert levels[-1].create_label_for_charts() == "<75% size ratio"
