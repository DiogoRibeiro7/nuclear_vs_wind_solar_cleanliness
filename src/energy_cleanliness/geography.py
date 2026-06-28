"""Geography-, grid-context- and deployment-year-aware emissions analysis.

A clean generator's *value* is not its lifecycle intensity alone but how much carbon it
avoids relative to the grid it displaces. That depends on three things:

- **geography** -- France's grid is already very clean, Germany's much dirtier;
- **grid context** -- what the new generation actually displaces (the grid average here);
- **deployment year** -- grids decarbonise over time, shrinking the marginal benefit.

This module loads a region x year grid carbon-intensity dataset and computes the marginal
carbon abatement (gCO2/kWh avoided) of deploying a clean technology in a given region and
year: ``abatement = grid_intensity(region, year) - technology_lifecycle_intensity``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: list[str] = ["region", "year", "grid_gco2_kwh", "source"]


class GridDataError(ValueError):
    """Raised when the grid carbon-intensity dataset is malformed."""


def load_grid_intensity(path: str | Path) -> pd.DataFrame:
    """Load and validate the region x year grid carbon-intensity dataset."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Grid intensity dataset not found: {csv_path}")
    data = pd.read_csv(csv_path)

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise GridDataError(f"Missing required columns: {missing}")

    data = data[REQUIRED_COLUMNS].copy()
    data["region"] = data["region"].astype(str).str.strip()
    data["source"] = data["source"].astype(str).str.strip()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data["grid_gco2_kwh"] = pd.to_numeric(data["grid_gco2_kwh"], errors="coerce")
    if data[["year", "grid_gco2_kwh"]].isna().to_numpy().any():
        raise GridDataError("Non-numeric year or grid_gco2_kwh value.")
    if (data["grid_gco2_kwh"] <= 0).any():
        raise GridDataError("grid_gco2_kwh values must be positive.")
    if data.duplicated(subset=["region", "year"]).any():
        raise GridDataError("Duplicate (region, year) rows in grid intensity dataset.")

    return data.sort_values(["region", "year"]).reset_index(drop=True)


def regions(data: pd.DataFrame) -> list[str]:
    """Return the sorted list of regions present in the dataset."""
    return sorted(data["region"].unique())


def grid_intensity(data: pd.DataFrame, region: str, year: int | float) -> float:
    """Grid carbon intensity (gCO2/kWh) for a region and year.

    Exact-year values are returned directly; intermediate years are linearly
    interpolated; years outside the data range are clamped to the nearest endpoint.
    """
    region_rows = data[data["region"] == region].sort_values("year")
    if region_rows.empty:
        raise KeyError(f"Region not found in grid dataset: {region!r}")
    years = region_rows["year"].to_numpy(dtype=float)
    values = region_rows["grid_gco2_kwh"].to_numpy(dtype=float)
    return float(np.interp(float(year), years, values))


def marginal_abatement(
    technology_lifecycle_gco2_kwh: float,
    region: str,
    year: int | float,
    data: pd.DataFrame,
) -> float:
    """Carbon avoided (gCO2/kWh) by displacing average grid generation with a clean tech.

    Can be negative if the grid is already cleaner than the technology's lifecycle
    intensity (e.g. high-carbon biomass on France's low-carbon grid).
    """
    return grid_intensity(data, region, year) - float(technology_lifecycle_gco2_kwh)


def trajectory_table(data: pd.DataFrame) -> pd.DataFrame:
    """Per-region grid-intensity trajectory with percent change from the first year."""
    rows = []
    for region in regions(data):
        region_rows = data[data["region"] == region].sort_values("year")
        baseline = float(region_rows["grid_gco2_kwh"].iloc[0])
        for _, row in region_rows.iterrows():
            value = float(row["grid_gco2_kwh"])
            rows.append(
                {
                    "region": region,
                    "year": int(row["year"]),
                    "grid_gco2_kwh": value,
                    "pct_change_from_first": round((value - baseline) / baseline * 100.0, 1),
                }
            )
    return pd.DataFrame(rows)


def abatement_table(
    technologies: dict[str, float],
    region_list: list[str],
    years: list[int],
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Marginal abatement for each (region, year, technology) combination."""
    rows = []
    for region in region_list:
        for year in years:
            grid = grid_intensity(data, region, year)
            for name, lifecycle in technologies.items():
                rows.append(
                    {
                        "region": region,
                        "year": int(year),
                        "grid_gco2_kwh": round(grid, 1),
                        "technology": name,
                        "lifecycle_gco2_kwh": float(lifecycle),
                        "abatement_gco2_kwh": round(grid - float(lifecycle), 1),
                    }
                )
    return pd.DataFrame(rows)
