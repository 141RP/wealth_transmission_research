"""Quick summary stats for a masked sample CSV.

    python -m scraper.summarize data/sample/franklin_sample_masked.csv
"""

import sys

import pandas as pd


def _share(series: pd.Series) -> str:
    known = series.dropna().astype(str).str.lower().map({"true": 1, "false": 0}).dropna()
    return f"{known.mean():.0%} of {len(known)}" if len(known) else "not collected"


def main(path: str) -> None:
    df = pd.read_csv(path)
    print(f"{len(df)} cases\n")
    print("Will vs. no will:")
    will = df["has_will"].astype(str).str.lower().map({"true": "with will", "false": "no will"})
    print(will.fillna("n/a").value_counts().to_string(), "\n")
    print("Administration tier (release and summary are Ohio's small-estate routes):")
    print(df["admin_tier"].fillna("other").value_counts().to_string(), "\n")
    print(f"Still open: {_share(df['is_open'])}")
    closed = df["days_to_close"].dropna()
    if len(closed):
        print(f"Days from opening to closing (closed cases): median {closed.median():.0f}, n={len(closed)}")
    print(f"Attorney of record: {_share(df['has_attorney'])}")
    print(f"Fiduciary shares the decedent's surname: {_share(df['fiduciary_same_surname'])}")
    for col, label in (("inventory_value", "Inventory value"), ("bond_amount", "Bond amount")):
        vals = df[col].dropna()
        if len(vals):
            print(f"\n{label} where filed (n={len(vals)}):")
            print(vals.describe()[["min", "50%", "max"]].to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/sample/franklin_sample_masked.csv")
