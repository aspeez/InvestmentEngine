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
2. Fetch price, RSI, ratios, growth, margin, and ownership data from Finviz (one call per ticker)
3. Compute **Graham Number** and flag undervalued stocks in the `Graham Undervalued` column
4. Use the Finviz analyst consensus **Target Price** to compute **Upside %**
5. Compute **Investment Score** (0–100 weighted composite) for every ticker
6. Write `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`

## 6. Review the workbook

Open `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`:

| Tab | What's in it |
|---|---|
| **Investment Master** | All tickers across all pillars sorted by Investment Score descending |
| **Audit** | Every raw Finviz value and intermediate calculation — use this to verify any computed number |
| **Formula Guide** | Each formula written out plainly with verification steps and the full Investment Score weight table |
| **AI [Sub-pillar]** | Full scored dataset for that pillar |

Key columns to note:

| Column | Notes |
|---|---|
| **Investment Score** | 0–100 composite. Higher = more attractive. Missing metrics are excluded and weights rescaled. |
| **Target Price** | Analyst consensus from Finviz. Upside % is derived from this. |
| **Graham Undervalued** | `True` if Current Price < Graham Number. `None` if EPS or Book Value data is missing. |
| **Upside %** | `((Target Price − Current Price) / Current Price) × 100` |
| **Analyst Recom** | 1.0 = Strong Buy, 5.0 = Strong Sell (Finviz consensus score) |

**To verify any number:** open the Audit tab, find the ticker's row, and check the raw inputs. The Formula Guide tab shows exactly how to reproduce each calculation from those inputs.

## 7. Set up automation (optional)

To run on a schedule via GitHub Actions:

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `FINVIZ` — your Finviz Elite auth token
3. The workflow runs weekly on Sundays at 21:00 UTC (4:00 PM EST)
   - Manual trigger: **Actions tab → "Investment Engine" → "Run workflow"** (workflow file: `data_engine.yml`)

## Troubleshooting

**`[WARN] FINVIZ not set`**
- The engine will still run but all Finviz fields will be empty. Set the token before running.

**`[WARN] Target Price unavailable for {TICKER}`**
- Finviz has no analyst consensus target for that ticker. Upside % will be `None`.

**`[WARN] Finviz returned no data for {TICKER}`**
- Check that the ticker symbol is valid in Finviz (must match exactly, e.g. `NVDA` not `Nvidia`).

**Adding a new pillar**
- Add it directly to `investment-engine/Ticker-Master.json` under the appropriate sector key. The engine creates the required directories automatically on its next run.

---

> **Claude ticker review** is currently disabled. The logic is preserved in `data_engine.py` (commented out) and can be re-enabled by uncommenting `generate_claude_ticker_review` and its call site in `run()`, then adding `ANTHROPIC_API_KEY` as a repository secret and restoring it to the workflow `env` block.
