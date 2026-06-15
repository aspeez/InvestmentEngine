# Column Reference — investment_data_MMDDYYYY.xlsx

This document covers every column generated in the workbook, including what it measures, what values you will see, and what ranges to look for from an investment perspective.

---

## Pillar *(Investment Master tab only)*

**What it means:** The AI sub-theme that the ticker belongs to (e.g., "AI Compute Chips", "AI Cybersecurity"). Pulled from `Ticker-Master.json`.

**Values:** One of the 19 configured AI pillars — always a string.

**Investment context:** Use the pillar to benchmark a ticker against its peers. A high Investment Score in a high-conviction pillar (e.g., AI Compute Chips) carries more weight than the same score in a less-core pillar.

---

## Ticker

**What it means:** The stock's exchange symbol as recognized by FMP (e.g., `NVDA`, `CRWD`, `MSFT`).

**Values:** Short uppercase string. Always present.

**Investment context:** No range applies — this is an identifier.

---

## Current Price

**What it means:** The latest market price of the stock in USD, sourced from FMP's `batch-quote` endpoint.

**Values:** Positive decimal, e.g. `142.50`. Can be `None` if the ticker is not found by FMP.

**Investment context:** Price alone is not meaningful — always evaluate relative to Buy Zone, Target Price, and Graham Number. A low price does not make a stock cheap; a high price does not make it expensive.

---

## RSI

**What it means:** Relative Strength Index — a momentum oscillator measuring the speed and magnitude of recent price changes. Calculated over a 10-period, 1-day timeframe via FMP.

**Values:** Float between 0 and 100. Can be `None` if FMP lacks sufficient price history.

| Range | What it means | Investment signal |
|---|---|---|
| < 30 | Oversold | **Strong buy opportunity** — stock may have pulled back too far |
| 30–50 | Neutral to slightly oversold | **Favorable entry zone** |
| 50–70 | Neutral to slightly overbought | Caution — momentum is fading |
| > 70 | Overbought | **Avoid new entries** — likely due for a pullback |

**Ideal:** 30–50. The Investment Score assigns maximum points at RSI = 30 and zero points at RSI ≥ 80.

---

## P/E Ratio

**What it means:** Price-to-Earnings ratio. Measures how much investors are paying per dollar of earnings. Calculated from Current Price and annual diluted EPS sourced from FMP `income-statement`.

**Formula:** `P/E Ratio = Current Price ÷ EPS Diluted (Annual)`

**Values:** Positive float. `None` if EPS is unavailable or zero. Negative result means EPS is negative (company is unprofitable) — these are capped to 0 in the Investment Score.

| Range | What it means | Investment signal |
|---|---|---|
| Negative / 0 | Company is losing money | Caution — no earnings base |
| < 20 | Cheap relative to earnings | **Very attractive** (rare for AI stocks) |
| 20–40 | Reasonable for established tech | **Attractive** |
| 40–80 | Typical for high-growth AI plays | Reasonable — check growth rate |
| > 80 | Expensive, priced for perfection | Elevated risk — needs strong growth to justify |

**Ideal for this universe:** Below 40 is attractive. The Investment Score caps the P/E component at 60 — anything at or above that scores 0. High P/E does not automatically disqualify a fast-grower, but it leaves no margin for error.

---

## P/S Ratio

**What it means:** Price-to-Sales ratio. Measures market cap relative to revenue. Useful for companies that are not yet profitable. Calculated from Market Cap and Revenue sourced from FMP `income-statement`.

**Formula:** `P/S Ratio = Market Cap ÷ Revenue`

**Values:** Positive float. `None` if revenue is unavailable or zero.

| Range | What it means | Investment signal |
|---|---|---|
| < 5 | Very cheap relative to revenue | **Very attractive** |
| 5–15 | Reasonable for a growth company | **Attractive** |
| 15–30 | Expensive | Requires strong revenue growth to justify |
| > 30 | Very expensive | Significant premium — high execution risk |

**Ideal:** Below 10. The Investment Score caps the P/S component at 30 — anything at or above that scores 0.

---

## Market Cap

**What it means:** Total market value of the company's outstanding shares in USD. Sourced from FMP `market-capitalization-batch`.

**Values:** Large positive number (typically in the billions). Can be `None`.

| Tier | Range |
|---|---|
| Mega Cap | > $200B |
| Large Cap | $10B – $200B |
| Mid Cap | $2B – $10B |
| Small Cap | < $2B |

**Investment context:** Most tickers in this universe are large or mega cap. Market Cap is used internally to compute the Net Cash Ratio and P/S Ratio and is not scored directly. Smaller market caps carry more growth potential but also more volatility and liquidity risk.

---

## Buy Zone

**What it means:** A reference entry price set at 20% below the current market price. Intended as a target for disciplined entry — if the stock pulls back to this level, it represents a more favorable risk/reward.

**Formula:** `Buy Zone = Current Price × 0.80`

**Values:** Positive float, always less than Current Price.

**Investment context:** Think of this as your limit-order target rather than a buy signal at today's price. If a stock is in a broader market pullback and approaches its Buy Zone level, that is an improved entry. The Buy Zone shifts with the price each run — track it across multiple weeks to identify meaningful support levels.

---

## Target Price

**What it means:** An estimated fair value for the stock based on expected earnings and a pillar-appropriate P/E multiple.

**Formula:** `Target Price = EPS Used × Pillar P/E Multiple`

**EPS source priority:**
1. Forward EPS from analyst consensus (`analyst-estimates`, field `epsAvg`)
2. Earnings estimate for the next unreported quarter (`earnings`, field `epsEstimated`; only attempted if analyst-estimates has no data)
3. Annual diluted EPS from `income-statement` (final fallback)

**Values:** Positive float. `None` if no EPS data is available for the ticker.

**Investment context:** Compare Target Price to Current Price.

| Scenario | Signal |
|---|---|
| Target Price > Current Price | Potential upside — stock may be undervalued |
| Target Price ≈ Current Price | Fairly valued at current levels |
| Target Price < Current Price | Potential downside — stock may be overvalued |

**Ideal:** Target Price meaningfully above Current Price (see Upside % for the quantified gap). Note that this is a model-derived estimate, not a guarantee — analyst EPS estimates can miss.

---

## Graham Undervalued

**What it means:** A boolean flag indicating whether the stock is trading below its Graham Number — a classic value-investing estimate of intrinsic worth developed by Benjamin Graham.

**Formula:** `Graham Number = √(22.5 × EPS × Book Value Per Share)`

**Values:**
- `True` — Current Price is below the Graham Number (stock appears undervalued by this measure)
- `False` — Current Price is at or above the Graham Number
- `None` — EPS or Book Value Per Share data was unavailable

**Investment context:** The Graham Number was designed for stable, dividend-paying businesses — it is a conservative metric that most high-growth AI stocks will fail. A reading of `True` in this universe is notable and worth investigating further. A reading of `False` is expected for growth stocks and does not by itself make them unattractive.

**This column does not affect the Investment Score.** It is informational only.

---

## Upside %

**What it means:** The percentage gain from Current Price to Target Price. Expresses how much return potential the model sees at the current price.

**Formula:** `Upside % = ((Target Price − Current Price) / Current Price) × 100`

**Values:** Float expressed as a percentage (e.g., `25.0` means 25%). Can be negative if Target Price is below Current Price. `None` if Target Price is `None`.

| Range | Investment signal |
|---|---|
| > 30% | **Strong upside** — attractive risk/reward |
| 15–30% | **Solid upside** — worth consideration |
| 5–15% | Modest upside — limited margin of safety |
| < 5% | Fairly to fully valued |
| Negative | Model sees downside risk at current price |

**Ideal:** ≥ 20%. The Investment Score uses Upside % as one of its inputs — higher values score better, normalized against the range observed across the universe.

---

## Revenue Growth %

**What it means:** Year-over-year percentage change in total revenue, sourced from FMP `financial-growth` (most recent annual filing).

**Values:** Float percentage (e.g., `18.5` = 18.5% growth). Can be negative (revenue declining). Can be `None`.

| Range | Investment signal |
|---|---|
| > 30% | **Exceptional growth** |
| 15–30% | **Strong growth** |
| 5–15% | Moderate growth — acceptable for mature businesses |
| 0–5% | Slow growth — below expectations for AI-adjacent names |
| Negative | Revenue contraction — significant red flag |

**Ideal:** ≥ 15% for most pillars; ≥ 25% for software/chip names with high valuations. This is the highest-weighted single metric in the Investment Score (20%).

---

## EPS Growth %

**What it means:** Year-over-year percentage change in earnings per share, sourced from FMP `financial-growth` (most recent annual filing).

**Values:** Float percentage. Can be very large (triple-digit) or negative. Can be `None`.

| Range | Investment signal |
|---|---|
| > 30% | **Exceptional** — earnings accelerating |
| 15–30% | **Strong** |
| 5–15% | Moderate |
| 0–5% | Slow — earnings barely growing |
| Negative | EPS declining — caution |

**Ideal:** ≥ 20%. Weight in the Investment Score is 10%. High EPS growth combined with high revenue growth is the clearest signal of a healthy business.

---

## Net Cash Ratio

**What it means:** Measures the company's net cash position (cash minus total debt) as a fraction of its market cap. A positive ratio means the company has more cash than debt. A negative ratio means the company carries net debt.

**Formula:** `Net Cash Ratio = (Cash − Total Debt) / Market Cap`

Data sourced from FMP `balance-sheet-statement`.

**Values:** Float. Positive = net cash; negative = net debt. Can be `None`.

| Range | Investment signal |
|---|---|
| > 0.20 | **Strong balance sheet** — 20%+ of market cap is net cash |
| 0.05–0.20 | **Healthy** |
| -0.05–0.05 | Roughly balanced — neither a strength nor a concern |
| -0.20 to -0.05 | Moderate leverage |
| < -0.20 | **High leverage** — watch debt service in a rising rate environment |

**Ideal:** ≥ 0.05 (net cash positive). Especially important in volatile macro environments. Weight in the Investment Score is 10%.

---

## Investment Score

**What it means:** A 0–100 composite score summarizing overall investment attractiveness across four categories: Growth, Financial Quality, Valuation, and Entry Timing. Higher is better.

**Values:** Float between 0 and 100. Can be `None` if too few metrics are available to compute a score.

**How it is computed:** Each metric is normalized to a 0–100 component score, then multiplied by its weight. If a metric is missing, its weight is redistributed proportionally to the remaining metrics so partial data still produces a meaningful score.

| Category | Metric | Weight |
|---|---|---|
| Growth (30%) | Revenue Growth % | 20% |
| | EPS Growth % | 10% |
| Financial Quality (10%) | Net Cash Ratio | 10% |
| Valuation (25%) | P/S Ratio | 10% |
| | Upside % | 10% |
| | P/E Ratio | 5% |
| Entry Timing (15%) | RSI | 10% |
| | Buy Zone Proximity | 5% |

| Score Range | Interpretation |
|---|---|
| 70–100 | **High conviction** — strong across most dimensions |
| 50–70 | **Solid candidate** — above average, worth monitoring |
| 30–50 | **Mixed signals** — some positives offset by weaknesses |
| < 30 | **Weak** — poor growth, expensive valuation, or bad timing |

**Ideal:** ≥ 60. Treat scores above 70 as priority watch-list candidates, especially if RSI is also below 50. Use this score to rank tickers within the same pillar and across pillars in the Investment Master tab.
