# Notebooks

## `franklin_sample.ipynb`

A first look at the Franklin County sample: days from opening to closing by administration tier, inventory values on a log scale, will versus no will within each tier, and a rough estimate of what a year of Franklin estates would take to collect.

It reads the masked CSV that the scraper writes:

```
python -m scraper.run_sample --start 2025-03-03 --days 2 --limit 30 --details
```

That CSV stays on your machine. It holds masked fields only, but its case numbers point to real court records, so it is not in the repo. The notebook is committed with its charts already drawn, so it can be read on GitHub without the data.

To open and rerun it:

```
pip install -r requirements.txt
jupyter notebook notebooks/franklin_sample.ipynb
```

Before committing a rerun, check that no output shows individual rows; every cell is written to print counts, medians and charts only.
