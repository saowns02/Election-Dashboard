# Election Centre

An interactive, map-first election results dashboard for **Bangladesh**, the **United Kingdom** and the **United States**, covering every national election from 2016 to today. It is fed live from Wikipedia and adds new elections as they happen.

## What you can do

- **Explore the map**: Bangladesh by district (64), the UK by constituency (650 equal-size hexagons) and the US by state.
- **Click any area** to open its local results: every constituency in a Bangladeshi district with winner and runner-up vote bars, the elected MP for a UK seat, or a state's vote split.
- **Switch map views**:
  - **Winner**: who won each area.
  - **Seats changed hands**: gains compared with the previous election.
  - **Margin**: safe, likely or lean seats.
  - **Timeline**: press ▶ to watch the map change election by election.
- **Highlight a party** to fade out the rest of the map.
- **Read the national picture** beside the map: headline, seat bar with the majority line, a parliament arc and party totals with seat change.
- **Search and sort** every constituency or state below the map, and see seat history from 2016 to today.

## Elections included

| Country | Elections |
|---|---|
| Bangladesh | 2018, 2024, 2026 general elections (Jatiya Sangsad, 300 seats) |
| United Kingdom | 2017, 2019, 2024 general elections (650 seats) |
| United States | 2016, 2020, 2024 presidential; 2016–2026 House of Representatives |

## Live data and future elections

Results are read from the English Wikipedia article for each election through the Wikimedia REST API. Editors update these articles continuously on election night.

- **Recent elections** (the last 30 days) are re-fetched every 5 minutes, and the page refreshes itself. A **Live** badge marks them.
- **Settled elections** load from snapshots bundled in `data/snapshots/`, so the app still works if Wikipedia is down or rate-limits requests. Rebuild the snapshots with `python scripts/refresh_snapshots.py`.
- **New elections** are added automatically:
  - US presidential and House elections come from the fixed November calendar.
  - UK and Bangladeshi general elections are detected when Wikipedia's *Next … general election* article moves to a dated title.

Wikipedia is not an official source. For official figures, see the Bangladesh Election Commission, the House of Commons Library and US state election offices.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (free) on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app** and choose this repository, the branch, and `app.py` as the main file.
3. Click **Deploy**. You get a public `*.streamlit.app` URL.

## Project layout

```
app.py                     Streamlit UI (map, side panel, tables, history)
election_data/
  registry.py              election catalogue, live/snapshot loading, auto-discovery
  wiki.py                  Wikimedia REST client with disk cache and back-off
  bd.py, uk.py, us.py      per-country parsers
  geo.py                   map geometry (district polygons, UK hex grid)
  parties.py               party names and colours
data/snapshots/            bundled results
data/geo/                  boundary files
static/topojson/           Plotly base-map files, served locally
scripts/refresh_snapshots.py
```

## Credits

- Results: Wikipedia contributors (CC BY-SA 4.0)
- Bangladesh district boundaries: [geoBoundaries](https://www.geoboundaries.org) (CC BY 4.0)
- UK constituency hex maps: [ODI Leeds HexMaps](https://github.com/odileeds/hexmaps)
- Base-map topojson: [plotly.js](https://github.com/plotly/plotly.js) (MIT)
