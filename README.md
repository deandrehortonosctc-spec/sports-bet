# sports-bet

Simple script to fetch odds from The Odds API and detect basic 2-way arbitrage opportunities.

Prerequisites

- Python 3.8+
- Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Usage

Set your API key via environment variable or pass with `--api-key`.

Examples:

```powershell
$env:ODDS_API_KEY="YOUR_API_KEY"
python app.py --sport basketball_nba --region us --markets h2h --stake 100

# Save results (CSV) even if empty
$env:ODDS_API_KEY="YOUR_API_KEY"
python app.py --sport basketball_nba --region us --markets h2h --stake 100 --save-csv arbs.csv
```

CLI options

- `--api-key`: Your The Odds API key (or set `ODDS_API_KEY` env var)
- `--sport`: Sport key (default: `basketball_nba`)
- `--region`: Region (default: `us`)
- `--markets`: Market (default: `h2h`)
- `--stake`: Total stake used to compute recommended stakes (default: `100`)
- `--save-csv`: Optional path to save found opportunities as CSV

Next steps

- Add a simple CSV save (implemented).
- Build a web dashboard (Streamlit or Flask) to visualize live odds — ask if you prefer Streamlit.
- Add a simple prediction model (start with logistic regression or XGBoost) — discuss available data and target.

Run the Streamlit dashboard

1. Ensure dependencies are installed:

```powershell
python -m pip install -r requirements.txt
```

2. Start the dashboard (recommended):

```powershell
# from project root
python -m streamlit run streamlit_app.py
```

3. Open the Local URL shown in the console (usually http://localhost:8501).

Notes

- The dashboard reuses the CLI functions in `app.py` and allows CSV download.
- To run headless on a specific port:

```powershell
python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true
```

Data Logging & Analytics

The dashboard automatically captures and stores:

- **Arbitrage snapshots** — saved to `data/arbs_{timestamp}.csv` and `data/arbs_master.csv`
- **Detailed bookmaker odds** — saved to `data/odds_detailed.csv` for line movement tracking
  - Includes: sport, teams, team, bookmaker, market, odds, timestamp

View trends in the dashboard's **Analytics** section (requires multiple snapshots).

Deployment

For free online deployment, see [DEPLOY.md](DEPLOY.md) — quickstart for Streamlit Cloud.

Roadmap

- ✅ Phase 1: Deploy on Streamlit Cloud
- 🔄 Phase 2: Enhanced data logging (bookmaker, line movement)
- 🚀 Phase 3: Prediction model (XGBoost on historical arb outcomes)
- 🌍 Phase 4: Production deployment (Flask + React + PostgreSQL)
