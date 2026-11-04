# Bangladesh Election 2026 Dashboard

A Streamlit prototype of a broadcast-style election night dashboard for Bangladesh, with a district-level results map, national seat tally and a close-races table.

> **Note:** all results in this dashboard are simulated. The app generates random vote margins and counting progress on every refresh to demonstrate how a live results page could look. It does not show real or official election results.

## Features

- **District map**: a choropleth of Bangladesh's 64 districts, shaded by the leading party, with vote margin and counting status on hover.
- **Seat tally**: headline metrics for seats declared out of 300 and seats won by each party.
- **Key battlegrounds**: a table of races with a margin under 5,000 votes, sorted closest first, with a progress bar for the share of votes counted.
- **Flash updates**: sample news alerts in the style of a live results feed.
- **Refresh button**: reruns the simulation to mimic results coming in.

## How the simulation works

For each district, the app:

1. Picks a random counting progress between 20% and 99%, and marks the district as declared once it passes 90%.
2. Assigns a leading party using simple regional rules. Named strongholds go to a set party, named battleground districts are a coin toss between the two largest blocs, and all other districts lean 70/30.
3. Draws a random vote margin, with tighter ranges in battleground districts.

The national tally adds a fixed baseline to each party's declared districts, so the totals read like a 300-seat parliament rather than a 64-district count.

To use real data, replace `get_live_data()` in `app.py` with a function that returns a DataFrame with the same columns (`District`, `Leading Party`, `Margin`, `Status`, `Reporting`) from an API or a regularly updated CSV.

## Map data

District boundaries load at startup from public GeoJSON sources, trying the first and falling back to the second:

- [Bangladesh GeoJSON project](https://github.com/fahim-muntasir-niloy/Bangladesh-geojson_project) (64 districts)
- [geoBoundaries](https://github.com/wmgeolab/geoBoundaries) (BGD ADM2)

An internet connection is needed to load the map.

## Tech stack

Python, Streamlit, Plotly Express, GeoPandas, pandas and NumPy.

## Getting started

Requires Python 3.9 or later.

```bash
git clone https://github.com/saowns02/Election-Dashboard.git
cd Election-Dashboard
pip install streamlit pandas geopandas plotly numpy
streamlit run app.py
```

Streamlit opens the dashboard in your browser, usually at `http://localhost:8501`.

## Project structure

```
└── app.py   # Page setup, map loading, results simulation and dashboard layout
```
