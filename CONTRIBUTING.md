# Contributing to InvestmentEngine

Thanks for your interest in improving InvestmentEngine!

## Getting Started

The engine is designed to be modified via **configuration**, not code. Most changes should live in `investment-engine/Ticker-Master.json`.

---

## Adding or Editing Tickers

### Prerequisites

You'll need:
- A local clone of this repository
- Python 3.8+
- A Finviz Elite account and auth token

### Steps

#### 1. Edit `Ticker-Master.json`

Navigate to `investment-engine/Ticker-Master.json`. The file is organized by **Sector → Pillar → Tickers**:

```json
{
  "Technology": {
    "AI Compute Chips": ["NVDA", "AMD", "QCOM"],
    "AI Software and Platforms": ["MSFT", "GOOGL", "META"]
  },
  "Infrastructure": {
    "AI Power Generation": ["NEE", "DUK"],
    "AI Cooling": ["SPT", "COOL"]
  }
}
```

**To add a ticker:**
- Find the appropriate Sector and Pillar
- Append the ticker symbol to the list (must match Finviz format exactly — e.g., `NVDA`, not `Nvidia`)
- If the Pillar doesn't exist, create it
- If the Sector doesn't exist, create it

**To remove a ticker:**
- Delete it from the list
- If a pillar becomes empty, delete the pillar key
- If a sector becomes empty, delete the sector key

#### 2. Verify Your Changes

```powershell
python investment-engine/engine/data_engine.py
```

The engine will:
- Load your ticker configuration
- Create required directories automatically
- Fetch live data from Finviz
- Output a scored Excel workbook and CSV

Review the files in `investment-engine/sector/<SECTOR>/stock-data/`.

#### 3. Commit and Push

```bash
git add investment-engine/Ticker-Master.json
git commit -m "chore: add [TICKER] to [PILLAR]"
git push origin main
```

On the next GitHub Actions run (or manual trigger), the engine will use your updated config.

---

## Adding a New Pillar

Pillars represent investment themes (e.g., "AI Cybersecurity", "AI Power Generation").

**To add a pillar:**

1. Edit `investment-engine/Ticker-Master.json`
2. Find the appropriate Sector (or create a new one)
3. Add a new key with your pillar name and an array of tickers:

```json
{
  "Technology": {
    "AI Compute Chips": ["NVDA"],
    "[NEW_PILLAR_NAME]": ["TICKER1", "TICKER2"]
  }
}
```

4. Run the engine:

```powershell
python investment-engine/engine/data_engine.py
```

The engine creates a per-sector `pillar_tickers.json` and a dedicated Excel sheet for your pillar automatically.

---

## Adding a New Sector

Sectors organize multiple related pillars (e.g., "Technology", "Infrastructure").

**To add a sector:**

1. Edit `investment-engine/Ticker-Master.json`
2. Add a new top-level key with pillars and tickers:

```json
{
  "Technology": { ... },
  "[NEW_SECTOR]": {
    "[PILLAR]": ["TICKER1", "TICKER2"]
  }
}
```

3. Run the engine — it creates `sector/[NEW_SECTOR]/` and all subdirectories.

---

## Modifying Scoring Logic

**For changes to the Investment Score algorithm, Graham Number, or watchlist thresholds:**

- Edit `investment-engine/engine/data_engine.py`
- Update the relevant function (e.g., `compute_investment_score()`, `ROBINHOOD_WATCHLISTS`)
- Add a docstring if the change is non-obvious
- Test locally
- Open a pull request with a clear description of the change

---

## Reporting Issues

If you encounter a bug or have a feature request:

1. **Check existing issues** — your concern may already be tracked
2. **Open a new issue** with:
   - A clear title
   - Steps to reproduce (if applicable)
   - Expected vs. actual behavior
   - Your Python version and OS

---

## Code Style

This project follows **PEP 8**. Key conventions:

- Python 3.8+
- Type hints on function signatures
- Docstrings for public functions
- Max line length: 100 characters
- Use `black` for formatting (recommended)

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes and test locally
4. Commit with a clear message: `git commit -m "feat: description"`
5. Push to your fork: `git push origin feat/your-feature`
6. Open a pull request with:
   - A clear title
   - Description of changes
   - Link to any related issues

Your PR will be reviewed, and changes may be requested before merging.

---

## Questions?

Open an issue or discussion — we're happy to help!
