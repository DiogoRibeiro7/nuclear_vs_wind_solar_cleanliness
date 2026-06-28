"""Tests for the geography / grid-context / deployment-year abatement model."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_cleanliness.geography import (
    GridDataError,
    abatement_table,
    grid_intensity,
    load_grid_intensity,
    marginal_abatement,
    trajectory_table,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRID = PROJECT_ROOT / "data" / "grid_carbon_intensity.csv"


def test_dataset_loads_and_is_sorted() -> None:
    data = load_grid_intensity(GRID)
    assert {"France", "Germany", "Portugal", "EU", "Global"} <= set(data["region"])
    assert (data["grid_gco2_kwh"] > 0).all()


def test_load_rejects_duplicate_region_year(tmp_path: Path) -> None:
    path = tmp_path / "g.csv"
    path.write_text(
        "region,year,grid_gco2_kwh,source\nX,2020,100,s\nX,2020,110,s\n", encoding="utf-8"
    )
    with pytest.raises(GridDataError):
        load_grid_intensity(path)


def test_load_rejects_non_positive(tmp_path: Path) -> None:
    path = tmp_path / "g.csv"
    path.write_text("region,year,grid_gco2_kwh,source\nX,2020,0,s\n", encoding="utf-8")
    with pytest.raises(GridDataError):
        load_grid_intensity(path)


def test_grid_intensity_exact_and_interpolated() -> None:
    data = load_grid_intensity(GRID)
    assert grid_intensity(data, "Germany", 2023) == pytest.approx(371)
    # 2021 is between 2020 (337) and 2023 (371): linear interpolation.
    mid = grid_intensity(data, "Germany", 2021)
    assert 337 < mid < 371


def test_grid_intensity_clamps_outside_range() -> None:
    data = load_grid_intensity(GRID)
    assert grid_intensity(data, "France", 1990) == grid_intensity(data, "France", 2015)
    assert grid_intensity(data, "France", 2100) == grid_intensity(data, "France", 2023)


def test_grid_intensity_unknown_region_raises() -> None:
    data = load_grid_intensity(GRID)
    with pytest.raises(KeyError):
        grid_intensity(data, "Atlantis", 2023)


def test_abatement_higher_in_dirty_grid() -> None:
    data = load_grid_intensity(GRID)
    germany = marginal_abatement(12.0, "Germany", 2023, data)
    france = marginal_abatement(12.0, "France", 2023, data)
    assert germany > france > 0


def test_abatement_negative_when_grid_cleaner_than_tech() -> None:
    data = load_grid_intensity(GRID)
    # High-carbon biomass (230) on France's clean grid (~56) has negative abatement.
    assert marginal_abatement(230.0, "France", 2023, data) < 0


def test_trajectory_first_year_is_zero_change() -> None:
    data = load_grid_intensity(GRID)
    traj = trajectory_table(data)
    firsts = traj.sort_values("year").groupby("region").first()
    assert (firsts["pct_change_from_first"] == 0).all()


def test_abatement_table_shape() -> None:
    data = load_grid_intensity(GRID)
    table = abatement_table({"Nuclear": 12.0}, ["France", "Germany"], [2015, 2023], data)
    assert len(table) == 1 * 2 * 2
    assert set(table.columns) >= {"region", "year", "technology", "abatement_gco2_kwh"}
