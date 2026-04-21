"""CRS classification and validation for geosplink."""

from __future__ import annotations

import warnings
from typing import Optional, Tuple, Union

CRSInput = Union[int, str, None]

# EPSG codes with geographic (angular) units — distance in degrees
_GEOGRAPHIC_EPSG: frozenset = frozenset(
    {
        4326,  # WGS 84
        4269,  # NAD83
        4759,  # NAD2011
        4258,  # ETRS89
        4230,  # ED50
        4277,  # OSGB 1936
        4283,  # GDA94
        7844,  # GDA2020
        4167,  # NZGD2000
        4214,  # Beijing 1954
        4490,  # CGCS2000
        4612,  # JGD2000
        6668,  # JGD2011
    }
)

# EPSG codes with linear (metre) units — distance in metres
_PROJECTED_EPSG: frozenset = frozenset(
    {
        3857,  # Web Mercator (pseudo-metres, distorted at high latitudes)
        27700,  # British National Grid
        28992,  # RD New (Netherlands)
        2154,  # RGF93 v1 / Lambert-93 (France)
        3035,  # ETRS89-LAEA Europe
        3034,  # ETRS89-LCC Europe
        3044,  # ETRS89 / TM35FIN (Finland)
        2056,  # CH1903+ / LV95 (Switzerland)
        3301,  # Estonian Coordinate System of 1997
        3059,  # LKS92 / Latvia TM
        3346,  # LKS94 / Lithuania TM
        2180,  # ETRS89 / Poland CS92
        31370,  # BD72 / Belgian Lambert 72
        32632,  # WGS 84 / UTM zone 32N (common European default)
        # UTM North zones 1–60
        *range(32601, 32661),
        # UTM South zones 1–60
        *range(32701, 32761),
        # ETRS89-TM / UTM Europe zones 28–38
        *range(25828, 25839),
        # NAD83 UTM North America zones 1–23
        *range(26901, 26924),
        # GDA94 / MGA zones 49–56 (Australia)
        *range(28349, 28357),
        # GDA2020 / MGA zones 49–56 (Australia)
        *range(7849, 7857),
    }
)


def parse_epsg(crs: CRSInput) -> Optional[int]:
    """Parse a CRS value to an integer EPSG code, or None if unrecognised."""
    if crs is None:
        return None
    if isinstance(crs, int):
        return crs
    if isinstance(crs, str):
        s = crs.strip().upper()
        if s.startswith("EPSG:"):
            try:
                return int(s[5:])
            except ValueError:
                return None
        try:
            return int(s)
        except ValueError:
            return None
    return None


def classify_epsg(epsg: int) -> Optional[str]:
    """Return 'geographic', 'projected', or None for unrecognised EPSG codes."""
    if epsg in _GEOGRAPHIC_EPSG:
        return "geographic"
    if epsg in _PROJECTED_EPSG:
        return "projected"
    return None


def resolve_crs(
    crs: CRSInput,
    context: str = "GeoSplink",
    stacklevel: int = 3,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse and classify a CRS input.

    Returns (epsg, crs_type) where crs_type is 'geographic', 'projected', or None.

    Warns:
        UserWarning: if crs is None, unrecognised, or unparseable.
    """
    if crs is None:
        warnings.warn(
            f"{context}: no CRS supplied. Distance thresholds are interpreted in "
            "the native units of your coordinate system (degrees for geographic "
            "CRS, metres for projected CRS). Pass crs='EPSG:4326' or similar to "
            "enable automatic distance routing and suppress this warning.",
            UserWarning,
            stacklevel=stacklevel,
        )
        return None, None

    epsg = parse_epsg(crs)

    if epsg is None:
        warnings.warn(
            f"{context}: could not parse CRS '{crs}'. "
            "Expected an EPSG code such as 'EPSG:4326' or 4326.",
            UserWarning,
            stacklevel=stacklevel,
        )
        return None, None

    crs_type = classify_epsg(epsg)
    if crs_type is None:
        warnings.warn(
            f"{context}: EPSG:{epsg} is not in geosplink's known CRS list. "
            "Falling back to Euclidean distance. If this is a geographic CRS, "
            "distance results will be in degrees, not metres.",
            UserWarning,
            stacklevel=stacklevel,
        )

    return epsg, crs_type
