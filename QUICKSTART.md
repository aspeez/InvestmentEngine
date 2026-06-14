# Quick Start Guide

## 1. Set up your environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Get your FMP API key

Sign up at https://financialmodelingprep.com/ and obtain an API key from your account dashboard.

Free tier: 250 requests/day
Paid tiers: Higher limits

## 3. Configure your API key

Option A: Create `.env` file (recommended)

```powershell
Copy-Item .env.example .env
# Edit .env and replace "your_fmp_api_key_here" with your actual key
```

Load it in your session:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '(\w+)=(.*)') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
```

Option B: Set it directly

```powershell
$env:FMP_API_KEY = "your_actual_key_here"
# or
$env:FMP = "your_actual_key_here"
```

## 4. Configure tickers

Edit `investment-engine/Ticker-Master.json` to add or remove tickers per pillar.

Default config includes the current AI pillar universe, and the master file is where future non-AI sectors will be added.

## 5. Run the engine

```powershell
python investment-engine/engine/data_engine.py
```

The script will:

1. Read tickers from `investment-engine/Ticker-Master.json`
2. Fetch current price, RSI, ratios, growth metrics, and analyst target price from FMP
3. Calculate Buy Zone, Upside %, and Net Cash Ratio
4. Write `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx` with one tab per pillar
5. Generate `investment-engine/sector/<SECTOR>/ticker-review/ticker_reviews_MMDDYYYY.txt` via ChatGPT (or fallback if `CHATGPT` is not set)

## 6. Review the workbook

Open `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`:

- **Pillar Map** tab: Maps pillar names to sheet names (for Excel's 31-char limit)
- **AI [Sub-pillar]** tabs: Investment data by pillar

Columns to note:

- **RSI**: Pulled from FMP technical indicators (`periodLength=10`, `timeframe=1day`)
- **Target Price**: Populated from FMP analyst consensus — used to calculate Upside %
- **Backlog Growth %**: Not auto-populated; fill in from your own research as needed

## 7. Set up automation (optional)

To run on a schedule via GitHub Actions:

1. Push your repo to GitHub
2. Add your FMP API key as a repository secret:
   - Go to Settings → Secrets and variables → Actions
    - Create `FMP` with your actual key value
3. Add `CHATGPT` if you want the daily ChatGPT review file to be generated from the API instead of the deterministic fallback
4. The workflow runs daily at 12:00 UTC
   - Manual trigger available: Actions tab → "Daily Investment Engine Refresh" → "Run workflow"

## Troubleshooting

**"FMP_API_KEY not set"**
- Verify your `.env` file exists and is formatted correctly
- Or set `$env:FMP_API_KEY` before running the script

**"Ticker not found"**
- Check spelling (must match FMP's ticker format, e.g., "NVDA" not "Nvidia")
- Some tickers may not have all metrics available

**Excel warnings on first run**
- These are benign and won't appear after sheet names are normalized

**No ChatGPT review file**
- The workflow will still generate a fallback ticker review if `CHATGPT` is not set

## Next steps

1. Add more tickers to `pillar_tickers.json`
2. Create additional pillars (e.g., Healthcare, ESG) using `python scaffold_pillar.py Healthcare`
3. Extend the engine with custom scoring logic in `run_ai_engine.py`
4. Export workbook data to ChatGPT or other tools for analysis
