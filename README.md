# InvestmentEngine

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/aspeez/InvestmentEngine.svg)](https://github.com/aspeez/InvestmentEngine/issues)

Automated weekly investment research and scoring platform for AI-sector stocks. Built on Finviz Elite data, delivers scored Excel workbooks and Robinhood watchlist integration.

## ✨ Features

- **📊 Automated Weekly Scoring** — Runs every Sunday at 9:00 PM UTC via GitHub Actions
- **💹 21-Column Analysis** — Evaluates growth, valuation, financial quality, and entry timing
- **🔢 Weighted Composite Scoring** — 0–100 investment score with dynamic weight redistribution for missing data
- **📁 Organized by AI Pillar** — 19 investment themes across Technology, Infrastructure, and Services
- **📈 Multi-Tab Excel Workbooks** — Investment Master, Speculative, and per-pillar tabs with sorting
- **🎯 Robinhood Integration** — Classifies tickers into 4 watchlists (WL1–WL4) with Claude.ai
- **⚡ Single Bulk API Call** — Fetches data for all tickers at once for speed and efficiency
- **🔄 CSV Export** — Consolidated Investment Master + Speculative combined for Claude.ai review

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Scoring Model](#scoring-model)
- [Watchlists](#watchlists)
- [Local Setup](#local-setup)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/aspeez/InvestmentEngine.git
cd InvestmentEngine
```

### 2. Set Up Your Environment

```powershell
python -m venv .venv
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Get Your Finviz Elite Auth Token

Sign up for [Finviz Elite](https://finviz.com/elite.ashx). Your auth token is the `auth=` value in any export URL:

```
https://elite.finviz.com/export?v=151&t=CEG&c=...&auth=YOUR_TOKEN_HERE
```

### 4. Set the Environment Variable

```powershell
$env:FINVIZ = "your_finviz_auth_token_here"
```

### 5. Run Phase 1 (Local)

```powershell
python investment-engine/engine/data_engine.py
```

Output files appear in `investment-engine/sector/<SECTOR>/stock-data/`.

### 6. Review the Workbook

Open `investment_data_MMDDYYYY.xlsx` to see:
- **Investment Master** — tickers with sufficient data, sorted by score
- **Speculative Investments** — high-risk tickers with sparse data
- **Pillar sheets** — all tickers for each investment theme

For column details, see [COLUMN_REFERENCE.md](COLUMN_REFERENCE.md).

### 7. Set Up GitHub Actions

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add `FINVIZ` secret with your auth token
4. The workflow runs automatically every Sunday at 9:00 PM UTC
5. Manual trigger: **Actions → Investment Engine → Run workflow**

After each run, a GitHub Issue signals that Phase 2 is ready.

---

## 🔄 How It Works

### Phase 1 — GitHub Actions (Automated)

Every Sunday at 9:00 PM UTC (or manually triggered):

1. **Load tickers** from `Ticker-Master.json` (organized by Sector → Pillar)
2. **Fetch live data** — single bulk GET to Finviz Elite for all tickers at once
3. **Derive metrics:**
   - Buy Zone = Current Price × 0.80
   - Graham Number = √(22.5 × EPS × Book/sh)
   - Upside % = ((Target − Price) / Price) × 100
4. **Compute Investment Score** — 0–100 weighted composite across 11 metrics
5. **Split tickers:**
   - ≤ 2 null data columns → Investment Master
   - \> 2 null data columns → Speculative Investments
6. **Write Excel workbook** — sorted by score, with per-pillar tabs
7. **Export consolidated CSV** — combines both tabs for Phase 2
8. **Classify watchlists** — evaluate every ticker against 4 Robinhood scorecards
9. **Commit and push** all output files
10. **Create GitHub Issue** — signals Phase 2 is ready

### Phase 2 — Claude.ai Investment Engine Project (Interactive)

After Phase 1 completes, open the **Investment Engine** project in Claude.ai and say:

> **"run the investment review for [date]"**

Claude will:
1. Confirm data received (row counts from consolidated CSV)
2. Check existing Robinhood watchlists for duplicates
3. Add qualifying tickers to WL1–WL4 via Robinhood MCP connector
4. Send completion summary with tickers added per watchlist
5. Research additional High Conviction candidates not in the current ticker universe
6. Deliver research results as a downloadable `research_MMDDYYYY.txt` file

Close the GitHub Issue when done.

---

## 📂 Project Structure

```
InvestmentEngine/
├── investment-engine/
│   ├── Ticker-Master.json                 ← Source of truth (Sector → Pillar → Tickers)
│   ├── engine/
│   │   ├── data_engine.py                 ← Phase 1 engine
│   │   └── push_watchlists.py             ← Reference script (Phase 2 via Claude)
│   └── sector/
│       └── <SECTOR>/
│           ├── pillar_tickers.json        ← Auto-synced from Ticker-Master.json
│           ├── stock-data/
│           │   ├── investment_data_MMDDYYYY.xlsx
│           │   └── consolidated_MMDDYYYY.csv
│           └── ticker-review/
│               └── watchlist_MMDDYYYY.json  ← watchlist classification (WL1–WL4)
├── .github/
│   └── workflows/
│       └── data_engine.yml
├── requirements.txt
├── pyproject.toml                         ← Python packaging metadata
├── QUICKSTART.md                          ← Step-by-step setup guide
├── COLUMN_REFERENCE.md                    ← Detailed column definitions
├── CONTRIBUTING.md                        ← How to add tickers & pillars
├── LICENSE                                ← MIT License
└── README.md                              ← You are here
```

---

## ⚙️ Configuration

### Ticker-Master.json

The source of truth for all tickers, organized hierarchically:

```json
{
  "Technology": {
    "AI Compute Chips": ["NVDA", "AMD", "AVGO"],
    "AI Software and Platforms": ["MSFT", "GOOGL", "META"],
    "AI Cybersecurity": ["CRWD", "NET", "PALO"]
  },
  "Infrastructure": {
    "AI Power Generation": ["NEE", "DUK", "EXC"],
    "AI Networking": ["JNPR", "SMCI", "FICO"]
  }
}
```

**To add a ticker:** Edit this file, append the symbol, and run the engine. Directories are created automatically.

**To add a pillar:** Create a new key under any Sector with an array of tickers.

**To add a sector:** Create a new top-level key with pillars.

For details, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🎯 Scoring Model

The **Investment Score (0–100)** is a weighted composite across 4 categories:

| Category | Metrics | Weight |
|---|---|---|
| **Growth (30%)** | Revenue Growth %, EPS Growth % | 20%, 10% |
| **Financial Quality (25%)** | Gross Margin %, Net Profit Margin %, Debt/Equity | 10%, 10%, 5% |
| **Valuation (25%)** | P/S Ratio, Upside %, P/E Ratio | 10%, 10%, 5% |
| **Entry Timing (20%)** | RSI, Buy Zone Proximity, Analyst Recom | 10%, 5%, 5% |

**Scoring direction:**
- ⬆️ Higher is better: Revenue Growth, EPS Growth, Gross Margin, Net Profit Margin, Upside %
- ⬇️ Lower is better: P/E (capped at 60), P/S (capped at 30), Debt/Equity (capped at 3.0), Analyst Recom (1.0 = strong buy)
- 📊 RSI: Peaks at 30 (oversold), zero at 80 (overbought)
- 💰 Buy Zone Proximity: 100 at or below buy zone, 0 when 25%+ above

**Missing data:** Weights are redistributed proportionally so partial data still produces a valid score.

**Score interpretation:**
- **70–100** — High conviction across most dimensions
- **50–70** — Solid candidate, above average
- **30–50** — Mixed signals
- **< 30** — Weak, poor growth or expensive valuation

See [COLUMN_REFERENCE.md](COLUMN_REFERENCE.md) for per-metric details.

---

## 📊 Watchlists

Every ticker is classified into one of four Robinhood watchlists (first match wins, no duplicates):

| Watchlist | Key Thresholds | Interpretation |
|---|---|---|
| **WL1 — High Conviction 🟢** | Score ≥70, Rev Growth ≥20%, EPS Growth ≥20%, Net Margin ≥10%, D/E ≤1.0, RSI 30–55, Upside ≥20%, Analyst ≤2.0 | Top-tier buys — strong fundamentals & entry |
| **WL2 — Pullback Watch 🔵** | Score ≥60, Rev Growth ≥15%, EPS Growth ≥10%, Net Margin ≥5%, D/E ≤1.5, RSI 30–50, Upside ≥20%, Analyst ≤2.5 | Wait for pullback to build position |
| **WL3 — Deep Value 🟡** | Score ≥50, Rev Growth ≥10%, EPS Growth ≥0%, Net Margin >0%, D/E ≤1.0, RSI ≤35, Upside ≥15%, Analyst ≤2.5 | Undervalued, oversold — entry for long-term |
| **WL4 — Pipeline ⚪** | Score 50–60, Rev Growth ≥15%, EPS Growth ≥10%, Net Margin ≥5%, D/E ≤1.5, Upside ≥15%, Analyst ≤2.5 | Watch for score acceleration into WL1–WL3 |

Note: Gross Margin % is intentionally excluded from watchlist thresholds to avoid penalizing hardware/infrastructure plays.

---

## 💻 Local Setup

### Prerequisites

- Python 3.8+
- pip
- Finviz Elite account

### Installation

```powershell
# Clone the repo
git clone https://github.com/aspeez/InvestmentEngine.git
cd InvestmentEngine

# Create virtual environment
python -m venv .venv
..\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set Finviz token
$env:FINVIZ = "your_token_here"

# Run Phase 1
python investment-engine/engine/data_engine.py
```

### Optional: Install with dev tools

```powershell
pip install -e ".[dev]"
```

Includes `black`, `isort`, `flake8`, `mypy`, `pytest` for code formatting and testing.

---

## 🐛 Troubleshooting

### `[WARN] FINVIZ not set`

Set the `FINVIZ` environment variable before running. Engine will execute but all data columns will be empty.

```powershell
$env:FINVIZ = "your_token_here"
```

### `[WARN] Target Price unavailable for {TICKER}`

Finviz has no analyst consensus target for that ticker. Upside % will be `None`.

### `[WARN] Finviz returned no data for: {TICKERS}`

Those symbols were not found in Finviz. Check spelling — must match Finviz format exactly (e.g., `NVDA` not `Nvidia`).

### Workbook shows all None values

Likely causes:
1. **FINVIZ token not set** — check environment variable
2. **Network issue** — confirm Finviz is accessible
3. **Ticker spelling** — verify against Finviz

### I made changes to Ticker-Master.json but they're not showing up

1. Run the engine locally to test: `python investment-engine/engine/data_engine.py`
2. Commit and push changes
3. Trigger GitHub Actions manually: **Actions → Investment Engine → Run workflow**

---

## 📝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on:

- Adding or editing tickers
- Creating new pillars and sectors
- Modifying the scoring algorithm
- Opening issues and pull requests

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🤝 Support

- **Questions?** Open an [issue](https://github.com/aspeez/InvestmentEngine/issues)
- **Have an idea?** Open a [discussion](https://github.com/aspeez/InvestmentEngine/discussions)
- **Found a bug?** Open an [issue with details](https://github.com/aspeez/InvestmentEngine/issues/new)

---

**Made with ❤️ for AI-sector stock research.**
