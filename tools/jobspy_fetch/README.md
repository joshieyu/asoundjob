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

## LinkedIn

LinkedIn is queried through JobSpy's public guest search endpoint. No
LinkedIn account or login is involved anywhere in this path, so nothing
about a credential is at risk here — the only thing exposed is the IP
address making the requests. LinkedIn rate-limits that endpoint
aggressively, and past roughly page 10 it starts returning HTTP 429. JobSpy
does not raise on a 429: it logs the error and returns whatever jobs it had
already collected, so an unprotected run can look like it succeeded while
quietly returning partial data. `fetch.py` watches for that signature (and
for JobSpy's "Bad proxy" message) and aborts the whole run the moment either
appears, rather than continuing to hammer an endpoint that is already
refusing the request.

**LinkedIn's terms of service prohibit automated scraping. Routing requests
through a proxy changes the IP making them, not that fact.** This tool does
not decide whether to run against LinkedIn — the owner does, term by term
and run by run.

### Supplying proxies

Proxy URLs contain credentials and must never land in shell history or in
this repo. There is deliberately no inline `--proxies` flag. Use one of:

- `--proxies-file PATH` — one proxy per line, blank lines and `#` comments
  ignored. See `proxies.txt.example` for the accepted formats
  (`user:pass@host:port`, or prefixed with `http://`, `https://`, or
  `socks5://`).
- the `JOBSPY_PROXIES` environment variable — comma-separated proxies.
  `--proxies-file` wins if both are set.

The kind of proxy that actually works against LinkedIn's guest endpoint is
a residential or rotating proxy; a cheap datacenter proxy tends to be
blocklisted already. This tool does not recommend or link a vendor — that
choice, and the credentials, are the owner's to supply.

Every log line, error message, and preflight report shows proxies masked to
`host:port` only (scheme, username and password stripped). The output JSON
records `proxy_count`, never the proxies themselves.

If `linkedin` is in `--sites` and no proxies resolved, `fetch.py` exits
before making any network call. `--i-understand-linkedin-without-proxy` is
an explicit, deliberately verbose escape hatch for when you want to accept
that risk anyway.

### Preflight

Before any search runs, when proxies are configured, `fetch.py` fetches the
direct (no-proxy) egress IP from a neutral IP-echo endpoint, then requests
the same endpoint through each configured proxy. A proxy only passes if it
responds and reports an IP different from the direct one — the same IP
means traffic isn't actually being proxied. Any failing proxy aborts the
run unless `--allow-partial-proxies` is passed, in which case the run
continues with only the passing proxies (a failing proxy is dropped, never
left in rotation). `--skip-preflight` skips this check for offline testing
and prints a warning when used.

### Defaults and flags specific to LinkedIn

- `--results-wanted` defaults to 25 (one page) instead of 50 when
  `linkedin` is in `--sites` and you don't pass `--results-wanted`
  explicitly. LinkedIn rate-limits aggressively past roughly page 10.
- `--linkedin-fetch-description` (default off) fetches the full job
  description for every LinkedIn result, passed through to JobSpy as
  `linkedin_fetch_description`. This is O(n) extra requests — one per job —
  so it multiplies block risk. Without it, LinkedIn rows arrive with no
  description at all, which matters because
  `scraper/scraper/propose_companies.py` scores candidates on title and
  description together.
- `--delay-between-terms` (seconds, default 0) sleeps between search terms,
  on top of JobSpy's own per-page pacing, so a multi-term sweep can be
  spread out further.

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
