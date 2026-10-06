"""
STEP 05 - Next-year demand forecast with base / high / low scenarios.

Method (bottom-up by molecule, then summed):
1. For each molecule, compute two growth rates:
       CAGR       = (claims_latest / claims_3_years_earlier) ** (1/3) - 1
       latest YoY = claims_latest / claims_prior_year - 1
   Base growth = the LOWER of the two. CAGR smooths one-off jumps, but when growth
   is slowing (semaglutide: 3-yr CAGR 78% vs latest YoY 52%) or turning negative
   (Trulicity: CAGR +5% vs latest -21%), the CAGR overstates next year. Taking the
   lower rate is the conservative choice a brand team would ask for.
2. Short-history rule: if a molecule has fewer than 4 years of data (tirzepatide /
   Mounjaro launched mid-2022), % growth is launch ramp (+208% in 2024) and cannot
   repeat. Instead, next year adds the SAME NUMBER of claims it added last year
   (a straight-line ramp), so % growth falls naturally as the base grows.
3. Scenarios = base growth +/- 10 percentage points.
   High: shortages fully resolved, more cardiometabolic coverage (e.g. Wegovy CV indication).
   Low : prior-auth tightening, payer pushback, share loss to oral/new entrants.
4. Next-year claims = latest claims x (1 + scenario growth).
5. Gross cost = claims x latest cost per claim (ASSUMPTION: flat price; ignores
   IRA negotiated prices, which start for semaglutide in 2027).
6. Cross-check: a straight-line (linear trend) fit on the same years. If CAGR and
   linear differ a lot, growth is accelerating or decelerating; mention it.
7. Brand view: each molecule's forecast is split across its brands by their
   latest-year share of that molecule (semaglutide -> Ozempic / Rybelsus / Wegovy).
   ASSUMPTION: share within a molecule holds for one year. Brands compete mainly
   across molecules (Ozempic vs Mounjaro), and that shift is already in the
   molecule growth rates.

Note on timing: the "next year" is the data year after the latest CMS year. Because
CMS lags ~2 years, that year may already be over in real life; it is still the
right test of the method, and the logic rolls forward when new data drops.
"""
import numpy as np
import pandas as pd

from config import CAGR_LOOKBACK_YEARS, PROCESSED_DIR, SCENARIO_SPREAD_PP, TABLES_DIR


def molecule_forecast(series):
    """series: claims indexed by year for one molecule (only years with claims)."""
    years = series.index.to_numpy()
    latest_year, latest = years[-1], series.iloc[-1]
    n_steps = len(series) - 1

    if n_steps >= CAGR_LOOKBACK_YEARS:
        start = series.iloc[-1 - CAGR_LOOKBACK_YEARS]
        cagr = (latest / start) ** (1 / CAGR_LOOKBACK_YEARS) - 1
        yoy = latest / series.iloc[-2] - 1
        base_g = min(cagr, yoy)
        method = f"{CAGR_LOOKBACK_YEARS}-yr CAGR" if cagr <= yoy else "latest YoY (slowing)"
    elif n_steps >= 1:
        base_g = (latest - series.iloc[-2]) / latest  # repeat last year's absolute gain
        method = "repeat last absolute gain (launch brand)"
    else:
        base_g, method = 0.0, "single year: held flat"

    # Linear-trend cross-check on the same window
    window = series.iloc[-(CAGR_LOOKBACK_YEARS + 1):]
    if len(window) >= 2:
        slope, intercept = np.polyfit(window.index, window.values, 1)
        linear_next = max(slope * (latest_year + 1) + intercept, 0)
    else:
        linear_next = latest

    return {
        "latest_year": latest_year,
        "claims_latest": latest,
        "years_of_data": len(series),
        "base_growth": base_g,
        "growth_method": method,
        "linear_trend_next": linear_next,
    }


def main():
    df = pd.read_csv(PROCESSED_DIR / "glp1_panel.csv", dtype={"Prscrbr_NPI": str})
    latest = df["Year"].max()
    by_mol = df.groupby(["Gnrc_Name", "Year"]).agg(claims=("Tot_Clms", "sum"), cost=("Tot_Drug_Cst", "sum"))

    rows = []
    for mol, g in by_mol.groupby(level=0):
        g = g.droplevel(0)
        if latest not in g.index:
            continue  # molecule no longer on the market
        r = molecule_forecast(g["claims"])
        r["Gnrc_Name"] = mol
        r["cost_per_claim"] = g.loc[latest, "cost"] / g.loc[latest, "claims"]
        rows.append(r)
    f = pd.DataFrame(rows)

    scen = {"low": -SCENARIO_SPREAD_PP, "base": 0.0, "high": SCENARIO_SPREAD_PP}
    for name, delta in scen.items():
        f[f"growth_{name}"] = (f["base_growth"] + delta).clip(lower=-0.9)
        f[f"claims_{name}"] = f["claims_latest"] * (1 + f[f"growth_{name}"])
        f[f"cost_{name}"] = f[f"claims_{name}"] * f["cost_per_claim"]
    f["forecast_year"] = latest + 1

    total = f[[c for c in f.columns if c.startswith(("claims_", "cost_", "linear_"))]].sum()
    total["Gnrc_Name"] = "TOTAL GLP-1"
    total["latest_year"], total["forecast_year"] = latest, latest + 1
    total["cost_per_claim"] = (f["claims_latest"] * f["cost_per_claim"]).sum() / f["claims_latest"].sum()
    for name in scen:
        total[f"growth_{name}"] = total[f"claims_{name}"] / total["claims_latest"] - 1
    f = pd.concat([f, total.to_frame().T], ignore_index=True)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    f.to_csv(TABLES_DIR / "forecast_next_year.csv", index=False)

    # Long format (history + forecast) for charts and Tableau
    hist = by_mol.reset_index().rename(columns={"claims": "claims_value"})
    hist["scenario"] = "Actual"
    fc = f[f["Gnrc_Name"] != "TOTAL GLP-1"].melt(
        id_vars=["Gnrc_Name", "forecast_year"], value_vars=["claims_low", "claims_base", "claims_high"],
        var_name="scenario", value_name="claims_value")
    fc["scenario"] = fc["scenario"].str.replace("claims_", "").str.title()
    fc = fc.rename(columns={"forecast_year": "Year"})
    pd.concat([hist[["Gnrc_Name", "Year", "scenario", "claims_value"]], fc], ignore_index=True) \
      .to_csv(TABLES_DIR / "forecast_long.csv", index=False)

    # Brand view: split each molecule's scenarios by latest-year brand share
    by_brand = df.groupby(["Brnd_Name", "Gnrc_Name", "Year"]).agg(
        claims=("Tot_Clms", "sum"), cost=("Tot_Drug_Cst", "sum")).reset_index()
    b = by_brand[by_brand["Year"] == latest].copy()
    b["share_of_molecule"] = b["claims"] / b.groupby("Gnrc_Name")["claims"].transform("sum")
    b["cost_per_claim"] = b["cost"] / b["claims"]
    b = b.merge(f[["Gnrc_Name", "growth_method", "claims_low", "claims_base", "claims_high"]],
                on="Gnrc_Name", suffixes=("", "_molecule"))
    for name in scen:
        b[f"claims_{name}"] = b[f"claims_{name}"] * b["share_of_molecule"]
        b[f"cost_{name}"] = b[f"claims_{name}"] * b["cost_per_claim"]
        b[f"growth_{name}"] = b[f"claims_{name}"] / b["claims"] - 1
    b["forecast_year"] = latest + 1
    b = b.rename(columns={"claims": "claims_latest"}).drop(columns=["Year", "cost"]) \
         .sort_values("claims_base", ascending=False)
    b.to_csv(TABLES_DIR / "forecast_by_brand.csv", index=False)

    # Brand long format (history + forecast) for Tableau
    bh = by_brand.rename(columns={"claims": "claims_value"})
    bh["scenario"] = "Actual"
    bf = b.melt(id_vars=["Brnd_Name", "Gnrc_Name", "forecast_year"],
                value_vars=["claims_low", "claims_base", "claims_high"],
                var_name="scenario", value_name="claims_value")
    bf["scenario"] = bf["scenario"].str.replace("claims_", "").str.title()
    bf = bf.rename(columns={"forecast_year": "Year"})
    pd.concat([bh[["Brnd_Name", "Gnrc_Name", "Year", "scenario", "claims_value"]], bf], ignore_index=True) \
      .to_csv(TABLES_DIR / "forecast_brand_long.csv", index=False)

    show = f[["Gnrc_Name", "years_of_data", "growth_method", "claims_latest",
              "growth_low", "growth_base", "growth_high", "claims_base", "linear_trend_next"]]
    with pd.option_context("display.float_format", "{:,.3f}".format, "display.width", 200):
        print(show.to_string(index=False))
        print("\nBy brand:")
        print(b[["Brnd_Name", "Gnrc_Name", "share_of_molecule", "claims_latest",
                 "claims_low", "claims_base", "claims_high"]].to_string(index=False))


if __name__ == "__main__":
    main()
