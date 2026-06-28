
"""Plotting utilities for lifecycle emissions analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

# These helpers only ever save figures to disk, so use the non-interactive Agg backend.
# This avoids depending on a GUI toolkit (Tk/Qt), which makes the functions robust in
# headless CI and on machines with a broken interactive backend. force=False preserves an
# already-active backend (e.g. a notebook's inline backend), so interactive use is unaffected.
matplotlib.use("Agg", force=False)

import matplotlib.pyplot as plt  # noqa: E402 - backend must be selected before importing pyplot


def plot_lifecycle_ranges(data: pd.DataFrame, output_path: str | Path) -> Path:
    """Create a horizontal range plot for lifecycle emissions.

    Parameters
    ----------
    data:
        Lifecycle emissions dataframe.
    output_path:
        Destination image path.

    Returns
    -------
    pathlib.Path
        Path to the written figure.
    """
    required = {"technology", "min_gco2e_kwh", "median_gco2e_kwh", "max_gco2e_kwh"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    plot_data = data.sort_values("median_gco2e_kwh", ascending=True).reset_index(drop=True)
    y_positions = range(len(plot_data))
    lower_error = plot_data["median_gco2e_kwh"] - plot_data["min_gco2e_kwh"]
    upper_error = plot_data["max_gco2e_kwh"] - plot_data["median_gco2e_kwh"]

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.errorbar(
        plot_data["median_gco2e_kwh"],
        list(y_positions),
        xerr=[lower_error, upper_error],
        fmt="o",
        capsize=4,
    )
    axis.set_yticks(list(y_positions))
    axis.set_yticklabels(plot_data["technology"])
    axis.set_xlabel("Lifecycle emissions, gCO2e/kWh")
    axis.set_title("Lifecycle greenhouse-gas emissions: min / median / max")
    axis.grid(axis="x", alpha=0.3)
    figure.tight_layout()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)
    return destination


def plot_scenario_scores(
    score_summary: pd.DataFrame,
    output_path: str | Path,
    title: str = "Cleanliness score with 95% credible interval",
) -> Path:
    """Plot per-technology Monte Carlo scores with 95% CI error bars.

    ``score_summary`` is the ``score_summary`` frame returned by
    :func:`energy_cleanliness.cleanliness_index.monte_carlo_cleanliness`.
    """
    required = {"technology", "mean_score", "ci_low", "ci_high"}
    missing = required.difference(score_summary.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    plot_data = score_summary.sort_values("mean_score", ascending=True).reset_index(drop=True)
    y_positions = range(len(plot_data))
    lower_error = (plot_data["mean_score"] - plot_data["ci_low"]).clip(lower=0)
    upper_error = (plot_data["ci_high"] - plot_data["mean_score"]).clip(lower=0)

    figure, axis = plt.subplots(figsize=(9, 5))
    axis.barh(list(y_positions), plot_data["mean_score"], color="#4c72b0", alpha=0.55)
    axis.errorbar(
        plot_data["mean_score"],
        list(y_positions),
        xerr=[lower_error, upper_error],
        fmt="o",
        color="#1f1f1f",
        capsize=4,
    )
    axis.set_yticks(list(y_positions))
    axis.set_yticklabels(plot_data["technology"])
    axis.set_xlabel("Cleanliness score (0–1, higher is cleaner)")
    axis.set_xlim(0, 1)
    axis.set_title(title)
    axis.grid(axis="x", alpha=0.3)
    figure.tight_layout()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)
    return destination


def plot_rank_stability(
    rank_stability: pd.DataFrame,
    output_path: str | Path,
    title: str = "Rank stability across Monte Carlo draws",
) -> Path:
    """Plot P(rank 1) and P(top 3) per technology as grouped horizontal bars.

    ``rank_stability`` is the ``rank_stability`` frame returned by
    :func:`energy_cleanliness.cleanliness_index.monte_carlo_cleanliness`.
    """
    if "technology" not in rank_stability.columns or "p_top1" not in rank_stability.columns:
        raise ValueError("rank_stability must contain 'technology' and 'p_top1' columns.")

    plot_data = rank_stability.sort_values("p_top1", ascending=True).reset_index(drop=True)
    positions = range(len(plot_data))
    height = 0.4

    figure, axis = plt.subplots(figsize=(9, 5))
    axis.barh(
        [p + height / 2 for p in positions],
        plot_data["p_top1"],
        height=height,
        label="P(rank 1)",
        color="#dd8452",
    )
    if "p_top3" in plot_data.columns:
        axis.barh(
            [p - height / 2 for p in positions],
            plot_data["p_top3"],
            height=height,
            label="P(top 3)",
            color="#55a868",
        )
    axis.set_yticks(list(positions))
    axis.set_yticklabels(plot_data["technology"])
    axis.set_xlabel("Probability across draws")
    axis.set_xlim(0, 1)
    axis.set_title(title)
    axis.legend(loc="lower right")
    axis.grid(axis="x", alpha=0.3)
    figure.tight_layout()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)
    return destination


def plot_probability_matrix(probability_matrix: pd.DataFrame, output_path: str | Path) -> Path:
    """Create a probability matrix plot for P(row technology < column technology)."""
    matrix = probability_matrix.copy()
    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(matrix.fillna(0.5).to_numpy(dtype=float), vmin=0, vmax=1)
    axis.set_xticks(range(len(matrix.columns)))
    axis.set_yticks(range(len(matrix.index)))
    axis.set_xticklabels(matrix.columns, rotation=45, ha="right")
    axis.set_yticklabels(matrix.index)
    axis.set_title("Proxy probability: row has lower lifecycle emissions than column")

    for row_index, row_name in enumerate(matrix.index):
        for col_index, col_name in enumerate(matrix.columns):
            value = matrix.loc[row_name, col_name]
            label = "—" if pd.isna(value) else f"{value:.2f}"
            axis.text(col_index, row_index, label, ha="center", va="center")

    figure.colorbar(image, ax=axis, label="P(row < column)")
    figure.tight_layout()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
    plt.close(figure)
    return destination
