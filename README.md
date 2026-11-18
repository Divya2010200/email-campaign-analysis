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
