# GeoSplink

[![Tests](https://github.com/tjavanderwielen/geosplink/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/tjavanderwielen/geosplink/actions/workflows/tests.yml)

Geospatial comparator classes to supplement [Splink](https://github.com/moj-analytical-services/splink) record linkage.

Provides SQL-based comparison levels for matching records based on geometric properties, designed to slot directly into Splink's `SettingsCreator` alongside standard comparators.

## Structure

Mirrors Splink's own library structure:

| File | Contents |
|------|----------|
| `geo_comparison_level_library.py` | Individual level classes (`GeoNullLevel`, `GeoOverlapLevel`, etc.) |
| `geo_comparison_library.py` | Full comparator classes (`GeoOverlap`, `GeoJaccard`, etc.) |

## Comparators

### `GeoOverlap(col_name, thresholds=[0.9, 0.5], bbox_prefix=None)`
Overlap coefficient: `intersection / min(area_l, area_r)`. 

![GeoOverlap: the intersection divided by the smaller shape's area. A inside B scores 100%; two equally sized shapes that partly overlap score 67%.](docs/img/geo_overlap.svg)

### `GeoJaccard(col_name, thresholds=[0.9, 0.5], bbox_prefix=None)`
Jaccard similarity (IoU): `intersection / union`. 

![GeoJaccard: the intersection divided by the union of both shapes. A inside B scores 25%; two equally sized shapes that partly overlap score 50%.](docs/img/geo_jaccard.svg)

### `GeoSizeRatio(col_name, thresholds=[0.5, 0.25])`
Size ratio: `min(area_l, area_r) / max(area_l, area_r)`.

![GeoSizeRatio: the smaller area divided by the larger area. A shape a quarter the size of the other scores 25%; two same-sized shapes score 100% even when far apart.](docs/img/geo_size_ratio.svg)

### `GeoDistance(col_name, distance_threshold_or_thresholds, distance_type="euclidean", use_centroid=False, crs=None)`
Distance between two geometries (or their centroids, if `use_centroid=True`).

![GeoDistance: by default the distance is the gap between the closest points of the two shapes. With use_centroid=True it is the distance between their centroids.](docs/img/geo_distance.svg)


## Usage

```python
from geosplink import GeoOverlap, GeoJaccard, GeoSizeRatio, GeoDistance, DuckDBAPI

settings = SettingsCreator(
    link_type="dedupe_only",
    comparisons=[
        GeoOverlap("geometry_wkt"),
        GeoDistance("geometry_wkt", [100, 500], crs="EPSG:4326"),
    ],
)

db_api = DuckDBAPI()  # installs and loads the DuckDB spatial extension automatically
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
- DuckDB with the [spatial extension](https://duckdb.org/docs/extensions/spatial.html). Use `geosplink.DuckDBAPI` in place of Splink's `DuckDBAPI` and it will automatically run `INSTALL spatial; LOAD spatial;` for you — no manual setup required.

The geometry column must contain WKT strings.

`GeoOverlap` and `GeoJaccard` run a cheap bounding box test before the expensive intersection, which discards most non-matching pairs early. By default the bounding boxes are computed inline from the WKT. If your data already has bounding box columns, pass `bbox_prefix` to use them instead, which is faster as the WKT does not have to be parsed again for every pair:

| Column | Description |
|--------|-------------|
| `{bbox_prefix}_minx` | Minimum x (longitude) of bounding box |
| `{bbox_prefix}_miny` | Minimum y (latitude) of bounding box |
| `{bbox_prefix}_maxx` | Maximum x (longitude) of bounding box |
| `{bbox_prefix}_maxy` | Maximum y (latitude) of bounding box |

```python
# e.g. in DuckDB: ST_XMin(ST_GeomFromText(geometry_wkt)) AS bbox_minx, ...
GeoOverlap("geometry_wkt", bbox_prefix="bbox")
```

Splink expects `_l` / `_r` suffixed versions of these in the comparison table. Rows with a NULL bounding box value never pass the pre-filter, so they fall through to the "no overlap" level.

## Notes

**u-probability estimation:** Splink's `estimate_u_using_random_sampling()` will produce near-zero observations for overlap levels, since random non-matching pairs almost never overlap geometrically. Set u-probabilities manually via `.configure()`:

```python
GeoOverlap("geometry_wkt").configure(
    u_probabilities=[0.9999, 0.00002, 0.00003, 0.00003, 0.00002]
    # null, exact, >=90%, >=50%, any overlap — no overlap is last (not listed)
)
```

**Dialect support:** All SQL targets DuckDB spatial functions. Other backends (Spark, Postgres/PostGIS) are not yet supported.

**CRS:** Geographic and projected CRSes are recognised by EPSG code for `GeoDistance` (see `src/geosplink/crs.py` for the full list, e.g. `EPSG:4326`, `EPSG:28992`, UTM zones, etc.). Recognised geographic CRSes are reprojected to Web Mercator before computing distance; recognised projected CRSes are used directly. Unrecognised or omitted CRSes fall back to Euclidean distance in the geometries' native coordinate units, with a `UserWarning`. `GeoOverlap`, `GeoJaccard`, and `GeoSizeRatio` do not use CRS and assume geometries are already in a consistent CRS.