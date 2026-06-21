# InvestmentEngine

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/aspeez/InvestmentEngine.svg)](https://github.com/aspeez/InvestmentEngine/issues)

Automated daily investment research and scoring platform. Scans the full Finviz Elite universe, scores every qualifying stock on a 0–100 composite, and surfaces the top 10 per sector in a consolidated CSV sorted by Investment Score.

## ✨ Features

- **📊 Automated Daily Scoring** — Runs every day at 7:00 AM EST via GitHub Actions
- **🌐 Full Universe Scan** — Scans all Finviz-covered stocks, not a fixed ticker list
- **🔢 Weighted Composite Scoring** — 0–100 investment score with dynamic weight redistribution for missing data
- **🗂️ Sector Diversification** — Top 10 stocks per sector across all 12 Finviz sectors (up to 120 total)
- **🔄 CSV Export** — Consolidated scored output sorted by Investment Score for Claude.ai review

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Scoring Model](#scoring-model)
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
https://elite.finviz.com/export?v=150&c=...&auth=YOUR_TOKEN_HERE
```

### 4. Set the Environment Variable

```powershell
$env:FINVIZ = "your_finviz_auth_token_here"
```

### 5. Run the Engine (Local)

```powershell
python investment-engine/engine/data_engine.py
```

Output files appear in `investment-engine/stock-data/` and `investment-engine/ticker-review/`.

### 6. Set Up GitHub Actions

1. Push your repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add `FINVIZ` secret with your auth token
4. The workflow runs automatically every day at 7:00 AM EST
5. Manual trigger: **Actions → Investment Engine → Run workflow**

After each run, a GitHub Issue signals that Phase 2 is ready.

---

## 🔄 How It Works

### Phase 1 — GitHub Actions (Automated)

Every day at 7:00 AM EST (or manually triggered):

1. **Scan Finviz universe** — calls the Finviz Elite export API with pre-filters (positive EPS growth, positive net margin, Buy/Strong Buy analyst rating) to narrow the universe before downloading
2. **Derive metrics:**
   - Buy Zone = 52-Week High × 0.80
   - PSG = P/S Ratio ÷ Revenue Growth %
   - Graham Number = √(22.5 × EPS × Book/sh)
   - Upside % = ((Target − Price) / Price) × 100
3. **Compute Investment Score** — 0–100 weighted composite across 11 metrics
4. **Filter** — keep only tickers with Investment Score ≥ 70 and Upside % > 10%
5. **Select top 10 per sector** — picks the highest-scoring 10 from each of the 12 Finviz sectors for diversity (up to 120 total)
6. **Sort** — all selected tickers ordered by Investment Score descending
7. **Split tickers:**
   - ≤ 3 null data columns → Investment Master
   - \> 3 null data columns → Speculative Investments
8. **Export consolidated CSV** — `investment-engine/stock-data/consolidated_MMDDYYYY.csv`
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

Close the GitHub Issue when done.

---

## 📂 Project Structure

```
InvestmentEngine/
├── investment-engine/
│   ├── Ticker-Master.json                 ← Retained for reference; not used as engine input
│   ├── engine/
│   │   └── data_engine.py                 ← Phase 1 engine
│   └── stock-data/
│       └── consolidated_MMDDYYYY.csv      ← Scored output (up to 120 stocks)
├── .github/
│   └── workflows/
│       └── data_engine.yml
├── requirements.txt
├── pyproject.toml                         ← Python packaging metadata
├── QUICKSTART.md                          ← Step-by-step setup guide
├── COLUMN_REFERENCE.md                    ← Detailed column definitions
├── CONTRIBUTING.md                        ← How to modify the engine
├── LICENSE                                ← MIT License
└── README.md                              ← You are here
```

---

## 🎯 Scoring Model

The **Investment Score (0–100)** is a weighted composite across 4 categories:

| Category | Metrics | Nominal Weight |
|---|---|---|
| **Growth (30%)** | Revenue Growth %, EPS Growth % | 20%, 10% |
| **Financial Quality (25%)** | Gross Margin %, Net Profit Margin %, Debt/Equity | 10%, 10%, 5% |
| **Valuation (20%)** | PEG, PSG, Upside % | 5%, 5%, 10% |
| **Entry Timing (15%)** | Buy Zone vs Price, Analyst Recom, Short Float % | 5%, 5%, 5% |

Weights sum to 90% nominally (RSI removed). The formula divides by `total_weight`, so the 10% redistributes proportionally across all present metrics automatically.

**Scoring direction:**
- ⬆️ Higher is better: Revenue Growth, EPS Growth, Gross Margin, Net Profit Margin, Upside %
- ⬇️ Lower is better: PEG (capped at 3.0), PSG (capped at 3.0), Debt/Equity (capped at 3.0), Short Float % (capped at 30%), Analyst Recom (1.0 = strong buy)
- 💰 Buy Zone vs Price: 100 at or below buy zone (52-Week High × 0.80), 0 when 25%+ above

**Display-only columns (not scored):** P/E Ratio, P/S Ratio, RSI, Short Interest

**Missing data:** Weights are redistributed proportionally so partial data still produces a valid score.

**Score interpretation:**
- **70–100** — High conviction across most dimensions
- **50–70** — Solid candidate, above average
- **30–50** — Mixed signals
- **< 30** — Weak, poor growth or expensive valuation

See [COLUMN_REFERENCE.md](COLUMN_REFERENCE.md) for per-metric details.

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

# Run the engine
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

### `[WARN] Finviz request failed`

Network issue or invalid auth token. Confirm Finviz Elite is accessible and your token is correct.

### A known ticker is missing from the output

The Finviz pre-filters (`fa_epsqoq_pos`, `fa_netmargin_pos`, `an_recomendation_buybetter`) may have excluded it. A ticker must have positive EPS growth, positive net margin, and a Buy or Strong Buy analyst rating to enter the scored pool. Tickers failing these gates are excluded before scoring.

### Fewer than 120 rows in the CSV

Not all 12 sectors will always have 10 stocks meeting both the score ≥ 70 and upside > 10% thresholds. The output row count reflects what actually qualifies on that run.

---

## 📝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on:

- Modifying the scoring algorithm
- Adjusting pre-filters or thresholds
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

**Made with ❤️ for stock research.**
