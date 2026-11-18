"""Validate the experiment, estimate its effects and export Power BI tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.stats import (
    bootstrap_difference_ci,
    compare_means,
    compare_proportions,
    holm_adjust,
    sample_ratio_p_value,
    standardized_difference,
)

CONTROL = "No E-Mail"
TREATMENTS = ["Mens E-Mail", "Womens E-Mail"]
REQUIRED = {
    "recency", "history_segment", "history", "mens", "womens", "zip_code",
    "newbie", "channel", "segment", "visit", "conversion", "spend",
}
METRICS = {"visit": "Visit rate", "conversion": "Conversion rate", "spend": "Revenue per customer"}


def load_data(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame[list(REQUIRED)].isna().any().any():
        raise ValueError("The file contains missing values")
    if set(frame["segment"]) != {CONTROL, *TREATMENTS}:
        raise ValueError(f"Unexpected segments: {sorted(frame['segment'].unique())}")
    for column in ["mens", "womens", "newbie", "visit", "conversion"]:
        if not set(frame[column].unique()) <= {0, 1}:
            raise ValueError(f"{column} must contain only 0 and 1")
    if (frame["spend"] < 0).any() or (frame["history"] < 0).any():
        raise ValueError("Money values cannot be negative")
    if ((frame["spend"] > 0) & (frame["conversion"] == 0)).any():
        raise ValueError("Spend found without a conversion")

    frame = frame.copy()
    frame.insert(0, "customer_id", np.arange(1, len(frame) + 1))
    # The source file spells this value "Surburban".
    frame["zip_code"] = frame["zip_code"].replace({"Surburban": "Suburban"})
    frame["purchase_history"] = np.select(
        [
            (frame["mens"] == 1) & (frame["womens"] == 1),
            frame["mens"] == 1,
            frame["womens"] == 1,
        ],
        ["Mens and Womens", "Mens only", "Womens only"],
        default="Neither",
    )
    frame["customer_type"] = np.where(frame["newbie"] == 1, "New customer", "Existing customer")
    return frame


def group(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    return frame[frame["segment"] == name]


def experiment_checks(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = frame["segment"].value_counts().reindex([CONTROL, *TREATMENTS])
    sample = pd.DataFrame({
        "campaign": counts.index,
        "customers": counts.values,
        "share": counts.values / counts.sum(),
        "sample_ratio_p_value": sample_ratio_p_value(counts.tolist()),
    })

    encoded = pd.concat(
        [
            frame[["segment", "recency", "history", "mens", "womens", "newbie"]],
            pd.get_dummies(frame[["zip_code", "channel"]], dtype=float),
        ],
        axis=1,
    )
    control = group(encoded, CONTROL)
    rows = []
    for treatment in TREATMENTS:
        selected = group(encoded, treatment)
        for column in encoded.columns.drop("segment"):
            rows.append({
                "campaign": treatment,
                "variable": column,
                "standardized_difference": standardized_difference(selected[column], control[column]),
            })
    return sample, pd.DataFrame(rows)


def compare(frame: pd.DataFrame, treatment: str, baseline: str, metric: str, bootstrap: bool) -> dict:
    t = group(frame, treatment)[metric]
    c = group(frame, baseline)[metric]
    result = compare_means(t, c) if metric == "spend" else compare_proportions(t, c)
    row = {
        "treatment": treatment,
        "baseline": baseline,
        "metric": METRICS[metric],
        "treatment_customers": len(t),
        "baseline_customers": len(c),
        "treatment_value": result.treatment_mean,
        "baseline_value": result.control_mean,
        "difference": result.difference,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "p_value": result.p_value,
        "relative_change": result.difference / result.control_mean if result.control_mean else np.nan,
    }
    if metric == "spend" and bootstrap:
        row["bootstrap_ci_low"], row["bootstrap_ci_high"] = bootstrap_difference_ci(t, c)
    return row


def experiment_results(frame: pd.DataFrame, bootstrap: bool = True) -> pd.DataFrame:
    pairs = [(name, CONTROL) for name in TREATMENTS] + [("Mens E-Mail", "Womens E-Mail")]
    rows = [compare(frame, t, b, metric, bootstrap) for t, b in pairs for metric in METRICS]
    results = pd.DataFrame(rows)
    results["adjusted_p_value"] = holm_adjust(results["p_value"])
    results["significant_after_adjustment"] = results["adjusted_p_value"] < 0.05
    return results


def segment_results(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dimension in ["purchase_history", "customer_type", "zip_code", "channel", "history_segment"]:
        for value, part in frame.groupby(dimension):
            for treatment in TREATMENTS:
                t = group(part, treatment)["spend"]
                c = group(part, CONTROL)["spend"]
                if len(t) < 30 or len(c) < 30:
                    continue
                result = compare_means(t, c)
                rows.append({
                    "dimension": dimension,
                    "segment_value": value,
                    "campaign": treatment,
                    "customers_in_campaign": len(t),
                    "customers_in_control": len(c),
                    "campaign_revenue_per_customer": result.treatment_mean,
                    "control_revenue_per_customer": result.control_mean,
                    "difference": result.difference,
                    "ci_low": result.ci_low,
                    "ci_high": result.ci_high,
                    "p_value": result.p_value,
                })
    output = pd.DataFrame(rows)
    output["adjusted_p_value"] = holm_adjust(output["p_value"])
    return output


def dimension(frame: pd.DataFrame, source: str, key: str, label: str) -> pd.DataFrame:
    values = sorted(frame[source].unique())
    return pd.DataFrame({key: range(1, len(values) + 1), label: values})


def export_power_bi(frame: pd.DataFrame, results, segments, sample, balance, output: Path) -> None:
    folder = output / "powerbi"
    folder.mkdir(parents=True, exist_ok=True)
    definitions = [
        ("segment", "campaign_key", "campaign", "dim_campaign"),
        ("history_segment", "history_band_key", "history_band", "dim_history_band"),
        ("zip_code", "area_key", "area_type", "dim_area"),
        ("channel", "channel_key", "channel", "dim_channel"),
        ("purchase_history", "purchase_history_key", "purchase_history", "dim_purchase_history"),
        ("customer_type", "customer_type_key", "customer_type", "dim_customer_type"),
    ]
    fact = frame[["customer_id", "recency", "history", "visit", "conversion", "spend"]].copy()
    for source, key, label, table in definitions:
        values = dimension(frame, source, key, label)
        values.to_csv(folder / f"{table}.csv", index=False)
        fact[key] = frame[source].map(dict(zip(values[label], values[key])))
    fact.to_csv(folder / "fact_customer_response.csv", index=False)
    results.to_csv(folder / "experiment_results.csv", index=False)
    segments.to_csv(folder / "segment_results.csv", index=False)
    sample.to_csv(folder / "sample_check.csv", index=False)
    balance.to_csv(folder / "balance_check.csv", index=False)


def money(value: float) -> str:
    return f"-${abs(value):.3f}" if value < 0 else f"${value:.3f}"


def percent_points(value: float) -> str:
    return f"{value * 100:+.2f} pts"


def write_report(frame, results, segments, sample, balance, output: Path) -> None:
    spend = results[(results["metric"] == METRICS["spend"]) & (results["baseline"] == CONTROL)]
    best = spend.sort_values("difference", ascending=False).iloc[0]
    head_to_head = results[(results["metric"] == METRICS["spend"]) & (results["baseline"] != CONTROL)].iloc[0]
    worst_balance = balance["standardized_difference"].abs().max()

    lines = [
        "# E-Mail Campaign Experiment Report", "",
        "## Decision summary", "",
        f"- Customers analysed: **{len(frame):,}**.",
        f"- Highest measured revenue lift: **{best['treatment']}**, {money(best['difference'])} per customer against no e-mail.",
        f"- 95% interval: {money(best['ci_low'])} to {money(best['ci_high'])}, or about "
        f"${best['ci_low'] * 1000:,.0f} to ${best['ci_high'] * 1000:,.0f} per 1,000 customers.",
        f"- Statistically clear after multiple-test adjustment: **{'yes' if best['significant_after_adjustment'] else 'no'}**.",
        f"- Mens versus Womens revenue difference is "
        f"{'clear' if head_to_head['significant_after_adjustment'] else 'not clear'} after adjustment "
        f"(adjusted p = {head_to_head['adjusted_p_value']:.4f}).", "",
        "Revenue is not profit. The data has no margin, e-mail cost, returns or long-term customer value.", "",
        "## Experiment checks", "",
        f"- Sample-ratio test p-value: {sample['sample_ratio_p_value'].iloc[0]:.4f}.",
        f"- Largest absolute standardized difference: {worst_balance:.4f}.", "",
        "## Results against no e-mail", "",
        "| Campaign | Metric | Campaign | No e-mail | Difference | 95% interval | Adjusted p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in results[results["baseline"] == CONTROL].iterrows():
        if row["metric"] == METRICS["spend"]:
            values = [money(row[c]) for c in ["treatment_value", "baseline_value", "difference", "ci_low", "ci_high"]]
        else:
            values = [f"{row['treatment_value']:.2%}", f"{row['baseline_value']:.2%}", percent_points(row["difference"]),
                      percent_points(row["ci_low"]), percent_points(row["ci_high"])]
        lines.append(
            f"| {row['treatment']} | {row['metric']} | {values[0]} | {values[1]} | {values[2]} | "
            f"{values[3]} to {values[4]} | {row['adjusted_p_value']:.4f} |"
        )
    clear_segments = segments[segments["adjusted_p_value"] < 0.05].sort_values("adjusted_p_value")
    lines += ["", "## Exploratory customer segments", "",
              f"{len(clear_segments)} of {len(segments)} segment comparisons show a clear revenue lift against "
              "no e-mail after multiple-test adjustment.",
              "These comparisons were not pre-specified. They do not prove that the lift is larger in one "
              "segment than another, so targeting needs a separate test.", ""]
    if clear_segments.empty:
        lines.append("No segment comparison remained clear after adjustment.")
    else:
        lines += ["| Dimension | Segment | Campaign | Revenue lift | 95% interval | Adjusted p |",
                  "|---|---|---|---:|---:|---:|"]
        for _, row in clear_segments.iterrows():
            lines.append(
                f"| {row['dimension']} | {row['segment_value']} | {row['campaign']} | {money(row['difference'])} | "
                f"{money(row['ci_low'])} to {money(row['ci_high'])} | {row['adjusted_p_value']:.4f} |"
            )
    lines += ["", "All segment results are in `output/powerbi/segment_results.csv`."]
    lines += ["", "## Data source", "",
              "Kevin Hillstrom, MineThatData E-Mail Analytics and Data Mining Challenge, 2008."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/hillstrom.csv"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()

    frame = load_data(args.input)
    sample, balance = experiment_checks(frame)
    results = experiment_results(frame)
    segments = segment_results(frame)
    args.output.mkdir(parents=True, exist_ok=True)
    export_power_bi(frame, results, segments, sample, balance, args.output)
    write_report(frame, results, segments, sample, balance, args.output)
    print((args.output / "REPORT.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
