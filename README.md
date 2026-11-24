# Wealth Transmission Research

Tools for collecting public probate court records for research on the intergenerational transmission of wealth and inequalities in the probate system.

## Status

Early setup. The first scraper (a Franklin County, Ohio demo) is in progress on a feature branch.

## Getting started

Requires Python 3.10 or newer.

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data policy

Raw court pages and unmasked data stay out of version control (see `.gitignore`). Only samples with names masked may be committed.
