"""Catalogue of elections (2016 onward) and the loader that decides live vs snapshot.

Adding a future election
------------------------
* United States: nothing to do. Presidential (every 4 years) and House
  (every 2 years) elections are generated from the fixed November calendar.
* United Kingdom / Bangladesh: discovered automatically. Wikipedia keeps a
  "Next ... general election" article; once the date is set it is moved to a
  "YYYY ... general election" title. We follow that redirect once a day and
  add the new year to the catalogue. You can also add it to KNOWN below.
"""
from __future__ import annotations

import datetime as dt
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from . import bd, uk, us, wiki
from .model import ElectionResult, load_snapshot

FIRST_YEAR = 2016
LIVE_WINDOW_DAYS = 30        # elections newer than this are always fetched live
LIVE_TTL = 5 * 60            # cache lifetime while an election is "live"
ARCHIVE_TTL = 30 * 24 * 3600


@dataclass
class ElectionSpec:
    country: str
    key: str
    year: int
    kind: str
    label: str
    date: dt.date
    page: str                                    # Wikipedia article with the per-unit results
    parse: Callable[[str, int, str], ElectionResult]
    extra_pages: list[str] = field(default_factory=list)

    @property
    def is_recent(self) -> bool:
        return (dt.date.today() - self.date).days <= LIVE_WINDOW_DAYS

    @property
    def is_upcoming(self) -> bool:
        return self.date > dt.date.today()


def _us_election_day(year: int) -> dt.date:
    d = dt.date(year, 11, 2)                     # first Tuesday after the first Monday
    while d.weekday() != 1:
        d += dt.timedelta(days=1)
    return d


# Known UK/BD election dates; later ones are discovered at runtime.
KNOWN = {
    "United Kingdom": {2017: dt.date(2017, 6, 8), 2019: dt.date(2019, 12, 12), 2024: dt.date(2024, 7, 4)},
    "Bangladesh": {2018: dt.date(2018, 12, 30), 2024: dt.date(2024, 1, 7), 2026: dt.date(2026, 2, 12)},
}
NEXT_PAGES = {
    "United Kingdom": "Next_United_Kingdom_general_election",
    "Bangladesh": "Next_Bangladeshi_general_election",
}


def _uk_spec(year: int, date: dt.date) -> ElectionSpec:
    return ElectionSpec("United Kingdom", f"uk-ge-{year}", year, "general", f"{year} General Election", date,
                        f"List_of_MPs_elected_in_the_{year}_United_Kingdom_general_election",
                        uk.parse_mps_list, [f"{year}_United_Kingdom_general_election"])


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _bd_spec(year: int, date: dt.date, parliament: int) -> ElectionSpec:
    # The member list fills in seats the results table leaves blank.
    return ElectionSpec("Bangladesh", f"bd-ge-{year}", year, "general", f"{year} General Election", date,
                        f"{year}_Bangladeshi_general_election", bd.parse_general,
                        [f"List_of_members_of_the_{_ordinal(parliament)}_Jatiya_Sangsad"])


def discover(country: str) -> dict[int, dt.date]:
    """Follow Wikipedia's 'Next … election' redirect to find newly scheduled elections."""
    found: dict[int, dt.date] = {}
    try:
        page = wiki.fetch(NEXT_PAGES[country], max_age=24 * 3600, retries=1, timeout=15)
    except Exception:
        return found
    m = re.match(r"(\d{4})_", page.title)
    if m:
        year = int(m.group(1))
        # Pull the polling date from the infobox if we can; else assume year-end.
        dm = re.search(r"(\d{1,2} (?:January|February|March|April|May|June|July|August|September|"
                       r"October|November|December) " + str(year) + ")", page.html)
        try:
            date = dt.datetime.strptime(dm.group(1), "%d %B %Y").date() if dm else dt.date(year, 12, 31)
        except ValueError:
            date = dt.date(year, 12, 31)
        found[year] = date
    return found


def catalogue(include_discovered: bool = True) -> dict[str, list[ElectionSpec]]:
    today = dt.date.today()
    out: dict[str, list[ElectionSpec]] = {"Bangladesh": [], "United Kingdom": [], "United States": []}

    for country in ("Bangladesh", "United Kingdom"):
        years = dict(KNOWN[country])
        if include_discovered:
            for y, d in discover(country).items():
                years.setdefault(y, d)
        ordered = sorted(years.items())
        specs = []
        for i, (y, d) in enumerate(ordered):
            if y < FIRST_YEAR:
                continue
            # 2018 elected the 11th parliament; each later election the next one
            specs.append(_bd_spec(y, d, 11 + i) if country == "Bangladesh" else _uk_spec(y, d))
        out[country] = specs[::-1]

    for year in range(today.year + (1 if today.month >= 11 else 0), FIRST_YEAR - 1, -1):
        if year % 2:
            continue
        day = _us_election_day(year)
        if year % 4 == 0:
            out["United States"].append(ElectionSpec(
                "United States", f"us-pres-{year}", year, "presidential", f"{year} Presidential", day,
                f"{year}_United_States_presidential_election", us.parse_presidential))
        out["United States"].append(ElectionSpec(
            "United States", f"us-house-{year}", year, "house", f"{year} House of Representatives", day,
            f"{year}_United_States_House_of_Representatives_elections", us.parse_house))
    return out


def apply_extra(spec: ElectionSpec, res: ElectionResult, html: str) -> ElectionResult:
    """Enrich a parsed result with a supplementary article."""
    if spec.country == "United Kingdom":
        uk.add_vote_share(res, html)
    elif spec.country == "Bangladesh":
        res = bd.fill_from_members(res, html)
    return res


def load(spec: ElectionSpec, force_live: bool = False) -> ElectionResult:
    """Load an election, preferring the bundled snapshot for settled elections."""
    snap = load_snapshot(spec.key)
    if snap is not None and not force_live and not spec.is_recent:
        return snap

    ttl = LIVE_TTL if spec.is_recent else ARCHIVE_TTL
    if force_live:
        ttl = 0
    try:
        page = wiki.fetch(spec.page, max_age=ttl)
        source = f"https://en.wikipedia.org/wiki/{page.title}"
        res = spec.parse(page.html, spec.year, source)
        res.fetched_at = page.fetched_at
        res.origin = "live" if time.time() - page.fetched_at < 60 else "cache"
        for extra in spec.extra_pages:
            try:
                ep = wiki.fetch(extra, max_age=ttl, retries=2)
                res = apply_extra(spec, res, ep.html)
            except Exception:
                pass
        return res
    except Exception as e:
        if snap is not None:
            snap.notes = snap.notes + [f"Live source unavailable ({e}); showing bundled snapshot."]
            return snap
        raise
