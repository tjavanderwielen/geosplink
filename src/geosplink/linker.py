"""Splink linker with input validation for GeoSplink comparisons."""

import duckdb
from splink import DuckDBAPI as SplinkDuckDBAPI
from splink import Linker as SplinkLinker
from splink import SettingsCreator
from splink.internals.comparison_library import CustomComparison

from geosplink import geo_comparison_level_library as levels
from geosplink.geo_comparison_library import (
    GeoDistance,
    GeoJaccard,
    GeoOverlap,
    GeoSizeRatio,
)

_GEO_COMPARISONS = (GeoOverlap, GeoJaccard, GeoSizeRatio, GeoDistance)
_GEO_LEVELS = (
    levels.GeoNullLevel,
    levels.GeoExactOverlapLevel,
    levels.GeoAnyOverlapLevel,
    levels.GeoOverlapLevel,
    levels.GeoJaccardLevel,
    levels.GeoSizeExactLevel,
    levels.GeoSizeRatioLevel,
    levels.GeoDistanceExactLevel,
    levels.GeoDistanceLevel,
)
_BBOX_SUFFIXES = ("minx", "miny", "maxx", "maxy")
_NUMERIC_TYPES = {
    "tinyint",
    "smallint",
    "integer",
    "bigint",
    "hugeint",
    "utinyint",
    "usmallint",
    "uinteger",
    "ubigint",
    "uhugeint",
    "float",
    "double",
    "decimal",
}


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class Linker(SplinkLinker):
    """Splink Linker that validates input data used by GeoSplink creators."""

    def __init__(
        self,
        input_table_or_tables,
        settings,
        db_api,
        set_up_basic_logging=True,
        input_table_aliases=None,
        validate_settings=True,
    ):
        self._geo_requirements = {}
        if isinstance(settings, SettingsCreator):
            for comparison in settings.comparisons:
                if isinstance(comparison, _GEO_COMPARISONS + (CustomComparison,)):
                    for level in comparison.create_comparison_levels():
                        if isinstance(level, _GEO_LEVELS):
                            prefixes = self._geo_requirements.setdefault(
                                level._col_name, set()
                            )
                            prefix = getattr(level, "bbox_prefix", None)
                            if prefix is not None:
                                prefixes.add(prefix)

        super().__init__(
            input_table_or_tables,
            settings,
            db_api,
            set_up_basic_logging=set_up_basic_logging,
            input_table_aliases=input_table_aliases,
            validate_settings=validate_settings,
        )

    def _validate_input_dfs(self):
        super()._validate_input_dfs()
        if not self._geo_requirements:
            return
        if not isinstance(self._db_api, SplinkDuckDBAPI):
            raise TypeError("GeoSplink input validation requires a DuckDB backend")

        errors = []
        for alias, table in self._input_tables_dict.items():
            relation = table.as_duckdbpyrelation()
            columns = {
                name.lower(): (name, str(col_type).split("(")[0].lower())
                for name, col_type in zip(relation.columns, relation.types)
            }
            for geometry, prefixes in self._geo_requirements.items():
                bbox_columns = [
                    f"{prefix}_{suffix}"
                    for prefix in sorted(prefixes)
                    for suffix in _BBOX_SUFFIXES
                ]
                missing = [
                    name
                    for name in [geometry, *bbox_columns]
                    if name.lower() not in columns
                ]
                if missing:
                    errors.append(f"{alias}: missing columns: {', '.join(missing)}")
                if geometry.lower() not in columns:
                    continue
                geom_name, geom_type = columns[geometry.lower()]
                if geom_type != "varchar":
                    errors.append(f"{alias}: {geometry} must contain WKT strings")
                    continue
                geom = _quote(geom_name)
                invalid_geometry = (
                    f"{geom} IS NOT NULL AND "
                    f"(ST_IsEmpty(ST_GeomFromText({geom})) OR "
                    f"NOT ST_IsValid(ST_GeomFromText({geom})))"
                )
                checks = [
                    (
                        invalid_geometry,
                        f"{alias}: {geometry} contains invalid or empty geometry",
                    )
                ]
                for bbox in bbox_columns:
                    if bbox.lower() not in columns:
                        continue
                    bbox_name, bbox_type = columns[bbox.lower()]
                    if bbox_type not in _NUMERIC_TYPES:
                        errors.append(f"{alias}: {bbox} must be a numeric column")
                        continue
                    col = _quote(bbox_name)
                    checks.extend(
                        [
                            (
                                f"{geom} IS NOT NULL AND {col} IS NULL",
                                f"{alias}: {bbox} contains NULL for a non-NULL {geometry}",
                            ),
                            (
                                f"{geom} IS NOT NULL AND {col} IS NOT NULL "
                                f"AND NOT isfinite({col})",
                                f"{alias}: {bbox} contains non-finite values",
                            ),
                        ]
                    )
                aggregates = ", ".join(
                    f"coalesce(bool_or({condition}), FALSE) AS check_{i}"
                    for i, (condition, _) in enumerate(checks)
                )
                try:
                    result = relation.aggregate(aggregates).fetchone()
                except duckdb.InvalidInputException as exc:
                    raise ValueError(
                        f"GeoSplink input validation failed: {alias}: {geometry} "
                        "contains invalid geometry"
                    ) from exc
                for failed, (_, message) in zip(result, checks):
                    if failed:
                        errors.append(message)
        if errors:
            raise ValueError("GeoSplink input validation failed:\n" + "\n".join(errors))
