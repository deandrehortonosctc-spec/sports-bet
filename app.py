import os
import argparse
import logging
import sys
from typing import List, Dict, Any

import requests
import pandas as pd


API_ENV_VAR = "ODDS_API_KEY"


def get_odds(api_key: str, sport: str, region: str, markets: str) -> List[Dict[str, Any]]:
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": api_key,
        "regions": region,
        "markets": markets,
        "oddsFormat": "decimal"
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logging.error("Error fetching odds: %s", e)
        return []


def find_arbitrage(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    opportunities = []

    for game in data:
        teams = game.get("teams", [])
        bookmakers = game.get("bookmakers", [])

        best_odds: Dict[str, float] = {}

        for book in bookmakers:
            for market in book.get("markets", []):
                # Only consider outcomes with prices
                for outcome in market.get("outcomes", []):
                    team = outcome.get("name")
                    odds = outcome.get("price")
                    if team is None or odds is None:
                        continue

                    if team not in best_odds or odds > best_odds[team]:
                        best_odds[team] = float(odds)

        if len(best_odds) == 2:
            odds_values = list(best_odds.values())

            arb = (1.0 / odds_values[0]) + (1.0 / odds_values[1])

            if arb < 1.0:
                opportunities.append({
                    "teams": teams,
                    "odds": best_odds,
                    "arb_value": arb
                })

    return opportunities


def compute_stakes(odds_a: float, odds_b: float, total: float = 100.0):
    inv_a = 1.0 / odds_a
    inv_b = 1.0 / odds_b
    arb = inv_a + inv_b
    share_a = inv_a / arb
    share_b = inv_b / arb
    stake_a = round(total * share_a, 2)
    stake_b = round(total * share_b, 2)
    payout = round(stake_a * odds_a, 2)  # should equal stake_b * odds_b
    profit = round(payout - total, 2)
    profit_pct = round((profit / total) * 100, 2)
    return stake_a, stake_b, profit, profit_pct


def main():
    parser = argparse.ArgumentParser(description="Find simple 2-way arbitrage from The Odds API")
    parser.add_argument("--api-key", help="The Odds API key (or set ODDS_API_KEY env var)")
    parser.add_argument("--sport", default="basketball_nba", help="Sport key, e.g. basketball_nba")
    parser.add_argument("--region", default="us", help="Region code, e.g. us")
    parser.add_argument("--markets", default="h2h", help="Market, e.g. h2h")
    parser.add_argument("--stake", type=float, default=100.0, help="Total stake to allocate for each arb")
    parser.add_argument("--save-csv", dest="save_csv", help="Path to save CSV of opportunities (optional)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get(API_ENV_VAR)
    if not api_key:
        print(f"Provide API key via --api-key or set environment variable {API_ENV_VAR}")
        sys.exit(1)

    data = get_odds(api_key, args.sport, args.region, args.markets)
    if not data:
        print("No data returned from the API.")
        sys.exit(0)

    arbs = find_arbitrage(data)

    print("\n🔥 Arbitrage Opportunities:\n")

    if not arbs:
        print("No arbitrage found right now.")
        return

    rows = []
    for arb in arbs:
        teams = arb["teams"]
        best = arb["odds"]
        arb_value = arb["arb_value"]
        # two teams - ensure consistent order
        team_names = list(best.keys())
        odds_vals = [best[team_names[0]], best[team_names[1]]]
        stake_a, stake_b, profit, profit_pct = compute_stakes(odds_vals[0], odds_vals[1], total=args.stake)

        rows.append({
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
        })

    df = pd.DataFrame(rows)
    pd.set_option('display.max_columns', None)
    if args.save_csv:
        try:
            df.to_csv(args.save_csv, index=False)
            print(f"Saved arbitrage results to {args.save_csv}")
        except Exception as e:
            logging.error("Failed to save CSV: %s", e)

    if df.empty:
        print("No valid arbitrage rows to display.")
        return

    print(df.to_string(index=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
