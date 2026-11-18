# Power BI Dashboard Guide

Build this after `python -m analysis.run_analysis` has created `output/powerbi`.

## 1. Load the tables

In Power BI Desktop, choose **Get data > Text/CSV**, then load every CSV in `output/powerbi`.

Check these types in **Transform data**:

- Whole number: all `*_key` columns, `customer_id`, `visit`, `conversion`, `recency`
- Decimal or Fixed decimal: `history`, `spend`, and result values such as `difference`
- True/False: `significant_after_adjustment`

## 2. Create relationships

In **Model view**, connect each dimension to `fact_customer_response`, one-to-many, with single-direction filtering:

| Dimension | Column | Fact column |
|---|---|---|
| `dim_campaign` | `campaign_key` | `campaign_key` |
| `dim_history_band` | `history_band_key` | `history_band_key` |
| `dim_area` | `area_key` | `area_key` |
| `dim_channel` | `channel_key` | `channel_key` |
| `dim_purchase_history` | `purchase_history_key` | `purchase_history_key` |
| `dim_customer_type` | `customer_type_key` | `customer_type_key` |

Leave `experiment_results`, `segment_results`, `sample_check` and `balance_check` unconnected.

## 3. Add DAX measures

Create these in `fact_customer_response`:

```dax
Customers = COUNTROWS(fact_customer_response)

Visits = SUM(fact_customer_response[visit])

Visit Rate = DIVIDE([Visits], [Customers])

Conversions = SUM(fact_customer_response[conversion])

Conversion Rate = DIVIDE([Conversions], [Customers])

Revenue = SUM(fact_customer_response[spend])

Revenue per Customer = DIVIDE([Revenue], [Customers])

Control Revenue per Customer =
CALCULATE(
    [Revenue per Customer],
    REMOVEFILTERS(dim_campaign),
    dim_campaign[campaign] = "No E-Mail"
)

Revenue Lift per Customer = [Revenue per Customer] - [Control Revenue per Customer]

Incremental Revenue per 1,000 = [Revenue Lift per Customer] * 1000

Control Visit Rate =
CALCULATE(
    [Visit Rate],
    REMOVEFILTERS(dim_campaign),
    dim_campaign[campaign] = "No E-Mail"
)

Visit Rate Lift = [Visit Rate] - [Control Visit Rate]
```

Format the rates as percentages and money measures as US dollars.

## 4. Build three pages

**Executive summary**

- Cards: Customers, Visit Rate, Conversion Rate, Revenue per Customer
- Clustered columns: Revenue per Customer by campaign
- Clustered columns: Incremental Revenue per 1,000 by campaign, excluding No E-Mail
- Text box: your recommendation from `output/REPORT.md`

**Experiment evidence**

- Table from `experiment_results`: treatment, baseline, metric, treatment value, baseline value, difference, interval, adjusted p-value
- Tables from `sample_check` and `balance_check`
- Note that the groups were randomised

**Customer segments**

- Slicers: area type, channel, customer type, purchase history, history band
- Matrix: campaign by history band, showing Revenue Lift per Customer
- Table from `segment_results`
- Label this page **Exploratory**

## 5. Save your work

Save as `email_campaign_dashboard.pbix`, and export a screenshot of each page to `images/`.
