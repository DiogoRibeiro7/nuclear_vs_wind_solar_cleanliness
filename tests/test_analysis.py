
"""Tests for the energy cleanliness analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from energy_cleanliness.analysis import (
    compare_to_baseline,
    estimate_pairwise_probabilities,
    simulate_uncertainty,
)
from energy_cleanliness.data import load_lifecycle_data
from energy_cleanliness.claim_classifier import classify_claim

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
    # The diagonal (self-comparison) is NaN by design; check only the off-diagonal
    # probabilities, independent of how pandas .stack() treats NaN across versions.
    values = matrix.to_numpy(dtype=float)
    values = values[~np.isnan(values)]
    assert values.size > 0
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


def test_classifier_covers_english_and_portuguese_claims() -> None:
    """Short PT/EN examples should map to the required five classifier labels."""
    en_cases = [
        ("Nuclear has 12 gCO2e/kWh lifecycle emissions.", "factual_and_testable"),
        ("Nuclear is cleaner than wind.", "ambiguous because of undefined metrics"),
        ("This claim is always better and never worse than everything else.", "overconfident because uncertainty is ignored"),
        ("This is a myth: nuclear is the only clean option.", "misleading framing"),
        ("Nuclear is the future of clean energy.", "unsupported by cited data"),
    ]
    pt_cases = [
        ("Nuclear tem 12 gCO2e/kWh no ciclo de vida.", "factual_and_testable"),
        ("Nuclear é mais limpo que solar.", "ambiguous because of undefined metrics"),
        ("A energia nuclear será sempre a melhor e nunca pior.", "overconfident because uncertainty is ignored"),
        ("O mito diz que nuclear é a opção perfeita e sem falhas.", "misleading framing"),
        ("Energia nuclear é a solução definitiva para o país.", "unsupported by cited data"),
    ]

    for text, expected_label in en_cases:
        result = classify_claim(text)
        assert result.label == expected_label

    for text, expected_label in pt_cases:
        result = classify_claim(text)
        assert result.label == expected_label
