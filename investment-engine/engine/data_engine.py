from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from openpyxl import Workbook

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
REPO_ROOT = Path(__file__).resolve().parents[1]
SECTOR_DIR = REPO_ROOT / "sector"
MASTER_JSON_PATH = REPO_ROOT / "Ticker-Master.json"
DAILY_WORKBOOK_PREFIX = "investment_data"
DAILY_REVIEW_PREFIX = "ticker_reviews"
DATE_FORMAT = "%m%d%Y"
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
    "Upside %",
    "Revenue Growth %",
    "EPS Growth %",
    "Backlog Growth %",
    "Gross Margin %",
    "Net Cash Ratio",
]


@dataclass(frozen=True)
class TickerContext:
    sector: str
    pillar: str
    tickers: List[str]


class FMPClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self._ratios_bulk_cache: Optional[Dict[str, dict]] = None

    def _get(self, endpoint: str, symbol: str, symbol_param: str = "symbol") -> Optional[dict]:
        params = {symbol_param: symbol, "apikey": self.api_key}
        response = self.session.get(f"{FMP_BASE_URL}/{endpoint}", params=params, timeout=25)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return payload[0]
        if isinstance(payload, dict):
            return payload
        return None

    def _get_rsi(self, symbol: str) -> Optional[float]:
        response = self.session.get(
            f"{FMP_BASE_URL}/technical-indicators/rsi",
            params={
                "symbol": symbol,
                "periodLength": 10,
                "timeframe": "1day",
                "apikey": self.api_key,
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return self._to_float(payload[0].get("rsi"))
        return None

    def _to_float(self, value: object) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_ratios_ttm_bulk(self) -> Dict[str, dict]:
        if self._ratios_bulk_cache is not None:
            return self._ratios_bulk_cache

        response = self.session.get(
            f"{FMP_BASE_URL}/ratios-ttm-bulk",
            params={"apikey": self.api_key},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        cache: Dict[str, dict] = {}
        if isinstance(payload, list):
            for row in payload:
                if not isinstance(row, dict):
                    continue
                symbol = str(row.get("symbol", "")).strip().upper()
                if symbol:
                    cache[symbol] = row

        self._ratios_bulk_cache = cache
        return cache

    def get_metrics(self, ticker: str) -> Dict[str, Optional[float]]:
        # Use FMP batch-quote endpoint for current price/market-cap parity with API docs.
        quote = self._get("batch-quote", ticker, symbol_param="symbols") or {}
        rsi = self._get_rsi(ticker)
        market_cap_data = self._get("market-capitalization-batch", ticker, symbol_param="symbols") or {}
        ratios = self._get_ratios_ttm_bulk().get(ticker.upper(), {})
        growth = self._get("financial-growth", ticker) or {}
        income = self._get("income-statement", ticker) or {}
        balance = self._get("balance-sheet-statement", ticker) or {}
        target = self._get("price-target-consensus", ticker) or {}

        market_cap = self._to_float(market_cap_data.get("marketCap")) or self._to_float(quote.get("marketCap"))
        cash_and_cash_equivalents = self._to_float(balance.get("cashAndCashEquivalents"))
        total_debt = self._to_float(balance.get("totalDebt"))
        net_debt = self._to_float(balance.get("netDebt"))
        if net_debt is None and total_debt is not None and cash_and_cash_equivalents is not None:
            net_debt = total_debt - cash_and_cash_equivalents
        revenue_growth = self._to_float(growth.get("revenueGrowth"))
        eps_growth = self._to_float(growth.get("epsgrowth"))
        if eps_growth is None:
            eps_growth = self._to_float(growth.get("epsdilutedGrowth"))
        gross_margin = self._to_float(ratios.get("grossProfitMarginTTM"))
        if gross_margin is None:
            gross_margin = self._to_float(income.get("grossProfitRatio"))
        analyst_target = target.get("targetConsensus") or target.get("priceTarget")

        return {
            "Current Price": quote.get("price"),
            "RSI": rsi,
            "P/E Ratio": self._to_float(ratios.get("priceToEarningsRatioTTM")),
            "P/S Ratio": self._to_float(ratios.get("priceToSalesRatioTTM")) or self._to_float(ratios.get("priceToSalesRatio")),
            "Market Cap": market_cap,
            "Target Price": analyst_target,
            "Revenue Growth %": revenue_growth * 100 if revenue_growth is not None else None,
            "EPS Growth %": eps_growth * 100 if eps_growth is not None else None,
            "Gross Margin %": gross_margin * 100 if gross_margin is not None else None,
            "Net Cash Ratio": (
                (-net_debt) / market_cap
                if net_debt is not None and market_cap
                else None
            ),
        }


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


def fetch_records_for_pillar(
    context: TickerContext,
    client: Optional[FMPClient],
) -> List[Dict[str, Optional[float]]]:
    records: List[Dict[str, Optional[float]]] = []
    for ticker in context.tickers:
        metrics: Dict[str, Optional[float]] = {}
        if client is not None:
            try:
                metrics = client.get_metrics(ticker)
                time.sleep(0.15)
            except Exception:
                metrics = {}

        current_price = metrics.get("Current Price")
        target_price = metrics.get("Target Price")

        record: Dict[str, Optional[float]] = {
            "Ticker": ticker,
            "Current Price": current_price,
            "P/E Ratio": metrics.get("P/E Ratio"),
            "P/S Ratio": metrics.get("P/S Ratio"),
            "Market Cap": metrics.get("Market Cap"),
            "Buy Zone": current_price * 0.8 if current_price is not None else None,
            "Target Price": target_price,
            "Upside %": (
                (target_price - current_price) / current_price
                if target_price is not None and current_price not in [None, 0]
                else None
            ),
            "Revenue Growth %": metrics.get("Revenue Growth %"),
            "EPS Growth %": metrics.get("EPS Growth %"),
            "Backlog Growth %": None,
            "Gross Margin %": metrics.get("Gross Margin %"),
            "Net Cash Ratio": metrics.get("Net Cash Ratio"),
        }
        records.append(record)

    return records


def write_records_to_sheet(workbook: Workbook, sheet_name: str, records: List[Dict[str, Optional[float]]]) -> None:
    if sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
    else:
        sheet = workbook.create_sheet(title=sheet_name)

    for column_index, header in enumerate(COLUMNS, start=1):
        sheet.cell(row=1, column=column_index, value=header)

    for row_index, record in enumerate(records, start=2):
        for column_index, header in enumerate(COLUMNS, start=1):
            sheet.cell(row=row_index, column=column_index, value=record.get(header))


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
    top_candidates = data_frame.head(15)[
        ["Sector", "Pillar", "Ticker", "Upside %", "Revenue Growth %", "EPS Growth %", "Gross Margin %", "Net Cash Ratio"]
    ].to_dict("records")

    return {
        "total_tickers": int(len(data_frame)),
        "pillar_counts": pillar_counts,
        "top_candidates": top_candidates,
        "all_records": all_records,
    }


def build_fallback_review(summary: Dict[str, object], date_stamp: str, sector: str) -> str:
    lines = [
        f"Ticker review for {sector} - {date_stamp}",
        "",
        f"Total tickers reviewed: {summary.get('total_tickers', 0)}",
        "",
        "Top candidates by analyst upside:",
    ]

    for candidate in summary.get("top_candidates", [])[:10]:
        lines.append(
            "- {ticker} | {pillar} | upside {upside} | rev {rev} | eps {eps} | gm {gm} | cash {cash}".format(
                ticker=candidate.get("Ticker", "n/a"),
                pillar=candidate.get("Pillar", "n/a"),
                upside=format_metric(candidate.get("Upside %"), "%"),
                rev=format_metric(candidate.get("Revenue Growth %"), "%"),
                eps=format_metric(candidate.get("EPS Growth %"), "%"),
                gm=format_metric(candidate.get("Gross Margin %"), "%"),
                cash=format_metric(candidate.get("Net Cash Ratio")),
            )
        )

    lines.extend(
        [
            "",
            "Note: Set OPENAI_API_KEY to generate a full ChatGPT review.",
        ]
    )
    return "\n".join(lines)


def build_chatgpt_prompt(summary: Dict[str, object], date_stamp: str, sector: str) -> str:
    return (
        "You are reviewing a daily investment research export. "
        "Return a concise text summary with: 1) strongest current names, 2) weaker names to avoid, "
        "3) 10-20 additional tickers to research, grouped by pillar, with one-line reasons. "
        "Do not mention that you are an AI model. Focus on public companies only. "
        f"Sector: {sector}. Data date: {date_stamp}. "
        f"Structured data: {json.dumps(summary.get('all_records', []), default=str)}"
    )


def generate_openai_review(summary: Dict[str, object], date_stamp: str, sector: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import importlib

        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI")
    except Exception:
        return None

    client = OpenAI(api_key=api_key)
    prompt = build_chatgpt_prompt(summary, date_stamp, sector)
    response = client.chat.completions.create(
        model=DEFAULT_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a buy-side investment research assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def run(api_key: Optional[str]) -> Dict[str, object]:
    ensure_directories()
    master_config = load_master_config()
    sync_master_files(master_config)
    ensure_sector_directories(master_config.keys())

    client = FMPClient(api_key) if api_key else None
    date_stamp = datetime.now().strftime(DATE_FORMAT)

    contexts_by_sector: Dict[str, List[TickerContext]] = {}
    for context in all_pillar_contexts(master_config):
        contexts_by_sector.setdefault(context.sector, []).append(context)

    outputs: Dict[str, object] = {"date": date_stamp, "sectors": {}}

    for sector, sector_contexts in contexts_by_sector.items():
        workbook = Workbook()
        workbook.remove(workbook.active)

        mapping_sheet = workbook.create_sheet(title="Pillar Map", index=0)
        mapping_sheet.cell(row=1, column=1, value="Sector")
        mapping_sheet.cell(row=1, column=2, value="Pillar")
        mapping_sheet.cell(row=1, column=3, value="Sheet Name")

        pillar_row = 2
        records_by_context: List[Tuple[TickerContext, List[Dict[str, Optional[float]]]]] = []

        for context in sector_contexts:
            sheet_name = sheet_name_for_pillar(context.pillar)
            mapping_sheet.cell(row=pillar_row, column=1, value=context.sector)
            mapping_sheet.cell(row=pillar_row, column=2, value=context.pillar)
            mapping_sheet.cell(row=pillar_row, column=3, value=sheet_name)
            pillar_row += 1

            records = fetch_records_for_pillar(context, client)
            write_records_to_sheet(workbook, sheet_name, records)
            records_by_context.append((context, records))

        daily_workbook_path = sector_stock_data_dir(sector) / f"{DAILY_WORKBOOK_PREFIX}_{date_stamp}.xlsx"
        workbook.save(daily_workbook_path)
        workbook.close()

        summary = build_summary(records_by_context)
        review_text = generate_openai_review(summary, date_stamp, sector)
        if not review_text:
            review_text = build_fallback_review(summary, date_stamp, sector)

        review_path = sector_ticker_review_dir(sector) / f"{DAILY_REVIEW_PREFIX}_{date_stamp}.txt"
        write_text(review_path, review_text)

        outputs["sectors"][sector] = {
            "daily_workbook": str(daily_workbook_path),
            "review_text": str(review_path),
        }

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the investment engine daily refresh")
    parser.add_argument("--api-key", default=None, help="Override FMP API key")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = args.api_key or os.getenv("FMP") or os.getenv("FMP_API_KEY")
    outputs = run(api_key=api_key)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
