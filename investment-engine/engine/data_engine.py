from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

FINVIZ_BASE_URL = "https://elite.finviz.com/export"
# Column codes for the Finviz export endpoint (v=150)
# 1=Ticker, 3=Sector, 65=Price, 59=RSI(14), 7=P/E, 9=PEG, 10=P/S, 6=Market Cap, 69=Target Price,
# 16=EPS(ttm), 22=EPS Growth Q/Q, 19=EPS Growth Past 5Y, 73=Book/sh,
# 23=Sales Growth Q/Q, 21=Sales Growth Past 5Y, 12=P/Cash, 38=Total Debt/Equity,
# 41=Profit Margin, 39=Gross Margin, 48=Beta, 26=Insider Ownership,
# 28=Institutional Ownership, 62=Analyst Recom, 57=52W High,
# 30=Short Float, 84=Short Interest
FINVIZ_COLUMNS = "1,3,65,59,7,9,10,6,69,16,22,19,73,23,21,12,38,41,39,48,26,28,62,57,30,84"

REPO_ROOT = Path(__file__).resolve().parents[1]
STOCK_DATA_DIR = REPO_ROOT / "stock-data"
DATE_FORMAT = "%m%d%Y"

COLUMNS = [
    "Ticker",
    "Sector",
    "Current Price",
    "52-Week High",
    "RSI",
    "P/E Ratio",
    "PEG",
    "P/S Ratio",
    "PSG",
    "Market Cap",
    "Target Price",
    "Upside %",
    "Revenue Growth %",
    "EPS Growth %",
    "Gross Margin %",
    "Net Profit Margin %",
    "Debt/Equity",
    "Beta",
    "Insider Ownership %",
    "Institutional Ownership %",
    "Analyst Recom",
    "Short Interest",
    "Short Float %",
    "Investment Score",
]


class FinvizClient:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.session = requests.Session()

    def _parse_float(self, value: object) -> Optional[float]:
        if value in (None, "", "-", "N/A"):
            return None
        s = str(value).strip().rstrip("%").replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    def _clamp_growth(self, value: Optional[float], cap: float = 300.0) -> Optional[float]:
        """Treat growth % beyond a sane cap as a data artifact (e.g. near-zero prior-period
        base in Finviz's Q/Q calc) and null it out rather than passing through a nonsense value."""
        if value is None:
            return None
        if abs(value) > cap:
            return None
        return value

    def _parse_row(self, row: dict) -> Dict[str, Optional[float]]:
        p = self._parse_float

        price = p(row.get("Price"))
        market_cap_raw = p(row.get("Market Cap"))
        # Finviz exports Market Cap in millions — convert to full dollars, store as int
        market_cap = int(market_cap_raw * 1_000_000) if market_cap_raw is not None else None

        rev_qq_raw = p(row.get("Sales Growth Quarter Over Quarter"))
        rev_5y_raw = p(row.get("Sales Growth Past 5 Years"))
        rev_growth_qq = self._clamp_growth(rev_qq_raw)
        rev_growth_5y = self._clamp_growth(rev_5y_raw)
        rev_growth = rev_growth_qq if rev_growth_qq is not None else rev_growth_5y
        # Finviz had data but every source was clamped — likely a near-zero base artifact
        rev_growth_suspect = rev_growth is None and (rev_qq_raw is not None or rev_5y_raw is not None)

        eps_qq_raw = p(row.get("EPS Growth Quarter Over Quarter"))
        eps_5y_raw = p(row.get("EPS Growth Past 5 Years"))
        eps_growth_qq = self._clamp_growth(eps_qq_raw)
        eps_growth_5y = self._clamp_growth(eps_5y_raw)
        eps_growth = eps_growth_qq if eps_growth_qq is not None else eps_growth_5y
        eps_growth_suspect = eps_growth is None and (eps_qq_raw is not None or eps_5y_raw is not None)
        
        
        # Finviz "52W High" is % below the 52-week high (negative number).
        # Convert to the actual dollar price: price / (1 + pct/100).
        pct_from_high = p(row.get("52-Week High"))
        if price is not None and price > 0 and pct_from_high is not None:
            fifty_two_wk_high: Optional[float] = price / (1 + pct_from_high / 100)
        else:
            fifty_two_wk_high = None

        return {
            "Sector": row.get("Sector", ""),
            "Current Price": price,
            "RSI": p(row.get("Relative Strength Index (14)")),
            "P/E Ratio": p(row.get("P/E")),
            "PEG": p(row.get("PEG")),
            "P/S Ratio": p(row.get("P/S")),
            "Market Cap": market_cap,
            "Finviz Target Price": p(row.get("Target Price")),
            "EPS": p(row.get("EPS (ttm)")),
            "Book Value Per Share": p(row.get("Book/sh")),
            "Revenue Growth %": rev_growth,
            "Revenue Growth Suspect": rev_growth_suspect,
            "EPS Growth %": eps_growth,
            "EPS Growth Suspect": eps_growth_suspect,
            "Gross Margin %": p(row.get("Gross Margin")),
            "Net Profit Margin %": p(row.get("Profit Margin")),
            "Debt/Equity": p(row.get("Total Debt/Equity")),
            "Beta": p(row.get("Beta")),
            "Insider Ownership %": p(row.get("Insider Ownership")),
            "Institutional Ownership %": p(row.get("Institutional Ownership")),
            "Analyst Recom": p(row.get("Analyst Recom")),
            "52-Week High": fifty_two_wk_high,
            "Short Interest": p(row.get("Short Interest")),
            "Short Float %": p(row.get("Short Float")),
        }

    def _fetch_export(self, extra_params: str = "", timeout: int = 30) -> Dict[str, Dict[str, Optional[float]]]:
        url = (
            f"{FINVIZ_BASE_URL}?v=150"
            f"{extra_params}"
            f"&c={FINVIZ_COLUMNS}"
            f"&auth={self.auth_token}"
        )
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
        except Exception as exc:
            print(f"[WARN] Finviz request failed: {exc}")
            return {}
        try:
            reader = csv.DictReader(io.StringIO(response.text))
            rows = list(reader)
        except Exception as exc:
            print(f"[WARN] Finviz CSV parse failed: {exc}")
            return {}
        if not rows:
            print("[WARN] Finviz returned no data")
            return {}
        return {
            row.get("Ticker", "").strip().upper(): self._parse_row(row)
            for row in rows
            if row.get("Ticker", "").strip()
        }

    def get_all_metrics(self, tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
        """Bulk export for a specific list of tickers."""
        result = self._fetch_export(f"&t={','.join(tickers)}")
        missing = [t for t in tickers if t not in result]
        if missing:
            print(f"[WARN] Finviz returned no data for: {', '.join(missing)}")
        return result

    def get_universe_metrics(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Export Finviz tickers pre-filtered by scoring criteria."""
        return self._fetch_export(f"&f={FINVIZ_UNIVERSE_FILTERS}", timeout=120)


def ensure_directories() -> None:
    STOCK_DATA_DIR.mkdir(exist_ok=True)



def compute_investment_score(record: Dict[str, Optional[float]]) -> Optional[float]:
    def clamp(val: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, val))

    def norm(val: Optional[float], lo: float, hi: float) -> Optional[float]:
        if val is None:
            return None
        return clamp((val - lo) / (hi - lo) * 100, 0.0, 100.0)

    def norm_inv(val: Optional[float], lo: float, hi: float) -> Optional[float]:
        if val is None:
            return None
        return clamp((hi - val) / (hi - lo) * 100, 0.0, 100.0)

    # Growth (30%)
    rev_score = norm(record.get("Revenue Growth %"), -50.0, 100.0)       # 20%
    # If Finviz had data but every source was clamped as an artifact, score as 0
    # rather than redistributing weight as though the metric were simply missing.
    if rev_score is None and record.get("Revenue Growth Suspect", False):
        rev_score = 0.0
    eps_score = norm(record.get("EPS Growth %"), -50.0, 100.0)           # 10%
    if eps_score is None and record.get("EPS Growth Suspect", False):
        eps_score = 0.0

    # Financial Quality (25%)
    gm_score = norm(record.get("Gross Margin %"), 0.0, 100.0)            # 10%
    npm_score = norm(record.get("Net Profit Margin %"), -20.0, 40.0)     # 10%
    de_score = norm_inv(record.get("Debt/Equity"), 0.0, 3.0)             # 5%

    # Valuation (20% nominal)
    # PEG: Finviz native value; lower is better; 0=undervalued, 3=overpriced
    peg = record.get("PEG")
    peg_score: Optional[float] = norm_inv(peg, 0.0, 3.0) if (peg is not None and peg > 0) else None  # 5%
    # PSG = P/S / Revenue Growth % (computed in fetch_records); lower is better
    psg_score = norm_inv(record.get("PSG"), 0.0, 3.0)                    # 5%
    upside_score = norm(record.get("Upside %"), -30.0, 100.0)            # 10%

    # Entry Timing (15% nominal)
    # Buy Zone: 80% of 52-Week High; score 100 at/below buy zone, 0 at 125% of buy zone
    current_price = record.get("Current Price")
    fifty_two_wk_high = record.get("52-Week High")
    buy_zone_score: Optional[float] = None
    if current_price is not None and current_price > 0 and fifty_two_wk_high is not None and fifty_two_wk_high > 0:
        buy_zone = fifty_two_wk_high * 0.80
        upper_bound = buy_zone * 1.25
        if current_price <= buy_zone:
            buy_zone_score = 100.0
        elif current_price >= upper_bound:
            buy_zone_score = 0.0
        else:
            buy_zone_score = clamp((upper_bound - current_price) / (upper_bound - buy_zone) * 100.0, 0.0, 100.0)
    # Analyst Recom: 1.0=Strong Buy (best), 5.0=Strong Sell (worst)
    recom = record.get("Analyst Recom")
    recom_score: Optional[float] = clamp((5.0 - recom) / 4.0 * 100.0, 0.0, 100.0) if recom is not None else None  # 5%
    # Short Float %: higher = more bearish pressure; lower is better; clamp at 30%
    short_float_score = norm_inv(record.get("Short Float %"), 0.0, 30.0) # 5%

    # Nominal weights sum to 0.90 (RSI removed); total_weight normalization redistributes
    # proportionally so missing metrics never silently deflate the score.
    weighted = [
        (rev_score, 0.20),           # Growth
        (eps_score, 0.10),
        (gm_score, 0.10),            # Financial Quality
        (npm_score, 0.10),
        (de_score, 0.05),
        (peg_score, 0.05),           # Valuation
        (psg_score, 0.05),
        (upside_score, 0.10),
        (buy_zone_score, 0.05),      # Entry Timing
        (recom_score, 0.05),
        (short_float_score, 0.05),
    ]

    total_weight = sum(w for s, w in weighted if s is not None)
    if total_weight == 0:
        return None
    weighted_sum = sum(s * w for s, w in weighted if s is not None)
    return round(weighted_sum / total_weight, 1)


DISCOVERY_SCORE_THRESHOLD = 70.0
UNIVERSE_TOP_PER_SECTOR = 10

# Finviz screener pre-filters aligned with scoring criteria (highest-weight metrics first):
# revenue growth QoQ > 10%, positive EPS growth, positive net margin, Buy or Strong Buy rating
FINVIZ_UNIVERSE_FILTERS = "fa_epsqoq_pos,fa_netmargin_pos,an_recomendation_buybetter"


def fetch_records(
    tickers: List[str],
    metrics_cache: Dict[str, Dict[str, Optional[float]]],
    quiet: bool = False,
) -> List[Dict[str, Optional[float]]]:
    records: List[Dict[str, Optional[float]]] = []
    for ticker in tickers:
        metrics: Dict[str, Optional[float]] = metrics_cache.get(ticker, {})

        current_price = metrics.get("Current Price")
        eps = metrics.get("EPS")
        bvps = metrics.get("Book Value Per Share")
        finviz_target = metrics.get("Finviz Target Price")

        target_price = finviz_target
        if target_price is None and not quiet:
            print(f"[WARN] Target Price unavailable for {ticker} — no analyst consensus from Finviz")

        if target_price is not None and current_price not in (None, 0):
            upside_pct: Optional[float] = ((target_price - current_price) / current_price) * 100
        else:
            upside_pct = None

        ps_ratio = metrics.get("P/S Ratio")
        rev_growth = metrics.get("Revenue Growth %")
        psg: Optional[float] = None
        if ps_ratio is not None and ps_ratio > 0 and rev_growth is not None and rev_growth > 0:
            psg = ps_ratio / rev_growth

        record: Dict[str, object] = {
            "Ticker": ticker,
            "Sector": metrics.get("Sector", ""),
            "Current Price": current_price,
            "52-Week High": metrics.get("52-Week High"),
            "RSI": metrics.get("RSI"),
            "P/E Ratio": metrics.get("P/E Ratio"),
            "PEG": metrics.get("PEG"),
            "P/S Ratio": ps_ratio,
            "PSG": psg,
            "Market Cap": metrics.get("Market Cap"),
            "Target Price": target_price,
            "Upside %": upside_pct,
            "Revenue Growth %": metrics.get("Revenue Growth %"),
            "Revenue Growth Suspect": metrics.get("Revenue Growth Suspect", False),
            "EPS Growth %": metrics.get("EPS Growth %"),
            "EPS Growth Suspect": metrics.get("EPS Growth Suspect", False),
            "Gross Margin %": metrics.get("Gross Margin %"),
            "Net Profit Margin %": metrics.get("Net Profit Margin %"),
            "Debt/Equity": metrics.get("Debt/Equity"),
            "Beta": metrics.get("Beta"),
            "Insider Ownership %": metrics.get("Insider Ownership %"),
            "Institutional Ownership %": metrics.get("Institutional Ownership %"),
            "Analyst Recom": metrics.get("Analyst Recom"),
            "Short Interest": metrics.get("Short Interest"),
            "Short Float %": metrics.get("Short Float %"),
        }
        record["Investment Score"] = compute_investment_score(record)
        records.append(record)

    return records


def _cell_value(value: object) -> object:
    """Round floats to 2 decimal places for clean cell display."""
    if isinstance(value, float):
        return round(value, 2)
    return value


# Columns checked when deciding if a ticker is speculative.
# Exclude non-data columns: Ticker (identifier), Sector (always a string).
_NULL_CHECK_COLUMNS = [c for c in COLUMNS if c not in ("Ticker", "Sector")]
_SPECULATIVE_NULL_THRESHOLD = 3  # more than this many nulls → Speculative


def _null_count(record: Dict) -> int:
    return sum(1 for col in _NULL_CHECK_COLUMNS if record.get(col) is None)


def _split_records(records: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Return (core_rows, speculative_rows) with Tab injected into each row."""
    core: List[Dict] = []
    speculative: List[Dict] = []
    for record in records:
        row = dict(record)
        if _null_count(row) > _SPECULATIVE_NULL_THRESHOLD:
            row["Tab"] = "Speculative Investments"
            speculative.append(row)
        else:
            row["Tab"] = "Investment Master"
            core.append(row)
    return core, speculative


CONSOLIDATED_CSV_FILENAME = "consolidated"


def _build_consolidated_csv(core: List[Dict], speculative: List[Dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Tab"] + COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in core + speculative:
        writer.writerow({col: _cell_value(row.get(col)) for col in ["Tab"] + COLUMNS})
    return buf.getvalue()


def _save_consolidated_csv(csv_content: str, date_stamp: str) -> Path:
    path = STOCK_DATA_DIR / f"{CONSOLIDATED_CSV_FILENAME}_{date_stamp}.csv"
    path.write_text(csv_content, encoding="utf-8")
    print(f"[INFO] Consolidated CSV saved: {path}")
    return path


def run(auth_token: Optional[str]) -> Dict[str, object]:
    ensure_directories()

    EST = timezone(timedelta(hours=-5))
    date_stamp = datetime.now(tz=EST).strftime(DATE_FORMAT)

    metrics_cache: Dict[str, Dict[str, Optional[float]]] = {}
    if auth_token:
        client = FinvizClient(auth_token)
        print("[INFO] Running Finviz universe scan...")
        metrics_cache = client.get_universe_metrics()
        print(f"[INFO] Finviz universe returned {len(metrics_cache)} tickers")

    all_tickers = list(metrics_cache.keys())
    records = fetch_records(all_tickers, metrics_cache, quiet=True)

    # Group eligible tickers by sector, take top 10 per sector by investment score
    sector_buckets: Dict[str, list] = {}
    for r in records:
        price = r.get("Current Price")
        if (
            (r.get("Investment Score") or 0) >= DISCOVERY_SCORE_THRESHOLD
            and (r.get("Upside %") or 0) > 10
            and (price is None or price <= 300.0)
        ):
            sector = str(r.get("Sector") or "Unknown")
            sector_buckets.setdefault(sector, []).append(r)

    selected = []
    for sector, bucket in sector_buckets.items():
        top = sorted(bucket, key=lambda r: r.get("Investment Score") or 0, reverse=True)[:UNIVERSE_TOP_PER_SECTOR]
        selected.extend(top)

    # Sort all selected tickers by investment score descending
    qualified = sorted(selected, key=lambda r: r.get("Investment Score") or 0, reverse=True)

    print(f"[INFO] {len(qualified)} tickers selected (top {UNIVERSE_TOP_PER_SECTOR} per sector, score >= {DISCOVERY_SCORE_THRESHOLD}, upside > 10%):")
    for i, r in enumerate(qualified, start=1):
        print(f"  #{i:<4} {r['Ticker']:<8} [{r.get('Sector', '')}] Score: {r.get('Investment Score')}")

    core, speculative = _split_records(qualified)

    csv_content = _build_consolidated_csv(core, speculative)
    csv_path = _save_consolidated_csv(csv_content, date_stamp)

    return {
        "date": date_stamp,
        "consolidated_csv": str(csv_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the investment engine weekly refresh")
    parser.add_argument("--auth-token", default=None, help="Override Finviz auth token")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    auth_token = args.auth_token or os.getenv("FINVIZ")
    if not auth_token:
        print("[WARN] FINVIZ not set — all Finviz fields will be empty")
    outputs = run(auth_token=auth_token)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
