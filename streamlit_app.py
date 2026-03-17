import io
import os
from typing import List, Dict

import streamlit as st
import pandas as pd

from app import get_odds, find_arbitrage, compute_stakes
from data_store import save_snapshot, load_master, save_detailed_odds


st.set_page_config(page_title="Sports Bet Arbitrage", layout="wide")

st.title("Sports Bet — Arbitrage Finder")

with st.sidebar.form(key="settings"):
    api_key = st.text_input("API Key", value=os.environ.get('ODDS_API_KEY', ''), type='password')
    sport = st.text_input("Sport", value="basketball_nba")
    region = st.text_input("Region", value="us")
    markets = st.text_input("Markets", value="h2h")
    stake = st.number_input("Total stake (for stake suggestion)", value=100.0, min_value=1.0)
    refresh_seconds = st.slider("Auto-refresh (seconds)", min_value=10, max_value=600, value=60, step=10)
    auto_refresh = st.checkbox("Enable auto-refresh (uses cached TTL)", value=True)
    arb_threshold = st.number_input("Max Arb Value (<=)", value=0.99, step=0.001, format="%.3f")
    bookmaker_filter = st.text_input("Bookmaker filter (comma-separated, optional)", value="")
    team_filter = st.text_input("Team filter (substring, optional)", value="")
    save_path = st.text_input("Auto-save CSV path (optional)", value="data/arbs_snapshot.csv")
    submit = st.form_submit_button("Fetch Odds")

# cached fetch using TTL so auto-refresh works without rerunning entire script
@st.cache_data(ttl=0)
def cached_get_odds_no_cache(api_key, sport, region, markets):
    return get_odds(api_key, sport, region, markets)

def cached_get_odds(api_key, sport, region, markets, ttl):
    if ttl <= 0:
        return cached_get_odds_no_cache(api_key, sport, region, markets)

    @st.cache_data(ttl=ttl)
    def _f(k, s, r, m):
        return get_odds(k, s, r, m)

    return _f(api_key, sport, region, markets)

if not api_key:
    st.warning("Provide an API key in the sidebar or set the ODDS_API_KEY environment variable.")

if submit and api_key:
    with st.spinner("Fetching odds..."):
        if auto_refresh:
            data = cached_get_odds(api_key, sport, region, markets, refresh_seconds)
        else:
            data = cached_get_odds_no_cache(api_key, sport, region, markets)

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
        st.subheader("Arbitrage Opportunities")
        if df.empty:
            st.info("No arbitrage found right now.")
        else:
            st.dataframe(df)

            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            csv_bytes = csv_buf.getvalue().encode('utf-8')

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.download_button("Download CSV", data=csv_bytes, file_name="arbitrage.csv", mime="text/csv")
            with col2:
                if st.button("Save snapshot to data/"):
                    try:
                        path = save_snapshot(df)
                        st.success(f"Saved snapshot: {path}")
                    except Exception as e:
                        st.error(f"Failed to save snapshot: {e}")
            with col3:
                st.write(f"Found {len(df)} opportunities")

        # Optional: show raw JSON
        with st.expander("Raw API response (first item)"):
            st.json(data[0] if data else {})

        # Analytics from master CSV
        master = load_master()
        if not master.empty:
            st.subheader("Analytics — historical snapshots")
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
