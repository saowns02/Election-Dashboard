"""Map geometry: Bangladesh districts, UK constituency hexes, US states."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from .uk import norm_name

GEO_DIR = Path(__file__).resolve().parent.parent / "data" / "geo"


@lru_cache(maxsize=1)
def bangladesh() -> dict:
    """GeoJSON FeatureCollection; feature.id = district name (geoBoundaries spelling)."""
    gj = json.loads((GEO_DIR / "bd_districts.geojson").read_text(encoding="utf-8"))
    for f in gj["features"]:
        f["id"] = f["properties"]["district"]
    return gj


@lru_cache(maxsize=4)
def uk_hexes(year: int) -> dict:
    """Constituency hex map as GeoJSON in a small synthetic lon/lat space.

    Hex grids come from ODI Leeds' HexJSON maps (odd-r layout). Elections
    from 2024 use the 2023 boundary review; earlier ones the 2010 boundaries.
    feature.id = normalised constituency name, so results can join on it.
    """
    fname = "uk_constituencies_2024.hexjson" if year >= 2024 else "uk_constituencies_2010.hexjson"
    hx = json.loads((GEO_DIR / fname).read_text(encoding="utf-8"))
    s = 0.25                                  # hex "radius" in degrees
    w = math.sqrt(3) * s
    feats = []
    for code, h in hx["hexes"].items():
        q, r = h["q"], h["r"]
        cx = q * w + (w / 2 if r % 2 else 0)  # odd rows are shifted right
        cy = r * 1.5 * s
        ring = [[cx + s * math.cos(math.radians(60 * i + 30)),
                 cy + s * math.sin(math.radians(60 * i + 30))] for i in range(7)]
        ring.reverse()  # clockwise exterior ring, as plotly's geo expects
        feats.append({"type": "Feature", "id": norm_name(h["n"]),
                      "properties": {"name": h["n"], "code": code},
                      "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {"type": "FeatureCollection", "features": feats}
