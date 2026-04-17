# tests/test_comparators.py
def test_geo_overlap_matches_overlapping_polygons(duckdb_spatial):
    """Two polygons that overlap by 100% should hit the highest level."""
    # ... build a DuckDB table with two identical polygons
    # ... run the comparator's SQL
    # ... assert the result is the top match level
    pass