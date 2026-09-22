# Power BI dashboard guide

Power BI reads the results the web app logs. The finished `.pbix` file has to be built in
Power BI Desktop, so this guide gives you every step, measure and visual to reproduce it in
about 20 minutes.

## 1. Load the data

1. Run the app and analyse some components, then open `http://127.0.0.1:5000/export/records.csv`
   (or click **Download CSV for Power BI** on the dashboard page) and save the file.
   No real analyses yet? Use `powerbi/ewaste_sample_records.csv` (150 synthetic rows).
2. In Power BI Desktop: **Home > Get data > Text/CSV**, pick the file, then **Transform data**.
3. Set column types: `date` = Date, `damage_severity`, `condition_confidence`,
   `detection_confidence`, `certainty` = Decimal number, `estimated_value_inr`,
   `value_low_inr`, `value_high_inr`, `id`, `is_sample` = Whole number.
4. Rename the query to `records` and choose **Close & Apply**.

## 2. Measures (Modeling > New measure)

```DAX
Total Items          = COUNTROWS(records)
Total Recovery Value = SUM(records[estimated_value_inr])
Avg Value per Item   = DIVIDE([Total Recovery Value], [Total Items])
Avg Certainty        = AVERAGE(records[certainty])

Reusable Items  = CALCULATE([Total Items], records[decision] = "Potentially reusable")
Repairable Items = CALCULATE([Total Items], records[decision] = "Potentially repairable")
Recycle Items   = CALCULATE([Total Items], records[decision] = "Recycle / material recovery")
Testing Items   = CALCULATE([Total Items], records[decision] = "Needs further testing")

Reuse Rate        = DIVIDE([Reusable Items], [Total Items])
Recycle Rate      = DIVIDE([Recycle Items], [Total Items])
Damaged Share     = DIVIDE(CALCULATE([Total Items], records[condition] <> "No visible damage"), [Total Items])
Value Range Low   = SUM(records[value_low_inr])
Value Range High  = SUM(records[value_high_inr])
```

Format `Total Recovery Value`, `Avg Value per Item`, `Value Range Low` and `Value Range High` as
currency (Rupee), and the rate measures as percentages.

## 3. Report pages

**Page 1: Overview**
- Cards: Total Items, Total Recovery Value, Reuse Rate, Avg Certainty.
- Donut chart: Legend = `decision`, Values = Total Items.
- Line chart: Axis = `date`, Values = Total Recovery Value.
- Slicers: `component`, `date`, `is_sample` (set `is_sample` to 0 to show only real analyses).

**Page 2: Components and condition**
- Clustered bar: Axis = `component`, Values = Total Items.
- Stacked column: Axis = `condition`, Legend = `component`, Values = Total Items.
- Matrix: Rows = `component`, Columns = `decision`, Values = Total Items (turn on conditional formatting).

**Page 3: Recovery value**
- Bar chart: Axis = `component`, Values = Total Recovery Value.
- Clustered column: Axis = `decision`, Values = Avg Value per Item.
- Scatter: X = `damage_severity`, Y = `estimated_value_inr`, Legend = `component`
  (shows that more damage lowers recoverable value).

**Page 4: Detail**
- Table: `id`, `date`, `component`, `condition`, `damage_found`, `decision`, `certainty`, `estimated_value_inr`.

## 4. Suggested colours (match the web app)

| Decision | Colour |
| --- | --- |
| Potentially reusable | `#1B6B43` |
| Potentially repairable | `#8F6410` |
| Recycle / material recovery | `#2F5D8A` |
| Needs further testing | `#65479B` |

## 5. Refreshing

Export a fresh CSV (or save it to the same path each time) and press **Refresh**. If you keep the
CSV in a fixed folder, Power BI Desktop refreshes from it without any re-mapping.

> The sample CSV is synthetic. Label it as sample data in your report and do not present it as
> results from real photos.
