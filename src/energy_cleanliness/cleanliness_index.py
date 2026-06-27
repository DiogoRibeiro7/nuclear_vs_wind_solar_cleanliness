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
    normalized = normalize_cleanliness_matrix(data, metrics, method=method, higher_is_better=higher_is_better)
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
    scores = pd.to_numeric(data[metrics], errors="coerce")
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

    normalized = normalize_cleanliness_matrix(data, metrics, method=method, higher_is_better=higher_is_better)
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
