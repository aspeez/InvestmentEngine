# Quick Start Guide

## 1. Set up your environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Get your Finviz Elite auth token

Sign up for Finviz Elite at https://finviz.com/elite.ashx. Your auth token is the `auth=` value in any Finviz export URL:

```
https://elite.finviz.com/export?v=151&t=CEG&c=...&auth=YOUR_TOKEN_HERE
```

## 3. Configure your auth token

```powershell
$env:FINVIZ = "your_finviz_auth_token_here"
```

## 4. Configure tickers

Edit `investment-engine/Ticker-Master.json` to add or remove tickers per pillar. This file is the source of truth — per-sector `pillar_tickers.json` files are kept in sync automatically on every run.

## 5. Run the engine (Phase 1)

```powershell
python investment-engine/engine/data_engine.py
```

**What it does:**

1. Loads tickers from `Ticker-Master.json`
2. Makes a single bulk Finviz export call for all tickers at once
3. Computes Buy Zone, Graham Number, and Upside % for each ticker
4. Computes Investment Score (0–100 weighted composite)
5. Splits tickers: ≤ 2 null columns → Investment Master; > 2 null columns → Speculative Investments
6. Writes `sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`
7. Writes `sector/<SECTOR>/stock-data/consolidated_MMDDYYYY.csv` (Investment Master + Speculative combined)
8. Classifies every ticker against the 4 Robinhood watchlist scorecards → `sector/<SECTOR>/ticker-review/watchlist_MMDDYYYY.json`

## 6. Review the workbook

Open `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`:

| Tab | Contents |
|---|---|
| **Investment Master** | Tickers with sufficient data, sorted by Investment Score descending |
| **Speculative Investments** | Tickers with > 2 null columns — less reliable scores, use with caution |
| **AI [Pillar Name]** | All tickers for that pillar including speculative |

Key columns:

| Column | Notes |
|---|---|
| **Investment Score** | 0–100 composite. Higher = more attractive. |
| **Buy Zone** | Current Price × 0.80 — disciplined entry target |
| **Target Price** | Analyst consensus from Finviz |
| **Upside %** | ((Target − Price) / Price) × 100 |
| **Graham Undervalued** | True if trading below Graham Number. None if data missing. |
| **Analyst Recom** | 1.0 = Strong Buy, 5.0 = Strong Sell |

## 7. Run Phase 2 (Claude.ai)

After Phase 1 runs (locally or via GitHub Actions), open the **Investment Engine** project in Claude.ai and say:

> **run the investment review for [date]**

Claude will:
1. Confirm the data received (row counts from the consolidated CSV)
2. Check existing Robinhood watchlists for duplicates
3. Add qualifying tickers to WL1–WL4 via the Robinhood MCP connector
4. Send a completion summary of what was added to each list
5. Research additional High Conviction candidates not currently in the ticker universe
6. Deliver research results as a downloadable `research_MMDDYYYY.txt` file

## 8. Set up GitHub Actions automation

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `FINVIZ` — your Finviz Elite auth token
3. The workflow (`data_engine.yml`) runs every Sunday at 9:00 PM UTC
   - Manual trigger: **Actions tab → Investment Engine → Run workflow**
4. After each run, a GitHub Issue is created under your repo signaling Phase 2 is ready

---

## Troubleshooting

**`[WARN] FINVIZ not set`**
Set the `FINVIZ` environment variable before running. The engine will still execute but all data columns will be empty.

**`[WARN] Target Price unavailable for {TICKER}`**
Finviz has no analyst consensus target for that ticker. Upside % will be None.

**`[WARN] Finviz returned no data for: {TICKERS}`**
Those symbols were not found in Finviz. Check spelling — must match Finviz format exactly (e.g. `NVDA` not `Nvidia`).

**Adding a new pillar**
Add it directly to `investment-engine/Ticker-Master.json` under the appropriate sector key. The engine creates required directories on its next run.

**Adding a new ticker to an existing pillar**
Edit `Ticker-Master.json` — find the pillar and append the ticker to its list. Changes take effect on the next run.
