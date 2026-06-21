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

1. Calls the Finviz Elite export API with pre-filters (positive EPS growth, positive net margin, Buy/Strong Buy analyst rating) to narrow the universe
2. Computes Buy Zone, Graham Number, and Upside % for each ticker
3. Computes Investment Score (0–100 weighted composite) for every ticker
4. Keeps only tickers with Investment Score ≥ 70 and Upside % > 10%
5. Selects top 10 per sector (up to 120 stocks across 12 sectors) for diversity
6. Sorts all selected tickers by Investment Score descending
7. Splits tickers: ≤ 3 null data columns → Investment Master; > 3 null columns → Speculative Investments
8. Writes `investment-engine/stock-data/consolidated_MMDDYYYY.csv`

## 5. Review the CSV

Open `investment-engine/stock-data/consolidated_MMDDYYYY.csv`:

| Column | Notes |
|---|---|
| **Sector** | Finviz sector (e.g., Technology, Healthcare) |
| **Investment Score** | 0–100 composite. Higher = more attractive. Sorted descending. |
| **Buy Zone** | 52-Week High × 0.80 — disciplined entry target |
| **Target Price** | Analyst consensus from Finviz |
| **Upside %** | ((Target − Price) / Price) × 100 |
| **Graham Undervalued** | True if trading below Graham Number. None if data missing. |
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

**Fewer than 120 rows in the CSV**
Not all 12 sectors will always have 10 stocks meeting both the score ≥ 70 and upside > 10% thresholds. The row count reflects what actually qualifies on that run.

**A known ticker is missing from the output**
The Finviz pre-filters (`fa_epsqoq_pos`, `fa_netmargin_pos`, `an_recomendation_buybetter`) may have excluded it. A ticker must have positive EPS growth, positive net margin, and a Buy or Strong Buy analyst rating to enter the scored pool.
