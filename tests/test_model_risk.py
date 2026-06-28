"""Tests for the shared model-risk caveats and their use in reports."""

from __future__ import annotations

import pandas as pd
import pytest

from energy_cleanliness.analysis import build_markdown_summary
from energy_cleanliness.model_risk import (
    GENERAL_RISKS,
    model_risk_markdown,
)


def test_contexts_render_heading_and_general_risks() -> None:
    for context in ("general", "carbon", "multimetric", "region"):
        text = model_risk_markdown(context=context)
        assert "## Model risk and limitations" in text
        # General risks appear in every context.
        for risk in GENERAL_RISKS:
            assert risk in text


def test_unknown_context_raises() -> None:
    with pytest.raises(ValueError):
        model_risk_markdown(context="nonsense")


def test_heading_level_is_configurable() -> None:
    assert model_risk_markdown(context="general", level=3).startswith("### ")


def test_region_context_adds_region_specific_risk() -> None:
    text = model_risk_markdown(context="region")
    assert "conserve total generation" in text
    # A multimetric-only caveat should not leak into the region context.
    assert "Min-max normalization" not in text


def test_carbon_summary_includes_model_risk() -> None:
    data = pd.DataFrame(
        {
            "technology": ["Nuclear", "Wind onshore", "Wind offshore"],
            "min_gco2e_kwh": [3.7, 7.0, 8.0],
            "median_gco2e_kwh": [12.0, 11.0, 12.0],
            "max_gco2e_kwh": [110.0, 56.0, 35.0],
        }
    )
    comparison = pd.DataFrame(
        {"technology": ["Wind onshore"], "baseline_minus_other": [1.0]}
    )
    matrix = pd.DataFrame(
        [[float("nan"), 0.5], [0.5, float("nan")]],
        index=["Nuclear", "Wind onshore"],
        columns=["Nuclear", "Wind onshore"],
    )
    summary = build_markdown_summary(data, comparison, matrix, baseline="Nuclear")
    assert "## Model risk and limitations" in summary
