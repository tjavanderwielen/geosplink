"""
GeoSplink — geospatial comparator classes for Splink record linkage.

Usage:
    from GeoSplink import GeoOverlap, GeoJaccard, GeoSizeRatio, GeoDistance, etc.
    from GeoSplink import gcll  # for individual level classes
"""

from geosplink.geo_comparison_library import GeoJaccard, GeoOverlap, GeoSizeRatio, GeoDistance
import geosplink.geo_comparison_level_library as gcll
from splink import DuckDBAPI as _DuckDBAPI


class DuckDBAPI(_DuckDBAPI):
    """DuckDB API for geosplink — ensures the spatial extension is loaded."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._con.execute("INSTALL spatial; LOAD spatial;")


__all__ = [
    "GeoOverlap",
    "GeoJaccard",
    "GeoSizeRatio",
    "GeoDistance",
    "gcll",
    "DuckDBAPI",
]
