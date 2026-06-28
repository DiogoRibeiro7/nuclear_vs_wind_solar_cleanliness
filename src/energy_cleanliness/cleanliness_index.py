"""Multi-metric cleanliness index calculations."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def minmax_normalize(values: pd.Series) -> pd.Series:
    """Min-max normalization in [0, 1], returning NaN-safe output."""
    values = pd.to_numeric(values, errors="coerce")
    denominator = float(values.max() - values.min())
    if denominator == 0:
        return pd.Series(0.5, index=values.index)
    return (values - values.min()) / denominator


def zscore_normalize(values: pd.Series) -> pd.Series:
    """z-score normalization."""
    values = pd.to_numeric(values, errors="coerce")
    denominator = float(values.std(ddof=0))
    if denominator == 0 or pd.isna(denominator):
        return pd.Series(0.0, index=values.index)
    return (values - values.mean()) / denominator


def normalize_cleanliness_matrix(
    data: pd.DataFrame,
    metrics: Iterable[str],
    method: str = "minmax",
    higher_is_better: Iterable[str] = (),
) -> pd.DataFrame:
    """Normalize a set of metrics into a cleaner-is-higher score."""
    matrix = pd.DataFrame(index=data.index)
    norm_fn = minmax_normalize if method == "minmax" else zscore_normalize
    higher_set = set(higher_is_better)
    for metric in metrics:
        if metric not in data.columns:
            raise ValueError(f"Missing metric column: {metric}")

        normalized = norm_fn(data[metric])
        if method == "zscore":
            axis_max = float(normalized.abs().max())
            normalized = normalized / axis_max if axis_max else normalized
            matrix[metric] = normalized if metric in higher_set else -normalized
            continue
        matrix[metric] = normalized if metric in higher_set else 1.0 - normalized
    return matrix


def weighted_cleanliness_score(
    data: pd.DataFrame,
    metrics: Iterable[str],
    weights: dict[str, float] | None = None,
    method: str = "minmax",
    higher_is_better: Iterable[str] = (),
) -> pd.DataFrame:
    """Compute user-weighted cleanliness scores from multiple metrics."""
    normalized = normalize_cleanliness_matrix(
        data, metrics, method=method, higher_is_better=higher_is_better
    )
    if weights is None:
        weight_value = 1.0 / len(normalized.columns)
        weights = {column: weight_value for column in normalized.columns}

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Weights must sum to a positive value.")

    normalized_weights = {k: v / total_weight for k, v in weights.items()}
    result = data[["technology"]].copy()
    result["cleanliness_score"] = 0.0
    for metric, weight in normalized_weights.items():
        if metric not in normalized.columns:
            continue
        result["cleanliness_score"] += weight * normalized[metric]
    return result.sort_values("cleanliness_score", ascending=False).reset_index(drop=True)


def pareto_frontier(
    data: pd.DataFrame,
    metrics: Iterable[str],
    minimize: bool = True,
    higher_is_better: Iterable[str] = (),
) -> pd.DataFrame:
    """Return rows on the Pareto frontier for the selected metrics."""
    scores = data[list(metrics)].apply(pd.to_numeric, errors="coerce")
    higher_set = set(higher_is_better)
    frontier_indices = []
    for i, row in scores.iterrows():
        candidates = scores.copy()
        if minimize:
            better_or_equal = (candidates <= row).all(axis=1)
            strictly_better = (candidates < row).any(axis=1)
        else:
            # metrics in higher_set are treated as "larger is cleaner"
            better_or_equal = np.ones(len(candidates), dtype=bool)
            strictly_better = np.zeros(len(candidates), dtype=bool)
            for metric in metrics:
                candidate_values = candidates[metric]
                row_value = row[metric]
                if metric in higher_set:
                    better_or_equal = better_or_equal & (candidate_values >= row_value)
                    strictly_better = strictly_better | (candidate_values > row_value)
                else:
                    better_or_equal = better_or_equal & (candidate_values <= row_value)
                    strictly_better = strictly_better | (candidate_values < row_value)
            strictly_better = strictly_better & better_or_equal
        improved = better_or_equal & strictly_better
        if not improved.any():
            frontier_indices.append(i)
    return data.loc[frontier_indices].copy().reset_index(drop=True)


def _normalize_weights(weights: dict[str, float], metrics: list[str]) -> "np.ndarray":
    """Return a weight vector aligned to ``metrics``, renormalised to sum to one."""
    raw = np.array([float(weights.get(metric, 0.0)) for metric in metrics], dtype=float)
    if (raw < 0).any():
        raise ValueError("Weights must be non-negative.")
    total = raw.sum()
    if total <= 0:
        raise ValueError("Weights must sum to a positive value.")
    return raw / total


def monte_carlo_cleanliness(
    profile: pd.DataFrame,
    weights: dict[str, float] | None = None,
    samples: int = 2_000,
    seed: int = 42,
    top_k: tuple[int, ...] = (1, 2, 3),
) -> dict[str, pd.DataFrame]:
    """Propagate per-metric uncertainty through the weighted cleanliness score.

    ``profile`` is a validated long dataframe (see :mod:`energy_cleanliness.multimetric`)
    with ``low/central/high`` columns and a ``direction`` per metric. Each Monte Carlo
    draw samples every cell from ``triangular(low, central, high)``, min-max normalises
    each metric within the draw into a cleaner-is-higher score, applies the weights and
    sums. Returns score summary statistics and rank-stability diagnostics.
    """
    if samples <= 0:
        raise ValueError("samples must be a positive integer")

    technologies = sorted(profile["technology"].unique())
    metrics = sorted(profile["metric"].unique())
    higher = {
        metric
        for metric, direction in profile.drop_duplicates("metric")
        .set_index("metric")["direction"]
        .items()
        if direction == "higher_better"
    }

    n_tech, n_metric = len(technologies), len(metrics)
    indexed = profile.set_index(["technology", "metric"])
    low = np.empty((n_tech, n_metric))
    central = np.empty((n_tech, n_metric))
    high = np.empty((n_tech, n_metric))
    for t, tech in enumerate(technologies):
        for m, metric in enumerate(metrics):
            row = indexed.loc[(tech, metric)]
            low[t, m] = float(row["low"])
            central[t, m] = float(row["central"])
            high[t, m] = float(row["high"])

    rng = np.random.default_rng(seed)
    sampled = np.empty((samples, n_tech, n_metric))
    for t in range(n_tech):
        for m in range(n_metric):
            lo, mode, hi = low[t, m], central[t, m], high[t, m]
            if hi <= lo:
                sampled[:, t, m] = mode
            else:
                sampled[:, t, m] = rng.triangular(lo, min(max(mode, lo), hi), hi, size=samples)

    # Min-max normalise per (draw, metric) across technologies, cleaner-is-higher.
    mn = sampled.min(axis=1, keepdims=True)
    mx = sampled.max(axis=1, keepdims=True)
    span = mx - mn
    with np.errstate(invalid="ignore", divide="ignore"):
        norm = np.where(span == 0, 0.5, (sampled - mn) / span)
    lower_mask = np.array([metric not in higher for metric in metrics])
    cleaner = norm.copy()
    cleaner[:, :, lower_mask] = np.where(
        span[:, :, lower_mask] == 0, 0.5, 1.0 - norm[:, :, lower_mask]
    )

    if weights is None:
        weights = dict.fromkeys(metrics, 1.0)
    weight_vector = _normalize_weights(weights, metrics)
    scores = cleaner @ weight_vector  # (samples, n_tech)

    # Ranks: rank 1 = highest score within each draw.
    order = np.argsort(-scores, axis=1)
    ranks = np.empty_like(order)
    rows = np.arange(samples)[:, None]
    ranks[rows, order] = np.arange(n_tech)[None, :] + 1  # 1-based rank per technology

    summary = pd.DataFrame(
        {
            "technology": technologies,
            "mean_score": scores.mean(axis=0),
            "std_score": scores.std(axis=0, ddof=0),
            "ci_low": np.quantile(scores, 0.025, axis=0),
            "ci_high": np.quantile(scores, 0.975, axis=0),
        }
    ).sort_values("mean_score", ascending=False).reset_index(drop=True)

    stability = {"technology": technologies, "mean_rank": ranks.mean(axis=0)}
    for k in top_k:
        stability[f"p_top{k}"] = (ranks <= k).mean(axis=0)
    rank_stability = (
        pd.DataFrame(stability)
        .sort_values("p_top1" if "p_top1" in stability else "mean_rank", ascending=False)
        .reset_index(drop=True)
    )

    return {"score_summary": summary, "rank_stability": rank_stability}


def sensitivity_analysis(
    data: pd.DataFrame,
    metrics: Iterable[str],
    method: str = "minmax",
    samples: int = 1_000,
    seed: int = 42,
    higher_is_better: Iterable[str] = (),
) -> pd.DataFrame:
    """Monte Carlo weight perturbation over user-defined weights."""
    rng = np.random.default_rng(seed)
    technologies = data["technology"].tolist()
    samples_matrix = []

    normalized = normalize_cleanliness_matrix(
        data, metrics, method=method, higher_is_better=higher_is_better
    )
    metric_columns = list(normalized.columns)
    n_metrics = len(metric_columns)

    for _ in range(samples):
        draw = rng.random(n_metrics)
        weights = draw / draw.sum()
        score = normalized.mul(weights, axis=1).sum(axis=1)
        row = {technologies[i]: float(score.iloc[i]) for i in range(len(technologies))}
        samples_matrix.append(row)

    if not samples_matrix:
        return pd.DataFrame(columns=["technology", "mean_score", "std_score"])

    scores = pd.DataFrame(samples_matrix)
    return (
        scores.agg(["mean", "std"])
        .T.reset_index()
        .rename(columns={"index": "technology", "mean": "mean_score", "std": "std_score"})
    )
