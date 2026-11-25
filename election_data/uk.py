"""United Kingdom: general election winners by constituency."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .htmltables import clean, flat_cols, num, tables
from .model import ElectionResult
from .parties import normalise


def norm_name(s: str) -> str:
    """Normalise a constituency name for matching across sources."""
    s = re.sub(r"\(.*?\)", "", clean(s))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ").replace("st.", "st ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_mps_list(html: str, year: int, source: str) -> ElectionResult:
    df = None
    for t in tables(html, min_rows=600):
        cols = [c.lower() for c in flat_cols(t)]
        if cols and cols[0].startswith("constituency") and any("returned" in c for c in cols):
            df = t
            break
    if df is None:
        raise ValueError("constituency table not found")
    cols = flat_cols(df)
    df.columns = range(len(cols))
    lc = [c.lower() for c in cols]
    ret = next(i for i, c in enumerate(lc) if "returned" in c)
    stop = next((i for i, c in enumerate(lc) if i > ret and c.startswith("notes")), len(cols))
    party_cols = [i for i in range(ret, stop) if "affil" in lc[i] or "party" in lc[i]]
    name_cols = [i for i in range(ret, stop) if i not in party_cols]
    # columns between the constituency name and "Member returned": previous/notional winner
    prev_cols = [i for i in range(1, ret) if "affil" in lc[i] or "party" in lc[i] or "incumbent" in lc[i]
                 or "notional" in lc[i]]

    rows = []
    for _, r in df.iterrows():
        con = clean(r[0])
        if not con or con.lower().rstrip(":") in ("source", "sources", "total") or con.lower().startswith("constituency"):
            continue
        party = ""
        for i in reversed(party_cols):
            v = clean(r[i])
            if v and v.lower() != "nan":
                party = v
                break
        mp = next((clean(r[i]) for i in name_cols if clean(r[i]) and clean(r[i]).lower() != "nan"), "")
        prev = next((clean(r[i]) for i in reversed(prev_cols) if clean(r[i]) and clean(r[i]).lower() != "nan"), "")
        rows.append({"unit": con, "key": norm_name(con), "winner": normalise(party) if party else "Pending",
                     "prev_winner": normalise(prev) if prev else None,
                     "member": mp, "notes": clean(r[stop]) if stop < len(cols) else ""})
    units = pd.DataFrame(rows).drop_duplicates("unit")
    national = (units.groupby("winner").size().rename("seats").reset_index()
                .rename(columns={"winner": "party"}).sort_values("seats", ascending=False)
                .reset_index(drop=True))
    return ElectionResult(
        country="United Kingdom", key=f"uk-ge-{year}", year=year,
        title=f"{year} General Election", kind="general", unit_label="Constituency",
        units=units, national=national, total_seats=650, majority=326,
        seat_label="Seats", source=source,
        notes=["Each hexagon is one constituency (equal area), so the map reflects seats, not land area."],
    )


def add_vote_share(result: ElectionResult, html: str) -> None:
    """Merge national vote counts/shares from the main general-election article, if found."""
    for t in tables(html, min_rows=6, must_contain=("Conservative", "Labour")):
        cols = flat_cols(t)
        tops = [c.split(" | ")[0].lower() for c in cols]
        if not tops or not tops[0].startswith("party") or "votes" not in tops:
            continue
        vgroup = [i for i, c in enumerate(tops) if c == "votes"]
        t.columns = range(len(cols))
        # within the Votes group: the big integer column is the count, the "%" one the share
        sample = t.head(5)
        vcol = next((i for i in vgroup if (sample[i].map(num).fillna(0) > 10000).any()), None)
        pcol = next((i for i in vgroup if sample[i].astype(str).str.contains("%").any()), None)
        if vcol is None:
            continue
        party_cols = [i for i, c in enumerate(tops) if c.startswith("party")]
        found = {}
        for _, r in t.iterrows():
            name = next((clean(r[i]) for i in party_cols if clean(r[i]) and clean(r[i]).lower() != "nan"), "")
            v = num(r[vcol])
            if not name or not v or v < 1000:
                continue
            party = normalise(name)
            if party not in found:
                found[party] = (v, num(r[pcol]) if pcol is not None else None)
        if len(found) >= 4 and {"Labour", "Conservative"} <= set(found):
            nat = result.national.set_index("party")
            for p, (v, pct) in found.items():
                if p in nat.index:
                    nat.loc[p, "votes"] = v
                    nat.loc[p, "vote_pct"] = pct
            result.national = nat.reset_index()
            return
