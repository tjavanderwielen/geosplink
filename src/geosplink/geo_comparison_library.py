"""
Geospatial comparator classes for use with Splink record linkage.
Mirrors the structure of splink.internals.comparison_library.

Each class is a ComparisonCreator that composes levels from
geo_comparison_level_library into a full comparison.
"""

from __future__ import annotations

from typing import Iterable, List, Literal, Optional, Union

from splink.internals.column_expression import ColumnExpression
from splink.internals.comparison_creator import ComparisonCreator
from splink.internals.comparison_level_creator import ComparisonLevelCreator
from splink.internals.comparison_level_library import CustomLevel
from splink.internals.dialects import SplinkDialect
from splink.internals.misc import ensure_is_iterable

from geosplink.crs import resolve_crs
import geosplink.geo_comparison_level_library as gcll
from geosplink.geo_comparison_level_library import (
    _check_col_name,
    _check_ratio_threshold,
    _check_distance_threshold,
    _check_use_centroid,
    _warn_thresholds_descending,
    _warn_thresholds_ascending,
)


class GeoOverlap(ComparisonCreator):
    def __init__(
        self,
        col_name: str,
        overlap_threshold_or_thresholds: Union[float, List[float]] = [0.9, 0.5],
    ):
        """
        Represents a comparison based on the geometric overlap of two geometries
        at three or more levels.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            overlap_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for area overlap levels.
                Defaults to [0.9, 0.5] for >=90% and >=50% overlap levels.
        """
        _check_col_name(col_name, "GeoOverlap")
        thresholds_as_iterable = ensure_is_iterable(overlap_threshold_or_thresholds)
        self.thresholds = [
            _check_ratio_threshold(t, "GeoOverlap") for t in thresholds_as_iterable
        ]
        if not self.thresholds:
            raise ValueError("GeoOverlap: at least one threshold is required")
        _warn_thresholds_descending(self.thresholds, "GeoOverlap")
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

    def create_description(self) -> str:
        thresholds_str = ", ".join(f"{int(t * 100)}%" for t in self.thresholds)
        plural = "s" if len(self.thresholds) > 1 else ""
        return (
            f"Exact overlap '{self._col_name}' vs. "
            f"overlap coefficient at threshold{plural} {thresholds_str} vs. "
            "any overlap vs. anything else"
        )

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
        at three or more levels.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            score_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for Jaccard similarity levels.
                Defaults to [0.9, 0.5] for >=90% and >=50% similarity levels.
        """
        _check_col_name(col_name, "GeoJaccard")
        thresholds_as_iterable = ensure_is_iterable(score_threshold_or_thresholds)
        self.thresholds = [
            _check_ratio_threshold(t, "GeoJaccard") for t in thresholds_as_iterable
        ]
        if not self.thresholds:
            raise ValueError("GeoJaccard: at least one threshold is required")
        _warn_thresholds_descending(self.thresholds, "GeoJaccard")
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

    def create_description(self) -> str:
        thresholds_str = ", ".join(f"{int(t * 100)}%" for t in self.thresholds)
        plural = "s" if len(self.thresholds) > 1 else ""
        return (
            f"Exact overlap '{self._col_name}' vs. "
            f"Jaccard similarity at threshold{plural} {thresholds_str} vs. "
            "any overlap vs. anything else"
        )

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
        of two geometries at three or more levels

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            size_ratio_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for size ratio levels.
                Defaults to [0.5, 0.25] for >=50% and >=25% size ratio levels.
        """
        _check_col_name(col_name, "GeoSizeRatio")
        thresholds_as_iterable = ensure_is_iterable(size_ratio_threshold_or_thresholds)
        self.thresholds = [
            _check_ratio_threshold(t, "GeoSizeRatio") for t in thresholds_as_iterable
        ]
        if not self.thresholds:
            raise ValueError("GeoSizeRatio: at least one threshold is required")
        _warn_thresholds_descending(self.thresholds, "GeoSizeRatio")
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

    def create_description(self) -> str:
        thresholds_str = ", ".join(f"{int(t * 100)}%" for t in self.thresholds)
        plural = "s" if len(self.thresholds) > 1 else ""
        return (
            f"Exact size match '{self._col_name}' vs. "
            f"size ratio at threshold{plural} {thresholds_str} vs. "
            "anything else"
        )

    def create_output_column_name(self) -> str:
        return self._col_name


class GeoDistance(ComparisonCreator):
    def __init__(
        self,
        col_name: str,
        distance_threshold_or_thresholds: Union[float, List[float]],
        distance_type: Literal["euclidean"] = "euclidean",
        use_centroid: bool = False,
        crs=None,
    ):
        """
        Represents a comparison based on the distance between two geometries
        at three or more levels.

        Args:
            col_name (str): The name of the column containing WKT geometry strings.
                Splink will look for {col_name}_l and {col_name}_r in the comparison table.
            distance_threshold_or_thresholds (Union[float, List[float]]):
                A single threshold or list of thresholds for distance levels.
            distance_type (Literal["euclidean"]):
                Distance function to use. Currently only supports ``"euclidean"``.
            use_centroid (bool): Calculate centroid-to-centroid distance over edge-to-edge.
                Defaults to False.
            crs: EPSG code of the geometry column's CRS. Both datasets must share the same CRS.
        """
        _check_col_name(col_name, "GeoDistance")
        if distance_type != "euclidean":
            raise ValueError(
                f"GeoDistance: unsupported distance_type {distance_type!r}, must be 'euclidean'"
            )
        _check_use_centroid(use_centroid, "GeoDistance")
        thresholds_as_iterable = ensure_is_iterable(distance_threshold_or_thresholds)
        self.thresholds = [
            _check_distance_threshold(t, "GeoDistance") for t in thresholds_as_iterable
        ]
        if not self.thresholds:
            raise ValueError("GeoDistance: at least one threshold is required")
        _warn_thresholds_ascending(self.thresholds, "GeoDistance")
        self._col_name = col_name
        self.distance_type = distance_type
        self.use_centroid = use_centroid

        self._epsg, self._crs_type = resolve_crs(crs, context="GeoDistance")

        super().__init__(col_name)

    def create_comparison_levels(self) -> List[ComparisonLevelCreator]:
        unit = " m" if self._crs_type in ("geographic", "projected") else ""
        return [
            gcll.GeoNullLevel(self._col_name),
            gcll.GeoDistanceExactLevel(
                self._col_name,
                use_centroid=self.use_centroid,
            ),
            *[
                gcll.GeoDistanceLevel(
                    self._col_name,
                    t,
                    use_centroid=self.use_centroid,
                    _epsg=self._epsg,
                    _crs_type=self._crs_type,
                    _pre_resolved=True,
                )
                for t in self.thresholds
            ],
            CustomLevel(
                "ELSE",
                label_for_charts=f"> {self.thresholds[-1]:g}{unit} distance",
            ),
        ]

    def create_description(self) -> str:
        unit = " m" if self._crs_type in ("geographic", "projected") else ""
        thresholds_str = ", ".join(f"{t:g}{unit}" for t in self.thresholds)
        plural = "s" if len(self.thresholds) > 1 else ""
        exact_label = (
            "Exact centroid match" if self.use_centroid else "Exact location match"
        )
        distance_label = "Centroid distance" if self.use_centroid else "Distance"
        return (
            f"{exact_label} '{self._col_name}' vs. "
            f"{distance_label} at threshold{plural} {thresholds_str} vs. "
            "anything else"
        )

    def create_output_column_name(self) -> str:
        return self._col_name
