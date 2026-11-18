import numpy as np
import pandas as pd
import pytest
from scipy import stats

from analysis.run_analysis import (
    CONTROL,
    TREATMENTS,
    experiment_checks,
    experiment_results,
    export_power_bi,
    load_data,
    segment_results,
    write_report,
)
from analysis.stats import compare_means, compare_proportions, holm_adjust, sample_ratio_p_value


def synthetic_csv(path, per_group=1500):
    rng = np.random.default_rng(1)
    rows = []
    for name, visit_rate, conversion_rate, value in [
        (CONTROL, 0.10, 0.02, 80), (TREATMENTS[0], 0.18, 0.05, 100), (TREATMENTS[1], 0.14, 0.03, 90),
    ]:
        visit = rng.binomial(1, visit_rate, per_group)
        conversion = rng.binomial(1, conversion_rate, per_group)
        rows.append(pd.DataFrame({
            "recency": rng.integers(1, 13, per_group),
            "history_segment": rng.choice(["1) $0 - $100", "2) $100 - $200"], per_group),
            "history": rng.uniform(30, 300, per_group),
            "mens": 1,
            "womens": rng.integers(0, 2, per_group),
            "zip_code": rng.choice(["Urban", "Surburban", "Rural"], per_group),
            "newbie": rng.integers(0, 2, per_group),
            "channel": rng.choice(["Web", "Phone"], per_group),
            "segment": name,
            "visit": np.maximum(visit, conversion),
            "conversion": conversion,
            "spend": conversion * rng.gamma(4, value / 4, per_group),
        }))
    frame = pd.concat(rows).sample(frac=1, random_state=1)
    frame.to_csv(path, index=False)
    return frame


def test_proportion_test_matches_chi_square():
    t = [1] * 120 + [0] * 880
    c = [1] * 90 + [0] * 910
    result = compare_proportions(t, c)
    expected = stats.chi2_contingency([[120, 880], [90, 910]], correction=False).pvalue
    assert result.p_value == pytest.approx(expected)
    assert result.difference == pytest.approx(0.03)


def test_welch_comparison_matches_scipy():
    rng = np.random.default_rng(2)
    a, b = rng.normal(2, 3, 500), rng.normal(1, 1, 800)
    result = compare_means(a, b)
    assert result.p_value == pytest.approx(stats.ttest_ind(a, b, equal_var=False).pvalue)
    assert result.ci_low < result.difference < result.ci_high


def test_holm_adjustment():
    assert holm_adjust([0.01, 0.04, 0.03]).tolist() == pytest.approx([0.03, 0.06, 0.06])


def test_sample_ratio_detects_imbalance():
    assert sample_ratio_p_value([1000, 1002, 998]) > 0.9
    assert sample_ratio_p_value([1200, 1000, 800]) < 0.001


def test_pipeline_outputs_connect(tmp_path):
    path = tmp_path / "input.csv"
    synthetic_csv(path)
    frame = load_data(path)
    assert "Surburban" not in set(frame["zip_code"])
    sample, balance = experiment_checks(frame)
    results = experiment_results(frame, bootstrap=False)
    segments = segment_results(frame)
    assert len(results) == 9
    assert results.loc[0, "difference"] > 0
    assert results["adjusted_p_value"].ge(results["p_value"]).all()

    export_power_bi(frame, results, segments, sample, balance, tmp_path)
    write_report(frame, results, segments, sample, balance, tmp_path)
    folder = tmp_path / "powerbi"
    fact = pd.read_csv(folder / "fact_customer_response.csv")
    assert len(fact) == len(frame) and fact["customer_id"].is_unique
    for table, key in [("dim_campaign", "campaign_key"), ("dim_area", "area_key"), ("dim_channel", "channel_key")]:
        dim = pd.read_csv(folder / f"{table}.csv")
        assert dim[key].is_unique and set(fact[key]) <= set(dim[key])
    report = (tmp_path / "REPORT.md").read_text(encoding="utf-8")
    assert "Revenue is not profit" in report
    assert f"of {len(segments)} segment comparisons" in report
    assert "do not prove" in report


@pytest.mark.parametrize("change", [{"visit": 2}, {"spend": -1}, {"segment": "Other"}])
def test_invalid_data_is_rejected(tmp_path, change):
    path = tmp_path / "input.csv"
    frame = synthetic_csv(path, 40)
    for column, value in change.items():
        frame.iloc[0, frame.columns.get_loc(column)] = value
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_data(path)
