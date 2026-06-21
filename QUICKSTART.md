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
https://elite.finviz.com/export?v=150&c=...&auth=YOUR_TOKEN_HERE
```

## 3. Configure your auth token

```powershell
$env:FINVIZ = "your_finviz_auth_token_here"
```

## 4. Run the engine (Phase 1)

```powershell
python investment-engine/engine/data_engine.py
```

**What it does:**

1. Calls the Finviz Elite export API with screener filters: small-to-mid cap, NASDAQ/NYSE, D/E < 1, net margin > 10%, PEG 0–1.5, avg volume > 1M
2. Fetches any tickers in `investment-engine/Ticker-Master.json` not already returned by the screener and merges them into the pool
3. Computes Buy Zone, PSG, and Upside % for each ticker
4. Computes Investment Score (0–100 weighted composite) for every ticker
5. Sorts all tickers by Investment Score descending
6. Splits tickers: ≤ 3 null data columns → Investment Master; > 3 null columns → Speculative Investments
7. Writes `investment-engine/stock-data/consolidated_MMDDYYYY.csv`

## 5. Review the CSV

Open `investment-engine/stock-data/consolidated_MMDDYYYY.csv`:

| Column | Notes |
|---|---|
| **Sector** | Finviz sector (e.g., Technology, Healthcare) |
| **Investment Score** | 0–100 composite. Higher = more attractive. Sorted descending. |
| **Buy Zone** | 52-Week High × 0.80 — disciplined entry target |
| **Target Price** | Analyst consensus from Finviz |
| **Upside %** | ((Target − Price) / Price) × 100 |
| **Analyst Recom** | 1.0 = Strong Buy, 5.0 = Strong Sell |
| **Tab** | Investment Master (≤ 3 nulls) or Speculative Investments (> 3 nulls) |

## 6. Run Phase 2 (Claude.ai)

After Phase 1 runs (locally or via GitHub Actions), open the **Investment Engine** project in Claude.ai and say:

> **run the investment review for [date]**

Claude will:
1. Confirm the data received (row counts from the consolidated CSV)
2. Check existing Robinhood watchlists for duplicates
3. Add qualifying tickers to WL1–WL4 via the Robinhood MCP connector
4. Send a completion summary of what was added to each list

## 7. Set up GitHub Actions automation

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `FINVIZ` — your Finviz Elite auth token
3. The workflow (`data_engine.yml`) runs automatically at 7:00 AM EST daily
   - Manual trigger: **Actions tab → Investment Engine → Run workflow**
4. After each run, a GitHub Issue is created signaling Phase 2 is ready

---

## Troubleshooting

**`[WARN] FINVIZ not set`**
Set the `FINVIZ` environment variable before running. The engine will still execute but all data columns will be empty.

**`[WARN] Target Price unavailable for {TICKER}`**
Finviz has no analyst consensus target for that ticker. Upside % will be None.

**`[WARN] Finviz request failed`**
Network issue or invalid auth token. Confirm Finviz Elite is accessible and your token is correct.

**A known ticker is missing from the output**
Add it to `investment-engine/Ticker-Master.json`. Every ticker in that file is fetched and scored on every run regardless of whether it passes the Finviz screener filters.

**Fewer rows than expected in the CSV**
Check `[WARN]` lines in the run log. Finviz occasionally returns no data for individual tickers — those will be absent from the output.
