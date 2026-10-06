"""
STEP 07 - Write tidy, dashboard-ready CSVs for Tableau Public.

Rules for Tableau-friendly files: one row per entity, plain column names with
spaces (they become field names), no index column, numbers unformatted (Tableau
formats them), and a State column with 2-letter codes so Tableau geocodes it
automatically for the map.
"""
import pandas as pd

from config import TABLEAU_DIR, TABLES_DIR


def write(df, name):
    df.to_csv(TABLEAU_DIR / name, index=False)
    print(f"saved outputs/tableau/{name} ({len(df):,} rows)")


def main():
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)

    b = pd.read_csv(TABLES_DIR / "market_by_brand_year.csv")
    write(b.rename(columns={
        "Brnd_Name": "Brand", "Gnrc_Name": "Molecule", "claims": "Claims", "drug_cost": "Gross Drug Cost",
        "prescribers": "Prescribers", "claim_share": "Claim Share", "claims_yoy": "Claims YoY",
        "cost_per_claim": "Cost per Claim", "benes_lower_bound": "Beneficiaries (lower bound)",
    }), "1_market_by_brand_year.csv")

    s = pd.read_csv(TABLES_DIR / "market_by_state.csv")
    seg_s = pd.read_csv(TABLES_DIR / "segment_by_state.csv")
    s = s.merge(seg_s, on="Prscrbr_State_Abrvtn", how="left")
    write(s.rename(columns={
        "Prscrbr_State_Abrvtn": "State", "claims": "Claims", "drug_cost": "Gross Drug Cost",
        "prescribers": "Prescribers", "claims_yoy": "Claims YoY", "claims_per_prescriber": "Claims per Prescriber",
        "claim_share": "Claim Share", "prescribers_high_value": "High-value Prescribers",
        "prescribers_emerging": "Emerging Prescribers", "prescribers_low_adopter": "Low-adopter Prescribers",
    }).drop(columns=["claims_prior", "total_claims", "benes_lower_bound"], errors="ignore"),
        "2_market_by_state.csv")

    sp = pd.read_csv(TABLES_DIR / "market_by_specialty.csv")
    write(sp.rename(columns={
        "Prscrbr_Type": "Specialty", "claims": "Claims", "drug_cost": "Gross Drug Cost",
        "prescribers": "Prescribers", "claims_per_prescriber": "Claims per Prescriber", "claim_share": "Claim Share",
    }).drop(columns=["benes_lower_bound"]), "3_market_by_specialty.csv")

    p = pd.read_csv(TABLES_DIR / "prescriber_segments.csv", dtype={"Prscrbr_NPI": str})
    p["Prescriber"] = p["Prscrbr_First_Name"].fillna("") + " " + p["Prscrbr_Last_Org_Name"].fillna("")
    write(p.rename(columns={
        "Prscrbr_NPI": "NPI", "Prscrbr_City": "City", "Prscrbr_State_Abrvtn": "State",
        "Prscrbr_Type": "Specialty", "segment": "Segment", "claims_latest": "Claims (latest yr)",
        "claims_prior": "Claims (prior yr)", "yoy_growth": "Claims YoY", "is_new": "New Prescriber",
        "top_brand": "Top Brand", "share_novo": "Novo Nordisk Share", "share_eli": "Eli Lilly Share",
        "drug_cost_latest": "Gross Drug Cost (latest yr)",
    }).drop(columns=["Prscrbr_First_Name", "Prscrbr_Last_Org_Name"]), "4_prescriber_segments.csv")

    f = pd.read_csv(TABLES_DIR / "forecast_long.csv")
    write(f.rename(columns={"Gnrc_Name": "Molecule", "scenario": "Scenario", "claims_value": "Claims"}),
          "5_forecast.csv")


if __name__ == "__main__":
    main()
