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
- Brand names standardised in case.
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
| Emerging | Below P80, but YoY growth of 25% or more, or new this year | Habits still forming: highest return on extra calls |
| Low-adopter | Everyone else | Low priority: non-personal promotion (email, digital) |

**Why percentiles, not clustering:** a brand manager can apply "top 20% by volume" in Excel; a k-means cluster cannot be explained in one sentence. The 80/20 split is the industry-standard decile approach in simplified form.
**Why 25% for emerging:** clearly above the market's own growth in most years, so it flags prescribers growing faster than the tide. It is a judgement call; the threshold sits in `config.py` and the result is easy to sensitivity test.
**Weaknesses:** two years only; growth from a small base is noisy (11 to 15 claims is +36%); suppression creates false "new" writers.

## 6. Forecast (`05_forecast.py`)
Bottom-up by molecule, then summed.

- **Base growth** = 3-year CAGR of claims: `(claims_latest / claims_3yrs_ago)^(1/3) - 1`. CAGR smooths one-off shocks such as the 2022-2024 semaglutide and tirzepatide shortages.
- **Short-history rule:** molecules with fewer than 4 years of data (tirzepatide) use latest YoY growth x 0.5, because launch-ramp growth (often +100% or more) cannot continue. The 0.5 is an explicit judgement.
- **Scenarios:** high and low = base plus or minus 10 percentage points of growth.
  - High drivers: supply fully restored, wider cardiovascular and kidney coverage (Wegovy CV, Ozempic CKD indication), more primary-care adoption.
  - Low drivers: tighter prior authorisation by Part D plans, budget pressure, share shift to new entrants or orals.
- **Cost** = forecast claims x latest cost per claim (flat price). Medicare's negotiated price for semaglutide starts in 2027, so a 2027+ forecast must cut price.
- **Cross-check:** a linear trend on the same years. If linear is well below CAGR, growth is decelerating and the base case may be optimistic.

**Why not ARIMA or machine learning:** 4 to 6 annual data points cannot support them, and the client needs to understand and challenge the assumptions. Scenario ranges are more honest than a single precise number.

## 7. Where to focus sales effort: logic used in the memo
1. Concentration: the high-value segment's share of volume shows how far a targeted call plan reaches.
2. Specialty: claims per prescriber identifies where each call buys the most volume (typically endocrinology); total claims identifies where the volume actually is (typically primary care, internal medicine and nurse practitioners).
3. Geography: rank states by volume AND by growth; big-and-growing states get extra reps.
4. Emerging prescribers are the upside list.
