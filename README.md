# InvestmentEngine

Automated weekly investment research and scoring platform for AI-sector stocks.

## Overview

The engine runs in two phases each week:

- **Phase 1 — GitHub Actions (automated):** Fetches live data from Finviz Elite, scores every ticker, generates the Excel workbook, exports a consolidated CSV, classifies tickers into Robinhood watchlists, and commits everything to the repo. Ends by creating a GitHub Issue signaling that Phase 2 is ready.
- **Phase 2 — Claude.ai Investment Engine Project (interactive):** Claude reads the committed files, pushes qualifying tickers to Robinhood watchlists via the MCP connector (duplicate-safe), sends a completion summary, then does deep research to surface additional High Conviction candidates and commits results back to the repo.

---

## Project structure

```
InvestmentEngine/
  investment-engine/
    Ticker-Master.json               ← source of truth for all tickers
    engine/
      data_engine.py                 ← Phase 1 engine
      push_watchlists.py             ← reference script (Phase 2 handled by Claude.ai)
    sector/
      <SECTOR>/
        pillar_tickers.json
        stock-data/
          investment_data_MMDDYYYY.xlsx   ← scored workbook
          consolidated_MMDDYYYY.csv       ← Investment Master + Speculative combined
        ticker-review/
          watchlist_MMDDYYYY.json         ← watchlist classification (WL1–WL4)
          research_MMDDYYYY.json          ← Claude deep research output
  .github/
    workflows/
      data_engine.yml
  requirements.txt
  README.md
  QUICKSTART.md
  COLUMN_REFERENCE.md
```

---

## Phase 1 — What GitHub Actions does

Runs automatically every Sunday at 9:00 PM UTC. Can also be triggered manually via Actions → Investment Engine → Run workflow.

### Step-by-step

1. **Load tickers** from `Ticker-Master.json` (organized by Sector → Pillar across 19 AI pillars)
2. **Sync** per-sector `pillar_tickers.json` files
3. **Fetch data** — single bulk GET to Finviz Elite for all tickers at once
4. **Derive calculated fields** per ticker:
   - `Buy Zone` = Current Price × 0.80
   - `Graham Number` = √(22.5 × EPS × Book/sh) → sets `Graham Undervalued` True/False/None
   - `Upside %` = ((Target Price − Current Price) / Current Price) × 100
5. **Compute Investment Score** (0–100 weighted composite — see scoring section below)
6. **Split tickers:**
   - ≤ 2 null data columns → Investment Master tab
   - \> 2 null data columns → Speculative Investments tab
7. **Write Excel workbook** to `sector/<SECTOR>/stock-data/investment_data_MMDDYYYY.xlsx`
   - Tab 1: Investment Master (sorted by Investment Score descending)
   - Tab 2: Speculative Investments (sorted by Investment Score descending)
   - Tabs 3+: One tab per pillar with all tickers for that pillar
8. **Export consolidated CSV** to `sector/<SECTOR>/stock-data/consolidated_MMDDYYYY.csv`
   - Combines Investment Master and Speculative rows into one file
   - Adds a `Tab` column identifying the source row
9. **Classify watchlists** — evaluates every ticker against the 4 Robinhood scorecards using highest-tier-wins logic; saves `sector/<SECTOR>/ticker-review/watchlist_MMDDYYYY.json`
10. **Commit and push** all output files
11. **Create GitHub Issue** — signals Phase 2 is ready with links to the committed files

### GitHub secret required

| Secret | Purpose |
|---|---|
| `FINVIZ` | Finviz Elite auth token (from the `auth=` parameter in your export URL) |

---

## Phase 2 — What Claude.ai does

After Phase 1 creates the GitHub Issue, open the **Investment Engine** project in Claude.ai and say **"run the investment review for [date]"**.

1. **Data received notification** — confirms row counts from the consolidated CSV
2. **Duplicate check** — reads all 4 Robinhood watchlists before adding anything
3. **Add to watchlists** — pushes qualifying tickers to WL1–WL4 via Robinhood MCP (each ticker appears on one list only)
4. **Completion summary** — lists every ticker added per watchlist
5. **Deep research** — surfaces additional High Conviction candidates not currently in the ticker universe
6. **Commit research** — writes `research_MMDDYYYY.json` to `ticker-review/` via GitHub MCP

Close the GitHub Issue when Phase 2 is complete.

---

## Workbook layout

| Tab | Contents |
|---|---|
| **Investment Master** | Tickers with ≤ 2 null columns, sorted by Investment Score descending |
| **Speculative Investments** | Tickers with > 2 null columns, sorted by Investment Score descending |
| **AI [Pillar Name]** | All tickers for that pillar (including speculative) |

### Columns (21 total)

| Column | Source |
|---|---|
| Pillar | `Ticker-Master.json` |
| Ticker | `Ticker-Master.json` |
| Current Price | Finviz |
| RSI | Finviz |
| P/E Ratio | Finviz |
| P/S Ratio | Finviz |
| Market Cap | Finviz (converted from millions to full dollars) |
| Buy Zone | Calculated — Current Price × 0.80 |
| Target Price | Finviz analyst consensus |
| Graham Undervalued | Calculated — True/False/None |
| Upside % | Calculated — ((Target − Price) / Price) × 100 |
| Revenue Growth % | Finviz Sales Q/Q (5Y fallback) |
| EPS Growth % | Finviz EPS Q/Q (5Y fallback) |
| Gross Margin % | Finviz |
| Net Profit Margin % | Finviz |
| Debt/Equity | Finviz |
| Beta | Finviz |
| Insider Ownership % | Finviz |
| Institutional Ownership % | Finviz |
| Analyst Recom | Finviz (1.0 = Strong Buy, 5.0 = Strong Sell) |
| Investment Score | Calculated — weighted 0–100 composite |

All float values are rounded to 2 decimal places.

---

## Investment Score

A 0–100 composite score across 11 metrics. Missing metrics are excluded and the remaining weights are rescaled proportionally so partial data still produces a valid score.

| Category | Metric | Weight |
|---|---|---|
| **Growth (30%)** | Revenue Growth % | 20% |
| | EPS Growth % | 10% |
| **Financial Quality (25%)** | Gross Margin % | 10% |
| | Net Profit Margin % | 10% |
| | Debt/Equity | 5% |
| **Valuation (25%)** | P/S Ratio | 10% |
| | Upside % | 10% |
| | P/E Ratio | 5% |
| **Entry Timing (20%)** | RSI | 10% |
| | Buy Zone Proximity | 5% |
| | Analyst Recom | 5% |

**Scoring direction:**
- Higher is better: Revenue Growth, EPS Growth, Gross Margin, Net Profit Margin, Upside %
- Lower is better: P/E (capped at 60; negative = 0), P/S (capped at 30), Debt/Equity (capped at 3.0), Analyst Recom (1.0 scores 100, 5.0 scores 0)
- RSI: peaks at 30 (oversold), zero at 80 (overbought)
- Buy Zone Proximity: 100 at or below buy zone, 0 when 25%+ above it

---

## Robinhood Watchlists

Four watchlists are pre-configured in Robinhood. Every ticker is evaluated against them in order — first match wins, no duplicates across lists. Gross Margin % is intentionally excluded from watchlist thresholds (varies too widely across 19 pillars) but remains in the workbook and CSV as a reference column.

| Watchlist | Key Thresholds |
|---|---|
| **WL1 — High Conviction 🟢** | Score ≥70 \| Rev Growth ≥20% \| EPS Growth ≥20% \| Net Margin ≥10% \| D/E ≤1.0 \| RSI 30–55 \| Upside ≥20% \| Analyst ≤2.0 |
| **WL2 — Pullback Watch 🔵** | Score ≥60 \| Rev Growth ≥15% \| EPS Growth ≥10% \| Net Margin ≥5% \| D/E ≤1.5 \| RSI 30–50 \| Upside ≥20% \| Analyst ≤2.5 |
| **WL3 — Deep Value 🟡** | Score ≥50 \| Rev Growth ≥10% \| EPS Growth ≥0% \| Net Margin >0% \| D/E ≤1.0 \| RSI ≤35 \| Upside ≥15% \| Analyst ≤2.5 |
| **WL4 — Pipeline ⚪** | Score 50–60 \| Rev Growth ≥15% \| EPS Growth ≥10% \| Net Margin ≥5% \| D/E ≤1.5 \| RSI any \| Upside ≥15% \| Analyst ≤2.5 |

---

## AI Pillars (19 total)

AI Power Generation, AI Networking, AI Memory and Storage, AI Land, AI Heating and Cooling, AI Grid and Power Transmission, AI Electrical Infrastructure, AI Construction, AI Cybersecurity, AI Semiconductor Chip Manufacturing, AI Server and Rack Systems, AI Software and Platforms, AI Backup Power, AI Cloud, AI Fire Detection, AI Water, AI Insurance and Risk, AI Security, AI Compute Chips

---

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:FINVIZ = "your_finviz_auth_token_here"
python investment-engine/engine/data_engine.py
```

To add tickers, edit `investment-engine/Ticker-Master.json`. The engine creates required directories automatically on the next run.
