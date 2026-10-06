"""
STEP 01 - Download GLP-1 rows from CMS "Medicare Part D Prescribers - by Provider and Drug".

WHY THIS APPROACH
- The full national file is ~25 million rows (several GB) per year. We only need
  5 molecules, so we ask the CMS Data API to filter server-side by generic name.
  That turns a multi-GB download into a few tens of MB.
- We discover the yearly datasets from the CMS catalog (data.json) instead of
  hard-coding URLs, so the script automatically picks up the newest year when
  CMS publishes it.

WHAT ONE ROW MEANS
- One prescriber (NPI) x one drug (brand + generic) x one year.
- Tot_Clms = number of Part D claims (original fills + refills) that prescriber wrote.

MIRROR
- data.cms.gov is blocked from some countries (e.g. India). The same GLP-1 rows
  for 2020-2024 are kept as a zip on this repo's GitHub release (data-v1).
  If CMS cannot be reached, the script falls back to that copy automatically.

Usage:
    python src/01_download.py              # latest 5 years
    python src/01_download.py --years 2021 2022 2023
    python src/01_download.py --mirror     # skip CMS, use the GitHub release copy
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
import re
import time
import urllib.parse
import urllib.request
import zipfile

import pandas as pd

from config import GLP1_GENERICS, KEEP_COLS, RAW_DIR

CATALOG_URL = "https://data.cms.gov/data.json"
DATASET_TITLE = "Medicare Part D Prescribers - by Provider and Drug"
PAGE_SIZE = 5000  # CMS API maximum rows per request
USER_AGENT = "Mozilla/5.0 (glp1-market-prescriber-analytics)"
MIRROR_URL = ("https://github.com/wreckVarun/glp1-market-prescriber-analytics/"
              "releases/download/data-v1/glp1_partd_raw_2020_2024.zip")


def get_json(url, retries=4):
    """GET a URL and parse JSON, retrying with exponential backoff on network errors."""
    for attempt in range(retries):
        try:
            # data.cms.gov rejects Python's default "Python-urllib" agent with
            # HTTP 403, so identify as a normal browser-style client.
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - we want to retry on any network error
            if attempt == retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(f"  retry in {wait}s after error: {exc}")
            time.sleep(wait)


def find_yearly_api_urls():
    """Return {year: api_url} for every year of the dataset listed in the CMS catalog.

    CMS lists each data year as its own catalog entry, titled like
    "Medicare Part D Prescribers - by Provider and Drug : 2023-12-31".
    The year is read from the distribution's temporal startDate.
    """
    catalog = get_json(CATALOG_URL)
    urls = {}
    for ds in catalog["dataset"]:
        if not ds.get("title", "").startswith(DATASET_TITLE + " :"):
            continue
        for dist in ds.get("distribution", []):
            url = dist.get("accessURL") or ""
            if dist.get("format") != "API" or "/data-api/v1/dataset/" not in url:
                continue
            temporal = dist.get("temporal")
            if isinstance(temporal, list) and temporal:
                text = temporal[0].get("startDate", "")
            else:
                text = f"{temporal or ''} {dist.get('title', '')}"
            match = re.search(r"(20\d\d)", text)
            if match:
                # accessURL already ends in /data; store the dataset root
                urls[int(match.group(1))] = re.sub(r"/data/?$", "", url)
    if not urls:
        raise RuntimeError("Could not find the dataset in the CMS catalog; check DATASET_TITLE.")
    return dict(sorted(urls.items()))


def download_generic(api_url, generic):
    """Page through the CMS API for one generic name and return a DataFrame."""
    rows, offset = [], 0
    while True:
        query = urllib.parse.urlencode(
            {"filter[Gnrc_Name]": generic, "size": PAGE_SIZE, "offset": offset}
        )
        page = get_json(f"{api_url}/data?{query}")
        if not page:
            break
        rows.extend(page)
        offset += PAGE_SIZE
        if len(page) < PAGE_SIZE:
            break
    return pd.DataFrame(rows)


def download_mirror():
    """Fetch the 2020-2024 GLP-1 CSVs from the GitHub release and unzip them into data/raw/."""
    print(f"Downloading mirror copy: {MIRROR_URL}", flush=True)
    req = urllib.request.Request(MIRROR_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        archive = zipfile.ZipFile(io.BytesIO(resp.read()))
    for name in archive.namelist():
        out = RAW_DIR / name
        if out.exists():
            print(f"{name}: already downloaded")
            continue
        out.write_bytes(archive.read(name))
        print(f"saved {name}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, nargs="*", help="data years to pull")
    parser.add_argument("--n-latest", type=int, default=5, help="if --years not given, pull this many latest years")
    parser.add_argument("--mirror", action="store_true", help="use the GitHub release copy instead of CMS")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.mirror:
        download_mirror()
        return
    try:
        available = find_yearly_api_urls()
    except Exception as exc:  # noqa: BLE001 - any CMS failure means use the mirror
        print(f"CMS not reachable ({exc}); using the GitHub release copy instead.")
        download_mirror()
        return
    print(f"CMS lists data years: {list(available)}", flush=True)
    years = args.years or list(available)[-args.n_latest:]

    for year in years:
        out = RAW_DIR / f"partd_glp1_{year}.csv"
        if out.exists():
            print(f"{year}: already downloaded -> {out.name}")
            continue
        # One request stream per molecule, run in parallel (6 small streams is
        # polite to the API and much faster than going one molecule at a time).
        with ThreadPoolExecutor(max_workers=len(GLP1_GENERICS)) as pool:
            frames = list(pool.map(lambda g: download_generic(available[year], g), GLP1_GENERICS))
        for generic, df in zip(GLP1_GENERICS, frames):
            print(f"{year} {generic:<22} {len(df):>8,} rows", flush=True)
        data = pd.concat(frames, ignore_index=True)
        data = data[[c for c in KEEP_COLS if c in data.columns]]
        data.insert(0, "Year", year)
        data.to_csv(out, index=False)
        print(f"{year}: saved {len(data):,} rows -> {out.name}", flush=True)


if __name__ == "__main__":
    main()
