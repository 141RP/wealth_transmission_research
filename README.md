# Wealth Transmission Research

Tools for collecting public probate court records for research on the intergenerational transmission of wealth and inequalities in the probate system.

## Demo: Franklin County, Ohio

A small proof of concept that reads the Franklin County Probate Court's public General Case Search (Columbus, Ohio) and turns estate cases into a research table. Franklin County stands in for North Carolina here: NC's statewide eCourts portal puts a bot check in front of every search, so it can't be read automatically.

### What it collects

One row per estate case, with names masked:

| Field | Meaning |
| --- | --- |
| `case_number`, `open_date`, `closed_date`, `status` | Case basics |
| `subtype`, `has_will` | The court codes every estate as with or without a will |
| `admin_tier` | Full, release or summary administration; release and summary are for smaller estates in Ohio |
| `has_attorney` | Whether an attorney is listed |
| `decedent_initials`, `decedent_id`, `fiduciary_id` | Initials and salted hashes instead of names |
| `estate_value` | Only if the court's pages list one |

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
python -m scraper.run_sample --start 2026-11-02 --days 3 --limit 30
python -m scraper.summarize data/sample/franklin_sample_masked.csv
```

The court's search is offline for backup from 10 PM to 2 AM Eastern, and the scraper won't run then.

## How it behaves

- One request at a time, at least 3 seconds apart, with backoff on errors. It stops if the court refuses a request.
- Raw pages are cached under `data/raw/` so re-runs don't hit the court again.
- A hard cap of 50 cases per demo run.

## Data policy

Raw court pages and unmasked data stay out of version control (see `.gitignore`). Only CSVs under `data/sample/` ending in `_masked.csv` may be committed.

## Layout

```
scraper/      fetching, parsing, masking, CLI
tests/        parser and masking tests (pytest)
notebooks/    analysis
data/         git-ignored except masked samples
```

## Status

The search URL pattern and the case-code list are confirmed from the court's site. The results-page parser is generic for now, because the results server was offline when this was written; it'll be tightened against real pages next.
