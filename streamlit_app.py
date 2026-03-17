import io
import os
from typing import List, Dict

import streamlit as st
import pandas as pd
import requests

from app import get_odds, find_arbitrage, compute_stakes
from data_store import save_snapshot, load_master, save_detailed_odds


st.set_page_config(page_title="Sports Bet Arbitrage", layout="wide")

st.title("🏀 Sports Bet — Arbitrage Finder")
st.markdown("**Live odds scanning for guaranteed wins across bookmakers**")

# Team logo mapping (expand as needed)
TEAM_LOGOS = {
    "Charlotte Hornets": "https://upload.wikimedia.org/wikipedia/en/c/c4/Charlotte_Hornets_logo.png",
    "Miami Heat": "https://upload.wikimedia.org/wikipedia/en/f/fb/Miami_Heat_logo.png",
    "Boston Celtics": "https://upload.wikimedia.org/wikipedia/en/1/10/Boston_Celtics.svg",
    "Los Angeles Lakers": "https://upload.wikimedia.org/wikipedia/en/3/3c/Los_Angeles_Lakers.svg",
}

# Fetch available sports from API
@st.cache_data(ttl=3600)
def get_available_sports(api_key):
    try:
        resp = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}")
        if resp.status_code == 200:
            sports = resp.json()
            return {s['title']: s['key'] for s in sports}
        return {"NBA": "basketball_nba", "NFL": "americanfootball_nfl", "MLB": "baseball_mlb"}
    except:
        return {"NBA": "basketball_nba", "NFL": "americanfootball_nfl", "MLB": "baseball_mlb"}

with st.sidebar:
    st.subheader("⚙️ Settings")
    
    api_key = st.text_input("API Key", value=os.environ.get('ODDS_API_KEY', ''), type='password')
    
    if api_key:
        sports_map = get_available_sports(api_key)
        sport_name = st.selectbox("Sport", list(sports_map.keys()), index=0)
        sport = sports_map[sport_name]
    else:
        sport = st.text_input("Sport code (e.g., basketball_nba)", value="basketball_nba")
    
    region = st.selectbox("Region", ["us", "eu", "uk", "au"], index=0)
    
    markets = st.multiselect(
        "Bet Types",
        ["h2h", "spreads", "totals"],
        default=["h2h"]
    )
    
    if not markets:
        markets = ["h2h"]
    
    markets_str = ",".join(markets)
    
    stake = st.number_input("Total stake (for calculations)", value=100.0, min_value=1.0)
    refresh_seconds = st.slider("Auto-refresh (seconds)", min_value=10, max_value=600, value=60, step=10)
    auto_refresh = st.checkbox("Enable auto-refresh", value=True)
    arb_threshold = st.number_input("Max Arb Value (<=)", value=0.99, step=0.001, format="%.3f")
    team_filter = st.text_input("Team filter (optional)", value="")
    
    st.divider()
    submit = st.button("🔍 Fetch Odds", use_container_width=True)

# cached fetch using TTL so auto-refresh works without rerunning entire script
@st.cache_data(ttl=0)
def cached_get_odds_no_cache(api_key, sport, region, markets_str):
    return get_odds(api_key, sport, region, markets_str)

def cached_get_odds(api_key, sport, region, markets_str, ttl):
    if ttl <= 0:
        return cached_get_odds_no_cache(api_key, sport, region, markets_str)

    @st.cache_data(ttl=ttl)
    def _f(k, s, r, m):
        return get_odds(k, s, r, m)

    return _f(api_key, sport, region, markets_str)

if not api_key:
    st.warning("Provide an API key in the sidebar or set the ODDS_API_KEY environment variable.")

if submit and api_key:
    with st.spinner("Fetching odds..."):
        if auto_refresh:
            data = cached_get_odds(api_key, sport, region, markets_str, refresh_seconds)
        else:
            data = cached_get_odds_no_cache(api_key, sport, region, markets_str)

    if not data:
        st.info("No data returned from the API.")
    else:
        # Save detailed bookmaker-level odds for line movement tracking
        save_detailed_odds(data)
        
        arbs = find_arbitrage(data)

        # build rows
        rows: List[Dict] = []
        for arb in arbs:
            teams = arb["teams"]
            best = arb["odds"]
            arb_value = arb["arb_value"]
            if arb_value > arb_threshold:
                continue
            team_names = list(best.keys())
            odds_vals = [best[team_names[0]], best[team_names[1]]]
            stake_a, stake_b, profit, profit_pct = compute_stakes(odds_vals[0], odds_vals[1], total=stake)

            row = {
                "Match": " vs ".join(teams),
                "Team A": team_names[0],
                "Odds A": odds_vals[0],
                "Team B": team_names[1],
                "Odds B": odds_vals[1],
                "Arb": round(arb_value, 4),
                "Stake A": stake_a,
                "Stake B": stake_b,
                "Profit": profit,
                "Profit %": profit_pct,
            }

            # apply filters
            if bookmaker_filter:
                # naive filter: include only if any bookmaker substring present in raw JSON
                # since we don't show bookmaker name in row, skip detailed filter for now
                pass

            if team_filter:
                if team_filter.lower() not in row["Match"].lower():
                    continue

            rows.append(row)

        df = pd.DataFrame(rows)

        # UI: display and allow saving
        st.subheader("💰 Arbitrage Opportunities")
        if df.empty:
            st.info("No arbitrage found right now.")
        else:
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Opps", len(df))
            with col2:
                st.metric("Avg Profit", f"${df['Profit'].mean():.2f}")
            with col3:
                st.metric("Max Profit", f"${df['Profit'].max():.2f}")
            with col4:
                st.metric("Avg ROI", f"{df['Profit %'].mean():.2f}%")
            
            st.divider()
            
            # Display detailed table
            st.dataframe(df, use_container_width=True)

            # CSV download & snapshot buttons
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            csv_bytes = csv_buf.getvalue().encode('utf-8')

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.download_button("📥 Download CSV", data=csv_bytes, file_name="arbitrage.csv", mime="text/csv", use_container_width=True)
            with col2:
                if st.button("💾 Save Snapshot", use_container_width=True):
                    try:
                        path = save_snapshot(df)
                        st.success(f"✅ Saved: {path}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
            with col3:
                pass

        # Optional: show raw JSON & bookmaker details
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("📊 Raw API Response"):
                st.json(data[0] if data else {})
        
        with col2:
            if data:
                with st.expander("📍 Bookmaker Details"):
                    for game in data[:3]:  # Show first 3 games
                        for bm in game.get("bookmakers", [])[:2]:  # Show first 2 bookmakers
                            st.write(f"**{bm.get('title')}**")
                            for market in bm.get("markets", []):
                                st.caption(f"{market.get('key')}: {[o.get('price') for o in market.get('outcomes', [])]}")

        # Analytics from master CSV
        master = load_master()
        if not master.empty:
            st.subheader("📈 Analytics — Historical Trends")
            try:
                master["fetched_at"] = pd.to_datetime(master["fetched_at"])
                summary = master.groupby(master["fetched_at"]).agg({
                    "Match": "count",
                    "Profit": "mean",
                }).rename(columns={"Match": "opps_count", "Profit": "avg_profit"}).sort_index()

                st.line_chart(summary[["opps_count"]])
                st.line_chart(summary[["avg_profit"]])
            except Exception:
                st.info("Not enough historical data for analytics yet.")

st.markdown("---")
st.markdown("Built on the existing CLI functions in `app.py`. Use the sidebar to change settings and fetch live odds.")


st.markdown("---")
st.markdown("Built on the existing CLI functions in `app.py`. Use the sidebar to change settings and fetch live odds.")
