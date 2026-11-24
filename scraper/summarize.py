"""Quick summary stats for a masked sample CSV.

    python -m scraper.summarize data/sample/franklin_sample_masked.csv
"""

import sys

import pandas as pd


def main(path: str) -> None:
    df = pd.read_csv(path)
    print(f"{len(df)} cases\n")
    print("Will vs. no will:")
    print(df["has_will"].map({True: "with will", False: "no will"}).fillna("n/a").value_counts().to_string(), "\n")
    print("Administration tier (proxy for estate size):")
    print(df["admin_tier"].fillna("other").value_counts().to_string(), "\n")
    print(f"Share with an attorney of record: {df['has_attorney'].mean():.0%}")
    if df["estate_value"].notna().any():
        print("\nEstate value where listed:")
        print(df["estate_value"].describe().to_string())
    else:
        print("\nNo estate values listed on these pages.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/sample/franklin_sample_masked.csv")
