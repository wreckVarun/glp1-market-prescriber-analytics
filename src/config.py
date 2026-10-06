"""
Shared settings for every step of the pipeline.

Keeping all assumptions in ONE file means that in an interview you can point
to exactly where each choice was made, and change it in one place.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"              # filtered CMS pulls (one CSV per year)
PROCESSED_DIR = ROOT / "data" / "processed"  # cleaned, combined panel
TABLES_DIR = ROOT / "outputs" / "tables"     # analysis results
CHARTS_DIR = ROOT / "outputs" / "charts"     # Matplotlib PNGs
TABLEAU_DIR = ROOT / "outputs" / "tableau"   # dashboard-ready extracts

# ---------------------------------------------------------------------------
# Scope: which drugs count as "GLP-1"
# ---------------------------------------------------------------------------
# We filter on the CMS generic-name column (Gnrc_Name). Using the generic name
# rather than brand catches every brand of a molecule in one go.
# ASSUMPTION: fixed-ratio insulin combos (Xultophy = insulin degludec/liraglutide,
# Soliqua = insulin glargine/lixisenatide) are EXCLUDED because they are
# positioned and promoted as insulin products, not GLP-1 brands.
# NOTE: CMS lists Bydureon's generic as "Exenatide Microspheres" (extended release),
# and the API filter is an exact match, so it must be listed separately.
GLP1_GENERICS = ["Semaglutide", "Tirzepatide", "Dulaglutide", "Liraglutide",
                 "Exenatide", "Exenatide Microspheres"]

# Collapse CMS generic-name variants into one molecule for analysis.
MOLECULE_STANDARD = {"Exenatide Microspheres": "Exenatide"}

# Collapse pack-size / device variants into one marketed brand.
# "Liraglutide" as a brand name = unbranded generic liraglutide (launched mid-2024).
BRAND_STANDARD = {
    "Victoza 2-Pak": "Victoza",
    "Victoza 3-Pak": "Victoza",
    "Bydureon Pen": "Bydureon",
    "Liraglutide": "Generic Liraglutide",
}

# Brand -> manufacturer. Used only for labelling outputs.
# Note: tirzepatide is a dual GIP/GLP-1 agonist; we group it with GLP-1s as the
# market does.
BRAND_MANUFACTURER = {
    "Ozempic": "Novo Nordisk",
    "Rybelsus": "Novo Nordisk",
    "Wegovy": "Novo Nordisk",
    "Victoza": "Novo Nordisk",
    "Saxenda": "Novo Nordisk",
    "Mounjaro": "Eli Lilly",
    "Zepbound": "Eli Lilly",
    "Trulicity": "Eli Lilly",
    "Byetta": "AstraZeneca",
    "Bydureon Bcise": "AstraZeneca",
    "Bydureon": "AstraZeneca",
    "Generic Liraglutide": "Generic",
}

# ---------------------------------------------------------------------------
# Segmentation thresholds (step 04)
# ---------------------------------------------------------------------------
HIGH_VALUE_PERCENTILE = 0.80  # top 20% of prescribers by latest-year GLP-1 claims
EMERGING_MIN_PERCENTILE = 0.50  # emerging writers must already be at or above median volume
# Emerging growth bar = the TOTAL market's own YoY claim growth in the latest year
# (computed in step 04, not hard-coded): a prescriber only counts as emerging if
# their GLP-1 writing is growing faster than the market around them.

# ---------------------------------------------------------------------------
# Forecast scenario settings (step 05)
# ---------------------------------------------------------------------------
CAGR_LOOKBACK_YEARS = 3       # base growth = CAGR over the last 3 year-on-year steps
SCENARIO_SPREAD_PP = 0.10     # high / low = base growth +/- 10 percentage points
# Molecules with < 4 years of data (launch brands): repeat last year's ABSOLUTE
# claim gain instead of a % growth rate (see 05_forecast.py).

# CMS column names we actually use (the public file has ~22 columns)
KEEP_COLS = [
    "Prscrbr_NPI", "Prscrbr_Last_Org_Name", "Prscrbr_First_Name",
    "Prscrbr_City", "Prscrbr_State_Abrvtn", "Prscrbr_Type",
    "Brnd_Name", "Gnrc_Name",
    "Tot_Clms", "Tot_30day_Fills", "Tot_Day_Suply", "Tot_Drug_Cst", "Tot_Benes",
]

# Non-state codes in Prscrbr_State_Abrvtn that we drop from state-level views
# (XX = unknown, ZZ = foreign, AA/AE/AP = armed forces, territories kept separately).
NON_STATE_CODES = {"XX", "ZZ", "AA", "AE", "AP"}
