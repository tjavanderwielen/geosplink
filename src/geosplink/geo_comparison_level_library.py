"""
Geospatial comparison level classes for use with Splink record linkage.
Mirrors the structure of splink.internals.comparison_level_library.

Each class is a ComparisonLevelCreator subclass that generates SQL for a single
comparison level. These can be used directly in CustomComparison or composed
into full comparators via geo_comparison_library.py.

Note:
    All SQL targets DuckDB spatial functions (ST_*, BBOX_OVERLAP, etc.).
    Dialect translation is not yet implemented.
"""

from __future__ import annotations

from typing import Union

from splink.internals.column_expression import ColumnExpression
from splink.internals.comparison_level_creator import ComparisonLevelCreator
from splink.internals.dialects import SplinkDialect


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
        self._col_name = col_name
        self.is_null_level = True

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        return f"{self._col_name}_l IS NULL OR {self._col_name}_r IS NULL"

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
    Uses a bounding box pre-filter for performance.

    Args:
        col_name (str): Name of the WKT geometry column.
    """

    def __init__(self, col_name: str):
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
    Uses a bounding box pre-filter for performance.

    Args:
        col_name (str): Name of the WKT geometry column.
        threshold (float): Minimum overlap coefficient (0-1).
    """

    def __init__(self, col_name: str, threshold: float):
        self._col_name = col_name
        self.threshold = threshold

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
        self._col_name = col_name
        self.threshold = threshold

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

    Note:
        Floating point equality on ST_Area will almost never match in practice.
        Consider using a tolerance-based approach if needed.

    Args:
        col_name (str): Name of the WKT geometry column.
    """

    def __init__(self, col_name: str):
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
        self._col_name = col_name
        self.threshold = threshold

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
        use_centroid (bool): If True, compare centroids instead of full geometries.
    """

    def __init__(self, col_name: str, use_centroid: bool = False):
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
    Comparison level for euclidean distance between geometries at a threshold.

    Args:
        col_name (str): Name of the WKT geometry column.
        threshold (float): Maximum distance in the same units as the geometries' coordinate system.
        use_centroid (bool): If True, compare centroids instead of full geometries.
    """

    def __init__(self, col_name: str, threshold: float, use_centroid: bool = False):
        self._col_name = col_name
        self.threshold = threshold
        self.use_centroid = use_centroid

    def create_sql(self, sql_dialect: SplinkDialect) -> str:
        l, r = f"{self._col_name}_l", f"{self._col_name}_r"
        if self.use_centroid:
            geom_l = f"ST_Centroid(ST_GeomFromText({l}))"
            geom_r = f"ST_Centroid(ST_GeomFromText({r}))"
        else:
            geom_l = f"ST_GeomFromText({l})"
            geom_r = f"ST_GeomFromText({r})"
        return f"ST_Distance({geom_l}, {geom_r}) <= {self.threshold}"

    def create_label_for_charts(self) -> str:
        prefix = "Centroid distance" if self.use_centroid else "Distance"
        return f"{prefix} <= {self.threshold}"
