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

Run these from the repo root, using the installed Python 3.12 interpreter
(adjust `python3.12` below to whatever 3.10+ interpreter your system
provides, e.g. `python3.10`, `python3.11`):

```
cd tools/jobspy_fetch
python3.12 -m venv .venv
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

## Countries

`scrape_jobs()` takes a `country_indeed` argument that controls which
country's Indeed (and Glassdoor) domain is queried. This tool exposes it as
`--country`, and **it defaults to `usa`** — an un-flagged run only ever sees
US listings, no matter what search term you pass. `--country` is validated
against `python-jobspy`'s own `Country` enum before any network call is
made; an invalid value exits immediately with the full list of valid
country names.

The country is recorded in the output payload (next to `fetched_at` and
`terms`) and stamped on every job dict as a `country` field, so
`propose_companies.py` can show which country a candidate company was found
in.

English search terms live in `terms.txt`. Non-English terms live in sibling
files, grouped by the language(s) they're written in rather than by any one
country, since several countries share a language:

- `terms-de.txt` — German (germany, austria, switzerland)
- `terms-fr.txt` — French (france, belgium, switzerland)
- `terms-nordic.txt` — Swedish, Danish, Norwegian, Finnish (sweden, denmark, norway, finland)
- `terms-nl.txt` — Dutch (netherlands, belgium)
- `terms-es-it.txt` — Spanish and Italian (spain, italy)

Every term in those files is chosen so the audio signal lands in the job
title itself — that's what `scraper/scraper/normalizer.py`'s
`AUDIO_TITLE_STRONG_INTL` pattern needs to classify an unknown company's
posting as audio-related. `scraper/tests/test_intl_search_terms.py` proves
each term survives that classifier.

### Sweep recipe

To cover the non-US audio industry, run one invocation per
country/terms-file pairing:

```
source tools/jobspy_fetch/.venv/bin/activate

python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-de.txt --sites indeed --country germany --output tools/jobspy_fetch/out/de-germany.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-de.txt --sites indeed --country austria --output tools/jobspy_fetch/out/de-austria.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-de.txt --sites indeed --country switzerland --output tools/jobspy_fetch/out/de-switzerland.json

python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-fr.txt --sites indeed --country france --output tools/jobspy_fetch/out/fr-france.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-fr.txt --sites indeed --country belgium --output tools/jobspy_fetch/out/fr-belgium.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-fr.txt --sites indeed --country switzerland --output tools/jobspy_fetch/out/fr-switzerland.json

python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-nordic.txt --sites indeed --country sweden --output tools/jobspy_fetch/out/nordic-sweden.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-nordic.txt --sites indeed --country denmark --output tools/jobspy_fetch/out/nordic-denmark.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-nordic.txt --sites indeed --country norway --output tools/jobspy_fetch/out/nordic-norway.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-nordic.txt --sites indeed --country finland --output tools/jobspy_fetch/out/nordic-finland.json

python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-nl.txt --sites indeed --country netherlands --output tools/jobspy_fetch/out/nl-netherlands.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-nl.txt --sites indeed --country belgium --output tools/jobspy_fetch/out/nl-belgium.json

python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-es-it.txt --sites indeed --country spain --output tools/jobspy_fetch/out/es-it-spain.json
python tools/jobspy_fetch/fetch.py --terms-file tools/jobspy_fetch/terms-es-it.txt --sites indeed --country italy --output tools/jobspy_fetch/out/es-it-italy.json
```

Each output file feeds `scraper/scraper/propose_companies.py` on its own
(or concatenate `jobs` arrays before running it) the same way the US output
does.
