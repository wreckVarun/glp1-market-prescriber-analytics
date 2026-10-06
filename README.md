# US GLP-1 Market Opportunity & Prescriber Analytics

A pharma consulting-style analysis of the US GLP-1 market (semaglutide, tirzepatide, dulaglutide,
liraglutide, exenatide) built on public **CMS Medicare Part D Prescribers by Provider and Drug** data.

**Business question:** where should a GLP-1 brand team focus its sales force next year?

## What it answers
1. **Market sizing:** how big is the Part D GLP-1 market, which brands lead, and which states and specialties hold the volume?
2. **Prescriber segmentation:** which prescribers are high-value, emerging or low-adopters?
3. **Forecast:** how many claims next year under base, high and low scenarios?
4. **Recommendation:** a one-page memo for the brand team (`docs/memo.md`) and a Tableau Public dashboard.

## Key results (CMS data years 2020 to 2024)
- **Market:** 19.6M GLP-1 Part D claims and $24.6B gross drug cost in 2024 (+39% claims YoY, 4.1x 2020).
- **Brands:** Ozempic 51% of claims, Mounjaro 24% (+209% YoY), Trulicity 19% (-21%).
- **Concentration:** the top 20% of prescribers write 59% of claims; primary care (FP, IM, NP, PA) writes 82%.
- **2025 forecast:** 27.5M claims base case (25.6M low, 29.5M high).
- **Recommendation:** see the brand-team memo, [`docs/memo.md`](docs/memo.md).

![Forecast](outputs/charts/06_forecast.png)

## Pipeline
| Step | Script | Output |
|---|---|---|
| 1 | `src/01_download.py` | GLP-1 rows per year pulled from the CMS Data API (`data/raw/`) |
| 2 | `src/02_clean.py` | one cleaned prescriber x brand x year panel |
| 3 | `src/03_market_sizing.py` | brand, molecule, state, specialty tables |
| 4 | `src/04_segmentation.py` | prescriber segments + segment summaries |
| 5 | `src/05_forecast.py` | next-year base / high / low forecast |
| 6 | `src/06_charts.py` | Matplotlib charts (`outputs/charts/`) |
| 7 | `src/07_tableau_extracts.py` | dashboard-ready CSVs (`outputs/tableau/`) |

All thresholds and assumptions live in `src/config.py`.

```bash
pip install -r requirements.txt
python run_all.py            # downloads real CMS data, then runs every step
python run_all.py --sample   # synthetic data with the CMS layout, for testing without internet
```

## Methods (deliberately simple and explainable)
- **Sizing:** `groupby` sums of claims and gross drug cost.
- **Segmentation:** percentile tiers. High-value = top 20% by latest-year claims; Emerging = mid-volume (P50 to P80) and growing faster than the market, or new; Low-adopter = rest.
- **Forecast:** base case = the lower of 3-year CAGR and latest YoY per molecule (launch brand: repeat last absolute gain), +/- 10 points of growth for high/low, with a linear-trend cross-check.

Full reasoning, assumptions and weaknesses: [`docs/methodology.md`](docs/methodology.md).

## Key caveats
- **Medicare only** (65+ and disabled); commercial patients are not included.
- **~2-year CMS lag:** the latest year is the newest CMS has published.
- **Rows with < 11 claims are suppressed** for privacy, so totals are slight undercounts.
- **Weight-loss-only use is not covered by Part D**, so Wegovy/Zepbound volume is small; this is mainly a type 2 diabetes view.
- **Drug cost is gross, before rebates.** It is not manufacturer revenue.
- **Mounjaro launched mid-2022**, so its trend rests on very few data points.

## Dashboard
Build guide: [`docs/tableau_guide.md`](docs/tableau_guide.md). Tableau Public link: _to be added_.

## Tools
Python (pandas, NumPy, Matplotlib), Tableau Public.
