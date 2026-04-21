import pytest
from geosplink.crs import parse_epsg, classify_epsg, resolve_crs


class TestParseEpsg:
    def test_integer_passthrough(self):
        assert parse_epsg(4326) == 4326

    def test_epsg_prefix_string(self):
        assert parse_epsg("EPSG:4326") == 4326

    def test_epsg_prefix_lowercase(self):
        assert parse_epsg("epsg:4326") == 4326

    def test_bare_integer_string(self):
        assert parse_epsg("28992") == 28992

    def test_whitespace_stripped(self):
        assert parse_epsg("  EPSG:4326  ") == 4326

    def test_none_returns_none(self):
        assert parse_epsg(None) is None

    def test_unparseable_string_returns_none(self):
        assert parse_epsg("WGS84") is None

    def test_malformed_epsg_prefix_returns_none(self):
        assert parse_epsg("EPSG:abc") is None


class TestClassifyEpsg:
    @pytest.mark.parametrize("epsg", [4326, 4269, 4258, 4283, 7844])
    def test_known_geographic(self, epsg):
        assert classify_epsg(epsg) == "geographic"

    @pytest.mark.parametrize(
        "epsg",
        [
            3857,  # Web Mercator
            27700,  # British National Grid
            28992,  # RD New
            32632,  # UTM 32N
            32701,  # UTM 1S
            25831,  # ETRS89 UTM 31N
            26901,  # NAD83 UTM 1N
        ],
    )
    def test_known_projected(self, epsg):
        assert classify_epsg(epsg) == "projected"

    def test_utm_north_zone_boundaries(self):
        assert classify_epsg(32601) == "projected"
        assert classify_epsg(32660) == "projected"

    def test_utm_south_zone_boundaries(self):
        assert classify_epsg(32701) == "projected"
        assert classify_epsg(32760) == "projected"

    def test_unknown_returns_none(self):
        assert classify_epsg(9999) is None


class TestResolveCrs:
    def test_none_warns_and_returns_none(self):
        with pytest.warns(UserWarning, match="no CRS supplied"):
            epsg, crs_type = resolve_crs(None)
        assert epsg is None
        assert crs_type is None

    def test_unparseable_warns_and_returns_none(self):
        with pytest.warns(UserWarning, match="could not parse"):
            epsg, crs_type = resolve_crs("WGS84")
        assert epsg is None
        assert crs_type is None

    def test_unknown_epsg_warns_and_returns_none_type(self):
        with pytest.warns(UserWarning, match="not in geosplink's known CRS list"):
            epsg, crs_type = resolve_crs(9999)
        assert epsg == 9999
        assert crs_type is None

    def test_geographic_epsg(self):
        epsg, crs_type = resolve_crs(4326)
        assert epsg == 4326
        assert crs_type == "geographic"

    def test_projected_epsg(self):
        epsg, crs_type = resolve_crs(28992)
        assert epsg == 28992
        assert crs_type == "projected"

    def test_epsg_string_input(self):
        epsg, crs_type = resolve_crs("EPSG:4326")
        assert epsg == 4326
        assert crs_type == "geographic"

    def test_no_warning_for_known_crs(self, recwarn):
        resolve_crs(4326)
        assert len(recwarn) == 0

    def test_context_appears_in_warning(self):
        with pytest.warns(UserWarning, match="MyComparator"):
            resolve_crs(None, context="MyComparator")
