# Contributing to InvestmentEngine

Thanks for your interest in improving InvestmentEngine!

## How the Engine Works

The engine is a single Python script: `investment-engine/engine/data_engine.py`.

On each run it:
1. Calls the Finviz Elite export API with pre-filters to narrow the universe
2. Scores every returned ticker on a 0–100 Investment Score
3. Keeps tickers with score ≥ 70 and Upside % > 10%
4. Selects the top 10 per sector for diversity (up to 120 total)
5. Writes a consolidated CSV sorted by Investment Score descending

---

## Modifying the Scoring Algorithm

All scoring logic lives in `compute_investment_score()` in `data_engine.py`.

**To change a metric weight:**

Find the `weighted` list inside `compute_investment_score()` and adjust the weight value. Weights are normalized by the sum of present metrics, so you do not need to ensure they sum to any fixed total.

```python
weighted = [
    (rev_score, 0.20),   # ← change 0.20 to adjust Revenue Growth % weight
    (eps_score, 0.10),
    ...
]
```

**To add a new metric:**

1. Add the Finviz column code to `FINVIZ_COLUMNS` and document it in the comment block above
2. Parse the raw value in `_parse_row()`
3. Map it to a named field in the returned dict
4. Carry it through `fetch_records()` into the record dict
5. Add a normalized component score in `compute_investment_score()`
6. Add the `(score, weight)` tuple to the `weighted` list
7. Add the field name to `COLUMNS` so it appears in the CSV
8. Update `COLUMN_REFERENCE.md` with a description

**To remove a metric:**

Reverse the steps above. If it is display-only, just remove it from `COLUMNS` — no scoring change needed.

---

## Changing Pre-filters

The Finviz screener pre-filters are defined in:

```python
FINVIZ_UNIVERSE_FILTERS = "fa_epsqoq_pos,fa_netmargin_pos,an_recomendation_buybetter"
```

These narrow the universe before data is downloaded. Valid filter codes are found in the Finviz Elite screener URL. Adding stricter filters reduces the universe and may prevent some sectors from reaching 10 qualifying tickers.

---

## Adjusting Score and Upside Thresholds

```python
DISCOVERY_SCORE_THRESHOLD = 70.0   # minimum Investment Score to qualify
UNIVERSE_TOP_PER_SECTOR = 10       # max tickers selected per sector
```

Lowering `DISCOVERY_SCORE_THRESHOLD` increases the number of qualifying tickers. Raising `UNIVERSE_TOP_PER_SECTOR` increases diversity but may dilute quality.

The Upside % floor (> 10%) is applied inline in `run()`:

```python
if (r.get("Investment Score") or 0) >= DISCOVERY_SCORE_THRESHOLD and (r.get("Upside %") or 0) > 10:
```

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
- Max line length: 100 characters
- Use `black` for formatting (recommended)

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes and test locally
4. Commit with a clear message: `git commit -m "feat: description"`
5. Push to your fork: `git push origin feat/your-feature`
6. Open a pull request with a clear title and description of changes

---

## Questions?

Open an issue or discussion — we're happy to help!
