# E-Mail Campaign Experiment Analysis

An end-to-end analysis of a randomised e-mail marketing experiment, with statistical testing and a Power BI dashboard.

## Business question

Should the retailer send the Mens e-mail, the Womens e-mail, or no e-mail, and which customers should be tested next?

## What it does

- Validates the source data
- Checks sample balance and covariate balance
- Estimates effects on visits, conversions and revenue with 95% intervals
- Adjusts for multiple comparisons using the Holm method
- Explores customer segments without treating them as proof
- Exports a star schema for Power BI

## Results

The 64,000 customers were randomly assigned in nearly equal groups, and balance checks passed.

| Compared with no e-mail | Mens e-mail | Womens e-mail |
|---|---:|---:|
| Visit rate | +7.66 points | +4.52 points |
| Conversion rate | +0.68 points | +0.31 points |
| Revenue per customer | +$0.77 | +$0.42 |

The Mens e-mail produced the highest revenue and also beat the Womens e-mail after multiple-test adjustment. For short-term revenue, it is the recommended option, subject to margin and send-cost data. Segment results are exploratory.

The dashboard is available in [`docs/email_campaign_dashboard.pdf`](docs/email_campaign_dashboard.pdf).

## Run it

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m analysis.download
.venv\Scripts\python -m analysis.run_analysis
```

Results are written to `output/REPORT.md`, and dashboard tables to `output/powerbi`. See `POWERBI_GUIDE.md`.

## Limitations

The data has revenue but not margin, send costs, returns or long-term value, and outcomes cover two weeks.

## Data

[Kevin Hillstrom's MineThatData E-Mail Analytics and Data Mining Challenge](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html). The raw file is downloaded by the script and isn't stored in this repository.
