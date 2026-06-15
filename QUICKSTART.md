# Quick Start Guide

## 1. Set up your environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Get your Finviz Elite auth token

Sign up for Finviz Elite at https://finviz.com/elite.ashx. Your auth token is the `auth=` parameter value in any Finviz export URL, for example:

```
https://elite.finviz.com/export?v=151&t=CEG&c=...&auth=YOUR_TOKEN_HERE
```

## 3. Configure your auth token

Option A: Set directly for the current session

```powershell
$env:FINVIZ = "your_finviz_auth_token_here"
```

Option B: Load from a `.env` file

```powershell
Copy-Item .env.example .env
# Edit .env and fill in your FINVIZ token
Get-Content .env | ForEach-Object {
    if ($_ -match '(\w+)=(.*)') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
```

## 4. Configure tickers

Edit `investment-engine/Ticker-Master.json` to add or remove tickers per pillar. The master file drives everything — per-sector `pillar_tickers.json` files are kept in sync automatically on every run.

## 5. Run the engine

```powershell
python investment-engine/engine/data_engine.py
```

The engine will:

1. Read tickers from `investment-engine/Ticker-Master.json`
2. Make a single bulk Finviz export call for all tickers at once
3. Compute **Graham Number** and flag undervalued stocks in the `Graham Undervalued` column
4. Use the Finviz analyst consensus **Target Price** to compute **Upside %**
5. Compute **Investment Score** (0–100 weighted composite) for every ticker
6. Split tickers: ≤ 2 null columns → Investment Master; > 2 null columns → Speculative Investments
7. Write `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`
8. Export a consolidated CSV (Investment Master + Speculative) and POST to Claude API for review
9. Save Claude's acknowledgment and top-5 ticker recommendations to `investment-engine/sector/<SECTOR>/ticker-review/ticker_review_MMDDYYYY.json`

## 6. Review the workbook

Open `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`:

| Tab | What's in it |
|---|---|
| **Investment Master** | Tickers with sufficient data, sorted by Investment Score descending |
| **Speculative Investments** | Tickers with more than 2 null columns — less data, interpret with caution |
| **AI [Sub-pillar]** | Full scored dataset for that pillar (all tickers, including speculative) |

Key columns to note:

| Column | Notes |
|---|---|
| **Investment Score** | 0–100 composite. Higher = more attractive. Missing metrics are excluded and weights rescaled. |
| **Target Price** | Analyst consensus from Finviz. Upside % is derived from this. |
| **Graham Undervalued** | `True` if Current Price < Graham Number. `None` if EPS or Book Value data is missing. |
| **Upside %** | `((Target Price − Current Price) / Current Price) × 100` |
| **Analyst Recom** | 1.0 = Strong Buy, 5.0 = Strong Sell (Finviz consensus score) |

## 7. Set up automation (optional)

To run on a schedule via GitHub Actions:

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `FINVIZ` — your Finviz Elite auth token
   - `ANTHROPIC_API_KEY` — your Anthropic API key (for Claude ticker review)
3. The workflow runs weekly on Sundays at 21:00 UTC (4:00 PM EST)
   - Manual trigger: **Actions tab → "Investment Engine" → "Run workflow"** (workflow file: `data_engine.yml`)

## Troubleshooting

**`[WARN] FINVIZ not set`**
- The engine will still run but all Finviz fields will be empty. Set the token before running.

**`[WARN] Target Price unavailable for {TICKER}`**
- Finviz has no analyst consensus target for that ticker. Upside % will be `None`.

**`[WARN] Finviz returned no data for: {TICKERS}`**
- Those ticker symbols were not found in Finviz. Check spelling — must match Finviz format exactly (e.g. `NVDA` not `Nvidia`).

**Adding a new pillar**
- Add it directly to `investment-engine/Ticker-Master.json` under the appropriate sector key. The engine creates the required directories automatically on its next run.

---

> **Claude ticker review** is enabled. After each run, a consolidated CSV of Investment Master + Speculative data is sent to the Claude API. Claude acknowledges receipt and returns up to 5 ranked ticker recommendations saved to `sector/<SECTOR>/ticker-review/ticker_review_MMDDYYYY.json`. Add `ANTHROPIC_API_KEY` as a GitHub secret to activate this in GitHub Actions; without it the step is skipped with a warning.
