"""
STEP 00 (testing only) - Create a SYNTHETIC dataset with the exact CMS column layout.

This lets the whole pipeline be run and checked before the real CMS download is
available. The numbers are made up; never quote them as findings.
Real data comes from 01_download.py and overwrites these files.

Usage:
    python src/00_make_sample_data.py
"""
import numpy as np
import pandas as pd

from config import RAW_DIR

rng = np.random.default_rng(42)
YEARS = [2020, 2021, 2022, 2023, 2024]
N_PRESCRIBERS = 12_000

STATES = ["CA", "TX", "FL", "NY", "PA", "OH", "IL", "MI", "GA", "NC", "NJ", "VA", "TN",
          "AZ", "IN", "MA", "MO", "WA", "AL", "KY", "SC", "LA", "WI", "MN", "CO"]
STATE_W = np.array([12, 9, 9, 7, 5, 5, 5, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2], float)
SPECIALTIES = ["Internal Medicine", "Family Practice", "Nurse Practitioner", "Endocrinology",
               "Physician Assistant", "Cardiology", "General Practice", "Nephrology"]
SPEC_W = np.array([30, 28, 18, 8, 9, 3, 2, 2], float)
SPEC_MULT = {"Endocrinology": 4.0, "Internal Medicine": 1.3, "Family Practice": 1.1}

# Brand, generic, relative weight per year, cost per claim ($)
BRANDS = [
    ("Ozempic", "Semaglutide", [30, 45, 60, 75, 85], 900),
    ("Rybelsus", "Semaglutide", [5, 9, 13, 16, 18], 880),
    ("Wegovy", "Semaglutide", [0, 0, 0, 0, 4], 1300),
    ("Mounjaro", "Tirzepatide", [0, 0, 3, 25, 45], 1000),
    ("Trulicity", "Dulaglutide", [55, 60, 60, 52, 44], 870),
    ("Victoza", "Liraglutide", [30, 24, 18, 12, 8], 1000),
    ("Bydureon Bcise", "Exenatide", [7, 6, 4, 3, 2], 800),
    ("Byetta", "Exenatide", [2, 1.5, 1, 0.6, 0.4], 750),
]

prescribers = pd.DataFrame({
    "Prscrbr_NPI": rng.choice(np.arange(1_000_000_000, 2_000_000_000), N_PRESCRIBERS, replace=False),
    "Prscrbr_Last_Org_Name": [f"Last{i}" for i in range(N_PRESCRIBERS)],
    "Prscrbr_First_Name": [f"First{i}" for i in range(N_PRESCRIBERS)],
    "Prscrbr_State_Abrvtn": rng.choice(STATES, N_PRESCRIBERS, p=STATE_W / STATE_W.sum()),
    "Prscrbr_Type": rng.choice(SPECIALTIES, N_PRESCRIBERS, p=SPEC_W / SPEC_W.sum()),
})
prescribers["Prscrbr_City"] = "City_" + prescribers["Prscrbr_State_Abrvtn"]
# Each prescriber has a latent "propensity" (lognormal = a few very heavy writers)
prescribers["propensity"] = rng.lognormal(0, 0.9, N_PRESCRIBERS) * prescribers["Prscrbr_Type"].map(SPEC_MULT).fillna(1.0)
prescribers["trend"] = rng.normal(1.0, 0.25, N_PRESCRIBERS)  # prescriber-specific momentum

RAW_DIR.mkdir(parents=True, exist_ok=True)
for yi, year in enumerate(YEARS):
    rows = []
    for brand, generic, weights, cost in BRANDS:
        w = weights[yi]
        if w == 0:
            continue
        lam = prescribers["propensity"] * w / 8 * prescribers["trend"] ** yi
        claims = rng.poisson(lam)
        keep = claims >= 11  # CMS suppresses prescriber-drug rows with < 11 claims
        sub = prescribers.loc[keep].copy()
        sub["Tot_Clms"] = claims[keep]
        sub["Brnd_Name"], sub["Gnrc_Name"] = brand, generic
        sub["Tot_30day_Fills"] = (sub["Tot_Clms"] * rng.uniform(1.0, 1.6, len(sub))).round(1)
        sub["Tot_Day_Suply"] = (sub["Tot_30day_Fills"] * 30).round()
        sub["Tot_Drug_Cst"] = (sub["Tot_Clms"] * cost * rng.uniform(0.9, 1.1, len(sub))).round(2)
        benes = (sub["Tot_Clms"] / rng.uniform(3, 8, len(sub))).round()
        sub["Tot_Benes"] = benes.where(benes >= 11)  # blank when suppressed
        rows.append(sub)
    data = pd.concat(rows, ignore_index=True).drop(columns=["propensity", "trend"])
    data.insert(0, "Year", year)
    data.to_csv(RAW_DIR / f"partd_glp1_{year}.csv", index=False)
    print(f"SAMPLE {year}: {len(data):,} rows")
