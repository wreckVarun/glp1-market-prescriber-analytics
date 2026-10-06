"""
STEP 02 - Combine the yearly files into one clean panel.

Cleaning decisions (each one is an assumption you should be able to defend):
1. Numeric columns arrive as text from the API; convert them, blanks -> NaN.
2. Tot_Benes is blank when a row has fewer than 11 beneficiaries (CMS privacy
   suppression). We keep it as NaN, never fill with 0, and treat any beneficiary
   total as a LOWER BOUND.
3. Brand names are standardised to title case ("OZEMPIC" -> "Ozempic"), and
   pack-size / device variants are merged ("Victoza 3-Pak" -> "Victoza",
   "Bydureon Pen" -> "Bydureon") so one brand is not split across rows.
   "Exenatide Microspheres" (Bydureon's CMS generic name) -> molecule "Exenatide".
4. Specialty (Prscrbr_Type) is trimmed; blank -> "Unknown".
5. Each NPI gets ONE state and ONE specialty: the value from their most recent
   year. Prescribers occasionally move or re-classify, and we want a stable label
   for segmentation.

Output: data/processed/glp1_panel.csv  (one row = prescriber x brand x year)
"""
import pandas as pd

from config import BRAND_MANUFACTURER, BRAND_STANDARD, MOLECULE_STANDARD, PROCESSED_DIR, RAW_DIR

NUMERIC = ["Tot_Clms", "Tot_30day_Fills", "Tot_Day_Suply", "Tot_Drug_Cst", "Tot_Benes"]


def main():
    files = sorted(RAW_DIR.glob("partd_glp1_*.csv"))
    if not files:
        raise SystemExit("No raw files. Run 01_download.py (or 00_make_sample_data.py to test).")
    df = pd.concat((pd.read_csv(f, dtype={"Prscrbr_NPI": str}) for f in files), ignore_index=True)
    print(f"Loaded {len(df):,} rows from {len(files)} files")

    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Brnd_Name"] = df["Brnd_Name"].str.strip().str.title()
    df["Brnd_Name"] = df["Brnd_Name"].replace(BRAND_STANDARD)
    df["Gnrc_Name"] = df["Gnrc_Name"].str.strip().str.title().replace(MOLECULE_STANDARD)
    df["Prscrbr_Type"] = df["Prscrbr_Type"].fillna("Unknown").str.strip()
    df["Manufacturer"] = df["Brnd_Name"].map(BRAND_MANUFACTURER).fillna("Other")

    # Stable state / specialty per NPI = most recent year's value
    latest = (df.sort_values("Year")
                .groupby("Prscrbr_NPI")[["Prscrbr_State_Abrvtn", "Prscrbr_Type"]]
                .last())
    df = df.drop(columns=["Prscrbr_State_Abrvtn", "Prscrbr_Type"]).join(latest, on="Prscrbr_NPI")

    # Sanity checks: claims must be >= 11 (suppression floor) and cost non-negative
    below_floor = (df["Tot_Clms"] < 11).sum()
    print(f"Rows with Tot_Clms < 11 (should be 0 in CMS data): {below_floor}")
    print(f"Suppressed Tot_Benes rows: {df['Tot_Benes'].isna().mean():.1%}")
    print(df.groupby("Year").agg(rows=("Tot_Clms", "size"), claims=("Tot_Clms", "sum")))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "glp1_panel.csv", index=False)
    print(f"Saved {len(df):,} rows -> data/processed/glp1_panel.csv")


if __name__ == "__main__":
    main()
