import os
import time
from datetime import datetime
from typing import Optional, List, Dict

import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MASTER_CSV = os.path.join(DATA_DIR, "arbs_master.csv")
DETAILED_CSV = os.path.join(DATA_DIR, "odds_detailed.csv")  # bookmaker-level detail


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_snapshot(df: pd.DataFrame, prefix: Optional[str] = "arbs") -> str:
    """Append dataframe to master CSV and write timestamped snapshot.

    Returns the path to the snapshot written.
    """
    ensure_data_dir()
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = os.path.join(DATA_DIR, f"{prefix}_{ts}.csv")

    # add fetched timestamp column
    df_copy = df.copy()
    df_copy["fetched_at"] = datetime.utcnow().isoformat()

    # write snapshot
    df_copy.to_csv(snapshot_path, index=False, encoding="utf-8")

    # append to master CSV
    if os.path.exists(MASTER_CSV):
        df_copy.to_csv(MASTER_CSV, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df_copy.to_csv(MASTER_CSV, mode="w", header=True, index=False, encoding="utf-8")

    return snapshot_path


def save_detailed_odds(raw_odds_data: List[Dict]) -> str:
    """Extract and save bookmaker-level odds for line movement tracking.
    
    Returns path to detailed CSV.
    """
    ensure_data_dir()
    rows = []
    ts = datetime.utcnow().isoformat()

    for game in raw_odds_data:
        teams = game.get("teams", [])
        sport = game.get("sport_key", "")
        
        for bookmaker in game.get("bookmakers", []):
            bm_name = bookmaker.get("title", "unknown")
            
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                
                for outcome in market.get("outcomes", []):
                    rows.append({
                        "sport": sport,
                        "teams": " vs ".join(teams),
                        "team": outcome.get("name", ""),
                        "bookmaker": bm_name,
                        "market": market_key,
                        "odds": outcome.get("price"),
                        "fetched_at": ts,
                    })

    df = pd.DataFrame(rows)
    if df.empty:
        return ""

    # append to detailed CSV
    if os.path.exists(DETAILED_CSV):
        df.to_csv(DETAILED_CSV, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df.to_csv(DETAILED_CSV, mode="w", header=True, index=False, encoding="utf-8")

    return DETAILED_CSV


def load_master() -> pd.DataFrame:
    """Load arbitrage opportunities master file."""
    ensure_data_dir()
    if os.path.exists(MASTER_CSV):
        return pd.read_csv(MASTER_CSV)
    return pd.DataFrame()


def compute_line_movement(team: str, bookmaker: str, hours: int = 24) -> Dict:
    """Compute line movement for a team/bookmaker over past N hours.
    
    Returns: {"current_odds": X, "previous_odds": Y, "movement": Z, "direction": "up|down"}
    """
    ensure_data_dir()
    if not os.path.exists(DETAILED_CSV):
        return {}

    df = pd.read_csv(DETAILED_CSV)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    now = pd.Timestamp(datetime.utcnow())
    
    # filter to team/bookmaker in past N hours
    mask = (
        (df["team"] == team) &
        (df["bookmaker"] == bookmaker) &
        (df["fetched_at"] >= now - pd.Timedelta(hours=hours))
    )
    subset = df[mask].sort_values("fetched_at")
    
    if len(subset) < 2:
        return {}

    current_odds = subset.iloc[-1]["odds"]
    previous_odds = subset.iloc[0]["odds"]
    movement = current_odds - previous_odds
    direction = "up" if movement > 0 else "down"

    return {
        "current_odds": current_odds,
        "previous_odds": previous_odds,
        "movement": movement,
        "direction": direction,
        "hours": hours,
    }
