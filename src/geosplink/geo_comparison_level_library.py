"""
Geospatial comparison level classes for use with Splink record linkage.
Mirrors the structure of splink.internals.comparison_level_library.

Each class is a ComparisonLevelCreator subclass that generates SQL for a single
comparison level. These can be used directly in CustomComparison or composed
into full comparators via geo_comparison_library.py.

CRS sensitivity:
    Only distance-based levels (GeoDistanceLevel, GeoDistanceExactLevel) are
    sensitive to the coordinate reference system. All other levels — overlap,
    Jaccard, size ratio — use ratios of areas, so the units cancel and results
    are identical regardless of CRS.

Note:
    All SQL targets DuckDB spatial functions (ST_*, BBOX_OVERLAP, etc.).
    Dialect translation is not yet implemented.
"""

from __future__ import annotations

import warnings
from typing import List, Optional, Union

from splink.internals.column_expression import ColumnExpression
from splink.internals.comparison_level_creator import ComparisonLevelCreator
from splink.internals.dialects import SplinkDialect

from geosplink.crs import CRSInput, resolve_crs


def _check_col_name(col_name: str, cls_name: str) -> None:
    if not isinstance(col_name, str) or not col_name.strip():
        raise TypeError(
            f"{cls_name}: col_name must be a non-empty string, got {col_name!r}"
        )


def _check_ratio_threshold(threshold: float, cls_name: str) -> float:
    """Validate and return threshold as a float in (0, 1)."""
    try:
        t = float(threshold)
    except (TypeError, ValueError):
        raise TypeError(
            f"{cls_name}: threshold must be a number, got {threshold!r}"
        ) from None
    if not (0 < t < 1):
        raise ValueError(f"{cls_name}: threshold must be in (0, 1), got {t}")
    return t


def _check_distance_threshold(threshold: float, cls_name: str) -> float:
    """Validate and return threshold as a float > 0."""
    try:
        t = float(threshold)
    except (TypeError, ValueError):
        raise TypeError(
            f"{cls_name}: threshold must be a number, got {threshold!r}"
        ) from None
    if t <= 0:
        raise ValueError(f"{cls_name}: distance threshold must be > 0, got {t}")
    return t


def _check_use_centroid(use_centroid: bool, cls_name: str) -> None:
    if not isinstance(use_centroid, bool):
        raise TypeError(
            f"{cls_name}: use_centroid must be a bool, got {use_centroid!r}"
        )


def _warn_thresholds_descending(thresholds: List[float], cls_name: str) -> None:
    """Warn if ratio thresholds are not in descending order."""
    for i in range(len(thresholds) - 1):
        if thresholds[i] < thresholds[i + 1]:
            warnings.warn(
                f"{cls_name}: thresholds should be in descending order so that "
                f"stricter levels are evaluated first (got {thresholds}). "
                "A threshold at position i+1 that is larger than position i "
                "can never be reached.",
                UserWarning,
                stacklevel=3,
            )
            break


def _warn_thresholds_ascending(thresholds: List[float], cls_name: str) -> None:
    """Warn if distance thresholds are not in ascending order."""
    for i in range(len(thresholds) - 1):
        if thresholds[i] > thresholds[i + 1]:
            warnings.warn(
                f"{cls_name}: distance thresholds should be in ascending order so "
                f"that stricter levels are evaluated first (got {thresholds}). "
                "A threshold at position i+1 that is smaller than position i "
                "can never be reached.",
                UserWarning,
                stacklevel=3,
            )
            break


def _geom_expr(
    col: str, use_centroid: bool, epsg: Optional[int], crs_type: Optional[str]
) -> str:
    """Build a DuckDB SQL geometry expression, applying centroid and/or ST_Transform as needed."""
    expr = f"ST_GeomFromText({col})"
    if use_centroid:
        expr = f"ST_Centroid({expr})"
    if crs_type == "geographic":
        expr = f"ST_Transform({expr}, {epsg}, 3857)"
    return expr


# Helper: bounding box overlap check
_BBOX_OVERLAP = (
    "NOT (bbox_maxx_l < bbox_minx_r OR bbox_minx_l > bbox_maxx_r OR "
    "bbox_maxy_l < bbox_miny_r OR bbox_miny_l > bbox_maxy_r)"
)


class GeoNullLevel(ComparisonLevelCreator):
    """
    Comparison level for missing geometry data.
    Matches any pair where either or both geometry columns are NULL.

    Args:
        col_name (str): Name of the WKT geometry column.
    """

    def __init__(self, col_name: str):
        _check_col_name(col_name, "GeoNullLevel")
        self._col_name = col_name
        self.is_null_level = True

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        col = self._col_name
        # NULL is checked first so a NULL + invalid pair still routes to the null level.
        # Empty and invalid (non-NULL) geometries raise a hard error rather than silently
        # producing incorrect spatial metrics.
        return (
            f"CASE WHEN {l} IS NULL OR {r} IS NULL THEN TRUE "
            f"WHEN ST_IsEmpty(ST_GeomFromText({l})) "
            f"THEN error('geosplink: empty geometry in {col}_l') "
            f"WHEN ST_IsEmpty(ST_GeomFromText({r})) "
            f"THEN error('geosplink: empty geometry in {col}_r') "
            f"WHEN NOT ST_IsValid(ST_GeomFromText({l})) "
            f"THEN error('geosplink: invalid geometry in {col}_l') "
            f"WHEN NOT ST_IsValid(ST_GeomFromText({r})) "
            f"THEN error('geosplink: invalid geometry in {col}_r') "
            f"ELSE FALSE END"
        )

    def create_label_for_charts(self) -> str:
        return "Null"


class GeoExactOverlapLevel(ComparisonLevelCreator):
    """
    Comparison level for geometrically identical geometries (ST_Equals).
    Uses a bounding box pre-filter for performance.

    Args:
        col_name (str): Name of the WKT geometry column.
    """

    def __init__(self, col_name: str):
        _check_col_name(col_name, "GeoExactOverlapLevel")
        self._col_name = col_name

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        return f"""
            {_BBOX_OVERLAP} AND
            ST_Equals(
                ST_GeomFromText({l}),
                ST_GeomFromText({r})
            )
        """

    def create_label_for_charts(self) -> str:
        return "Exact overlap"


class GeoAnyOverlapLevel(ComparisonLevelCreator):
    """
    Comparison level for any spatial intersection (ST_Intersects).

    Args:
        col_name (str): Name of the WKT geometry column.
    """

    def __init__(self, col_name: str):
        _check_col_name(col_name, "GeoAnyOverlapLevel")
        self._col_name = col_name

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        return f"""
            {_BBOX_OVERLAP} AND
            ST_Intersects(
                ST_GeomFromText({l}),
                ST_GeomFromText({r})
            )
        """

    def create_label_for_charts(self) -> str:
        return "Any overlap"


class GeoOverlapLevel(ComparisonLevelCreator):
    """
    Comparison level for overlap coefficient (intersection / min area) at a threshold.

    Args:
        col_name (str): Name of the WKT geometry column.
        threshold (float): Minimum overlap coefficient (0-1).
    """

    def __init__(self, col_name: str, threshold: float):
        _check_col_name(col_name, "GeoOverlapLevel")
        self._col_name = col_name
        self.threshold = _check_ratio_threshold(threshold, "GeoOverlapLevel")

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        return f"""
            {_BBOX_OVERLAP} AND
            ST_Area(
                ST_Intersection(
                    ST_GeomFromText({l}),
                    ST_GeomFromText({r})
                )
            ) / NULLIF(
                LEAST(
                    ST_Area(ST_GeomFromText({l})),
                    ST_Area(ST_GeomFromText({r}))
                ),
                0
            ) >= {self.threshold}
        """

    def create_label_for_charts(self) -> str:
        return f">={int(self.threshold * 100)}% overlap"


class GeoJaccardLevel(ComparisonLevelCreator):
    """
    Comparison level for Jaccard similarity (intersection / union area) at a threshold.
    Uses a bounding box pre-filter for performance.

    Args:
        col_name (str): Name of the WKT geometry column.
        threshold (float): Minimum Jaccard similarity (0-1).
    """

    def __init__(self, col_name: str, threshold: float):
        _check_col_name(col_name, "GeoJaccardLevel")
        self._col_name = col_name
        self.threshold = _check_ratio_threshold(threshold, "GeoJaccardLevel")

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        return f"""
            {_BBOX_OVERLAP} AND
            ST_Area(
                ST_Intersection(
                    ST_GeomFromText({l}),
                    ST_GeomFromText({r})
                )
            ) / NULLIF(
                ST_Area(
                    ST_Union(
                        ST_GeomFromText({l}),
                        ST_GeomFromText({r})
                    )
                ),
                0
            ) >= {self.threshold}
        """

    def create_label_for_charts(self) -> str:
        return f">={int(self.threshold * 100)}% Jaccard similarity"


class GeoSizeExactLevel(ComparisonLevelCreator):
    """
    Comparison level for geometries with equal area.

    Args:
        col_name (str): Name of the WKT geometry column.
    """

    def __init__(self, col_name: str):
        _check_col_name(col_name, "GeoSizeExactLevel")
        self._col_name = col_name

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        return f"ST_Area(ST_GeomFromText({l})) = ST_Area(ST_GeomFromText({r}))"

    def create_label_for_charts(self) -> str:
        return "Exact size match"


class GeoSizeRatioLevel(ComparisonLevelCreator):
    """
    Comparison level for size ratio (smallest / largest area) at a threshold.

    Args:
        col_name (str): Name of the WKT geometry column.
        threshold (float): Minimum size ratio (0-1).
    """

    def __init__(self, col_name: str, threshold: float):
        _check_col_name(col_name, "GeoSizeRatioLevel")
        self._col_name = col_name
        self.threshold = _check_ratio_threshold(threshold, "GeoSizeRatioLevel")

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        return f"""
            LEAST(
                ST_Area(ST_GeomFromText({l})),
                ST_Area(ST_GeomFromText({r}))
            ) / NULLIF(
                GREATEST(
                    ST_Area(ST_GeomFromText({l})),
                    ST_Area(ST_GeomFromText({r}))
                ),
                0
            ) >= {self.threshold}
        """

    def create_label_for_charts(self) -> str:
        return f">={int(self.threshold * 100)}% size ratio"


class GeoDistanceExactLevel(ComparisonLevelCreator):
    """
    Comparison level for geometries at exactly the same location (distance = 0).

    Args:
        col_name (str): Name of the WKT geometry column.
        use_centroid (bool): If True, compare centroids instead edge-to-edge.
    """

    def __init__(self, col_name: str, use_centroid: bool = False):
        _check_col_name(col_name, "GeoDistanceExactLevel")
        _check_use_centroid(use_centroid, "GeoDistanceExactLevel")
        self._col_name = col_name
        self.use_centroid = use_centroid

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        if self.use_centroid:
            geom_l = f"ST_Centroid(ST_GeomFromText({l}))"
            geom_r = f"ST_Centroid(ST_GeomFromText({r}))"
        else:
            geom_l = f"ST_GeomFromText({l})"
            geom_r = f"ST_GeomFromText({r})"
        return f"ST_Distance({geom_l}, {geom_r}) = 0"

    def create_label_for_charts(self) -> str:
        if self.use_centroid:
            return "Exact centroid match"
        return "Exact location match"


class GeoDistanceLevel(ComparisonLevelCreator):
    """
    Comparison level for distance between geometries at a threshold.

    Args:
        col_name (str): Name of the WKT geometry column.
        threshold (float): Maximum distance.
        use_centroid (bool): If True, compare centroids instead edge-to-edge.
        crs: EPSG code of the geometry column's CRS. Both datasets must share the same CRS.
    """

    def __init__(
        self,
        col_name: str,
        threshold: float,
        use_centroid: bool = False,
        crs: CRSInput = None,
        _epsg: Optional[int] = None,
        _crs_type: Optional[str] = None,
        _pre_resolved: bool = False,
    ):
        _check_col_name(col_name, "GeoDistanceLevel")
        _check_use_centroid(use_centroid, "GeoDistanceLevel")
        self._col_name = col_name
        self.threshold = _check_distance_threshold(threshold, "GeoDistanceLevel")
        self.use_centroid = use_centroid
        if _pre_resolved:
            self._epsg, self._crs_type = _epsg, _crs_type
        else:
            self._epsg, self._crs_type = resolve_crs(crs, context="GeoDistanceLevel")

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        geom_l = _geom_expr(l, self.use_centroid, self._epsg, self._crs_type)
        geom_r = _geom_expr(r, self.use_centroid, self._epsg, self._crs_type)
        return f"ST_Distance({geom_l}, {geom_r}) <= {self.threshold}"

    def create_label_for_charts(self) -> str:
        prefix = "Centroid distance" if self.use_centroid else "Distance"
        unit = " m" if self._crs_type in ("geographic", "projected") else ""
        return f"{prefix} <= {self.threshold:g}{unit}"
