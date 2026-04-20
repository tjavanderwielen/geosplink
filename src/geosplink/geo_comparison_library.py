"""
Geospatial comparator classes for use with Splink record linkage.
Mirrors the structure of splink.internals.comparison_library.

Each class is a ComparisonCreator that composes levels from
geo_comparison_level_library into a full comparison.

Note:
    u-probabilities for overlap/Jaccard levels will likely require manual
    configuration via .configure() — random sampling produces near-zero
    observations for non-matching geometry pairs.
"""

from __future__ import annotations

from typing import Iterable, List, Literal, Optional, Union

from splink.internals.column_expression import ColumnExpression
from splink.internals.comparison_creator import ComparisonCreator
from splink.internals.comparison_level_creator import ComparisonLevelCreator
from splink.internals.comparison_level_library import CustomLevel
from splink.internals.dialects import SplinkDialect
from splink.internals.misc import ensure_is_iterable

import geosplink.geo_comparison_level_library as gcll


class GeoOverlap(ComparisonCreator):
    def __init__(
        self,
        col_name: str,
        overlap_threshold_or_thresholds: Union[float, List[float]] = [0.9, 0.5],
    ):
        """
        Represents a comparison based on the geometric overlap of two geometries
        at three or more levels:

        - Exact overlap of geometries
        - Overlapping area at specified thresholds (e.g. >=90%, >=50%)
        - ...
        - Any overlap
        - Anything else

        For example, with overlap_threshold_or_thresholds = [0.9, 0.5] the levels are:

        - Exact overlap of geometries
        - Area overlap of geometries >= 90%
        - Area overlap of geometries >= 50%
        - Any overlap
        - Anything else

        The overlap metric is the overlap coefficient: intersection area / min(area_l, area_r).
        This is asymmetric — a small geometry fully inside a large one scores 100%.
        For a symmetric metric, use GeoJaccard instead.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            overlap_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for area overlap levels.
                Defaults to [0.9, 0.5] for >=90% and >=50% overlap levels.

        Note:
            Requires bounding box columns in the data: bbox_minx, bbox_miny, bbox_maxx,
            bbox_maxy (Splink will expect _l/_r suffixed versions in comparisons).
        """
        thresholds_as_iterable = ensure_is_iterable(overlap_threshold_or_thresholds)
        self.thresholds = [*thresholds_as_iterable]
        self._col_name = col_name
        super().__init__(col_name)

    def create_comparison_levels(self) -> List[ComparisonLevelCreator]:
        return [
            gcll.GeoNullLevel(self._col_name),
            gcll.GeoExactOverlapLevel(self._col_name),
            *[gcll.GeoOverlapLevel(self._col_name, t) for t in self.thresholds],
            gcll.GeoAnyOverlapLevel(self._col_name),
            CustomLevel("ELSE", label_for_charts="No overlap"),
        ]

    def create_output_column_name(self) -> str:
        return self._col_name


class GeoJaccard(ComparisonCreator):
    def __init__(
        self,
        col_name: str,
        score_threshold_or_thresholds: Union[float, List[float]] = [0.9, 0.5],
    ):
        """
        Represents a comparison based on the Jaccard similarity (IoU) of two geometries
        at three or more levels:

        - Exact overlap of geometries
        - Jaccard similarity at specified thresholds (e.g. >=90%, >=50%)
        - ...
        - Any overlap
        - Anything else

        For example, with score_threshold_or_thresholds = [0.9, 0.5] the levels are:

        - Exact overlap of geometries
        - Jaccard similarity of geometries >= 90%
        - Jaccard similarity of geometries >= 50%
        - Any overlap
        - Anything else

        The Jaccard metric is symmetric: intersection area / union area.
        For an asymmetric metric (useful when geometries differ in scale),
        use GeoOverlap instead.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            score_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for Jaccard similarity levels.
                Defaults to [0.9, 0.5] for >=90% and >=50% similarity levels.

        Note:
            Requires bounding box columns in the data: bbox_minx, bbox_miny, bbox_maxx,
            bbox_maxy (Splink will expect _l/_r suffixed versions in comparisons).
        """
        thresholds_as_iterable = ensure_is_iterable(score_threshold_or_thresholds)
        self.thresholds = [*thresholds_as_iterable]
        self._col_name = col_name
        super().__init__(col_name)

    def create_comparison_levels(self) -> List[ComparisonLevelCreator]:
        return [
            gcll.GeoNullLevel(self._col_name),
            gcll.GeoExactOverlapLevel(self._col_name),
            *[gcll.GeoJaccardLevel(self._col_name, t) for t in self.thresholds],
            gcll.GeoAnyOverlapLevel(self._col_name),
            CustomLevel("ELSE", label_for_charts="No overlap"),
        ]

    def create_output_column_name(self) -> str:
        return self._col_name


class GeoSizeRatio(ComparisonCreator):
    def __init__(
        self,
        col_name: str,
        size_ratio_threshold_or_thresholds: Union[float, List[float]] = [0.5, 0.25],
    ):
        """
        Represents a comparison based on the size ratio (smallest / largest area)
        of two geometries at three or more levels:

        - Exact match in size of geometries
        - Size ratio at specified thresholds (e.g. >=50%, >=25%)
        - ...
        - Anything else

        For example, with size_ratio_threshold_or_thresholds = [0.75, 0.5, 0.25] the levels are:

        - Exact match in size of geometries
        - Size ratio of geometries >= 75%
        - Size ratio of geometries >= 50%
        - Size ratio of geometries >= 25%
        - Anything else

        Note:
            The exact size match level uses floating point equality on ST_Area,
            which will rarely match in practice. Consider dropping it if unused.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            size_ratio_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for size ratio levels.
                Defaults to [0.5, 0.25] for >=50% and >=25% size ratio levels.
        """
        thresholds_as_iterable = ensure_is_iterable(size_ratio_threshold_or_thresholds)
        self.thresholds = [*thresholds_as_iterable]
        self._col_name = col_name
        super().__init__(col_name)

    def create_comparison_levels(self) -> List[ComparisonLevelCreator]:
        return [
            gcll.GeoNullLevel(self._col_name),
            gcll.GeoSizeExactLevel(self._col_name),
            *[gcll.GeoSizeRatioLevel(self._col_name, t) for t in self.thresholds],
            CustomLevel(
                "ELSE",
                label_for_charts=f"<{int(self.thresholds[-1] * 100)}% size ratio",
            ),
        ]

    def create_output_column_name(self) -> str:
        return self._col_name


class GeoDistance(ComparisonCreator):
    def __init__(
        self,
        col_name: str,
        distance_threshold_or_thresholds: Union[float, List[float]],
        distance_type: Literal["euclidean"] = "euclidean",
        use_centroid: bool = False,
    ):
        """
        Represents a comparison based on the distance between two geometries
        at three or more levels:

        - Exact match in location of geometries
        - Distance at specified thresholds (e.g. <=100m, <=500m)
        - ...
        - Anything else

        For example, with distance_threshold_or_thresholds = [100, 500] the levels are:

        - Exact match in location of geometries
        - Distance between geometries <= 100 meters
        - Distance between geometries <= 500 meters
        - Anything else

        Notes:
        - This comparator assumes geometries are in a projected coordinate system
          with units in meters. If using geographic coordinates (lat/lon), consider
          using a geodesic distance function or reprojecting to an appropriate CRS.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            distance_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for distance levels.
                No default provided as appropriate thresholds depend on the use case.
            distance_type (Literal["euclidean"]):
                Which distance type to compute out of: "euclidean" (default)
                    — currently only euclidean distance is supported.
            use_centroid (bool): Whether to compute distance between geometry centroids
                instead of between geometries themselves. Defaults to False.
        """
        thresholds_as_iterable = ensure_is_iterable(distance_threshold_or_thresholds)
        self.thresholds = [*thresholds_as_iterable]
        self._col_name = col_name
        self.distance_type = distance_type
        self.use_centroid = use_centroid
        super().__init__(col_name)

    def create_comparison_levels(self) -> List[ComparisonLevelCreator]:
        if self.distance_type == "euclidean":
            return [
                gcll.GeoNullLevel(self._col_name),
                gcll.GeoDistanceExactLevel(
                    self._col_name, use_centroid=self.use_centroid
                ),
                *[
                    gcll.GeoDistanceLevel(
                        self._col_name, t, use_centroid=self.use_centroid
                    )
                    for t in self.thresholds
                ],
                CustomLevel(
                    "ELSE",
                    label_for_charts=f"> {self.thresholds[-1]} distance",
                ),
            ]
        else:
            raise ValueError(f"Unsupported distance type: {self.distance_type}")

    def create_output_column_name(self) -> str:
        return self._col_name
