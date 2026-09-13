# jobspy_fetch

Standalone fetcher that calls `python-jobspy`'s `scrape_jobs()` and dumps raw
results to a JSON file. This directory is intentionally **outside** the
`scraper` package and must never be imported from it.

## Why this needs its own venv

`python-jobspy` requires Python `>=3.10`, while the rest of this repo's
`scraper` package is pinned to Python 3.9.6. `python-jobspy` also pulls in
`numpy==1.26.3`, which must never enter the scraper's dependency tree.

Keeping this tool in its own directory with its own virtual environment keeps
both constraints satisfied: the scraper stays on 3.9 with no numpy, and this
fetcher gets the newer Python it needs.

## Setup

Run these from the repo root, using a Python 3.10+ interpreter (adjust the
`python3.10` command below to whatever your system provides, e.g.
`python3.11`, `python3.12`):

```
cd tools/jobspy_fetch
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```
source tools/jobspy_fetch/.venv/bin/activate
python tools/jobspy_fetch/fetch.py \
  --terms-file tools/jobspy_fetch/terms.txt \
  --sites indeed,linkedin \
  --results-wanted 50 \
  --hours-old 720 \
  --output tools/jobspy_fetch/out/jobs.json
```

The output JSON feeds into `scraper/scraper/propose_companies.py`, which runs
in the scraper's own Python 3.9 environment and never imports anything from
this directory.
