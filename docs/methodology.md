# Methodology, assumptions and caveats

Written so every choice can be defended in a case interview. Each section: what we did, why, and the honest weakness.

## 1. Data source
**What:** CMS "Medicare Part D Prescribers - by Provider and Drug", one file per year. One row = one prescriber (NPI) x one drug x one year, with total claims, 30-day fills, days' supply, gross drug cost and beneficiaries.

**Why this dataset:** it is the only free, national, prescriber-level prescription dataset in the US. Commercial equivalents (IQVIA, Symphony) cost six figures, which is exactly what consulting firms buy, so this is a realistic proxy.

**Caveats (say these before the interviewer does):**
- **Medicare only.** Part D covers people 65+ and some disabled people, about 50M+ enrollees. Younger, commercially insured patients, where obesity GLP-1 use is largest, are not in this data.
- **Data lag.** CMS publishes each year's data about 1.5 to 2 years later. The latest year here is the newest CMS has released, not this year.
- **Suppression under 11.** Any prescriber-drug row with fewer than 11 claims is removed for privacy. Totals are therefore slightly understated, and "new prescriber" really means "crossed 11 claims". Beneficiary counts under 11 are blanked, so beneficiary totals are lower bounds.
- **Obesity drugs are mostly excluded by law.** Part D cannot cover drugs used for weight loss alone, so Wegovy and Zepbound appear only through other covered uses (Wegovy's cardiovascular indication from March 2024). Saxenda is essentially absent. This is a type 2 diabetes plus cardiovascular market view.
- **Gross cost, not revenue.** `Tot_Drug_Cst` is before manufacturer rebates, which are large for GLP-1s. Never call it revenue.
- **Mounjaro has a short history.** Launched mid-2022, so it has at most a partial first year. Its growth is launch ramp, not a stable trend.

## 2. Scope
GLP-1 = generic names semaglutide (Ozempic, Rybelsus, Wegovy), tirzepatide (Mounjaro, technically GIP/GLP-1), dulaglutide (Trulicity), liraglutide (Victoza), exenatide (Byetta, Bydureon BCise). Filtered by generic name so every brand of a molecule is caught.
**Assumption:** insulin combination products (Xultophy, Soliqua) are excluded because they are sold as insulins.

## 3. Cleaning (`02_clean.py`)
- Text numbers to numeric; suppressed values stay blank, never zero.
- Brand names standardised in case, and pack or device variants merged (Victoza 2-Pak and 3-Pak into Victoza; Bydureon Pen into Bydureon).
- CMS lists Bydureon's generic as "Exenatide Microspheres"; it is downloaded separately (the API filter is an exact match) and mapped to the exenatide molecule. Without this, Bydureon would be silently missing.
- "Liraglutide" as a brand name is unbranded generic liraglutide, launched in 2024, labelled "Generic Liraglutide".
- Each prescriber gets one state and one specialty: the latest year's. Otherwise a doctor who moved would be split across two states.

## 4. Market sizing (`03_market_sizing.py`)
Simple sums with `groupby`: claims, gross cost, distinct prescribers, by brand x year, molecule x year, state and specialty. Share = brand claims / total GLP-1 claims that year.
**Why claims as the headline metric:** it measures prescribing behaviour, which is what a sales force can influence. Cost is distorted by list price and rebates.
**Weakness:** state totals reflect where the prescriber practises, not where the patient lives, and are not adjusted for each state's Medicare population.

## 5. Prescriber segmentation (`04_segmentation.py`)
All GLP-1 claims per prescriber, latest year vs prior year.

| Segment | Rule | Sales meaning |
|---|---|---|
| High-value | Latest-year claims at or above the 80th percentile | A small group writing most of the volume: defend and grow share |
| Emerging | Between P50 and P80 by volume, AND growing faster than the total market (or new this year) | Habits still forming and enough volume to matter: highest return on extra calls |
| Low-adopter | Everyone else | Low priority: non-personal promotion (email, digital) |

**Why percentiles, not clustering:** a brand manager can apply "top 20% by volume" in Excel; a k-means cluster cannot be explained in one sentence. The 80/20 split is the industry-standard decile approach in simplified form.
**Why "faster than the market" for emerging:** the first version used a fixed +25% bar. On real data the market grew 39% in 2024, so +25% labelled 56% of all prescribers "emerging", which is not a target list. Benchmarking against the market's own growth flags prescribers gaining ground faster than the tide. The P50 volume floor removes tiny writers whose growth is noise (11 to 15 claims is +36%).
**Weaknesses:** two years only; growth from a small base is noisy (11 to 15 claims is +36%); suppression creates false "new" writers.

## 6. Forecast (`05_forecast.py`)
Bottom-up by molecule, then summed.

- **Base growth** = the lower of the 3-year CAGR, `(claims_latest / claims_3yrs_ago)^(1/3) - 1`, and the latest YoY growth. CAGR smooths shocks such as the 2022-2024 shortages, but a market that is slowing down makes CAGR too optimistic: semaglutide's CAGR is 78% while its latest YoY is 52%, and Trulicity's CAGR is +5% while it actually fell 21% in 2024. Taking the lower rate is the conservative, defensible choice.
- **Short-history rule:** tirzepatide (Mounjaro, launched mid-2022) has only 3 data years and grew +208% in 2024, which is launch ramp. The forecast assumes it adds the same number of claims next year as it added last year (a straight-line ramp), so percentage growth slows naturally as the base grows. No arbitrary damping factor is needed.
- **Scenarios:** high and low = base plus or minus 10 percentage points of growth.
  - High drivers: supply fully restored, wider cardiovascular and kidney coverage (Wegovy CV, Ozempic CKD indication), more primary-care adoption.
  - Low drivers: tighter prior authorisation by Part D plans, budget pressure, share shift to new entrants or orals.
- **Cost** = forecast claims x latest cost per claim (flat price). Medicare's negotiated price for semaglutide starts in 2027, so a 2027+ forecast must cut price.
- **Cross-check:** a linear trend on the same years, reported next to the base case. If the two differ a lot, say why.

**Why not ARIMA or machine learning:** 4 to 6 annual data points cannot support them, and the client needs to understand and challenge the assumptions. Scenario ranges are more honest than a single precise number.

## 7. Where to focus sales effort: logic used in the memo
1. Concentration: the high-value segment's share of volume shows how far a targeted call plan reaches.
2. Specialty: claims per prescriber identifies where each call buys the most volume (typically endocrinology); total claims identifies where the volume actually is (typically primary care, internal medicine and nurse practitioners).
3. Geography: rank states by volume AND by growth; big-and-growing states get extra reps.
4. Emerging prescribers are the upside list.
