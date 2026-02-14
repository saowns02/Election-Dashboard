import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import numpy as np
import time

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Bangladesh Election 2026 - Live Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for "Dark Mode" Broadcast look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .metric-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #41444b;
        text-align: center;
    }
    h1, h2, h3 {
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DATA LOADING & CACHING
# ---------------------------------------------------------
@st.cache_data
def load_map_data():
    # Robust dual-source loading
    url_primary = "https://raw.githubusercontent.com/fahim-muntasir-niloy/Bangladesh-geojson_project/master/Geo%20Json%20Maps/bangladesh_geojson_adm2_64_districts_zillas.json"
    url_backup = "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/BGD/ADM2/geoBoundaries-BGD-ADM2.geojson"
    
    try:
        gdf = gpd.read_file(url_primary)
    except:
        try:
            gdf = gpd.read_file(url_backup)
        except:
            return None
            
    # Normalize district names column
    possible_cols = ['ADM2_EN', 'shapeName', 'name', 'NAME_2', 'dist_name']
    for col in possible_cols:
        if col in gdf.columns:
            gdf = gdf.rename(columns={col: 'District'})
            break
            
    return gdf

# ---------------------------------------------------------
# 3. LIVE DATA SIMULATION ENGINE
# ---------------------------------------------------------
def get_live_data(gdf):
    """
    Simulates live counting. In a real app, this would fetch 
    from an API or a CSV file updated by field agents.
    """
    districts = gdf['District'].unique()
    
    # Create a simulated dataframe
    data = []
    
    # Define regional biases (The "Model")
    bnp_strongholds = ['Bogra', 'Sirajganj', 'Khulna', 'Rajshahi', 'Barisal']
    jp_strongholds = ['Rangpur', 'Gaibandha', 'Kurigram']
    alliance_strongholds = ['Satkhira', 'Comilla', 'Feni', 'Cox\'s Bazar']
    battlegrounds = ['Dhaka', 'Chittagong', 'Gazipur', 'Narayanganj']
    
    total_seats_declared = 0
    
    for district in districts:
        # Randomized "Reporting Status" (0% to 100% counted)
        # We use time to simulate progression if we wanted, 
        # but here we randomize to show "Live" nature on refresh.
        reporting_percent = np.random.randint(20, 100)
        
        # Determine likely winner based on region + random swing
        d_name = str(district)
        
        if d_name in bnp_strongholds:
            lead = "BNP"
            margin = np.random.randint(5000, 50000)
        elif d_name in jp_strongholds:
            lead = "Jatiya Party"
            margin = np.random.randint(1000, 20000)
        elif d_name in alliance_strongholds:
            lead = "11-Party Alliance"
            margin = np.random.randint(2000, 15000)
        elif d_name in battlegrounds:
            # Coin toss in battlegrounds
            lead = np.random.choice(["BNP", "11-Party Alliance"])
            margin = np.random.randint(100, 5000) # Close fight
        else:
            # Rural generic bias to BNP
            lead = np.random.choice(["BNP", "11-Party Alliance"], p=[0.7, 0.3])
            margin = np.random.randint(1000, 10000)
            
        # Status
        status = "Declared" if reporting_percent > 90 else f"Counting ({reporting_percent}%)"
        if status == "Declared":
            total_seats_declared += 1
            
        data.append({
            "District": d_name,
            "Leading Party": lead,
            "Margin": margin,
            "Status": status,
            "Reporting": reporting_percent
        })
        
    return pd.DataFrame(data)

# ---------------------------------------------------------
# 4. DASHBOARD LAYOUT
# ---------------------------------------------------------

# Title Section
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🗳️ Bangladesh Election 2026")
    st.markdown("### Live Results & Analytical Dashboard")
with col2:
    if st.button("🔄 Refresh Data"):
        st.rerun()
    st.caption(f"Last Updated: {time.strftime('%H:%M:%S')}")

# Load Data
gdf = load_map_data()

if gdf is not None:
    # Get "Live" Data
    live_df = get_live_data(gdf)
    
    # Merge for Map
    map_df = gdf.merge(live_df, on="District")
    
    # --- TOP METRICS ROW ---
    # Aggregate stats
    party_counts = live_df[live_df['Status'] == 'Declared']['Leading Party'].value_counts()
    
    bnp_seats = party_counts.get("BNP", 0) + 120 # Padding to simulate national total, not just districts
    alliance_seats = party_counts.get("11-Party Alliance", 0) + 40
    jp_seats = party_counts.get("Jatiya Party", 0) + 10
    
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric(label="Total Seats Declared", value=f"{int(bnp_seats + alliance_seats + jp_seats)} / 300", delta="Live")
    with m2:
        st.metric(label="BNP (Sheaf)", value=bnp_seats, delta=f"Lead: {bnp_seats - alliance_seats}")
    with m3:
        st.metric(label="Alliance (Scale)", value=alliance_seats, delta="-Trailing")
    with m4:
        st.metric(label="Jatiya Party", value=jp_seats, delta="Stable")

    st.markdown("---")

    # --- MAIN VISUALIZATION ROW ---
    c_map, c_table = st.columns([2, 1])
    
    with c_map:
        st.subheader("📍 Live District Map")
        
        # Color Map matching the NYT style
        color_discrete_map = {
            "BNP": "#006d2c",           # Green
            "11-Party Alliance": "#d95f02", # Orange
            "Jatiya Party": "#e6ab02",  # Gold
        }
        
        fig = px.choropleth_mapbox(
            map_df,
            geojson=map_df.geometry,
            locations=map_df.index,
            color="Leading Party",
            hover_name="District",
            hover_data=["Margin", "Status"],
            color_discrete_map=color_discrete_map,
            mapbox_style="carto-positron",
            center={"lat": 23.6850, "lon": 90.3563},
            zoom=5.5,
            opacity=0.7,
            height=600
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)

    with c_table:
        st.subheader("📊 Key Battlegrounds")
        
        # Filter for close races (Margin < 5000)
        close_races = live_df[live_df['Margin'] < 5000].sort_values('Margin')
        
        st.dataframe(
            close_races[['District', 'Leading Party', 'Margin', 'Reporting']],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Reporting": st.column_config.ProgressColumn(
                    "Counted %", format="%d%%", min_value=0, max_value=100
                ),
                "Margin": st.column_config.NumberColumn(
                    "Vote Margin", format="%d 🗳️"
                )
            }
        )
        
        st.markdown("### 🚨 Flash Updates")
        st.info("Dhaka-10: BNP candidate claims voting irregularities in 3 centers.")
        st.success("Bogra-6: Tarique Rahman declared winner by 150,000+ votes.")
        st.warning("Chittagong: Counting delayed due to server issues.")

else:
    st.error("Could not load map data. Please check internet connection.")