"""Pull a small, polite sample of Franklin County estate cases into a masked CSV.

Example (run on your own machine, outside 10 PM - 2 AM Eastern):
    python -m scraper.run_sample --start 2026-11-02 --days 3 --limit 30

Only masked fields are written to the CSV. Raw pages are cached under data/raw/,
which git ignores, so re-runs don't hit the court again.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

from . import config
from .client import PoliteClient
from .franklin import date_index_url, normalize, parse_label_values, parse_tables

FIELDS = ["county", "case_number", "open_date", "closed_date", "status", "case_type",
          "subtype_code", "subtype", "has_will", "admin_tier", "decedent_initials",
          "decedent_id", "fiduciary_id", "has_attorney", "date_of_death", "estate_value"]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=date.fromisoformat, required=True, help="first open date, YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=3, help="how many consecutive days to search")
    ap.add_argument("--limit", type=int, default=30, help=f"max cases (hard cap {config.DEMO_MAX_CASES})")
    ap.add_argument("--details", action="store_true", help="also open each case's detail page")
    ap.add_argument("--all-types", action="store_true", help="keep guardianship, trust and other case types too")
    ap.add_argument("--out", type=Path, default=Path("data/sample/franklin_sample_masked.csv"))
    args = ap.parse_args(argv)

    limit = min(args.limit, config.DEMO_MAX_CASES)
    client = PoliteClient()
    records: list[dict] = []
    for i in range(args.days):
        day = args.start + timedelta(days=i)
        for row in parse_tables(client.get(date_index_url(day))):
            if args.details and row.get("_links"):
                detail = parse_label_values(client.get(row["_links"][0]))
                row = {**detail, **{k: v for k, v in row.items() if v}}
            rec = normalize(row)
            if not args.all_types and rec["case_type"] not in ("Estate", "E", ""):
                continue
            records.append(rec)
            if len(records) >= limit:
                break
        if len(records) >= limit:
            break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    print(f"Wrote {len(records)} cases to {args.out} using {client.requests_made} requests.")


if __name__ == "__main__":
    main()
