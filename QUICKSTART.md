# Quick Start Guide

## 1. Set up your environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Get your FMP API key

Sign up at https://financialmodelingprep.com/ and obtain an API key from your account dashboard.
- Free tier: 250 requests/day
- Paid tiers: Higher limits (recommended — the engine makes several calls per ticker)

## 3. Configure your API key

Option A: Set directly for the current session

```powershell
$env:FMP_API_KEY = "your_fmp_key_here"
```

Option B: Load from a `.env` file

```powershell
Copy-Item .env.example .env
# Edit .env and fill in your FMP key
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
2. Fetch price, RSI, ratios, growth metrics, and balance sheet data from FMP
3. Compute **Target Price** from Forward EPS × Pillar P/E multiple (TTM EPS as fallback)
4. Compute **Graham Number** and flag undervalued stocks in the `Graham Undervalued` column
5. Compute **Investment Score** (0–100 weighted composite) for every ticker
6. Write `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx` with one tab per pillar

## 6. Review the workbook

Open `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`:

- **Pillar Map** tab: Maps pillar names to their shortened sheet names (Excel's 31-char limit)
- **AI [Sub-pillar]** tabs: Full scored dataset for that pillar

Key columns to note:

| Column | Notes |
|---|---|
| **Investment Score** | 0–100 composite. Higher = more attractive. Missing metrics are excluded and weights rescaled. |
| **Target Price** | Forward EPS × Pillar P/E multiple. Logs a warning to console if EPS is unavailable. |
| **Graham Undervalued** | `True` if Current Price < Graham Number. `None` if Book Value or EPS data is missing. |
| **Upside %** | `((Target Price − Current Price) / Current Price) × 100` |
| **RSI** | FMP technical indicator, period 10, 1-day timeframe |
| **Backlog Growth %** | Not auto-populated — fill in from your own research as needed |

## 7. Set up automation (optional)

To run on a schedule via GitHub Actions:

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `FMP` — your FMP API key
3. The workflow runs daily at 12:00 UTC
   - Manual trigger: **Actions tab → "Daily Investment Engine Refresh" → "Run workflow"**

## Troubleshooting

**`[WARN] Target Price unavailable for {TICKER} — missing EPS data`**
- The ticker has no forward EPS estimate, earnings estimate, or TTM EPS available from FMP.
- Target Price and Upside % will be `None` for that row.

**`FMP_API_KEY not set`**
- The engine will still run but all FMP fields will be empty. Set the key before running.

**Ticker not found / empty row**
- Check spelling — must match FMP's ticker format exactly (e.g., `NVDA` not `Nvidia`)
- Some tickers may not have all metrics available from FMP

**Adding a new pillar**
- Add it directly to `investment-engine/Ticker-Master.json` under the appropriate sector key. The engine creates the required directories automatically on its next run.

**Excel warnings on first run**
- Benign — related to sheet name normalization and will not recur

---

> **Claude ticker review** is currently disabled. The logic is preserved in `data_engine.py` (commented out) and can be re-enabled by uncommenting `generate_claude_ticker_review` and its call site in `run()`, then adding `ANTHROPIC_API_KEY` as a repository secret and restoring it to the workflow `env` block.
