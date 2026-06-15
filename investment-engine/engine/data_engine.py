from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from openpyxl import Workbook

FINVIZ_BASE_URL = "https://elite.finviz.com/export"
# Column codes for the Finviz export endpoint (v=151)
# 1=Ticker, 65=Price, 59=RSI(14), 7=P/E, 10=P/S, 6=Market Cap, 69=Target Price,
# 16=EPS(ttm), 22=EPS Growth Q/Q, 19=EPS Growth Past 5Y, 73=Book/sh,
# 23=Sales Growth Q/Q, 21=Sales Growth Past 5Y, 12=P/Cash, 38=Total Debt/Equity,
# 41=Profit Margin, 39=Gross Margin, 48=Beta, 26=Insider Ownership,
# 28=Institutional Ownership, 62=Analyst Recom
FINVIZ_COLUMNS = "1,65,59,7,10,6,69,16,22,19,73,23,21,12,38,41,39,48,26,28,62"

REPO_ROOT = Path(__file__).resolve().parents[1]
SECTOR_DIR = REPO_ROOT / "sector"
MASTER_JSON_PATH = REPO_ROOT / "Ticker-Master.json"
DAILY_WORKBOOK_PREFIX = "investment_data"
DATE_FORMAT = "%m%d%Y"
TICKER_REVIEW_PREFIX = "ticker_review"

KNOWN_SHEET_NAMES = {
    "AI Power Generation": "AI Power Gen",
    "AI Networking": "AI Networking",
    "AI Memory and Storage": "AI Memory Storage",
    "AI Land": "AI Land",
    "AI Heating and Cooling": "AI Heat Cooling",
    "AI Grid and Power Transmission": "AI Grid Transmission",
    "AI Electrical Infrastructure": "AI Electrical Infra",
    "AI Construction": "AI Construction",
    "AI Cybersecurity": "AI Cybersecurity",
    "AI Semiconductor Chip Manufacturing": "AI Semi Mfg",
    "AI Server and Rack Systems": "AI Server Rack",
    "AI Software and Platforms": "AI Software Platform",
    "AI Backup Power": "AI Backup Power",
    "AI Cloud": "AI Cloud",
    "AI Fire Detection": "AI Fire Detection",
    "AI Water": "AI Water",
    "AI Insurance and Risk": "AI Insurance Risk",
    "AI Security": "AI Security",
    "AI Compute Chips": "AI Compute Chips",
}

COLUMNS = [
    "Ticker",
    "Current Price",
    "RSI",
    "P/E Ratio",
    "P/S Ratio",
    "Market Cap",
    "Buy Zone",
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
    "Investment Score",
]


@dataclass(frozen=True)
class TickerContext:
    sector: str
    pillar: str
    tickers: List[str]


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

        return {
            "Current Price": price,
            "RSI": p(row.get("Relative Strength Index (14)")),
            "P/E Ratio": p(row.get("P/E")),
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
        }

    def get_all_metrics(self, tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
        """Single bulk export call — returns a dict keyed by ticker symbol."""
        ticker_param = ",".join(tickers)
        url = (
            f"{FINVIZ_BASE_URL}?v=151"
            f"&t={ticker_param}"
            f"&c={FINVIZ_COLUMNS}"
            f"&auth={self.auth_token}"
        )
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            print(f"[WARN] Finviz bulk request failed: {exc}")
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

        result: Dict[str, Dict[str, Optional[float]]] = {}
        for row in rows:
            ticker = row.get("Ticker", "").strip().upper()
            if ticker:
                result[ticker] = self._parse_row(row)

        missing = [t for t in tickers if t not in result]
        if missing:
            print(f"[WARN] Finviz returned no data for: {', '.join(missing)}")

        return result


def ensure_directories() -> None:
    SECTOR_DIR.mkdir(exist_ok=True)


def sector_root(sector: str) -> Path:
    return SECTOR_DIR / sector


def sector_stock_data_dir(sector: str) -> Path:
    return sector_root(sector) / "stock-data"


def sector_ticker_review_dir(sector: str) -> Path:
    return sector_root(sector) / "ticker-review"


def sector_pillar_tickers_path(sector: str) -> Path:
    return sector_root(sector) / "pillar_tickers.json"


def ensure_sector_directories(sectors: Iterable[str]) -> None:
    for sector in sectors:
        sector_stock_data_dir(sector).mkdir(parents=True, exist_ok=True)
        sector_ticker_review_dir(sector).mkdir(parents=True, exist_ok=True)


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


def load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def load_master_config() -> Dict[str, Dict[str, List[str]]]:
    payload = load_json_file(MASTER_JSON_PATH)
    if payload:
        return {
            sector: {
                pillar: unique(tickers)
                for pillar, tickers in sector_payload.items()
                if isinstance(tickers, list)
            }
            for sector, sector_payload in payload.items()
            if isinstance(sector_payload, dict)
        }

    fallback: Dict[str, Dict[str, List[str]]] = {}
    if SECTOR_DIR.exists():
        for child in SECTOR_DIR.iterdir():
            if not child.is_dir():
                continue
            sector_payload = load_json_file(child / "pillar_tickers.json")
            if sector_payload:
                fallback[child.name] = {
                    pillar: unique(tickers)
                    for pillar, tickers in sector_payload.items()
                    if isinstance(tickers, list)
                }
    if fallback:
        return fallback

    return {}


def sync_master_files(master_config: Dict[str, Dict[str, List[str]]]) -> None:
    with MASTER_JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(master_config, handle, indent=2)
        handle.write("\n")

    ensure_sector_directories(master_config.keys())
    for sector, sector_config in master_config.items():
        with sector_pillar_tickers_path(sector).open("w", encoding="utf-8") as handle:
            json.dump(sector_config, handle, indent=2)
            handle.write("\n")


def all_pillar_contexts(master_config: Dict[str, Dict[str, List[str]]]) -> List[TickerContext]:
    contexts: List[TickerContext] = []
    for sector, sector_payload in master_config.items():
        for pillar, tickers in sector_payload.items():
            contexts.append(TickerContext(sector=sector, pillar=pillar, tickers=unique(tickers)))
    return contexts


def sheet_name_for_pillar(pillar: str) -> str:
    if pillar in KNOWN_SHEET_NAMES:
        return KNOWN_SHEET_NAMES[pillar]

    cleaned = "".join(char for char in pillar if char.isalnum() or char in [" ", "&", "-"])
    cleaned = cleaned.replace("&", "And").replace("-", " ")
    parts = [part for part in cleaned.split() if part]
    if not parts:
        return pillar[:31]

    abbreviated = []
    for part in parts:
        abbreviated.append(part[:4].title() if len(part) > 4 else part.title())

    return " ".join(abbreviated)[:31]


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

    # Valuation (25%)
    pe = record.get("P/E Ratio")
    pe_score: Optional[float] = 0.0 if (pe is not None and pe <= 0) else norm_inv(pe, 0.0, 60.0)  # 5%
    ps_score = norm_inv(record.get("P/S Ratio"), 0.0, 30.0)              # 10%
    upside_score = norm(record.get("Upside %"), -30.0, 100.0)            # 10%

    # Entry Timing (20%)
    rsi = record.get("RSI")
    # Score highest at RSI=30 (oversold), linearly to 0 at RSI=80 (overbought)
    rsi_score: Optional[float] = clamp((80.0 - rsi) / 50.0 * 100.0, 0.0, 100.0) if rsi is not None else None  # 10%
    current_price = record.get("Current Price")
    buy_zone = record.get("Buy Zone")
    if current_price is not None and buy_zone is not None and buy_zone > 0:
        # Score 100 at or below buy zone, 0 when 25%+ above it
        ratio = current_price / buy_zone
        bz_score: Optional[float] = clamp((1.25 - ratio) / 0.25 * 100.0, 0.0, 100.0)
    else:
        bz_score = None
    # Analyst Recom: 1.0=Strong Buy (best), 5.0=Strong Sell (worst)
    recom = record.get("Analyst Recom")
    recom_score: Optional[float] = clamp((5.0 - recom) / 4.0 * 100.0, 0.0, 100.0) if recom is not None else None  # 5%

    weighted = [
        (rev_score, 0.20),
        (eps_score, 0.10),
        (gm_score, 0.10),
        (npm_score, 0.10),
        (de_score, 0.05),
        (pe_score, 0.05),
        (ps_score, 0.10),
        (upside_score, 0.10),
        (rsi_score, 0.10),
        (bz_score, 0.05),
        (recom_score, 0.05),
    ]

    total_weight = sum(w for s, w in weighted if s is not None)
    if total_weight == 0:
        return None
    weighted_sum = sum(s * w for s, w in weighted if s is not None)
    return round(weighted_sum / total_weight, 1)


def fetch_records_for_pillar(
    context: TickerContext,
    metrics_cache: Dict[str, Dict[str, Optional[float]]],
) -> List[Dict[str, Optional[float]]]:
    records: List[Dict[str, Optional[float]]] = []
    for ticker in context.tickers:
        metrics: Dict[str, Optional[float]] = metrics_cache.get(ticker, {})

        current_price = metrics.get("Current Price")
        eps = metrics.get("EPS")
        bvps = metrics.get("Book Value Per Share")
        finviz_target = metrics.get("Finviz Target Price")

        target_price = finviz_target
        if target_price is None:
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

        record: Dict[str, object] = {
            "Ticker": ticker,
            "Current Price": current_price,
            "RSI": metrics.get("RSI"),
            "P/E Ratio": metrics.get("P/E Ratio"),
            "P/S Ratio": metrics.get("P/S Ratio"),
            "Market Cap": metrics.get("Market Cap"),
            "Buy Zone": current_price * 0.8 if current_price is not None else None,
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
        }
        record["Investment Score"] = compute_investment_score(record)
        records.append(record)

    return records


MASTER_COLUMNS = ["Pillar"] + COLUMNS


def _cell_value(value: object) -> object:
    """Round floats to 2 decimal places for clean cell display."""
    if isinstance(value, float):
        return round(value, 2)
    return value


# Columns checked when deciding if a ticker is speculative (all data columns except Ticker)
_NULL_CHECK_COLUMNS = [c for c in COLUMNS if c != "Ticker"]
_SPECULATIVE_NULL_THRESHOLD = 2  # more than this many nulls → Speculative


def _null_count(record: Dict) -> int:
    return sum(1 for col in _NULL_CHECK_COLUMNS if record.get(col) is None)


def _split_records(
    records_by_context: List[Tuple[TickerContext, List[Dict[str, Optional[float]]]]],
) -> Tuple[List[Dict], List[Dict]]:
    """Return (core_rows, speculative_rows) with Pillar injected into each row."""
    core: List[Dict] = []
    speculative: List[Dict] = []
    for context, records in records_by_context:
        for record in records:
            row = dict(record)
            row["Pillar"] = context.pillar
            if _null_count(row) > _SPECULATIVE_NULL_THRESHOLD:
                speculative.append(row)
            else:
                core.append(row)
    return core, speculative


def _write_rows_to_sheet(sheet, rows: List[Dict]) -> None:
    for col_idx, header in enumerate(MASTER_COLUMNS, start=1):
        sheet.cell(row=1, column=col_idx, value=header)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, header in enumerate(MASTER_COLUMNS, start=1):
            sheet.cell(row=row_idx, column=col_idx, value=_cell_value(row.get(header)))


def write_master_sheet(
    workbook: Workbook,
    records_by_context: List[Tuple[TickerContext, List[Dict[str, Optional[float]]]]],
) -> None:
    core, speculative = _split_records(records_by_context)

    core.sort(key=lambda r: (r.get("Investment Score") is None, -(r.get("Investment Score") or 0)))

    sheet = workbook.create_sheet(title="Investment Master", index=0)
    _write_rows_to_sheet(sheet, core)

    spec_sheet = workbook.create_sheet(title="Speculative Investments")
    speculative.sort(key=lambda r: (r.get("Investment Score") is None, -(r.get("Investment Score") or 0)))
    _write_rows_to_sheet(spec_sheet, speculative)


def write_records_to_sheet(workbook: Workbook, sheet_name: str, records: List[Dict[str, Optional[float]]]) -> None:
    if sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
    else:
        sheet = workbook.create_sheet(title=sheet_name)

    for column_index, header in enumerate(COLUMNS, start=1):
        sheet.cell(row=1, column=column_index, value=header)

    for row_index, record in enumerate(records, start=2):
        for column_index, header in enumerate(COLUMNS, start=1):
            sheet.cell(row=row_index, column=column_index, value=_cell_value(record.get(header)))


def format_metric(value: Optional[float], suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def build_summary(records_by_context: List[Tuple[TickerContext, List[Dict[str, Optional[float]]]]]) -> Dict[str, object]:
    all_records: List[Dict[str, object]] = []
    pillar_counts: Dict[str, int] = {}

    for context, records in records_by_context:
        pillar_counts[context.pillar] = len(records)
        for record in records:
            row = dict(record)
            row["Sector"] = context.sector
            row["Pillar"] = context.pillar
            all_records.append(row)

    if not all_records:
        return {"total_tickers": 0, "top_candidates": [], "pillar_counts": {}, "all_records": []}

    data_frame = pd.DataFrame(all_records)
    data_frame = data_frame.sort_values(by=["Upside %", "Ticker"], ascending=[False, True], na_position="last")
    top_candidates = data_frame.head(5)[
        ["Sector", "Pillar", "Ticker", "Upside %", "Revenue Growth %", "EPS Growth %", "Gross Margin %"]
    ].to_dict("records")

    return {
        "total_tickers": int(len(data_frame)),
        "pillar_counts": pillar_counts,
        "top_candidates": top_candidates,
        "all_records": all_records,
    }


# Claude ticker review — commented out to avoid API usage costs.
# Uncomment this function and the call site in run() to re-enable.
#
# def generate_claude_ticker_review(summary: Dict[str, object], date_stamp: str, sector: str) -> Optional[str]:
#     ...


def run(auth_token: Optional[str]) -> Dict[str, object]:
    ensure_directories()
    master_config = load_master_config()
    sync_master_files(master_config)
    ensure_sector_directories(master_config.keys())

    date_stamp = datetime.now().strftime(DATE_FORMAT)

    all_contexts = all_pillar_contexts(master_config)

    # Single bulk Finviz call for all tickers across all pillars
    metrics_cache: Dict[str, Dict[str, Optional[float]]] = {}
    if auth_token:
        client = FinvizClient(auth_token)
        all_tickers: List[str] = []
        seen: set = set()
        for ctx in all_contexts:
            for t in ctx.tickers:
                if t not in seen:
                    all_tickers.append(t)
                    seen.add(t)
        print(f"[INFO] Fetching Finviz data for {len(all_tickers)} tickers...")
        metrics_cache = client.get_all_metrics(all_tickers)
        print(f"[INFO] Received data for {len(metrics_cache)} tickers")

    contexts_by_sector: Dict[str, List[TickerContext]] = {}
    for context in all_contexts:
        contexts_by_sector.setdefault(context.sector, []).append(context)

    outputs: Dict[str, object] = {"date": date_stamp, "sectors": {}}

    for sector, sector_contexts in contexts_by_sector.items():
        workbook = Workbook()
        workbook.remove(workbook.active)

        records_by_context: List[Tuple[TickerContext, List[Dict[str, Optional[float]]]]] = []

        for context in sector_contexts:
            records = fetch_records_for_pillar(context, metrics_cache)
            records_by_context.append((context, records))

        write_master_sheet(workbook, records_by_context)

        for context, records in records_by_context:
            sheet_name = sheet_name_for_pillar(context.pillar)
            write_records_to_sheet(workbook, sheet_name, records)

        daily_workbook_path = sector_stock_data_dir(sector) / f"{DAILY_WORKBOOK_PREFIX}_{date_stamp}.xlsx"
        workbook.save(daily_workbook_path)
        workbook.close()

        outputs["sectors"][sector] = {
            "daily_workbook": str(daily_workbook_path),
        }

    return outputs


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
