# Column Reference — consolidated_MMDDYYYY.csv

This document covers every column in the consolidated CSV output, including what it measures, what values you will see, and what ranges to look for from an investment perspective.

---

## Tab

**What it means:** Indicates which data-quality tier the ticker falls in.

**Values:**
- `Investment Master` — ≤ 3 null data columns; sufficient data for a reliable score
- `Speculative Investments` — > 3 null data columns; score is less reliable, use with caution

---

## Ticker

**What it means:** The stock's exchange symbol as recognized by Finviz (e.g., `NVDA`, `CRWD`, `MSFT`).

**Values:** Short uppercase string. Always present.

**Investment context:** No range applies — this is an identifier.

---

## Sector

**What it means:** The Finviz sector classification for the stock (e.g., Technology, Healthcare, Financial).

**Values:** One of the 12 Finviz sectors — always a string.

**Investment context:** The engine selects the top 10 stocks per sector to ensure diversity across the consolidated CSV. Use Sector to benchmark a ticker against its peers.

---

## Current Price

**What it means:** The latest market price of the stock in USD, sourced from Finviz.

**Values:** Positive decimal, e.g. `142.50`. Can be `None` if the ticker is not found by Finviz.

**Investment context:** Price alone is not meaningful — always evaluate relative to Buy Zone, Target Price, and Graham Number. A low price does not make a stock cheap; a high price does not make it expensive.

---

## 52-Week High

**What it means:** The highest price the stock has traded at over the past 52 weeks, in USD. Derived from Finviz's "% below 52-week high" field and converted to a dollar price.

**Formula:** `52W High = Current Price / (1 + pct_from_high / 100)`

**Values:** Positive float. Can be `None` if data is unavailable.

**Investment context:** Used as the anchor for the Buy Zone calculation. A stock trading 20%+ below its 52-week high signals a genuine pullback from recent strength.

---

## RSI

**What it means:** Relative Strength Index (14-period). Sourced from Finviz. Display-only — **not included in the Investment Score**.

**Values:** Float between 0 and 100. Can be `None` if Finviz lacks sufficient price history.

| Range | What it means | Investment signal |
|---|---|---|
| < 30 | Oversold | **Strong buy opportunity** — stock may have pulled back too far |
| 30–50 | Neutral to slightly oversold | **Favorable entry zone** |
| 50–70 | Neutral to slightly overbought | Caution — momentum is fading |
| > 70 | Overbought | **Avoid new entries** — likely due for a pullback |

**Ideal entry:** 30–50.

---

## P/E Ratio

**What it means:** Price-to-Earnings ratio. Measures how much investors are paying per dollar of earnings. Sourced directly from Finviz. Display-only — **not included in the Investment Score** (see PEG).

**Values:** Positive float. `None` if EPS is unavailable or negative.

| Range | What it means | Investment signal |
|---|---|---|
| Negative / 0 | Company is losing money | Caution — no earnings base |
| < 20 | Cheap relative to earnings | **Very attractive** (rare for AI stocks) |
| 20–40 | Reasonable for established tech | **Attractive** |
| 40–80 | Typical for high-growth plays | Reasonable — check growth rate |
| > 80 | Expensive, priced for perfection | Elevated risk — needs strong growth to justify |

---

## PEG

**What it means:** Price/Earnings-to-Growth ratio. Sourced directly from Finviz. Measures valuation relative to earnings growth — lower is better.

**Values:** Positive float. `None` if unavailable.

**Scoring:** Normalized inversely between 0 and 3.0 (capped). Weight in the Investment Score: 5%.

| Range | Investment signal |
|---|---|
| < 1.0 | **Undervalued relative to growth** |
| 1.0–2.0 | **Reasonably valued** |
| 2.0–3.0 | Elevated — growth must deliver |
| > 3.0 | Overpriced relative to growth |

---

## P/S Ratio

**What it means:** Price-to-Sales ratio. Measures market cap relative to revenue. Display-only — **not included in the Investment Score** (see PSG).

**Values:** Positive float. `None` if revenue is unavailable.

| Range | What it means | Investment signal |
|---|---|---|
| < 5 | Very cheap relative to revenue | **Very attractive** |
| 5–15 | Reasonable for a growth company | **Attractive** |
| 15–30 | Expensive | Requires strong revenue growth to justify |
| > 30 | Very expensive | Significant premium — high execution risk |

---

## PSG

**What it means:** Price/Sales-to-Growth ratio. Computed as `P/S Ratio ÷ Revenue Growth %`. Measures valuation relative to sales growth — lower is better.

**Formula:** `PSG = P/S Ratio / Revenue Growth %`

**Values:** Positive float. `None` if P/S or Revenue Growth % is unavailable or zero/negative.

**Scoring:** Normalized inversely between 0 and 3.0 (capped). Weight in the Investment Score: 5%.

---

## Market Cap

**What it means:** Total market value of the company's outstanding shares in USD. Sourced from Finviz (converted from millions to absolute dollars).

**Values:** Large positive integer (typically in the billions). Can be `None`.

| Tier | Range |
|---|---|
| Mega Cap | > $200B |
| Large Cap | $10B – $200B |
| Mid Cap | $2B – $10B |
| Small Cap | < $2B |

**Investment context:** Market Cap is not scored directly. Smaller market caps carry more growth potential but also more volatility and liquidity risk.

---

## Target Price

**What it means:** The analyst consensus price target sourced directly from Finviz. Represents where Wall Street expects the stock to trade.

**Values:** Positive float. `None` if no analyst coverage is available.

**Investment context:** Compare Target Price to Current Price.

| Scenario | Signal |
|---|---|
| Target Price > Current Price | Potential upside — analysts see room to run |
| Target Price ≈ Current Price | Fairly valued at current analyst consensus |
| Target Price < Current Price | Analysts see downside from current levels |

---

## Graham Undervalued

**What it means:** A boolean flag indicating whether the stock is trading below its Graham Number — a classic value-investing estimate of intrinsic worth.

**Formula:** `Graham Number = √(22.5 × EPS (ttm) × Book Value Per Share)`

**Values:**
- `True` — Current Price is below the Graham Number (stock appears undervalued by this measure)
- `False` — Current Price is at or above the Graham Number
- `None` — EPS or Book Value Per Share data was unavailable

**Investment context:** The Graham Number was designed for stable, dividend-paying businesses — most high-growth stocks will fail this test. A reading of `True` in this universe is notable. A reading of `False` is expected for growth stocks.

**This column does not affect the Investment Score.** It is informational only.

---

## Upside %

**What it means:** The percentage gain from Current Price to analyst consensus Target Price.

**Formula:** `Upside % = ((Target Price − Current Price) / Current Price) × 100`

**Values:** Float expressed as a percentage (e.g., `25.0` means 25%). Can be negative if Target Price is below Current Price.

| Range | Investment signal |
|---|---|
| > 30% | **Strong upside** — attractive risk/reward |
| 15–30% | **Solid upside** — worth consideration |
| 5–15% | Modest upside — limited margin of safety |
| < 5% | Fairly to fully valued |
| Negative | Analysts see downside risk at current price |

**Ideal:** ≥ 20%. Weight in the Investment Score: 10%. Tickers with Upside % ≤ 10% are excluded before selection.

---

## Revenue Growth %

**What it means:** Year-over-year percentage change in revenue. Uses Sales Growth Q/Q (quarter over quarter) as the primary source, with Sales Growth Past 5 Years as a fallback. Both sourced from Finviz.

**Values:** Float percentage (e.g., `18.5` = 18.5% growth). Can be negative.

| Range | Investment signal |
|---|---|
| > 30% | **Exceptional growth** |
| 15–30% | **Strong growth** |
| 5–15% | Moderate growth |
| 0–5% | Slow growth |
| Negative | Revenue contraction — significant red flag |

**Ideal:** ≥ 15%. Highest-weighted single metric in the Investment Score at 20%.

---

## EPS Growth %

**What it means:** Year-over-year percentage change in earnings per share. Uses EPS Growth Q/Q as the primary source, with EPS Growth Past 5 Years as a fallback. Both sourced from Finviz.

**Values:** Float percentage. Can be very large (triple-digit) or negative.

| Range | Investment signal |
|---|---|
| > 30% | **Exceptional** — earnings accelerating |
| 15–30% | **Strong** |
| 5–15% | Moderate |
| 0–5% | Slow |
| Negative | EPS declining — caution |

**Ideal:** ≥ 20%. Weight in the Investment Score: 10%.

---

## Gross Margin %

**What it means:** The percentage of revenue retained after subtracting the cost of goods sold. A measure of pricing power and business efficiency. Sourced directly from Finviz.

**Values:** Float percentage (e.g., `68.5` = 68.5%). Can be `None`.

| Range | What it means | Investment signal |
|---|---|---|
| > 60% | High-margin software / chip design | **Excellent** |
| 40–60% | Mixed or hardware-software model | **Good** |
| 25–40% | Hardware, infrastructure, utilities | Acceptable for the sector |
| < 25% | Low margin — commoditized or capital-intensive | Requires high volume or growth |

Weight in the Investment Score: 10%.

---

## Net Profit Margin %

**What it means:** The percentage of revenue that becomes net income after all expenses, taxes, and interest. Sourced from Finviz (Profit Margin field).

**Values:** Float percentage. Can be negative for unprofitable companies.

| Range | Investment signal |
|---|---|
| > 20% | **Excellent profitability** |
| 10–20% | **Strong** |
| 5–10% | Moderate |
| 0–5% | Thin — watch for compression |
| Negative | Company is losing money |

**Ideal:** ≥ 10%. Weight in the Investment Score: 10%.

---

## Debt/Equity

**What it means:** Total debt divided by shareholders' equity. Measures how leveraged the company is. Sourced from Finviz (Total Debt/Equity).

**Values:** Positive float. Higher = more leveraged. Can be `None`.

| Range | Investment signal |
|---|---|
| < 0.3 | **Very low leverage** — strong balance sheet |
| 0.3–1.0 | **Moderate** — manageable |
| 1.0–2.0 | High leverage — monitor debt service |
| > 2.0 | **Very high leverage** — significant risk in rising rate environment |

**Ideal:** Below 1.0. The Investment Score caps at 3.0 — anything above that scores 0. Weight: 5%.

---

## Beta

**What it means:** A measure of how volatile the stock is relative to the broader market. Beta of 1.0 means it moves with the market; above 1.0 means more volatile; below 1.0 means less volatile. Sourced from Finviz.

**Values:** Float. Typically between 0 and 3 for most stocks.

| Range | What it means |
|---|---|
| < 0.8 | Low volatility — moves less than the market |
| 0.8–1.2 | Market-like volatility |
| 1.2–2.0 | Elevated volatility — common for growth stocks |
| > 2.0 | High volatility — large swings in both directions |

**Investment context:** Beta is informational — it does not affect the Investment Score. Use Beta to size positions appropriately and set expectations for drawdown risk.

---

## Insider Ownership %

**What it means:** The percentage of shares held by company insiders (executives, directors, large individual shareholders). Sourced from Finviz.

**Values:** Float percentage. Can be `None`.

| Range | Investment signal |
|---|---|
| > 20% | **Strong alignment** — management has significant skin in the game |
| 5–20% | **Healthy insider ownership** |
| 1–5% | Modest — common for large caps |
| < 1% | Low — management may have limited personal stake |

**Investment context:** This column is informational — it does not affect the Investment Score.

---

## Institutional Ownership %

**What it means:** The percentage of shares held by institutional investors (mutual funds, ETFs, hedge funds, pension funds). Sourced from Finviz.

**Values:** Float percentage.

| Range | Investment signal |
|---|---|
| > 70% | **Heavily institutionalized** — validates the thesis |
| 40–70% | **Strong institutional interest** |
| 20–40% | Moderate |
| < 20% | Low institutional coverage — may be underfollowed |

**Investment context:** This column is informational — it does not affect the Investment Score.

---

## Analyst Recom

**What it means:** The Finviz analyst consensus recommendation score. Aggregates buy/hold/sell ratings across covering analysts into a single number.

**Values:** Float between 1.0 and 5.0.

| Score | Meaning |
|---|---|
| 1.0 | Strong Buy |
| 2.0 | Buy |
| 3.0 | Hold |
| 4.0 | Sell |
| 5.0 | Strong Sell |

**Investment context:** Lower is more bullish. Scores below 2.0 indicate broad analyst conviction. Weight in the Investment Score: 5%.

---

## Short Interest

**What it means:** The absolute number of shares currently sold short. Sourced from Finviz. Display-only — **not included in the Investment Score** (see Short Float %).

**Values:** Large positive integer. Can be `None`.

**Investment context:** High short interest can mean either bearish conviction or potential for a short squeeze. Use Short Float % (below) for the scored representation.

---

## Short Float %

**What it means:** Short interest as a percentage of the float. Measures how much of the tradeable supply is sold short. Sourced from Finviz.

**Values:** Float percentage (e.g., `5.2` = 5.2% of float is short). Can be `None`.

| Range | Investment signal |
|---|---|
| < 5% | **Low short pressure** — broadly owned |
| 5–15% | Moderate — watch for sentiment shifts |
| 15–30% | High — significant bearish conviction or squeeze risk |
| > 30% | **Very high** — scores 0 (capped at 30% in scoring) |

**Ideal:** Below 10%. Weight in the Investment Score: 5%.

---

## Investment Score

**What it means:** A 0–100 composite score summarizing overall investment attractiveness across four categories: Growth, Financial Quality, Valuation, and Entry Timing. Higher is better.

**Values:** Float between 0 and 100. Can be `None` if too few metrics are available.

**How it is computed:** Each metric is normalized to a 0–100 component score, then multiplied by its weight. If a metric is missing, its weight is redistributed proportionally to the remaining metrics so partial data still produces a meaningful score.

| Category | Metric | Nominal Weight | Notes |
|---|---|---|---|
| Growth (30%) | Revenue Growth % | 20% | |
| | EPS Growth % | 10% | |
| Financial Quality (25%) | Gross Margin % | 10% | |
| | Net Profit Margin % | 10% | |
| | Debt/Equity | 5% | |
| Valuation (20%) | PEG | 5% | Finviz native (col 9) |
| | PSG | 5% | Computed: P/S ÷ Revenue Growth % |
| | Upside % | 10% | |
| Entry Timing (15%) | Buy Zone vs Price | 5% | Based on 52-Week High × 0.80 |
| | Analyst Recom | 5% | |
| | Short Float % | 5% | Lower is better; capped at 30% |

P/E Ratio, P/S Ratio, RSI, and Short Interest are display-only columns — they are not part of the weighted score sum.

**Weight normalization note:** The 11 metrics above sum to 90% nominally. The scoring formula divides by `total_weight` rather than a fixed 1.0, so missing metrics redistribute their weight proportionally to the remaining present metrics.

| Score Range | Interpretation |
|---|---|
| 70–100 | **High conviction** — strong across most dimensions |
| 50–70 | **Solid candidate** — above average, worth monitoring |
| 30–50 | **Mixed signals** — some positives offset by weaknesses |
| < 30 | **Weak** — poor growth, expensive valuation, or bad timing |

**Ideal:** ≥ 70 (minimum threshold to appear in the output CSV).
