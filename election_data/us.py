"""United States: presidential results by state, House seats by state."""
from __future__ import annotations

import re

import pandas as pd

from .htmltables import clean, flat_cols, num, tables
from .model import ElectionResult
from .parties import normalise

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
_STATE_LOOKUP = {k.lower(): k for k in STATES}
_STATE_LOOKUP.update({"washington, d.c.": "District of Columbia", "d.c.": "District of Columbia",
                      "washington d.c.": "District of Columbia"})


def _state(cell) -> str | None:
    s = clean(cell).replace("†", "").replace("*", "").strip().lower()
    s = re.sub(r"\(.*?\)", "", s).strip()
    return _STATE_LOOKUP.get(s)


def parse_presidential(html: str, year: int, source: str) -> ElectionResult:
    cands = [t for t in tables(html, min_rows=45, must_contain=("Alabama", "Wyoming"))
             if any("State" in c for c in flat_cols(t)) and any("EV" in c or "Votes" in c for c in flat_cols(t))]
    if not cands:
        raise ValueError("results-by-state table not found")
    df = cands[0]
    cols = flat_cols(df)
    df.columns = cols

    # Candidate groups look like "Trump/Vance Republican | Votes" / "| %" / "| EV"
    groups: dict[str, dict[str, str]] = {}
    for c in cols:
        if " | " not in c:
            continue
        top, sub = c.split(" | ", 1)
        if "/" not in top:
            continue
        party = normalise(top.split()[-1])
        ticket = top.rsplit(" ", 1)[0]
        g = groups.setdefault(party, {"ticket": ticket})
        if sub.startswith("Votes"):
            g["votes"] = c
        elif sub.startswith("%"):
            g["pct"] = c
        elif sub.startswith("EV"):
            g["ev"] = c
    total_col = next((c for c in cols if c.startswith("Total votes")), None)
    state_col = cols[0]

    rows = []
    for _, r in df.iterrows():
        st = _state(r[state_col])
        if not st:
            continue  # skips Maine/Nebraska congressional districts and totals
        rec = {"unit": st, "code": STATES[st]}
        shares, evs = {}, {}
        for party, g in groups.items():
            v = num(r.get(g.get("votes"))) if g.get("votes") else None
            p = num(r.get(g.get("pct"))) if g.get("pct") else None
            e = num(r.get(g.get("ev"))) if g.get("ev") else None
            rec[f"votes_{party}"] = v
            rec[f"pct_{party}"] = p
            shares[party] = p or 0
            evs[party] = e or 0
        ranked = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)
        rec["winner"] = ranked[0][0] if ranked and ranked[0][1] > 0 else "Pending"
        rec["winner_pct"] = ranked[0][1] if ranked else None
        rec["runner_up"] = ranked[1][0] if len(ranked) > 1 else None
        rec["margin_pct"] = round(ranked[0][1] - ranked[1][1], 2) if len(ranked) > 1 else None
        rec["electoral_votes"] = sum(evs.values())
        rec["total_votes"] = num(r.get(total_col)) if total_col else None
        rows.append(rec)
    units = pd.DataFrame(rows).drop_duplicates("unit")

    # National totals: EVs from the table's Total row; votes summed over states
    total_row = df[df[state_col].astype(str).str.strip().str.lower() == "total"]
    nat = []
    for party, g in groups.items():
        ev = num(total_row.iloc[0][g["ev"]]) if len(total_row) and g.get("ev") else None
        votes = units[f"votes_{party}"].sum(skipna=True)
        nat.append({"party": party, "candidate": g["ticket"], "seats": int(ev or 0), "votes": int(votes)})
    national = pd.DataFrame(nat)
    tv = units["total_votes"].sum(skipna=True) or national["votes"].sum()
    national["vote_pct"] = (national["votes"] / tv * 100).round(2) if tv else None
    national = national.sort_values(["seats", "votes"], ascending=False).reset_index(drop=True)

    return ElectionResult(
        country="United States", key=f"us-pres-{year}", year=year,
        title=f"{year} Presidential Election", kind="presidential", unit_label="State",
        units=units, national=national, total_seats=538, majority=270,
        seat_label="Electoral votes", source=source,
        notes=["Maine and Nebraska split electoral votes by congressional district; "
               "the map shows the statewide winner."],
    )


def parse_house(html: str, year: int, source: str) -> ElectionResult:
    """Per-state delegation table from the 'United States House of Representatives elections' article."""
    best = None
    for t in tables(html, min_rows=45, must_contain=("Alabama", "Wyoming")):
        cols = flat_cols(t)
        low = " ".join(cols).lower()
        if "republican" in low and "democratic" in low and ("seats" in low or "total" in low):
            best = t
            break
    if best is None:
        raise ValueError("House per-state table not found")
    df = best
    cols = flat_cols(df)
    df.columns = cols
    state_col = cols[0]

    def pick(party: str):
        # prefer a column like "Democratic | Seats" (not "Change"/"Votes"/"%")
        pl = party.lower()
        for c in cols:
            cl = c.lower()
            if pl in cl and "seat" in cl and "change" not in cl and "+/-" not in cl and "%" not in cl:
                return c
        for c in cols:
            cl = c.lower()
            if cl.startswith(pl) and not any(x in cl for x in ("change", "%", "+/", "vote", "±")):
                return c
        return None

    dcol, rcol = pick("Democratic"), pick("Republican")
    if not dcol or not rcol:
        raise ValueError(f"House seat columns not found in {cols}")
    rows = []
    for _, r in df.iterrows():
        st = _state(r[state_col])
        if not st:
            continue
        d, rep = num(r[dcol]) or 0, num(r[rcol]) or 0
        winner = "Democratic" if d > rep else "Republican" if rep > d else "Tie"
        rows.append({"unit": st, "code": STATES[st], "seats_Democratic": int(d),
                     "seats_Republican": int(rep), "winner": winner,
                     "margin_seats": int(abs(d - rep))})
    units = pd.DataFrame(rows).drop_duplicates("unit")
    if len(units) < 45:
        raise ValueError("House table parsed too few states")
    national = pd.DataFrame([
        {"party": "Republican", "seats": int(units["seats_Republican"].sum())},
        {"party": "Democratic", "seats": int(units["seats_Democratic"].sum())},
    ])
    other = 435 - national["seats"].sum()
    if other > 0:
        national = pd.concat([national, pd.DataFrame([{"party": "Other/Pending", "seats": int(other)}])])
    national = national.sort_values("seats", ascending=False).reset_index(drop=True)
    return ElectionResult(
        country="United States", key=f"us-house-{year}", year=year,
        title=f"{year} House of Representatives Elections", kind="house", unit_label="State",
        units=units, national=national, total_seats=435, majority=218,
        seat_label="House seats", source=source,
        notes=["Map colour shows which party won the majority of each state's House delegation."],
    )
