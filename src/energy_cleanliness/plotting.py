
"""Plotting utilities for lifecycle emissions analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


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
