"""
STEP 03 - Market sizing: how big is the Medicare Part D GLP-1 market, and where is it?

Metrics (all are simple groupby sums):
- Claims (Tot_Clms)      -> volume. Best measure of prescribing activity.
- Drug cost (Tot_Drug_Cst) -> gross spend at list-ish price, BEFORE manufacturer
  rebates. Overstates net revenue; say "gross Part D spend", never "revenue".
- Prescribers            -> count of distinct NPIs writing >= 11 claims of the brand.
- Share of claims        -> brand claims / total GLP-1 claims in that year.

Cuts: by brand x year, by molecule x year, by state (latest year, with YoY growth),
by specialty (latest year).
"""
import pandas as pd

from config import NON_STATE_CODES, PROCESSED_DIR, TABLES_DIR


def summarise(df, by):
    out = df.groupby(by).agg(
        claims=("Tot_Clms", "sum"),
        drug_cost=("Tot_Drug_Cst", "sum"),
        prescribers=("Prscrbr_NPI", "nunique"),
        benes_lower_bound=("Tot_Benes", "sum"),
    ).reset_index()
    out["cost_per_claim"] = out["drug_cost"] / out["claims"]
    return out


def add_share_and_growth(table, group_col):
    """Share of claims within a year, and YoY claim growth within a group."""
    table = table.sort_values([group_col, "Year"])
    table["claim_share"] = table["claims"] / table.groupby("Year")["claims"].transform("sum")
    table["claims_yoy"] = table.groupby(group_col)["claims"].pct_change()
    return table


def main():
    df = pd.read_csv(PROCESSED_DIR / "glp1_panel.csv", dtype={"Prscrbr_NPI": str})
    latest, prior = df["Year"].max(), df["Year"].max() - 1
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Total market by year
    total = summarise(df, ["Year"])
    total["claims_yoy"] = total["claims"].pct_change()
    total["cost_yoy"] = total["drug_cost"].pct_change()
    total.to_csv(TABLES_DIR / "market_total_by_year.csv", index=False)

    # 2) Brand and molecule by year
    brand = add_share_and_growth(summarise(df, ["Year", "Brnd_Name", "Gnrc_Name", "Manufacturer"]), "Brnd_Name")
    brand.to_csv(TABLES_DIR / "market_by_brand_year.csv", index=False)
    molecule = add_share_and_growth(summarise(df, ["Year", "Gnrc_Name"]), "Gnrc_Name")
    molecule.to_csv(TABLES_DIR / "market_by_molecule_year.csv", index=False)

    # 3) State: latest year, plus growth vs prior year
    states = df[~df["Prscrbr_State_Abrvtn"].isin(NON_STATE_CODES)]
    st = summarise(states[states["Year"] == latest], ["Prscrbr_State_Abrvtn"])
    st_prior = states[states["Year"] == prior].groupby("Prscrbr_State_Abrvtn")["Tot_Clms"].sum()
    st["claims_prior"] = st["Prscrbr_State_Abrvtn"].map(st_prior)
    st["claims_yoy"] = st["claims"] / st["claims_prior"] - 1
    st["claims_per_prescriber"] = st["claims"] / st["prescribers"]
    st["claim_share"] = st["claims"] / st["claims"].sum()
    st.sort_values("claims", ascending=False).to_csv(TABLES_DIR / "market_by_state.csv", index=False)

    # 4) Specialty: latest year
    sp = summarise(df[df["Year"] == latest], ["Prscrbr_Type"])
    sp["claims_per_prescriber"] = sp["claims"] / sp["prescribers"]
    sp["claim_share"] = sp["claims"] / sp["claims"].sum()
    sp.sort_values("claims", ascending=False).to_csv(TABLES_DIR / "market_by_specialty.csv", index=False)

    # Console summary
    t = total.set_index("Year")
    print(f"GLP-1 Part D claims {t.index.min()}-{latest}: "
          f"{t['claims'].iloc[0]:,.0f} -> {t['claims'].iloc[-1]:,.0f}")
    print(f"Gross drug cost {latest}: ${t.loc[latest, 'drug_cost'] / 1e9:,.2f}B")
    print("\nLatest-year brand share:")
    print(brand[brand["Year"] == latest].sort_values("claims", ascending=False)
          [["Brnd_Name", "claims", "claim_share", "claims_yoy"]].to_string(index=False))
    print("\nTop 5 states:\n", st.nlargest(5, "claims")[["Prscrbr_State_Abrvtn", "claims", "claims_yoy"]].to_string(index=False))
    print("\nTop 5 specialties:\n", sp.nlargest(5, "claims")[["Prscrbr_Type", "claims", "claims_per_prescriber"]].to_string(index=False))


if __name__ == "__main__":
    main()
