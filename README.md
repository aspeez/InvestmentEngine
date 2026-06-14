# InvestmentEngine

Automated investment research and scoring platform for public companies.

## Current scope

- Source of truth: `Ticker-Master.json`
- Main project folder: `investment-engine`
- Sector parent directory: `investment-engine/sector`
- Data source: Financial Modeling Prep (FMP)
- Output artifacts:
	- `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx (File Generated after Git Action)`
	- `investment-engine/sector/<SECTOR>/ticker-review/ticker_reviews_MMDDYYYY.txt (file should be generated from ChatGPT)`
- Automation: GitHub Actions scheduled and manual runs

## Project structure

```text
InvestmentEngine/
	investment-engine/
		Ticker-Master.json
		engine/
			data_engine.py
		sector/
			<SECTOR>/
				pillar_tickers.json
				stock-data/
					investment_data_MMDDYYYY.xlsx
				ticker-review/
					ticker_reviews_MMDDYYYY.txt
	.github/
		workflows/
			update_ai_workbook.yml
	requirements.txt
```

## Workbook model

The master workbook contains one tab per pillar:

- AI Power Generation
- AI Networking
- AI Memory and Storage
- AI Land
- AI Heating and Cooling
- AI Grid and Power Transmission
- AI Electrical Infrastructure
- AI Construction
- AI Cybersecurity
- AI Semiconductor Chip Manufacturing
- AI Server and Rack Systems
- AI Software and Platforms
- AI Backup Power
- AI Cloud
- AI Fire Detection
- AI Water
- AI Insurance and Risk
- AI Security
- AI Compute Chips

Each tab is created with these columns:

- Ticker
- Current Price
- RSI
- P/E Ratio
- P/S Ratio
- Market Cap
- Buy Zone
- Target Price
- Upside %
- Revenue Growth %
- EPS Growth %
- Backlog Growth %
- Gross Margin %
- Net Cash Ratio

## Pulled from Ticker-Master.json

- `Ticker`

## Pulled from FMP

- `Current Price`
- `RSI`
- `P/E Ratio`
- `P/S Ratio`
- `Market Cap`
- `Revenue Growth %`
- `EPS Growth %`
- `Gross Margin %`
- `Net Cash Ratio`

## Calculated

* `Buy Zone = Current Price * 0.80`
* `Upside % = (Target Price - Current Price) / Current Price`
* `Net Cash Ratio % = (Cash - Total Debt)/ Market Capitalization`

## Local setup

1. Create a virtual environment and install dependencies.
2. Set `FMP_API_KEY` (or `FMP`) in your environment.
3. Run the engine.

Get your FMP API key at: https://financialmodelingprep.com/

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Create .env from template and add your API key
Copy-Item .env.example .env
# Edit .env with your FMP_API_KEY

# (Or set it directly for the current session)
$env:FMP_API_KEY = "your_api_key_here"
# or
$env:FMP = "your_api_key_here"
python investment-engine/engine/data_engine.py
```

The engine will:

1. Read tickers from `investment-engine/Ticker-Master.json`
2. Fetch current price, RSI, ratios, growth metrics, and analyst target price from FMP
3. Calculate Buy Zone (Current Price × 0.80), Upside %, and Net Cash Ratio
4. Write `investment-engine/sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx` with one tab per pillar
5. Generate `investment-engine/sector/<SECTOR>/ticker-review/ticker_reviews_MMDDYYYY.txt` via ChatGPT (or a fallback summary if `CHATGPT` is not set)

## Configure tickers

Edit `investment-engine/Ticker-Master.json` to control the full multi-sector ticker universe.

Each sector compatibility file `investment-engine/sector/<SECTOR>/pillar_tickers.json` is kept in sync automatically.

The engine also keeps manually added tickers already present in the workbook.

## Add a new pillar

To scaffold a new pillar (e.g., Healthcare, ESG):

```bash
python scaffold_pillar.py Healthcare
```

This creates:

- `Healthcare/pillar_tickers.json` — configure your ticker universe
- `Healthcare/run_healthcare_engine.py` — ready to run

Create a new GitHub Actions workflow for the pillar following the same pattern as `update_ai_workbook.yml`.

## Workbook reference

The first tab, "Pillar Map", documents the mapping between sector, pillar, and shortened sheet name.

## GitHub Actions automation

Workflow file: `.github/workflows/update_ai_workbook.yml`

Triggers:

- Manual: `workflow_dispatch`
- Schedule: Daily at 12:00 UTC

Setup required:

1. Add your FMP API key as a repository secret named `FMP`.
2. Add your OpenAI API key as a repository secret named `CHATGPT` if you want ChatGPT review generation.
   - In GitHub: Settings → Secrets and variables → Actions → New repository secret
3. Commit and push the repository to GitHub.

On each run, the workflow refreshes sector workbooks, writes dated files into `investment-engine/sector/<SECTOR>/stock-data/` and `investment-engine/sector/<SECTOR>/ticker-review/`, and commits them if changed.
