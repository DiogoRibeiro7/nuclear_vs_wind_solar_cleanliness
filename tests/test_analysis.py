
"""Tests for the energy cleanliness analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from energy_cleanliness.analysis import (
    compare_to_baseline,
    estimate_pairwise_probabilities,
    simulate_uncertainty,
)
from energy_cleanliness.data import load_lifecycle_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"


def test_load_lifecycle_data_returns_expected_columns() -> None:
    """The seed dataset should load with the required columns."""
    data = load_lifecycle_data(DATA_PATH)
    assert "technology" in data.columns
    assert "median_gco2e_kwh" in data.columns
    assert not data.empty


def test_onshore_wind_has_lower_median_than_nuclear() -> None:
    """This is the direct falsification of the broad social-media claim."""
    data = load_lifecycle_data(DATA_PATH)
    nuclear = float(data.loc[data["technology"] == "Nuclear", "median_gco2e_kwh"].iloc[0])
    wind_onshore = float(data.loc[data["technology"] == "Wind onshore", "median_gco2e_kwh"].iloc[0])
    assert wind_onshore < nuclear


def test_compare_to_baseline_identifies_wind_onshore() -> None:
    """The comparison output should identify wind onshore as lower than nuclear."""
    data = load_lifecycle_data(DATA_PATH)
    comparison = compare_to_baseline(data, baseline="Nuclear")
    row = comparison.loc[comparison["technology"] == "Wind onshore"].iloc[0]
    assert row["baseline_minus_other"] > 0


def test_probability_matrix_is_bounded() -> None:
    """Pairwise probabilities should be between zero and one."""
    data = load_lifecycle_data(DATA_PATH)
    samples = simulate_uncertainty(data, draws=1_000, seed=7)
    matrix = estimate_pairwise_probabilities(samples)
    values = matrix.stack().to_numpy(dtype=float)
    assert ((values >= 0) & (values <= 1)).all()


def test_simulate_uncertainty_rejects_non_positive_draws() -> None:
    """The simulation function should validate the number of draws."""
    data = pd.DataFrame(
        {
            "technology": ["A"],
            "min_gco2e_kwh": [1],
            "median_gco2e_kwh": [2],
            "max_gco2e_kwh": [3],
        }
    )
    try:
        simulate_uncertainty(data, draws=0)
    except ValueError as error:
        assert "draws" in str(error)
    else:
        raise AssertionError("Expected ValueError for non-positive draws")
