from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

FINVIZ_BASE_URL = "https://elite.finviz.com/export"
# Column codes for the Finviz export endpoint (v=150)
# 1=Ticker, 65=Price, 59=RSI(14), 7=P/E, 9=PEG, 10=P/S, 6=Market Cap, 69=Target Price,
# 16=EPS(ttm), 22=EPS Growth Q/Q, 19=EPS Growth Past 5Y, 73=Book/sh,
# 23=Sales Growth Q/Q, 21=Sales Growth Past 5Y, 12=P/Cash, 38=Total Debt/Equity,
# 41=Profit Margin, 39=Gross Margin, 48=Beta, 26=Insider Ownership,
# 28=Institutional Ownership, 62=Analyst Recom, 57=52W High,
# 30=Short Float, 84=Short Interest
FINVIZ_COLUMNS = "1,65,59,7,9,10,6,69,16,22,19,73,23,21,12,38,41,39,48,26,28,62,57,30,84"

REPO_ROOT = Path(__file__).resolve().parents[1]
STOCK_DATA_DIR = REPO_ROOT / "stock-data"
TICKER_REVIEW_DIR = REPO_ROOT / "ticker-review"
MASTER_JSON_PATH = REPO_ROOT / "Ticker-Master.json"
DATE_FORMAT = "%m%d%Y"

COLUMNS = [
    "Ticker",
    "Current Price",
    "52-Week High",
    "RSI",
    "P/E Ratio",
    "PEG",
    "P/S Ratio",
    "PSG",
    "Market Cap",
    "Target Price",
    "Graham Undervalued",
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

    def _parse_row(self, row: dict) -> Dict[str, Optional[float]]:
        p = self._parse_float

        price = p(row.get("Price"))
        market_cap_raw = p(row.get("Market Cap"))
        # Finviz exports Market Cap in millions — convert to full dollars, store as int
        market_cap = int(market_cap_raw * 1_000_000) if market_cap_raw is not None else None

        rev_growth_qq = p(row.get("Sales Growth Quarter Over Quarter"))
        rev_growth_5y = p(row.get("Sales Growth Past 5 Years"))
        rev_growth = rev_growth_qq if rev_growth_qq is not None else rev_growth_5y

        eps_growth_qq = p(row.get("EPS Growth Quarter Over Quarter"))
        eps_growth_5y = p(row.get("EPS Growth Past 5 Years"))
        eps_growth = eps_growth_qq if eps_growth_qq is not None else eps_growth_5y
        
        
        # Finviz "52W High" is % below the 52-week high (negative number).
        # Convert to the actual dollar price: price / (1 + pct/100).
        pct_from_high = p(row.get("52W High"))
        if price is not None and price > 0 and pct_from_high is not None:
            fifty_two_wk_high: Optional[float] = price / (1 + pct_from_high / 100)
        else:
            fifty_two_wk_high = None

        return {
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
            "EPS Growth %": eps_growth,
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
    TICKER_REVIEW_DIR.mkdir(exist_ok=True)


def normalize_ticker(value: object) -> str:
    return str(value).strip().upper()


def unique(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        ticker = normalize_ticker(value)
        if ticker and ticker not in seen:
            seen.add(ticker)
            ordered.append(ticker)
    return ordered


def load_master_config() -> List[str]:
    if not MASTER_JSON_PATH.exists():
        return []
    with MASTER_JSON_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return unique(t for t in data if isinstance(t, str))



def _graham_number(eps: Optional[float], bvps: Optional[float]) -> Optional[float]:
    if eps is None or bvps is None or eps <= 0 or bvps <= 0:
        return None
    return math.sqrt(22.5 * eps * bvps)


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
    eps_score = norm(record.get("EPS Growth %"), -50.0, 100.0)           # 10%

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
UNIVERSE_TOP_N = 100

# Finviz screener pre-filters aligned with scoring criteria (highest-weight metrics first):
# revenue growth QoQ > 10%, positive EPS growth, positive net margin, Buy or Strong Buy rating
FINVIZ_UNIVERSE_FILTERS = "fa_salesqoq_o10,fa_epsqoq_pos,fa_netmargin_pos,an_recomendation_buybetter"


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

        graham = _graham_number(eps, bvps)
        if graham is None:
            graham_undervalued: Optional[bool] = None
        else:
            graham_undervalued = current_price is not None and current_price < graham

        ps_ratio = metrics.get("P/S Ratio")
        rev_growth = metrics.get("Revenue Growth %")
        psg: Optional[float] = None
        if ps_ratio is not None and ps_ratio > 0 and rev_growth is not None and rev_growth > 0:
            psg = ps_ratio / rev_growth

        record: Dict[str, object] = {
            "Ticker": ticker,
            "Current Price": current_price,
            "52-Week High": metrics.get("52-Week High"),
            "RSI": metrics.get("RSI"),
            "P/E Ratio": metrics.get("P/E Ratio"),
            "PEG": metrics.get("PEG"),
            "P/S Ratio": ps_ratio,
            "PSG": psg,
            "Market Cap": metrics.get("Market Cap"),
            "Target Price": target_price,
            "Graham Undervalued": graham_undervalued,
            "Upside %": upside_pct,
            "Revenue Growth %": metrics.get("Revenue Growth %"),
            "EPS Growth %": metrics.get("EPS Growth %"),
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


MASTER_COLUMNS = COLUMNS


def _cell_value(value: object) -> object:
    """Round floats to 2 decimal places for clean cell display."""
    if isinstance(value, float):
        return round(value, 2)
    return value


# Columns checked when deciding if a ticker is speculative (all data columns except Ticker)
_NULL_CHECK_COLUMNS = [c for c in COLUMNS if c != "Ticker"]
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



# ── Robinhood watchlist IDs (created in Claude.ai Investment Engine session) ──
ROBINHOOD_WATCHLISTS = [
    {
        "name": "High Conviction",
        "label": "WL1 — High Conviction 🟢",
        "list_id": "915585b4-44b7-4a02-944a-02755d2389a7",
        "checks": [
            ("Investment Score", ">=", 70),
            ("Revenue Growth %", ">=", 20),
            ("EPS Growth %", ">=", 20),
            ("Net Profit Margin %", ">=", 10),
            ("Debt/Equity", "<=", 1.0),
            ("Upside %", ">=", 20),
            ("Analyst Recom", "<=", 2.0),
        ],
    },
    {
        "name": "Pullback Watch",
        "label": "WL2 — Pullback Watch 🔵",
        "list_id": "cde9b1bd-a043-450b-b8b5-e4ed0c74d61b",
        "checks": [
            ("Investment Score", ">=", 60),
            ("Revenue Growth %", ">=", 15),
            ("EPS Growth %", ">=", 10),
            ("Net Profit Margin %", ">=", 5),
            ("Debt/Equity", "<=", 1.5),
            ("Upside %", ">=", 20),
            ("Analyst Recom", "<=", 2.5),
        ],
    },
    {
        "name": "Deep Value",
        "label": "WL3 — Deep Value 🟡",
        "list_id": "9de9edca-b052-415b-b933-cf65746eb1e8",
        "checks": [
            ("Investment Score", ">=", 50),
            ("Revenue Growth %", ">=", 10),
            ("EPS Growth %", ">=", 0),
            ("Net Profit Margin %", ">", 0),
            ("Debt/Equity", "<=", 1.0),
            ("Upside %", ">=", 15),
            ("Analyst Recom", "<=", 2.5),
        ],
    },
    {
        "name": "Pipeline",
        "label": "WL4 — Pipeline ⚪",
        "list_id": "eb977178-35f0-43c6-b6ec-9e9f4ee2cb4c",
        "checks": [
            ("Investment Score", "range", 50, 60),
            ("Revenue Growth %", ">=", 15),
            ("EPS Growth %", ">=", 10),
            ("Net Profit Margin %", ">=", 5),
            ("Debt/Equity", "<=", 1.5),
            # RSI: any — no threshold check
            ("Upside %", ">=", 15),
            ("Analyst Recom", "<=", 2.5),
        ],
    },
]

WATCHLIST_FILENAME = "watchlist"
CONSOLIDATED_CSV_FILENAME = "consolidated"


def _passes_check(value: Optional[float], op: str, *args: float) -> bool:
    if value is None:
        return False
    if op == ">=":
        return value >= args[0]
    if op == ">":
        return value > args[0]
    if op == "<=":
        return value <= args[0]
    if op == "<":
        return value < args[0]
    if op == "range":
        return args[0] <= value <= args[1]
    return False


def _as_float(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    try:
        return float(str(value).strip().rstrip("%").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def classify_watchlists(core: List[Dict], speculative: List[Dict]) -> Dict[str, object]:
    """
    Apply highest-tier-wins logic across all rows.
    Returns a summary dict with per-watchlist ticker lists and a count breakdown.
    """
    placement: Dict[str, List[Dict]] = {wl["name"]: [] for wl in ROBINHOOD_WATCHLISTS}
    unqualified: List[str] = []

    for row in core + speculative:
        placed = False
        for wl in ROBINHOOD_WATCHLISTS:
            qualifies = all(
                _passes_check(_as_float(row.get(col)), op, *args)
                for col, op, *args in wl["checks"]
            )
            if qualifies:
                placement[wl["name"]].append({
                    "ticker": row.get("Ticker"),
                    "investment_score": _cell_value(row.get("Investment Score")),
                    "tab": row.get("Tab"),
                    "list_id": wl["list_id"],
                    "label": wl["label"],
                })
                placed = True
                break
        if not placed:
            unqualified.append(row.get("Ticker", ""))

    counts = {wl["name"]: len(placement[wl["name"]]) for wl in ROBINHOOD_WATCHLISTS}
    print(f"[INFO] Watchlist classification — " + ", ".join(f"{k}: {v}" for k, v in counts.items()))
    print(f"[INFO] Unqualified tickers: {len(unqualified)}")

    return {
        "watchlists": placement,
        "counts": counts,
        "unqualified_count": len(unqualified),
    }


def _save_watchlist_classification(classification: Dict, date_stamp: str) -> Path:
    path = TICKER_REVIEW_DIR / f"{WATCHLIST_FILENAME}_{date_stamp}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(classification, fh, indent=2)
        fh.write("\n")
    print(f"[INFO] Watchlist classification saved: {path}")
    return path


def _build_consolidated_csv(core: List[Dict], speculative: List[Dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Tab"] + MASTER_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in core + speculative:
        writer.writerow({col: _cell_value(row.get(col)) for col in ["Tab"] + MASTER_COLUMNS})
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

    qualified = sorted(
        [r for r in records if (r.get("Investment Score") or 0) >= DISCOVERY_SCORE_THRESHOLD],
        key=lambda r: r.get("Investment Score") or 0,
        reverse=True,
    )[:UNIVERSE_TOP_N]
    print(f"[INFO] {len(qualified)} tickers with Investment Score >= {DISCOVERY_SCORE_THRESHOLD} (top {UNIVERSE_TOP_N}):")
    for r in qualified:
        print(f"  {r['Ticker']:<8} Score: {r.get('Investment Score')}")

    core, speculative = _split_records(qualified)

    csv_content = _build_consolidated_csv(core, speculative)
    csv_path = _save_consolidated_csv(csv_content, date_stamp)

    classification = classify_watchlists(core, speculative)
    watchlist_path = _save_watchlist_classification(classification, date_stamp)

    return {
        "date": date_stamp,
        "consolidated_csv": str(csv_path),
        "watchlist_classification": str(watchlist_path),
        "watchlist_counts": classification["counts"],
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
