"""Election Centre: an interactive, map-first results dashboard.

Bangladesh, United Kingdom and United States elections from 2016 onward,
fed live from Wikipedia with bundled snapshots as a fallback.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import colorsys
import datetime as dt
import html
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from election_data import geo, registry
from election_data.model import ElectionResult
from election_data.parties import color, color_map

st.set_page_config(page_title="Election Centre", page_icon="🗳️", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# Styling: newsroom look with motion (serif headlines, party stripes, animated bars)
# ---------------------------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap" rel="stylesheet">
<style>
:root { --ink:#121212; --muted:#5c5c5c; --rule:#e2e2e2; --live:#c8102e; }
html, body, [class*="css"], .stMarkdown, p, li, label, input, button { font-family: 'Inter', system-ui, sans-serif; }
.block-container { padding-top: .5rem; padding-bottom: 2rem; max-width: 1480px; }
header[data-testid="stHeader"] { height: 0; background: transparent; }
#MainMenu, footer { visibility: hidden; }
.masthead { display:flex; align-items:flex-end; justify-content:space-between; border-bottom: 3px solid var(--ink); padding: 8px 0 6px; margin-bottom: 8px; }
.masthead .brand { font-family:'Source Serif 4', Georgia, serif; font-weight:700; font-size: 30px; letter-spacing:-.5px; color:var(--ink); line-height:1; }
.masthead .brand span { color: var(--live); }
.masthead .tag { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
.kicker { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 2px 0 2px; }
.badge { display:inline-flex; align-items:center; gap:6px; font-size:10px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; padding:3px 7px; border-radius:2px; margin-right:6px; vertical-align: middle; }
.badge.live { background: var(--live); color:#fff; }
.badge.live::before { content:""; width:7px; height:7px; border-radius:50%; background:#fff; animation: pulse 1.4s infinite; }
.badge.final { background: #121212; color:#fff; }
.badge.snap { background: #eee; color:#333; }
@keyframes pulse { 0%{opacity:1} 50%{opacity:.25} 100%{opacity:1} }
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes rise { from { opacity:0; transform: translateY(10px); } to { opacity:1; transform: none; } }
.headline { font-family:'Source Serif 4', Georgia, serif; font-weight:700; font-size: 30px; line-height:1.08; color: var(--ink); margin: 2px 0 6px; letter-spacing: -.3px; animation: rise .5s ease-out both; }
.standfirst { font-size: 14px; color: #333; margin-bottom: 8px; animation: rise .6s ease-out both; }
.meta { font-size: 11px; color: var(--muted); margin: 4px 0 6px; }
.meta a { color: var(--muted); }
.seatbar { position: relative; display:flex; height: 34px; background:#efefef; margin: 22px 0 4px; transform-origin: left; animation: grow .9s cubic-bezier(.2,.8,.2,1) both; }
.seatbar .seg { height:100%; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; font-size: 13px; border-right: 1px solid #fff; transition: filter .15s; cursor: default; }
.seatbar .seg:hover { filter: brightness(1.15); }
.seatbar .maj { position:absolute; top:-18px; bottom:-4px; border-left: 2px dotted #121212; }
.seatbar .maj span { position:absolute; top:-2px; left:4px; font-size: 11px; white-space: nowrap; color:#121212; }
.plist { margin-top: 10px; }
.prow { display:grid; grid-template-columns: 6px 1fr auto auto; gap: 10px; align-items:center; padding: 7px 0; border-bottom: 1px solid #eee; animation: rise .45s ease-out both; }
.prow .sw { height: 30px; }
.prow .nm { font-weight: 700; font-size: 14px; line-height:1.15; }
.prow .nm small { display:block; font-weight: 500; color: var(--muted); font-size: 11px; }
.prow .st { font-size: 24px; font-weight: 800; font-variant-numeric: tabular-nums; text-align:right; }
.prow .ch { font-size: 11px; font-weight: 700; min-width: 54px; text-align:right; }
.up { color:#0a7d32; } .down { color:#b00020; } .flat { color: var(--muted); }
.prow .win { font-size: 9px; font-weight: 800; color:#fff; padding: 1px 5px; border-radius:2px; margin-left: 6px; vertical-align: 2px; }
.detail { max-height: 640px; overflow-y: auto; border: 1px solid var(--rule); border-top: 5px solid #999; padding: 12px 14px; background:#fff; animation: rise .35s ease-out both; }
.detail h3 { font-family:'Source Serif 4', Georgia, serif; font-size: 24px; margin: 0 0 2px; padding:0; }
.detail .sub { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
.cand { margin: 8px 0; }
.cand .top { display:flex; justify-content:space-between; font-size: 13px; }
.cand .top b { font-weight: 700; }
.cand .bar { height: 10px; background:#f0f0f0; margin-top: 3px; }
.cand .bar div { height:100%; transform-origin:left; animation: grow .8s cubic-bezier(.2,.8,.2,1) both; }
.chip { display:inline-block; font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 10px; color:#fff; margin: 2px 4px 2px 0; }
.section { font-family:'Source Serif 4', Georgia, serif; font-weight:700; font-size: 20px; border-top: 1px solid var(--ink); padding-top: 6px; margin: 14px 0 6px; }
.note { font-size: 11px; color: var(--muted); }
.hint { font-size: 12px; color: var(--muted); background: #f6f6f6; padding: 8px 10px; border-left: 3px solid var(--live); margin: 8px 0; }
div[data-testid="stTabs"] button p { font-weight: 600; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

COUNTRIES = {"Bangladesh": "🇧🇩 Bangladesh", "United Kingdom": "🇬🇧 United Kingdom",
             "United States": "🇺🇸 United States"}
NEUTRAL = "#d9d9d9"
# Plotly's geo maps need base-layer topojson; serve it from ./static so maps work without the plotly CDN.
MAP_CFG = {"displayModeBar": False, "scrollZoom": False, "topojsonURL": "./app/static/topojson/"}


# ---------------------------------------------------------------------------
# Data access (cached)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_catalogue() -> dict[str, list[registry.ElectionSpec]]:
    return registry.catalogue()


@st.cache_data(ttl=registry.LIVE_TTL, show_spinner=False)
def get_result(key: str, refresh_token: int = 0) -> dict:
    spec = spec_by_key(key)
    try:
        res = registry.load(spec, force_live=refresh_token > 0)
    except Exception as e:  # noqa: BLE001 - surfaced in the UI
        return {"error": str(e)}
    d = res.to_json()
    d["origin"] = res.origin
    return d


def spec_by_key(key: str) -> registry.ElectionSpec:
    for specs in get_catalogue().values():
        for s in specs:
            if s.key == key:
                return s
    raise KeyError(key)


def result(key: str, token: int = 0) -> ElectionResult | None:
    d = get_result(key, token)
    if not d or "error" in d:
        return None
    r = ElectionResult.from_json(d)
    r.origin = d.get("origin", "snapshot")
    return r


def previous_spec(spec: registry.ElectionSpec) -> registry.ElectionSpec | None:
    same = [s for s in get_catalogue()[spec.country] if s.kind == spec.kind and s.year < spec.year]
    return max(same, key=lambda s: s.year) if same else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def esc(x) -> str:
    return html.escape("" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x))


def fmt_int(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{int(x):,}"


def tint(hex_color: str, amount: float) -> str:
    """Lighten a colour towards white (amount 0..1)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = ll + (1 - ll) * amount
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def real_parties(res: ElectionResult) -> pd.DataFrame:
    return res.national[~res.national["party"].isin(["Pending", "Withheld", "Other/Pending"])]


def headline(res: ElectionResult) -> tuple[str, str]:
    nat = real_parties(res)
    if nat.empty or nat["seats"].sum() == 0:
        return "Results awaited", "No results have been declared yet."
    top = nat.iloc[0]
    declared = int(nat["seats"].sum())
    unit = res.seat_label.lower()
    who = top["party"]
    if res.kind == "presidential" and "candidate" in nat.columns and pd.notna(top.get("candidate")):
        who = str(top["candidate"]).split("/")[0]
    if top["seats"] >= res.majority:
        h = {"presidential": f"{who} wins the presidency",
             "house": f"{ {'Democratic': 'Democrats', 'Republican': 'Republicans'}.get(top['party'], top['party']) } win control of the House"}.get(res.kind, f"{top['party']} wins majority")
        s = f"{int(top['seats'])} of {res.total_seats} {unit}; {res.majority} needed."
    elif declared < res.total_seats:
        h = f"{who} ahead as results come in"
        s = f"{declared} of {res.total_seats} {unit} declared; {res.majority} needed."
    else:
        h = f"Hung parliament: {top['party']} largest party"
        s = f"{int(top['seats'])} {unit}, short of the {res.majority} needed."
    return h, s


# ---------------------------------------------------------------------------
# Map data preparation
# ---------------------------------------------------------------------------
def map_frame(res: ElectionResult, prev: ElectionResult | None) -> pd.DataFrame:
    """Units with location ids, previous winner and a strength measure for shading."""
    u = res.units.copy()
    if res.country == "United Kingdom":
        u["loc"] = u["key"]
    elif res.country == "United States":
        u["loc"] = u["code"]
    else:
        u["loc"] = u["unit"]

    if "prev_winner" not in u.columns or u["prev_winner"].isna().all():
        if prev is not None:
            u["prev_winner"] = u["unit"].map(dict(zip(prev.units["unit"], prev.units["winner"])))
        else:
            u["prev_winner"] = None

    u.loc[u["prev_winner"].isin(["Pending", "Withheld", "Tie"]), "prev_winner"] = None
    # strength: 0 = narrow, 1 = dominant (used for margin shading)
    if res.country == "United States" and res.kind == "presidential":
        u["strength"] = (u["margin_pct"].fillna(0) / 30).clip(0, 1)
        u["strength_label"] = u["margin_pct"].map(lambda m: f"won by {m:.1f} pts" if pd.notna(m) else "")
    elif res.country == "United States":
        tot = (u["seats_Democratic"] + u["seats_Republican"]).replace(0, 1)
        u["strength"] = (u["margin_seats"] / tot).clip(0, 1)
        u["strength_label"] = u.apply(lambda r: f"D {r['seats_Democratic']} – R {r['seats_Republican']}", axis=1)
    elif res.country == "Bangladesh" and res.detail is not None:
        d = res.detail
        share = d.groupby("district")["pct"].mean()
        u["strength"] = ((u["unit"].map(share).fillna(55) - 40) / 50).clip(0, 1)
        u["strength_label"] = u["unit"].map(share).map(lambda v: f"avg winning share {v:.0f}%" if pd.notna(v) else "")
    else:
        u["strength"] = 1.0
        u["strength_label"] = ""
    return u


def colour_units(u: pd.DataFrame, mode: str, focus: str | None) -> pd.DataFrame:
    u = u.copy()
    if mode == "Change":
        flipped = u["prev_winner"].notna() & (u["prev_winner"] != u["winner"])
        u["cat"] = u.apply(lambda r: f"{r['winner']} gain" if flipped[r.name] else "No change", axis=1)
        u["col"] = u.apply(lambda r: color(r["winner"]) if flipped[r.name] else "#e6e6e6", axis=1)
    elif mode == "Margin":
        def band(s):
            return "Safe" if s >= .5 else "Likely" if s >= .2 else "Lean"
        u["cat"] = u.apply(lambda r: f"{r['winner']} · {band(r['strength'])}", axis=1)
        u["col"] = u.apply(lambda r: tint(color(r["winner"]),
                                          {"Safe": 0, "Likely": .35, "Lean": .62}[band(r["strength"])]), axis=1)
    else:
        u["cat"] = u["winner"]
        u["col"] = u["winner"].map(color)
    if focus:
        mask = u["winner"] != focus
        u.loc[mask, "cat"] = "Other parties"
        u.loc[mask, "col"] = "#ececec"
    return u


def geojson_for(res: ElectionResult):
    if res.country == "Bangladesh":
        return geo.bangladesh()
    if res.country == "United Kingdom":
        return geo.uk_hexes(res.year)
    return None


def build_map(res: ElectionResult, u: pd.DataFrame, height: int, selected: str | None) -> go.Figure:
    cats = list(dict.fromkeys(u.sort_values("cat")["cat"]))
    # legend order: by count
    cats = list(u["cat"].value_counts().index)
    cmap = dict(zip(u["cat"], u["col"]))
    u = u.copy()
    u["hover"] = u.apply(lambda r: hover_text(res, r), axis=1)
    kwargs = dict(locations="loc", color="cat", color_discrete_map=cmap, category_orders={"cat": cats},
                  custom_data=["loc", "hover"])
    gj = geojson_for(res)
    if gj is not None:
        fig = px.choropleth(u, geojson=gj, **kwargs)
    else:
        fig = px.choropleth(u, locationmode="USA-states", scope="usa", **kwargs)
    fig.update_traces(hovertemplate="%{customdata[1]}<extra></extra>",
                      marker_line_color="#ffffff", marker_line_width=0.7)
    if selected is not None:
        sel = u[u["loc"] == selected]
        if len(sel):
            outline = dict(locations=sel["loc"], z=[1] * len(sel), showscale=False, hoverinfo="skip",
                           colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                           marker_line_color="#121212", marker_line_width=3)
            if gj is not None:
                fig.add_trace(go.Choropleth(geojson=gj, **outline))
            else:
                fig.add_trace(go.Choropleth(locationmode="USA-states", **outline))
    if gj is not None:
        fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)",
                        projection_type="mercator" if res.country == "Bangladesh" else "equirectangular")
    else:
        fig.update_geos(scope="usa", showlakes=False, bgcolor="rgba(0,0,0,0)", landcolor="#f4f4f4",
                        subunitcolor="#ffffff")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(title=None, orientation="h", yanchor="top", y=0.0, x=0.0,
                                  font=dict(size=12), itemclick="toggleothers", bgcolor="rgba(255,255,255,.8)"),
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor="#121212", font=dict(size=13, family="Inter")),
                      clickmode="event+select", dragmode=False)
    return fig


def hover_text(res: ElectionResult, r) -> str:
    name = f"<b>{esc(r['unit'])}</b>"
    if res.country == "Bangladesh":
        return (f"{name}<br>{esc(r['breakdown'])}<br><span style='color:#777'>{r['seats']} seats · "
                f"{esc(r['strength_label'])}</span><br><i>Click for constituencies</i>")
    if res.country == "United Kingdom":
        prev = r.get("prev_winner")
        chg = f"<br>{esc(r['winner'])} gain from {esc(prev)}" if prev and prev != r["winner"] else "<br>Hold"
        return f"{name}<br>{esc(r['member'])} ({esc(r['winner'])}){chg}"
    if res.kind == "presidential":
        return (f"{name}<br>{esc(r['winner'])} {r['winner_pct']:.1f}% · {esc(r['strength_label'])}"
                f"<br>{int(r['electoral_votes'])} electoral votes")
    return f"{name}<br>{esc(r['strength_label'])}"


def timeline_map(country: str, kind: str, height: int) -> go.Figure | None:
    """All elections of one kind as animation frames (press ▶ to play)."""
    specs = sorted([s for s in get_catalogue()[country] if s.kind == kind and not s.is_upcoming],
                   key=lambda s: s.year)
    frames = []
    for s in specs:
        r = result(s.key)
        if r is None:
            continue
        u = map_frame(r, None)
        if country == "United Kingdom":
            u["loc"] = ("2024:" if r.year >= 2024 else "2010:") + u["loc"]
        u["Election"] = str(s.year)
        frames.append(u)
    if len(frames) < 2:
        return None
    df = pd.concat(frames, ignore_index=True)
    parties = list(df["winner"].value_counts().index)
    kwargs = dict(locations="loc", color="winner", animation_frame="Election", hover_name="unit",
                  color_discrete_map=color_map(parties), category_orders={"winner": parties,
                  "Election": sorted(df["Election"].unique())})
    if country == "Bangladesh":
        fig = px.choropleth(df, geojson=geo.bangladesh(), **kwargs)
        fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    elif country == "United Kingdom":
        gj = {"type": "FeatureCollection", "features": []}
        for prefix, year in (("2010:", 2019), ("2024:", 2024)):
            for f in geo.uk_hexes(year)["features"]:
                gj["features"].append({**f, "id": prefix + f["id"]})
        fig = px.choropleth(df, geojson=gj, **kwargs)
        fig.update_geos(fitbounds="locations", visible=False)
    else:
        fig = px.choropleth(df, locationmode="USA-states", scope="usa", **kwargs)
        fig.update_geos(showlakes=False, landcolor="#f4f4f4")
    fig.update_traces(marker_line_color="#fff", marker_line_width=0.6)
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(title=None, orientation="h", y=1.02, x=0), geo=dict(bgcolor="rgba(0,0,0,0)"))
    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1400
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 500
    return fig


# ---------------------------------------------------------------------------
# Side panel components
# ---------------------------------------------------------------------------
def seat_bar_html(res: ElectionResult) -> str:
    nat = res.national[res.national["seats"] > 0]
    segs = []
    for _, r in nat.iterrows():
        w = r["seats"] / res.total_seats * 100
        label = int(r["seats"]) if w > 5 else ""
        segs.append(f'<div class="seg" style="width:{w:.3f}%;background:{color(r["party"])}" '
                    f'title="{esc(r["party"])}: {int(r["seats"])}">{label}</div>')
    maj = res.majority / res.total_seats * 100
    return (f'<div class="seatbar">{"".join(segs)}<div class="maj" style="left:{maj:.2f}%">'
            f'<span><b>{res.majority}</b> to win</span></div></div>')


def party_list_html(res: ElectionResult, prev: ElectionResult | None, limit: int = 8) -> str:
    nat = real_parties(res)
    nat = nat[nat["seats"] > 0] if (nat["seats"] > 0).any() else nat
    prev_seats = dict(zip(prev.national["party"], prev.national["seats"])) if prev is not None else {}
    rows = []
    for i, (_, r) in enumerate(nat.head(limit).iterrows()):
        p = r["party"]
        sub = []
        if "candidate" in nat.columns and pd.notna(r.get("candidate")):
            sub.append(esc(r["candidate"]))
        if "vote_pct" in nat.columns and pd.notna(r.get("vote_pct")):
            sub.append(f"{r['vote_pct']:.1f}% of vote")
        ch = ""
        if prev is not None and res.kind != "presidential":
            n = int(r["seats"]) - int(prev_seats.get(p, 0))
            ch = f'<span class="{"up" if n > 0 else "down" if n < 0 else "flat"}">{"+" if n > 0 else ""}{n}</span>'
        win = (f'<span class="win" style="background:{color(p)}">WIN</span>' if r["seats"] >= res.majority else "")
        rows.append(f'<div class="prow" style="animation-delay:{i * 60}ms"><div class="sw" style="background:{color(p)}"></div>'
                    f'<div class="nm">{esc(p)}{win}<small>{" · ".join(sub)}</small></div>'
                    f'<div class="st">{int(r["seats"])}</div><div class="ch">{ch}</div></div>')
    head = (f'<div class="note" style="display:flex;justify-content:space-between;margin-top:6px">'
            f'<span>{esc(res.seat_label)}</span><span>{"Change vs " + str(prev.year) if prev is not None and res.kind != "presidential" else ""}</span></div>')
    return head + '<div class="plist">' + "".join(rows) + "</div>"


def hemicycle(res: ElectionResult) -> go.Figure:
    """Parliament-style arc, one dot per seat, parties left→right by size."""
    n = res.total_seats
    rows = max(4, round(math.sqrt(n / 4)))
    radii = [1 + i * 0.9 / (rows - 1) for i in range(rows)]
    tot_r = sum(radii)
    counts = [round(n * r / tot_r) for r in radii]
    counts[-1] += n - sum(counts)
    pts = []
    for r, c in zip(radii, counts):
        for k in range(c):
            a = math.pi * (1 - k / max(c - 1, 1))
            pts.append((a, r))
    pts.sort(key=lambda p: (-p[0], p[1]))
    seq = []
    for _, r in res.national.iterrows():
        seq += [r["party"]] * int(r["seats"])
    seq += ["Pending"] * (n - len(seq))
    xs = [r * math.cos(a) for a, r in pts]
    ys = [r * math.sin(a) for a, r in pts]
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="markers", text=seq[:len(xs)],
                               marker=dict(color=[color(p) for p in seq[:len(xs)]],
                                           size=max(3.5, 10 - n / 100), line=dict(width=0)),
                               hovertemplate="%{text}<extra></extra>"))
    fig.add_annotation(x=0, y=0.15, text=f"<b>{int(real_parties(res)['seats'].max() or 0)}</b>",
                       showarrow=False, font=dict(size=22, family="Inter"))
    fig.update_layout(height=180, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      xaxis=dict(visible=False, range=[-2.0, 2.0]),
                      yaxis=dict(visible=False, range=[-0.05, 2.0], scaleanchor="x"),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def cand_bar(name: str, party: str, votes, pct, winner: bool) -> str:
    pct_txt = f"{pct:.1f}%" if pct is not None and not pd.isna(pct) else ""
    width = pct if pct is not None and not pd.isna(pct) else (100 if winner else 0)
    return (f'<div class="cand"><div class="top"><span>{"<b>" if winner else ""}{esc(name) or esc(party)}'
            f'{"</b> ✓" if winner else ""} <span class="note">{esc(party)}</span></span>'
            f'<span>{fmt_int(votes)} <span class="note">{pct_txt}</span></span></div>'
            f'<div class="bar"><div style="width:{width:.1f}%;background:{color(party)}"></div></div></div>')


def detail_panel(res: ElectionResult, u: pd.DataFrame, loc: str) -> None:
    row = u[u["loc"] == loc]
    if row.empty:
        return
    r = row.iloc[0]
    prev = r.get("prev_winner")
    status = (f"{esc(r['winner'])} gain from {esc(prev)}" if prev and isinstance(prev, str) and prev != r["winner"]
              else f"{esc(r['winner'])} hold" if prev else esc(r["winner"]))
    out = [f'<div class="detail" style="border-top-color:{color(r["winner"])}"><h3>{esc(r["unit"])}</h3>'
           f'<div class="sub">{status}</div>']
    if res.country == "Bangladesh" and res.detail is not None:
        seats = res.detail[res.detail["district"] == r["unit"]]
        out.append(f'<div class="note">{len(seats)} constituencies</div>')
        for _, s in seats.iterrows():
            out.append(f'<div style="margin-top:10px;font-weight:700;font-size:13px">{esc(s["constituency"])}'
                       f'<span class="chip" style="background:{color(s["winner"])};margin-left:6px">{esc(s["winner"])}</span></div>')
            out.append(cand_bar(s["candidate"], s["winner"], s["votes"], s["pct"], True))
            if s.get("runner_up") and s["runner_up"] != "Pending":
                rp = (s["runner_up_votes"] / s["votes"] * s["pct"]) if s["votes"] and s["pct"] and s["runner_up_votes"] else None
                out.append(cand_bar(s["runner_up_candidate"], s["runner_up"], s["runner_up_votes"], rp, False))
    elif res.country == "United Kingdom":
        out.append(f'<div style="font-size:15px"><b>{esc(r["member"])}</b> elected</div>')
        if r.get("notes"):
            out.append(f'<div class="note" style="margin-top:6px">{esc(r["notes"])}</div>')
    elif res.kind == "presidential":
        parties = sorted([c[4:] for c in u.columns if c.startswith("pct_")],
                         key=lambda p: -(r.get(f"pct_{p}") or 0))
        for p in parties:
            if r.get(f"pct_{p}"):
                out.append(cand_bar(p, p, r.get(f"votes_{p}"), r.get(f"pct_{p}"), p == r["winner"]))
        out.append(f'<div class="note">{int(r["electoral_votes"])} electoral votes · {fmt_int(r["total_votes"])} votes cast</div>')
    else:
        tot = r["seats_Democratic"] + r["seats_Republican"]
        for p in ("Democratic", "Republican"):
            v = r[f"seats_{p}"]
            out.append(cand_bar(p, p, v, v / tot * 100 if tot else 0, p == r["winner"]))
    out.append("</div>")
    st.markdown("".join(out), unsafe_allow_html=True)


def close_races_html(res: ElectionResult) -> str:
    if res.country == "Bangladesh" and res.detail is not None and res.detail["margin"].notna().any():
        d = res.detail.dropna(subset=["margin"]).nsmallest(6, "margin")
        rows = [(r["constituency"], r["winner"], f"by {fmt_int(r['margin'])} votes over {r['runner_up']}")
                for _, r in d.iterrows()]
    elif res.country == "United States" and res.kind == "presidential":
        d = res.units.dropna(subset=["margin_pct"]).nsmallest(6, "margin_pct")
        rows = [(r["unit"], r["winner"], f"by {r['margin_pct']:.1f} pts") for _, r in d.iterrows()]
    else:
        return ""
    items = "".join(f'<div class="prow" style="grid-template-columns:6px 1fr;animation-delay:{i * 50}ms">'
                    f'<div class="sw" style="background:{color(p)}"></div><div class="nm">{esc(n)}'
                    f'<small>{esc(p)} {esc(t)}</small></div></div>' for i, (n, p, t) in enumerate(rows))
    return '<div class="section">Closest races</div>' + items


# ---------------------------------------------------------------------------
# Below-the-map sections
# ---------------------------------------------------------------------------
def results_table(res: ElectionResult) -> None:
    if res.country == "Bangladesh" and res.detail is not None:
        d = res.detail.copy()
        c1, c2 = st.columns(2)
        q = c1.text_input("Search constituency or candidate", placeholder="e.g. Dhaka-10 or Rahman")
        dist = c2.selectbox("District", ["All districts"] + sorted(d["district"].dropna().unique()))
        if q:
            d = d[d["constituency"].str.contains(q, case=False, na=False)
                  | d["candidate"].str.contains(q, case=False, na=False)
                  | d["runner_up_candidate"].str.contains(q, case=False, na=False)]
        if dist != "All districts":
            d = d[d["district"] == dist]
        cols = ["constituency", "winner", "candidate", "votes", "pct", "runner_up", "runner_up_candidate",
                "margin", "margin_pct"]
        st.dataframe(d[cols], hide_index=True, width="stretch", height=480, column_config={
            "constituency": "Seat", "winner": "Winning party", "candidate": "Winner",
            "votes": st.column_config.NumberColumn("Votes", format="localized"),
            "pct": st.column_config.ProgressColumn("Share", format="%.1f%%", min_value=0, max_value=100),
            "runner_up": "Runner-up party", "runner_up_candidate": "Runner-up",
            "margin": st.column_config.NumberColumn("Majority", format="localized"),
            "margin_pct": st.column_config.NumberColumn("Majority %", format="%.1f%%")})
    elif res.country == "United Kingdom":
        d = res.units.copy()
        c1, c2 = st.columns(2)
        q = c1.text_input("Search constituency or MP", placeholder="e.g. Holborn or Starmer")
        party = c2.selectbox("Party", ["All parties"] + list(res.national["party"]))
        if q:
            d = d[d["unit"].str.contains(q, case=False, na=False) | d["member"].str.contains(q, case=False, na=False)]
        if party != "All parties":
            d = d[d["winner"] == party]
        st.dataframe(d[["unit", "winner", "prev_winner", "member", "notes"]], hide_index=True,
                     width="stretch", height=480,
                     column_config={"unit": "Constituency", "winner": "Party", "prev_winner": "Previously",
                                    "member": "MP elected", "notes": "Notes"})
    elif res.kind == "presidential":
        d = res.units.copy()
        parties = [c[4:] for c in d.columns if c.startswith("pct_")][:2]
        cfg = {"unit": "State", "winner": "Winner", "electoral_votes": "EV",
               "margin_pct": st.column_config.NumberColumn("Margin (pts)", format="%.1f"),
               "total_votes": st.column_config.NumberColumn("Total votes", format="localized")}
        for p in parties:
            cfg[f"pct_{p}"] = st.column_config.ProgressColumn(p, format="%.1f%%", min_value=0, max_value=100)
        cols = ["unit", "winner", "electoral_votes"] + [f"pct_{p}" for p in parties] + ["margin_pct", "total_votes"]
        st.dataframe(d[cols].sort_values("margin_pct"), hide_index=True, width="stretch",
                     height=480, column_config=cfg)
    else:
        st.dataframe(res.units[["unit", "winner", "seats_Democratic", "seats_Republican"]], hide_index=True,
                     width="stretch", height=480,
                     column_config={"unit": "State", "winner": "Delegation majority",
                                    "seats_Democratic": "Democratic", "seats_Republican": "Republican"})


def history(country: str) -> None:
    specs = [s for s in get_catalogue()[country] if not s.is_upcoming]
    for kind in sorted({s.kind for s in specs}, key=["presidential", "house", "general"].index):
        rows = []
        for s in sorted([s for s in specs if s.kind == kind], key=lambda s: s.year):
            r = result(s.key)
            if r is None:
                continue
            for _, p in r.national.iterrows():
                if p["seats"] > 0 and p["party"] not in ("Pending", "Withheld", "Other/Pending"):
                    rows.append({"Election": str(s.year), "party": p["party"], "seats": int(p["seats"])})
        if not rows:
            continue
        df = pd.DataFrame(rows)
        big = df.groupby("party")["seats"].max()
        df["party"] = df["party"].where(df["party"].isin(big[big > 2].index), "Other")
        df = df.groupby(["Election", "party"], as_index=False)["seats"].sum()
        order = df.groupby("party")["seats"].sum().sort_values(ascending=False).index.tolist()
        title = {"presidential": "Electoral votes", "house": "House seats", "general": "Seats won"}[kind]
        st.markdown(f'<div class="section">{title} by party, {df["Election"].min()}–{df["Election"].max()}</div>',
                    unsafe_allow_html=True)
        fig = px.bar(df, x="Election", y="seats", color="party", text="seats",
                     color_discrete_map=color_map(df["party"].unique()), category_orders={"party": order})
        fig.update_traces(textposition="inside", textfont=dict(color="#fff", size=12),
                          marker_line_color="#fff", marker_line_width=1)
        fig.update_layout(height=380, bargap=0.35, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(title=None, orientation="h", y=-0.15),
                          yaxis=dict(title=None, gridcolor="#eee"), xaxis=dict(title=None, type="category"),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.markdown(f'<div class="masthead"><div class="brand">Election<span>Centre</span></div>'
            f'<div class="tag">Bangladesh · United Kingdom · United States · {registry.FIRST_YEAR}–{dt.date.today().year}'
            f' · {dt.date.today():%d %b %Y}</div></div>', unsafe_allow_html=True)

catalogue = get_catalogue()
c1, c2, c3 = st.columns([2.2, 2.2, 1])
with c1:
    country = st.segmented_control("Country", list(COUNTRIES), format_func=COUNTRIES.get, default="Bangladesh",
                                   label_visibility="collapsed") or "Bangladesh"
specs = catalogue[country]
labels = {s.key: s.label + (" · upcoming" if s.is_upcoming else " · LIVE" if s.is_recent else "") for s in specs}
with c2:
    key = st.selectbox("Election", [s.key for s in specs], format_func=labels.get, label_visibility="collapsed",
                       key=f"election_{country}")
with c3:
    if st.button("↻ Refresh live", width="stretch",
                 help="Fetch the latest version from Wikipedia now, bypassing caches."):
        st.session_state[f"refresh_{key}"] = st.session_state.get(f"refresh_{key}", 0) + 1
spec = spec_by_key(key)


def render() -> None:
    token = st.session_state.get(f"refresh_{key}", 0)
    if spec.is_upcoming:
        st.markdown(f'<div class="headline">{esc(spec.label)}</div><div class="standfirst">Polling day is '
                    f'{spec.date:%d %B %Y}. Results will appear here automatically.</div>', unsafe_allow_html=True)
        return
    with st.spinner("Loading results…"):
        res = result(key, token)
    if res is None:
        st.error(f"Results for {spec.label} are not available yet ({get_result(key, token).get('error', '')}). "
                 "The page keeps retrying.")
        return
    ps = previous_spec(spec)
    prev = result(ps.key) if ps else None

    # --- map controls ---
    modes = ["Winner", "Change", "Margin", "Timeline"]
    if res.country == "United Kingdom":
        modes.remove("Margin")
    m1, m2 = st.columns([3, 2])
    with m1:
        mode = st.segmented_control("Map view", modes, default="Winner", key=f"mode_{key}",
                                    format_func={"Winner": "🏆 Winner", "Change": "🔄 Seats changed hands",
                                                 "Margin": "📊 Margin", "Timeline": "▶ Timeline"}.get,
                                    label_visibility="collapsed") or "Winner"
    with m2:
        parties = ["All parties"] + list(real_parties(res)[real_parties(res)["seats"] > 0]["party"])
        focus = st.selectbox("Highlight party", parties, key=f"focus_{key}", label_visibility="collapsed",
                             disabled=mode == "Timeline")
    focus = None if focus == "All parties" else focus

    u = map_frame(res, prev)
    sel_key = f"sel_{key}"
    selected = st.session_state.get(sel_key)

    col_map, col_side = st.columns([2.15, 1], gap="large")
    with col_map:
        height = {"Bangladesh": 760, "United Kingdom": 800, "United States": 600}[res.country]
        if mode == "Timeline":
            fig = timeline_map(res.country, res.kind, height)
            if fig is None:
                st.info("Not enough past elections to animate.")
            else:
                st.plotly_chart(fig, width="stretch", config=MAP_CFG)
                st.markdown('<div class="hint">Press ▶ to watch how the map changed, election by election.</div>',
                            unsafe_allow_html=True)
        else:
            fig = build_map(res, colour_units(u, mode, focus), height, selected)
            ev = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points",
                                 key=f"map_{key}_{mode}_{focus}",
                                 config=MAP_CFG)
            pts = (ev or {}).get("selection", {}).get("points", []) if ev else []
            if pts:
                loc = pts[0].get("location") or (pts[0].get("customdata") or [None])[0]
                if loc and loc != selected:
                    st.session_state[sel_key] = loc
                    st.rerun()
            if mode == "Change":
                n = int((u["prev_winner"].notna() & (u["prev_winner"] != u["winner"])).sum())
                base = "previous holder" if res.country == "United Kingdom" else str(prev.year) if prev else "previous"
                st.markdown(f'<div class="hint"><b>{n}</b> {res.unit_label.lower()}{"s" if n != 1 else ""} '
                            f'changed hands vs {base}.</div>', unsafe_allow_html=True)
            for n in res.notes:
                st.markdown(f'<div class="note">{esc(n)}</div>', unsafe_allow_html=True)

    with col_side:
        h, s = headline(res)
        badge = ('<span class="badge live">Live</span>' if spec.is_recent else '<span class="badge final">Final</span>')
        when = dt.datetime.fromtimestamp(res.fetched_at).strftime("%d %b %Y %H:%M") if res.fetched_at else "—"
        origin = {"live": "live", "cache": "cached", "snapshot": "archived"}[res.origin]
        st.markdown(f'<div class="kicker">{badge}{esc(res.title)}</div><div class="headline">{esc(h)}</div>'
                    f'<div class="standfirst">{esc(s)}</div>{seat_bar_html(res)}', unsafe_allow_html=True)
        if selected and selected in set(u["loc"]):
            detail_panel(res, u, selected)
            if st.button("← Back to national result", width="stretch"):
                st.session_state.pop(sel_key, None)
                st.rerun()
        else:
            st.markdown('<div class="hint">Click any area on the map for local results.</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(hemicycle(res), width="stretch", config={"displayModeBar": False})
            st.markdown(party_list_html(res, prev), unsafe_allow_html=True)
            st.markdown(close_races_html(res), unsafe_allow_html=True)
        st.markdown(f'<div class="meta">Polling day {spec.date:%d %b %Y} · data {origin} {when} · '
                    f'<a href="{esc(res.source)}" target="_blank">Source: Wikipedia</a></div>',
                    unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([f"📋 All {res.unit_label.lower()} results", f"📈 History {registry.FIRST_YEAR}–{dt.date.today().year}",
                          "ℹ️ About the data"])
    with t1:
        results_table(res)
    with t2:
        history(country)
    with t3:
        st.markdown(f"""
**Source.** Results are read from the English Wikipedia article for each election
([{esc(res.source.rsplit('/', 1)[-1].replace('_', ' '))}]({res.source})) through the Wikimedia REST API.
Editors update these articles continuously on election night, so they act as a free live feed for all three
countries. Official sources: Bangladesh Election Commission, UK House of Commons Library, US state election offices.

**Live updates.** Elections from the last {registry.LIVE_WINDOW_DAYS} days are re-fetched every
{registry.LIVE_TTL // 60} minutes and the page refreshes itself. Settled elections load from snapshots bundled
with the app (`python scripts/refresh_snapshots.py` rebuilds them), so the dashboard still works if Wikipedia is
unreachable or rate-limits requests.

**Future elections.** US presidential and House elections are added automatically from the November calendar.
New UK and Bangladeshi general elections are found when Wikipedia's *Next … general election* article moves to
a dated title.

**Maps.** Bangladesh district boundaries: geoBoundaries (CC BY 4.0). UK constituency hex maps: ODI Leeds.
US states: Plotly.
""")


if spec.is_recent or spec.is_upcoming:
    st.fragment(run_every=registry.LIVE_TTL)(render)()
else:
    render()
