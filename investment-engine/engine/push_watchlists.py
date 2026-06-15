"""
push_watchlists.py — Interactive Robinhood watchlist population.

Run this inside a Claude Code session (not GitHub Actions) after the weekly
engine run has committed a watchlist_MMDDYYYY.json to the repo.

Usage:
    python investment-engine/engine/push_watchlists.py [--date MMDDYYYY] [--sector SECTOR] [--dry-run]

The script reads the most recent watchlist_*.json for the given sector,
then prints the MCP calls needed to populate each Robinhood watchlist.
Because the Robinhood MCP requires Claude Code's OAuth session, this script
cannot make the API calls itself — it outputs a structured plan that Claude
Code (or you) can execute via the MCP connector.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SECTOR_DIR = REPO_ROOT / "sector"


def find_latest_watchlist_file(sector: str, date_stamp: str | None) -> Path | None:
    ticker_review_dir = SECTOR_DIR / sector / "ticker-review"
    if not ticker_review_dir.exists():
        return None
    if date_stamp:
        candidate = ticker_review_dir / f"watchlist_{date_stamp}.json"
        return candidate if candidate.exists() else None
    files = sorted(ticker_review_dir.glob("watchlist_*.json"), reverse=True)
    return files[0] if files else None


def load_classification(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print Robinhood watchlist population plan")
    parser.add_argument("--date", default=None, help="Date stamp MMDDYYYY (default: latest)")
    parser.add_argument("--sector", default=None, help="Sector name (default: first found)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    # Resolve sector
    if args.sector:
        sector = args.sector
    else:
        sectors = [d.name for d in SECTOR_DIR.iterdir() if d.is_dir()]
        if not sectors:
            print("[ERROR] No sector directories found under investment-engine/sector/")
            sys.exit(1)
        sector = sectors[0]
        print(f"[INFO] No sector specified — using '{sector}'")

    path = find_latest_watchlist_file(sector, args.date)
    if not path:
        print(f"[ERROR] No watchlist classification file found for sector '{sector}'")
        sys.exit(1)

    print(f"[INFO] Reading: {path}")
    classification = load_classification(path)
    watchlists = classification.get("watchlists", {})
    counts = classification.get("counts", {})

    print("\n── Watchlist Population Plan ──────────────────────────────────────")
    total = 0
    for wl_name, entries in watchlists.items():
        if not entries:
            print(f"\n{wl_name}: 0 tickers — nothing to add")
            continue
        list_id = entries[0]["list_id"]
        symbols = [e["ticker"] for e in entries if e.get("ticker")]
        print(f"\n{entries[0]['label']}")
        print(f"  list_id : {list_id}")
        print(f"  symbols : {symbols}")
        total += len(symbols)

    print(f"\n── Total tickers to add: {total} ──────────────────────────────────")

    if args.dry_run:
        print("\n[DRY RUN] No MCP calls made. Remove --dry-run to execute.")
        return

    print(
        "\n[ACTION REQUIRED] Run the following in your Claude Code session:\n"
        "  The Robinhood MCP (add_to_watchlist) requires Claude Code's OAuth session.\n"
        "  Pass Claude Code this output and ask it to execute each watchlist add.\n"
        "  Alternatively, paste the symbol lists into Claude.ai with the Robinhood connector.\n"
    )

    # Emit a structured block Claude Code can act on
    print("── MCP Calls (paste to Claude Code) ──────────────────────────────")
    for wl_name, entries in watchlists.items():
        if not entries:
            continue
        list_id = entries[0]["list_id"]
        symbols = [e["ticker"] for e in entries if e.get("ticker")]
        print(f"\nadd_to_watchlist(list_id='{list_id}', symbols={symbols})")
        print(f"  # {entries[0]['label']}")


if __name__ == "__main__":
    main()
