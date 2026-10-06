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

Usage:
    python src/01_download.py              # latest 5 years
    python src/01_download.py --years 2021 2022 2023
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

import pandas as pd

from config import GLP1_GENERICS, KEEP_COLS, RAW_DIR

CATALOG_URL = "https://data.cms.gov/data.json"
DATASET_TITLE = "Medicare Part D Prescribers - by Provider and Drug"
PAGE_SIZE = 5000  # CMS API maximum rows per request


def get_json(url, retries=4):
    """GET a URL and parse JSON, retrying with exponential backoff on network errors."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - we want to retry on any network error
            if attempt == retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(f"  retry in {wait}s after error: {exc}")
            time.sleep(wait)


def find_yearly_api_urls():
    """Return {year: api_url} for every year of the dataset listed in the CMS catalog."""
    catalog = get_json(CATALOG_URL)
    urls = {}
    for ds in catalog["dataset"]:
        if ds.get("title", "").strip() != DATASET_TITLE:
            continue
        for dist in ds.get("distribution", []):
            url = dist.get("accessURL", "")
            if dist.get("format") != "API" or "/data-api/v1/dataset/" not in url:
                continue
            # The year lives in "temporal" (e.g. "2023-01-01/2023-12-31") or the title.
            text = f"{dist.get('temporal', '')} {dist.get('title', '')}"
            match = re.search(r"(20\d\d)", text)
            if match:
                urls[int(match.group(1))] = url.rstrip("/")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, nargs="*", help="data years to pull")
    parser.add_argument("--n-latest", type=int, default=5, help="if --years not given, pull this many latest years")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    available = find_yearly_api_urls()
    print(f"CMS lists data years: {list(available)}")
    years = args.years or list(available)[-args.n_latest:]

    for year in years:
        out = RAW_DIR / f"partd_glp1_{year}.csv"
        if out.exists():
            print(f"{year}: already downloaded -> {out.name}")
            continue
        frames = []
        for generic in GLP1_GENERICS:
            df = download_generic(available[year], generic)
            print(f"{year} {generic:<12} {len(df):>8,} rows")
            frames.append(df)
        data = pd.concat(frames, ignore_index=True)
        data = data[[c for c in KEEP_COLS if c in data.columns]]
        data.insert(0, "Year", year)
        data.to_csv(out, index=False)
        print(f"{year}: saved {len(data):,} rows -> {out.name}")


if __name__ == "__main__":
    main()
