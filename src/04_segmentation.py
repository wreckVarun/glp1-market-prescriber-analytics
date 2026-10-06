"""
STEP 04 - Prescriber segmentation: who should the sales force call on?

Unit: one prescriber (NPI), all GLP-1 brands combined, latest year vs prior year.

Rules (percentile tiers, no clustering, so every label is explainable in one line):
- High-value  : latest-year GLP-1 claims in the top 20% of prescribers (>= P80).
                These write most of the volume -> protect and grow share.
- Emerging    : not high-value, but claims grew >= 25% YoY, OR the prescriber is
                new in the latest year. Rising writers -> where call effort can
                still change habits.
- Low-adopter : everyone else (small and flat/declining).

Caveat to state in interviews: "new" really means "crossed the 11-claim
suppression threshold". A prescriber with 0-10 claims last year is invisible in
CMS data, so some "new" writers were already writing small volumes.

Outputs:
- outputs/tables/prescriber_segments.csv   (one row per prescriber)
- outputs/tables/segment_summary.csv        (how much volume each segment holds)
- outputs/tables/segment_by_specialty.csv, segment_by_state.csv
"""
import numpy as np
import pandas as pd

from config import EMERGING_MIN_GROWTH, HIGH_VALUE_PERCENTILE, PROCESSED_DIR, TABLES_DIR


def main():
    df = pd.read_csv(PROCESSED_DIR / "glp1_panel.csv", dtype={"Prscrbr_NPI": str})
    latest, prior = df["Year"].max(), df["Year"].max() - 1

    # Prescriber x year totals, pivoted to one row per NPI
    by_year = df.pivot_table(index="Prscrbr_NPI", columns="Year", values="Tot_Clms", aggfunc="sum", fill_value=0)
    p = pd.DataFrame({
        "claims_latest": by_year[latest],
        "claims_prior": by_year[prior] if prior in by_year else 0,
    })
    lapsed = int(((p["claims_latest"] == 0) & (p["claims_prior"] > 0)).sum())
    p = p[p["claims_latest"] > 0].copy()  # segment only active prescribers
    p["yoy_growth"] = np.where(p["claims_prior"] > 0, p["claims_latest"] / p["claims_prior"] - 1, np.nan)
    p["is_new"] = p["claims_prior"] == 0

    # Attributes: name, state, specialty (stable per NPI from step 02)
    attrs = (df[df["Year"] == latest]
             .groupby("Prscrbr_NPI")[["Prscrbr_Last_Org_Name", "Prscrbr_First_Name", "Prscrbr_City",
                                      "Prscrbr_State_Abrvtn", "Prscrbr_Type"]].first())
    p = p.join(attrs)

    # Brand mix: which brand does this prescriber write most, and the Lilly vs Novo split
    lt = df[df["Year"] == latest]
    brand_claims = lt.pivot_table(index="Prscrbr_NPI", columns="Brnd_Name", values="Tot_Clms", aggfunc="sum", fill_value=0)
    p["top_brand"] = brand_claims.idxmax(axis=1)
    mfr = lt.pivot_table(index="Prscrbr_NPI", columns="Manufacturer", values="Tot_Clms", aggfunc="sum", fill_value=0)
    for m in ["Novo Nordisk", "Eli Lilly"]:
        p[f"share_{m.split()[0].lower()}"] = (mfr.get(m, 0) / p["claims_latest"]).reindex(p.index).fillna(0)
    p["drug_cost_latest"] = lt.groupby("Prscrbr_NPI")["Tot_Drug_Cst"].sum()

    # --- Segment rules -----------------------------------------------------
    cutoff = p["claims_latest"].quantile(HIGH_VALUE_PERCENTILE)
    high = p["claims_latest"] >= cutoff
    emerging = ~high & ((p["yoy_growth"] >= EMERGING_MIN_GROWTH) | p["is_new"])
    p["segment"] = np.select([high, emerging], ["High-value", "Emerging"], default="Low-adopter")
    print(f"High-value cutoff (P{HIGH_VALUE_PERCENTILE * 100:.0f}): {cutoff:,.0f} GLP-1 claims in {latest}")
    print(f"Lapsed prescribers (wrote in {prior}, none visible in {latest}): {lapsed:,}")

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    p.reset_index().sort_values("claims_latest", ascending=False).to_csv(
        TABLES_DIR / "prescriber_segments.csv", index=False)

    # Segment summary: the classic "20% of prescribers write X% of volume" table
    summ = p.groupby("segment").agg(
        prescribers=("claims_latest", "size"),
        claims=("claims_latest", "sum"),
        median_claims=("claims_latest", "median"),
        median_yoy=("yoy_growth", "median"),
        new_prescribers=("is_new", "sum"),
    )
    summ["pct_prescribers"] = summ["prescribers"] / summ["prescribers"].sum()
    summ["pct_claims"] = summ["claims"] / summ["claims"].sum()
    summ = summ.reindex(["High-value", "Emerging", "Low-adopter"]).reset_index()
    summ.to_csv(TABLES_DIR / "segment_summary.csv", index=False)
    print(summ.to_string(index=False))

    # Where the segments sit: specialty and state
    for col, name in [("Prscrbr_Type", "specialty"), ("Prscrbr_State_Abrvtn", "state")]:
        t = p.pivot_table(index=col, columns="segment", values="claims_latest", aggfunc=["size", "sum"], fill_value=0)
        t.columns = [f"{'prescribers' if a == 'size' else 'claims'}_{b.lower().replace('-', '_')}" for a, b in t.columns]
        t["total_claims"] = t.filter(like="claims_").sum(axis=1)
        t.sort_values("total_claims", ascending=False).reset_index().to_csv(
            TABLES_DIR / f"segment_by_{name}.csv", index=False)


if __name__ == "__main__":
    main()
