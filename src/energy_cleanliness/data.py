
"""Data loading utilities for lifecycle electricity emissions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS: set[str] = {
    "technology",
    "group",
    "min_gco2e_kwh",
    "median_gco2e_kwh",
    "max_gco2e_kwh",
    "source",
}


def load_lifecycle_data(path: str | Path) -> pd.DataFrame:
    """Load and validate lifecycle emissions data.

    Parameters
    ----------
    path:
        CSV path containing lifecycle greenhouse-gas emissions in gCO2e/kWh.

    Returns
    -------
    pandas.DataFrame
        Validated dataframe sorted by median lifecycle emissions.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If required columns are missing or numerical ranges are invalid.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Lifecycle data file not found: {csv_path}")

    data = pd.read_csv(csv_path)
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    numeric_columns = ["min_gco2e_kwh", "median_gco2e_kwh", "max_gco2e_kwh"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")

    invalid_ranges = data[
        (data["min_gco2e_kwh"] > data["median_gco2e_kwh"])
        | (data["median_gco2e_kwh"] > data["max_gco2e_kwh"])
    ]
    if not invalid_ranges.empty:
        bad_technologies = invalid_ranges["technology"].tolist()
        raise ValueError(f"Invalid min/median/max ranges for: {bad_technologies}")

    return data.sort_values("median_gco2e_kwh").reset_index(drop=True)
