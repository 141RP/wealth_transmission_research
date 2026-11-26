"""Pull a small, polite sample of Franklin County estate cases into a masked CSV.

Example (run on your own machine, outside 10 PM - 2 AM Eastern):
    python -m scraper.run_sample --start 2025-03-03 --days 2 --limit 30 --details

Without --details it reads only the open-date index (about one request per 40
cases). With --details it also opens each estate's detail, fiduciary and docket
pages, three more requests per case, which adds date of death, zip, bond,
inventory value, fiduciary title and attorney presence.

Only masked fields are written to the CSV. Raw pages are cached under data/raw/,
which git ignores, so re-runs don't hit the court again.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config
from .client import PoliteClient
from .franklin import (FIELDS, build_record, case_urls, date_index_url, parse_docket,
                       parse_estate_detail, parse_fiduciaries, parse_index)

MAX_INDEX_PAGES = 20


def _opened(row: dict) -> date | None:
    try:
        return datetime.strptime(row.get("opened", ""), "%m/%d/%Y").date()
    except ValueError:
        return None


def collect(client: PoliteClient, start: date, days: int, limit: int,
            details: bool, all_types: bool) -> list[dict]:
    end = start + timedelta(days=days - 1)
    url: str | None = date_index_url(start)
    records: list[dict] = []
    seen: set[str] = set()  # "Next Cases" pages start with the previous page's last case
    for _ in range(MAX_INDEX_PAGES):
        if not url:
            break
        rows, url = parse_index(client.get(url))
        for row in rows:
            if row["case_number"] in seen:
                continue
            seen.add(row["case_number"])
            opened = _opened(row)
            if opened and opened > end:
                return records
            if opened and opened < start:
                continue
            is_estate = row.get("case_type", "").upper() == "ESTATE"
            if not (is_estate or all_types):
                continue
            if details and is_estate:
                pages = case_urls(row["case_number"])
                rec = build_record(row,
                                   parse_estate_detail(client.get(pages["detail"])),
                                   parse_fiduciaries(client.get(pages["fiduciaries"])),
                                   parse_docket(client.get(pages["docket"])))
            else:
                rec = build_record(row)
            records.append(rec)
            if len(records) >= limit:
                return records
    return records


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=date.fromisoformat, required=True, help="first open date, YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=1, help="how many consecutive open dates to cover")
    ap.add_argument("--limit", type=int, default=30, help=f"max cases (hard cap {config.DEMO_MAX_CASES})")
    ap.add_argument("--details", action="store_true", help="also open each estate's detail, fiduciary and docket pages")
    ap.add_argument("--all-types", action="store_true", help="keep guardianship and miscellaneous cases too")
    ap.add_argument("--out", type=Path, default=Path("data/sample/franklin_sample_masked.csv"))
    args = ap.parse_args(argv)

    client = PoliteClient()
    records = collect(client, args.start, max(args.days, 1), min(args.limit, config.DEMO_MAX_CASES),
                      args.details, args.all_types)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    print(f"Wrote {len(records)} cases to {args.out} using {client.requests_made} requests.")


if __name__ == "__main__":
    main()
