# Deployment Guide — Streamlit Cloud

This guide walks through deploying the Sports Bet Arbitrage dashboard on Streamlit Cloud for free.

## Phase 1: Prepare GitHub Repository

1. Create a GitHub account if needed: https://github.com/signup

2. Create a new repository (e.g., `sports-bet`) at https://github.com/new

3. Clone locally and push this project:

```bash
git clone https://github.com/YOUR_USERNAME/sports-bet.git
cd sports-bet
git add .
git commit -m "Initial commit"
git push -u origin main
```

## Phase 2: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io

2. Sign in with GitHub

3. Click `New app` and select:
   - GitHub repo: YOUR_USERNAME/sports-bet
   - Branch: `main`
   - Main file path: `streamlit_app.py`

4. Click `Deploy`

Your dashboard will be live at `https://YOUR_USERNAME-sports-bet.streamlit.app`

## Phase 3: Set API Key as Secret

1. In Streamlit Cloud dashboard, go to your app settings ⚙️

2. Secrets: Add `ODDS_API_KEY=YOUR_KEY`

3. Users can now use your dashboard without entering the API key (it reads from secrets)

## Notes

- Streamlit Cloud includes a small data folder for storing CSV snapshots (ephemeral—resets on deploy)
- To persist data long-term, use an external database (SQLite file in GitHub, DuckDB, or PostgreSQL)
- Auto-refresh works with Streamlit's caching layer

## Optional: Use SQLite for Persistent Data

Replace `data_store.py` with SQLite version:

```python
import sqlite3
db = sqlite3.connect('arbs.db')
# Store snapshots in table instead of CSV
```

Then commit `arbs.db` to GitHub (or use a cloud DB like Supabase).
