# GeoSplink

Geospatial comparator classes to supplement [Splink](https://github.com/moj-analytical-services/splink) record linkage.

Provides SQL-based comparison levels for matching records based on geometric properties, designed to slot directly into Splink's `SettingsCreator` alongside standard comparators.

## Structure

Mirrors Splink's own library structure:

| File | Contents |
|------|----------|
| `geo_comparison_level_library.py` | Individual level classes (`GeoNullLevel`, `GeoOverlapLevel`, etc.) |
| `geo_comparison_library.py` | Full comparator classes (`GeoOverlap`, `GeoJaccard`, etc.) |

## Comparators

### `GeoOverlap(col_name, thresholds=[0.9, 0.5])`
Overlap coefficient: `intersection area / min(area_l, area_r)`. Asymmetric — a small geometry fully inside a large one scores 100%. Useful when one dataset has coarser geometries than the other.

### `GeoJaccard(col_name, thresholds=[0.9, 0.5])`
Jaccard similarity (IoU): `intersection area / union area`. Symmetric. Preferred when both datasets have comparable geometry precision.

### `GeoSizeRatio(col_name, thresholds=[0.5, 0.25])`
Size ratio: `min(area_l, area_r) / max(area_l, area_r)`. Useful as an independent signal when geometries may not overlap but should be similar in scale.


## Usage

```python
from geosplink import GeoOverlap, GeoJaccard, GeoSizeRatio

settings = SettingsCreator(
    link_type="dedupe_only",
    comparisons=[
        GeoOverlap("geometry_wkt"),
    ],
)
```

Individual levels can also be composed into a `CustomComparison`:

```python
from geosplink import gcll
from splink.internals.comparison_library import CustomComparison

comparison = CustomComparison(
    comparison_levels=[
        gcll.GeoNullLevel("geometry_wkt"),
        gcll.GeoJaccardLevel("geometry_wkt", threshold=0.8),
        gcll.GeoAnyOverlapLevel("geometry_wkt"),
    ]
)
```

## Requirements

- [Splink](https://github.com/moj-analytical-services/splink)
- DuckDB with the [spatial extension](https://duckdb.org/docs/extensions/spatial.html) (`INSTALL spatial; LOAD spatial;`)

The geometry column must contain WKT strings. For `GeoOverlap` and `GeoJaccard`, bounding box columns are required in the data:

| Column | Description |
|--------|-------------|
| `bbox_minx` | Minimum x (longitude) of bounding box |
| `bbox_miny` | Minimum y (latitude) of bounding box |
| `bbox_maxx` | Maximum x (longitude) of bounding box |
| `bbox_maxy` | Maximum y (latitude) of bounding box |

Splink expects `_l` / `_r` suffixed versions of these in the comparison table.

## Notes

**u-probability estimation:** Splink's `estimate_u_using_random_sampling()` will produce near-zero observations for overlap levels, since random non-matching pairs almost never overlap geometrically. Set u-probabilities manually via `.configure()`:

```python
GeoOverlap("geometry_wkt").configure(
    u_probabilities=[0.9999, 0.00002, 0.00003, 0.00003, 0.00002]
    # null, exact, >=90%, >=50%, any overlap — no overlap is last (not listed)
)
```

**Dialect support:** All SQL targets DuckDB spatial functions. Other backends (Spark, Postgres/PostGIS) are not yet supported.

**CRS:** No coordinate reference system handling is implemented. Ensure geometries are in a consistent CRS before use.