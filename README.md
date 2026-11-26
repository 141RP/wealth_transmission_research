# Wealth Transmission Research

Tools for collecting public probate court records for research on the intergenerational transmission of wealth and inequalities in the probate system.

## Demo: Franklin County, Ohio

A small proof of concept that reads the Franklin County Probate Court's public General Case Search (Columbus, Ohio) and turns estate cases into a research table. Franklin County stands in for North Carolina here: NC's statewide eCourts portal puts a bot check in front of every search, so it can't be read automatically.

### What it collects

One row per estate case, with names masked. The open-date index gives the first group of fields; `--details` opens each estate's detail, fiduciary and docket pages for the rest.

| Field | Source | Meaning |
| --- | --- | --- |
| `case_number`, `status`, `open_date`, `closed_date`, `is_open`, `days_to_close` | index | Case basics; `status` is the court's code (99 = closed) |
| `subtype_code`, `subtype`, `has_will` | index | The court codes every estate as testate or intestate |
| `admin_tier` | index | Full, release or summary administration; release and summary are Ohio's small-estate routes |
| `decedent_initials`, `decedent_id` | index | Initials and a salted hash instead of the name |
| `date_of_death`, `days_death_to_open`, `decedent_zip` | detail | Timing and neighborhood (the street address is never read) |
| `bond_amount`, `related_cases` | detail | Fiduciary bond, which scales with estate size; count of linked cases |
| `inventory_value`, `estate_tax_anticipated` | docket | Value on the filed inventory, where one exists |
| `n_fiduciaries`, `fiduciary_title`, `fiduciary_id` | fiduciaries | Who administers the estate (executor, administrator, ...) |
| `fiduciary_same_surname` | fiduciaries | Rough family proxy, computed in memory from the names |
| `has_attorney` | fiduciaries | Whether an attorney of record is listed |

## Getting started

Requires Python 3.10 or newer.

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

### Run the demo

```
export PROBATE_SCRAPER_CONTACT="you@example.edu"   # shown in the User-Agent
export PROBATE_MASK_SALT="some-private-string"     # keeps hashed ids private
python -m scraper.run_sample --start 2025-03-03 --days 2 --limit 30 --details
python -m scraper.summarize data/sample/franklin_sample_masked.csv
```

The charts from the first real run are in [`notebooks/franklin_sample.ipynb`](notebooks/franklin_sample.ipynb).

Without `--details` a run needs about one request per 40 cases; with it, three more per estate (so a 30-case run takes a couple of minutes at the polite rate). The court's search is offline for backup from 10 PM to 2 AM Eastern, and the scraper won't run then.

## How it behaves

- One request at a time, at least 3 seconds apart, with backoff on errors. It stops if the court refuses a request.
- Raw pages are cached under `data/raw/` so re-runs don't hit the court again.
- A hard cap of 50 cases per demo run.
- Docket continuation lines, which hold next-of-kin names and addresses, are skipped; only coded filings are read.

## Data policy

Raw court pages and unmasked data stay out of version control (see `.gitignore`). Only CSVs under `data/sample/` ending in `_masked.csv` may be committed.

## Layout

```
scraper/      fetching, parsing, masking, CLI
tests/        parser and masking tests (pytest), on synthetic pages in tests/fixtures/
notebooks/    analysis
data/         git-ignored except masked samples
```

## Status

The parsers are written against the court's live pages as of Nov 24, 2026, and tested on synthetic copies of their structure. A first real run on a local machine is next.
