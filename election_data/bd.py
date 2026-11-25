"""Bangladesh: Jatiya Sangsad general elections, 300 constituencies → 64 districts."""
from __future__ import annotations

import difflib
import re

import pandas as pd

from .htmltables import clean, flat_cols, num, tables
from .model import ElectionResult
from .parties import ALIASES, normalise

# District names as used by the geoBoundaries ADM2 layer the map draws.
DISTRICTS = [
    'Bagerhat', 'Bandarban', 'Barguna', 'Barisal', 'Bhola', 'Bogra', 'Brahamanbaria', 'Chandpur',
    'Chittagong', 'Chuadanga', 'Comilla', "Cox's Bazar", 'Dhaka', 'Dinajpur', 'Faridpur', 'Feni',
    'Gaibandha', 'Gazipur', 'Gopalganj', 'Habiganj', 'Jamalpur', 'Jessore', 'Jhalokati', 'Jhenaidah',
    'Joypurhat', 'Khagrachhari', 'Khulna', 'Kishoreganj', 'Kurigram', 'Kushtia', 'Lakshmipur',
    'Lalmonirhat', 'Madaripur', 'Magura', 'Manikganj', 'Maulvibazar', 'Meherpur', 'Munshiganj',
    'Mymensingh', 'Naogaon', 'Narail', 'Narayanganj', 'Narsingdi', 'Natore', 'Nawabganj',
    'Netrakona', 'Nilphamari', 'Noakhali', 'Pabna', 'Panchagarh', 'Patuakhali', 'Pirojpur',
    'Rajbari', 'Rajshahi', 'Rangamati', 'Rangpur', 'Satkhira', 'Shariatpur', 'Sherpur',
    'Sirajganj', 'Sunamganj', 'Sylhet', 'Tangail', 'Thakurgaon',
]
# New official spellings (2018 renaming) and other variants → map names
DISTRICT_ALIASES = {
    "chattogram": "Chittagong", "cumilla": "Comilla", "barishal": "Barisal", "bogura": "Bogra",
    "jashore": "Jessore", "chapai nawabganj": "Nawabganj", "chapainawabganj": "Nawabganj",
    "brahmanbaria": "Brahamanbaria", "moulvibazar": "Maulvibazar", "jhalokathi": "Jhalokati",
    "netrokona": "Netrakona", "khagrachari": "Khagrachhari", "laxmipur": "Lakshmipur",
    "lakshmipur": "Lakshmipur", "coxs bazar": "Cox's Bazar", "cox's bazar": "Cox's Bazar",
    "khagrachhari": "Khagrachhari", "rangamati": "Rangamati", "parbatya rangamati": "Rangamati",
    "parbatya khagrachhari": "Khagrachhari", "parbatya bandarban": "Bandarban",
    "jhenaidaha": "Jhenaidah", "narsingdi": "Narsingdi", "narshingdi": "Narsingdi",
}

# Short party labels used in the constituency tables
BD_ABBR = {
    "al": "Awami League", "bnp": "BNP", "jp(e)": "Jatiya Party", "jp": "Jatiya Party", "jp (e)": "Jatiya Party",
    "japa": "Jatiya Party", "jamaat": "Jamaat-e-Islami", "bji": "Jamaat-e-Islami", "ji": "Jamaat-e-Islami",
    "wpb": "Workers Party of Bangladesh", "jsd": "Jatiya Samajtantrik Dal", "jsd (inu)": "Jatiya Samajtantrik Dal",
    "bkp": "Bangladesh Kalyan Party", "gf": "Gano Forum", "iab": "Islami Andolan Bangladesh",
    "ncp": "NCP", "bkm": "Khelafat Majlis", "ind": "Independent", "ind.": "Independent",
    "independent": "Independent", "bdb": "Bikalpa Dhara Bangladesh", "jasad": "Jatiya Samajtantrik Dal",
    "btf": "Tariqat Federation", "jp(m)": "Jatiya Party (Manju)", "bjp": "Bangladesh Jatiya Party",
    "ab party": "AB Party", "jei": "Jamaat-e-Islami", "km": "Khelafat Majlis",
    "gsa": "Ganosamhati Andolan", "bkm.": "Khelafat Majlis", "jp(e)/ind": "Jatiya Party", "gop": "Gano Odhikar Parishad", "gano odhikar parishad": "Gano Odhikar Parishad",
}


def district_of(constituency: str) -> str | None:
    base = re.sub(r"[-–\s]*\d+\s*$", "", clean(constituency)).strip()
    key = base.lower().replace("'", "'")
    if key in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[key]
    for d in DISTRICTS:
        if d.lower() == key:
            return d
    m = difflib.get_close_matches(base, DISTRICTS, n=1, cutoff=0.75)
    return m[0] if m else None


def party(label: str) -> str:
    s = clean(label)
    k = s.lower().strip()
    if k in BD_ABBR:
        return BD_ABBR[k]
    if "withh" in k or "postpon" in k or "suspend" in k or "cancel" in k:
        return "Withheld"
    return normalise(s) if s else "Pending"


def _col(cols, *needles, exclude=()):
    for i, c in enumerate(cols):
        cl = c.lower()
        if all(n in cl for n in needles) and not any(x in cl for x in exclude):
            return i
    return None


def parse_general(html: str, year: int, source: str) -> ElectionResult:
    con_df = None
    for t in tables(html, min_rows=150):
        cols = [c.lower() for c in flat_cols(t)]
        if any("constituency" in c for c in cols) and any("winner" in c or "elected" in c for c in cols):
            con_df = t
            break
    if con_df is None:
        raise ValueError("constituency results table not found")
    cols = flat_cols(con_df)
    con_df.columns = range(len(cols))

    name_i = _col(cols, "constituency", "name") or _col(cols, "constituency", exclude=("#", "voters", "no"))
    w_party = [i for i, c in enumerate(cols) if c.lower().startswith(("winner", "elected")) and "party" in c.lower()]
    w_alliance = _col(cols, "winner", "alliance")
    w_cand = _col(cols, "winner", "candidate") or _col(cols, "elected", "name")
    w_votes = _col(cols, "winner", "votes")
    w_pct = _col(cols, "winner", "%")
    r_party = [i for i, c in enumerate(cols) if c.lower().startswith("runner") and "party" in c.lower()]
    r_cand = _col(cols, "runner", "candidate")
    r_votes = _col(cols, "runner", "votes")
    m_votes = _col(cols, "margin", "votes")
    m_pct = _col(cols, "margin", "%")
    turnout = _col(cols, "turnout")

    def pick_party(r, idxs):
        for i in reversed(idxs):
            v = clean(r[i])
            if v and v.lower() != "nan":
                return party(v)
        return "Pending"

    rows = []
    for _, r in con_df.iterrows():
        name = clean(r[name_i]) if name_i is not None else ""
        # numbered seats ("Dhaka-10"), plus the single-seat hill districts ("Bandarban")
        if not name or (not re.search(r"\d+\s*$", name) and district_of(name) is None):
            continue
        rows.append({
            "constituency": name,
            "district": district_of(name),
            "winner": pick_party(r, w_party) if w_party else "Pending",
            "alliance": clean(r[w_alliance]) if w_alliance is not None else "",
            "candidate": clean(r[w_cand]) if w_cand is not None else "",
            "votes": num(r[w_votes]) if w_votes is not None else None,
            "pct": num(r[w_pct]) if w_pct is not None else None,
            "runner_up": pick_party(r, r_party) if r_party else None,
            "runner_up_candidate": clean(r[r_cand]) if r_cand is not None else "",
            "runner_up_votes": num(r[r_votes]) if r_votes is not None else None,
            "margin": num(r[m_votes]) if m_votes is not None else None,
            "margin_pct": num(r[m_pct]) if m_pct is not None else None,
            "turnout": num(r[turnout]) if turnout is not None else None,
        })
    seats = pd.DataFrame(rows).drop_duplicates("constituency")
    if seats["margin"].isna().all() and seats["votes"].notna().any() and seats["runner_up_votes"].notna().any():
        seats["margin"] = seats["votes"] - seats["runner_up_votes"]
    national_votes = national_votes_table(html)
    return build_result(seats, year, source, national_votes)


def build_result(seats: pd.DataFrame, year: int, source: str,
                 national_votes: pd.DataFrame | None = None) -> ElectionResult:
    """Aggregate constituency rows into districts and national totals."""
    drows = []
    for d, g in seats.dropna(subset=["district"]).groupby("district"):
        counts = g["winner"].value_counts()
        top = counts.index[0] if len(counts) else "Pending"
        if len(counts) > 1 and counts.iloc[0] == counts.iloc[1]:
            top = "Tie"
        has_margin = g["margin"].notna().any()
        drows.append({
            "unit": d, "winner": top, "seats": int(len(g)),
            "breakdown": ", ".join(f"{p} {n}" for p, n in counts.items()),
            "closest_seat": g.sort_values("margin").iloc[0]["constituency"] if has_margin else "",
            "closest_margin": g["margin"].min() if has_margin else None,
        })
    units = pd.DataFrame(drows)
    national = (seats.groupby("winner").size().rename("seats").reset_index()
                .rename(columns={"winner": "party"}))
    if national_votes is not None and "votes" in national_votes.columns and len(national_votes):
        national = national.merge(national_votes[["party", "votes", "vote_pct"]], on="party", how="left")
    national = national.sort_values("seats", ascending=False).reset_index(drop=True)
    return ElectionResult(
        country="Bangladesh", key=f"bd-ge-{year}", year=year,
        title=f"{year} General Election (Jatiya Sangsad)", kind="general", unit_label="District",
        units=units, national=national, total_seats=300, majority=151, seat_label="Seats", source=source,
        notes=["300 directly elected constituencies are grouped into 64 districts; a district is "
               "coloured by the party that won most of its seats. The 50 reserved women's seats are not shown."],
        detail=seats,
    )


def fill_from_members(res: ElectionResult, html: str) -> ElectionResult:
    """Fill constituencies the results table leaves blank from a 'List of members of the Nth Jatiya Sangsad'."""
    seats = res.detail
    if seats is None or not (seats["winner"] == "Pending").any():
        return res
    for t in tables(html, min_rows=100):
        cols = flat_cols(t)
        t.columns = range(len(cols))
        name_i = next((i for i in range(len(cols)) if t[i].astype(str).str.contains(r"^Dhaka-\d+$").any()), None)
        party_is = [i for i, c in enumerate(cols) if "party" in c.lower()]
        mp_i = next((i for i, c in enumerate(cols) if c.lower().startswith(("name", "member"))), None)
        if name_i is None or not party_is:
            continue
        lookup = {}
        for _, r in t.iterrows():
            p = next((clean(r[i]) for i in reversed(party_is) if clean(r[i]) and clean(r[i]).lower() != "nan"), "")
            lookup[clean(r[name_i])] = (party(p) if p else "Pending", clean(r[mp_i]) if mp_i is not None else "")
        seats = seats.copy()
        miss = seats["winner"] == "Pending"
        seats.loc[miss, "candidate"] = seats.loc[miss, "constituency"].map(lambda c: lookup.get(c, ("", ""))[1])
        seats.loc[miss, "winner"] = seats.loc[miss, "constituency"].map(lambda c: lookup.get(c, ("Pending",))[0])
        nv = res.national[[c for c in ("party", "votes", "vote_pct") if c in res.national.columns]]
        new = build_result(seats, res.year, res.source, nv if "votes" in nv.columns else None)
        new.notes.append(f"{int(miss.sum())} constituency winners taken from the list of members of parliament "
                         "because the results table had no figures for them.")
        return new
    return res


def national_votes_table(html: str) -> pd.DataFrame:
    """National vote totals per party from the article's party results table, when present."""
    for t in tables(html, min_rows=5):
        cols = flat_cols(t)
        lc = [c.lower() for c in cols]
        if not any(c.startswith("party") for c in lc) or not any(c.startswith("votes") for c in lc):
            continue
        if not any("seat" in c for c in lc):
            continue
        t.columns = range(len(cols))
        vi = next(i for i, c in enumerate(lc) if c.startswith("votes"))
        pi = next((i for i, c in enumerate(lc) if c.startswith("%")), None)
        votes = {}
        for _, r in t.iterrows():
            names = [clean(r[i]) for i in range(vi) if clean(r[i]) and clean(r[i]).lower() != "nan"]
            if not names:
                continue
            p = party(names[-1])
            v = num(r[vi])
            if v and v > 1000 and p not in votes:
                votes[p] = (v, num(r[pi]) if pi is not None else None)
        if len(votes) >= 3:
            return pd.DataFrame([{"party": p, "votes": v, "vote_pct": pc} for p, (v, pc) in votes.items()])
    return pd.DataFrame(columns=["party", "votes", "vote_pct"])
