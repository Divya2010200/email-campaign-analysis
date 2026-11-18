"""Statistical helpers for a randomised experiment."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

Z_95 = stats.norm.ppf(0.975)


@dataclass(frozen=True)
class Comparison:
    treatment_mean: float
    control_mean: float
    difference: float
    ci_low: float
    ci_high: float
    p_value: float


def sample_ratio_p_value(counts: list[int]) -> float:
    """Test whether groups meant to be equal differ more than chance suggests."""
    return float(stats.chisquare(counts).pvalue)


def compare_proportions(treatment, control) -> Comparison:
    t = np.asarray(treatment, dtype=float)
    c = np.asarray(control, dtype=float)
    p_t, p_c = t.mean(), c.mean()
    difference = p_t - p_c
    pooled = (t.sum() + c.sum()) / (len(t) + len(c))
    test_se = np.sqrt(pooled * (1 - pooled) * (1 / len(t) + 1 / len(c)))
    p_value = 1.0 if test_se == 0 else 2 * stats.norm.sf(abs(difference / test_se))
    interval_se = np.sqrt(p_t * (1 - p_t) / len(t) + p_c * (1 - p_c) / len(c))
    return Comparison(
        float(p_t), float(p_c), float(difference),
        float(difference - Z_95 * interval_se), float(difference + Z_95 * interval_se),
        float(p_value),
    )


def compare_means(treatment, control) -> Comparison:
    t = np.asarray(treatment, dtype=float)
    c = np.asarray(control, dtype=float)
    difference = t.mean() - c.mean()
    variance_t = t.var(ddof=1) / len(t)
    variance_c = c.var(ddof=1) / len(c)
    se = np.sqrt(variance_t + variance_c)
    freedom = (variance_t + variance_c) ** 2 / (
        variance_t**2 / (len(t) - 1) + variance_c**2 / (len(c) - 1)
    )
    critical = stats.t.ppf(0.975, freedom)
    p_value = stats.ttest_ind(t, c, equal_var=False).pvalue
    return Comparison(
        float(t.mean()), float(c.mean()), float(difference),
        float(difference - critical * se), float(difference + critical * se),
        float(p_value),
    )


def bootstrap_difference_ci(treatment, control, samples=2000, batch=100, seed=7):
    """Percentile interval, useful because spend is mostly zeros with a long tail."""
    t = np.asarray(treatment, dtype=float)
    c = np.asarray(control, dtype=float)
    rng = np.random.default_rng(seed)
    differences = []
    for start in range(0, samples, batch):
        size = min(batch, samples - start)
        t_means = rng.choice(t, (size, len(t))).mean(axis=1)
        c_means = rng.choice(c, (size, len(c))).mean(axis=1)
        differences.append(t_means - c_means)
    low, high = np.percentile(np.concatenate(differences), [2.5, 97.5])
    return float(low), float(high)


def holm_adjust(p_values) -> np.ndarray:
    """Holm correction, which controls false positives across several tests."""
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty(len(p))
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[index]))
        adjusted[index] = running
    return adjusted


def standardized_difference(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    spread = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return 0.0 if spread == 0 else float((a.mean() - b.mean()) / spread)
