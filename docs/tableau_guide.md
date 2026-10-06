# Building the dashboard in Tableau Public

Time: about 45 minutes. You need Tableau Public (free desktop app) and a free Tableau Public account.
All files are in `outputs/tableau/`.

| File | One row = | Used for |
|---|---|---|
| `1_market_by_brand_year.csv` | brand x year | brand trend and share |
| `2_market_by_state.csv` | state (latest year) | US map |
| `3_market_by_specialty.csv` | specialty (latest year) | specialty bar |
| `4_prescriber_segments.csv` | prescriber (NPI) | segment view, target list |
| `5_forecast.csv` | brand x year x scenario | forecast chart (by brand or molecule) |

## 1. Connect the data (5 min)
1. Open Tableau Public. Under **Connect > To a File > Text file**, choose `1_market_by_brand_year.csv`.
2. On the Data Source page, drag the other four CSVs into the canvas one at a time. When Tableau
   tries to join them, **delete the join**. Instead, for each extra file use **Data > New Data Source**
   so each file is its own data source. (They are at different grains; joining them would double count.)
3. In each source, check the field types: `Year` should be a number (Dimension, discrete is fine), `State` should
   show a globe icon. If not, click the icon > **Geographic Role > State/Province**.
   `NPI` should be a String, not a number.

## 2. Sheet "Brand Trend" (5 min)
Source: `1_market_by_brand_year`.
1. Drag `Year` to Columns (right-click > Discrete). Drag `Claims` to Rows.
2. Drag `Brand` to Color. You get one line per brand.
3. Right-click the Claims axis > Format > Numbers > Number (Custom) > Display units: Thousands (K).
4. Title: "GLP-1 Part D claims by brand".

## 3. Sheet "Brand Share" (5 min)
Same source.
1. Drag `Brand` to Rows, `Claim Share` to Columns. Drag `Year` to Filters and pick the latest year only.
2. Sort descending (toolbar sort button). Format `Claim Share` as Percentage, 0 decimals.
3. Drag `Claim Share` to Label so each bar shows its value.

## 4. Sheet "State Map" (5 min)
Source: `2_market_by_state`.
1. Double-click `State`. Tableau draws a map.
2. Drag `Claims` to Color. Edit colors > a single-hue sequential palette (e.g. Blue).
3. Drag `Claims YoY`, `Prescribers`, `High-value Prescribers` and `Emerging Prescribers` to Tooltip.
4. Title: "Where GLP-1 volume is (latest year)".

## 5. Sheet "Specialty" (3 min)
Source: `3_market_by_specialty`.
1. `Specialty` to Rows, `Claims` to Columns, sort descending.
2. Drag `Specialty` to Filters > Top tab > By field: Top 10 by Claims.
3. `Claims per Prescriber` to Tooltip. This is the key talking point: specialists write far more per head.

## 6. Sheet "Segments" (5 min)
Source: `4_prescriber_segments`.
1. `Segment` to Columns. `Claims (latest yr)` to Rows. Right-click the pill >
   **Quick Table Calculation > Percent of Total**. This shows each segment's share of volume.
2. Drag `NPI` to Label, right-click > Measure > Count (Distinct). Now each bar also shows how many prescribers.
3. Drag `Segment` to Color and give the three segments fixed colors (Edit Colors).

## 7. Sheet "Target List" (5 min)
Same source. This is what a sales rep would actually use.
1. Rows: `Prescriber`, `Specialty`, `City`, `State`. Text (Marks card): `Claims (latest yr)`, `Claims YoY`, `Top Brand`.
2. Filters: `Segment` (show filter, single-value dropdown), `State` (show filter, multi-select dropdown).
3. Sort by `Claims (latest yr)` descending. Format `Claims YoY` as percent.

## 8. Sheet "Forecast" (5 min)
Source: `5_forecast`.
1. `Year` to Columns (discrete), `Claims` to Rows (SUM), `Scenario` to Color.
2. Drag `Brand` and `Molecule` to Filters and Show Filter on both, so the viewer can pick one brand, one molecule or all.
   Brands add up exactly to their molecule, so SUM(Claims) is correct at any level.
3. Edit colors: Actual = dark grey, Base = blue, High and Low = light blue. On the Marks card, choose Line.
   Optional: Low and High as dashed lines (Marks > Path > dashed).

## 9. Assemble the dashboard (7 min)
1. **New Dashboard**. Size: Fixed, 1200 x 900.
2. Layout suggestion:
   - Top row: Brand Trend (left), Brand Share (right).
   - Middle row: State Map (left, larger), Specialty (right).
   - Bottom row: Segments (left), Forecast (right).
   - Put Target List on a second dashboard tab (it is a table and needs width).
3. Add a Text object at the top: title "US GLP-1 Market & Prescriber Opportunity (Medicare Part D)" and a
   one-line caveat: "Source: CMS Part D Prescribers by Provider and Drug. Prescriber-drug rows with < 11 claims are suppressed. Gross cost is before rebates."
4. Click the State Map sheet on the dashboard > the funnel icon (**Use as Filter**). Clicking a state now filters the other sheets that share the State field.

## 10. Publish (2 min)
**File > Save to Tableau Public As**, sign in, name it "GLP-1 Market & Prescriber Analytics".
It opens in your browser. Copy the URL into the repo README under "Dashboard".

## Interview talking points for the dashboard
- Why separate data sources instead of one join? Different grains (brand-year vs prescriber vs state). A join would duplicate rows and inflate totals.
- Why claims, not cost, as the main metric? Cost is gross of rebates (net prices are confidential), so claims better reflect prescribing behaviour.
- What would you add with more time? Commercial claims data (Part D covers 65+ and disabled only), and payer formulary status by state.
