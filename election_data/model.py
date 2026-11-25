"""Common result model shared by every country parser."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "snapshots"


@dataclass
class ElectionResult:
    country: str              # "Bangladesh" | "United Kingdom" | "United States"
    key: str                  # unique id, e.g. "us-pres-2024"
    year: int
    title: str
    kind: str                 # "general" | "presidential" | "house"
    unit_label: str           # "District" | "Constituency" | "State"
    units: pd.DataFrame       # one row per map unit; must have unit, winner
    national: pd.DataFrame    # party, seats, (votes), (vote_pct)
    total_seats: int
    majority: int
    seat_label: str = "Seats"
    source: str = ""
    fetched_at: float | None = None
    origin: str = "live"      # "live" | "cache" | "snapshot"
    notes: list[str] = field(default_factory=list)
    detail: pd.DataFrame | None = None   # optional finer-grained rows (e.g. BD constituencies)

    # ---- (de)serialisation for bundled snapshots ----
    def to_json(self) -> dict:
        return {
            "country": self.country, "key": self.key, "year": self.year, "title": self.title,
            "kind": self.kind, "unit_label": self.unit_label, "total_seats": self.total_seats,
            "majority": self.majority, "seat_label": self.seat_label, "source": self.source,
            "fetched_at": self.fetched_at, "notes": self.notes,
            "units": json.loads(self.units.to_json(orient="records")),
            "national": json.loads(self.national.to_json(orient="records")),
            "detail": None if self.detail is None else json.loads(self.detail.to_json(orient="records")),
        }

    @classmethod
    def from_json(cls, d: dict) -> "ElectionResult":
        return cls(
            country=d["country"], key=d["key"], year=d["year"], title=d["title"], kind=d["kind"],
            unit_label=d["unit_label"], units=pd.DataFrame(d["units"]),
            national=pd.DataFrame(d["national"]), total_seats=d["total_seats"],
            majority=d["majority"], seat_label=d.get("seat_label", "Seats"), source=d.get("source", ""),
            fetched_at=d.get("fetched_at"), origin="snapshot", notes=d.get("notes", []),
            detail=pd.DataFrame(d["detail"]) if d.get("detail") else None,
        )

    def save_snapshot(self) -> Path:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        p = SNAPSHOT_DIR / f"{self.key}.json"
        p.write_text(json.dumps(self.to_json(), indent=1, ensure_ascii=False), encoding="utf-8")
        return p


def load_snapshot(key: str) -> ElectionResult | None:
    p = SNAPSHOT_DIR / f"{key}.json"
    if not p.exists():
        return None
    return ElectionResult.from_json(json.loads(p.read_text(encoding="utf-8")))
