"""Regression tests for the multi-metric cleanliness pipeline.

Covers schema validation, score directionality (higher-is-better vs lower-is-better),
Pareto behavior, Monte Carlo determinism, rank-stability diagnostics, scenario
rankings and the structured JSON report.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from energy_cleanliness.cleanliness_index import (
    monte_carlo_cleanliness,
    pareto_frontier,
    weighted_cleanliness_score,
)
from energy_cleanliness.multimetric import (
    EXPECTED_TECHNOLOGIES,
    METRIC_UNITS,
    SchemaValidationError,
    higher_is_better_set,
    load_multimetric_profile,
    to_wide,
    validate_multimetric_profile,
)
from energy_cleanliness.dashboard import build_dashboard_html
from energy_cleanliness.reporting import build_report, validate_report
from energy_cleanliness.scenarios import SCENARIOS, get_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = PROJECT_ROOT / "data" / "multimetric_cleanliness_reference.csv"
FIXTURE_TINY = Path(__file__).resolve().parent / "fixtures" / "multimetric_tiny.csv"


# --------------------------------------------------------------------------- schema


def test_reference_profile_validates() -> None:
    profile = load_multimetric_profile(REFERENCE)
    # Every expected technology carries every known metric exactly once.
    assert len(profile) == len(EXPECTED_TECHNOLOGIES) * len(METRIC_UNITS)
    assert (profile["low"] <= profile["central"]).all()
    assert (profile["central"] <= profile["high"]).all()


def test_beccs_has_net_negative_carbon() -> None:
    profile = load_multimetric_profile(REFERENCE)
    beccs = profile[
        (profile["technology"] == "Biomass with CCS") & (profile["metric"] == "lifecycle_co2e")
    ]
    assert float(beccs["central"].iloc[0]) < 0  # carbon-removal technology


def _valid_rows() -> pd.DataFrame:
    return load_multimetric_profile(REFERENCE)


def test_validation_rejects_unsupported_version() -> None:
    profile = _valid_rows()
    profile.loc[0, "schema_version"] = "9.9"
    with pytest.raises(SchemaValidationError):
        validate_multimetric_profile(profile)


def test_validation_rejects_bad_direction() -> None:
    profile = _valid_rows()
    profile.loc[0, "direction"] = "sideways"
    with pytest.raises(SchemaValidationError):
        validate_multimetric_profile(profile)


def test_validation_rejects_out_of_order_range() -> None:
    profile = _valid_rows()
    profile.loc[0, "low"] = profile.loc[0, "high"] + 1
    with pytest.raises(SchemaValidationError):
        validate_multimetric_profile(profile)


def test_validation_rejects_missing_cell() -> None:
    profile = _valid_rows().iloc[1:].copy()  # drop one (technology, metric) cell
    with pytest.raises(SchemaValidationError):
        validate_multimetric_profile(profile)


def test_validation_rejects_wrong_unit() -> None:
    profile = _valid_rows()
    profile.loc[0, "unit"] = "wrong_unit"
    with pytest.raises(SchemaValidationError):
        validate_multimetric_profile(profile)


# --------------------------------------------------------------- score directionality


def test_lower_is_better_metric_ranks_smaller_value_higher() -> None:
    data = pd.DataFrame({"technology": ["A", "B"], "cost": [10.0, 20.0]})
    scores = weighted_cleanliness_score(data, metrics=["cost"], higher_is_better=())
    assert scores.iloc[0]["technology"] == "A"  # lower cost is cleaner


def test_higher_is_better_metric_ranks_larger_value_higher() -> None:
    data = pd.DataFrame({"technology": ["A", "B"], "uptime": [0.3, 0.9]})
    scores = weighted_cleanliness_score(
        data, metrics=["uptime"], higher_is_better=("uptime",)
    )
    assert scores.iloc[0]["technology"] == "B"  # higher uptime is cleaner


def test_pareto_respects_metric_direction() -> None:
    # B dominates: lower cost AND higher uptime than A; C is dominated by B too.
    data = pd.DataFrame(
        {
            "technology": ["A", "B", "C"],
            "cost": [20.0, 10.0, 30.0],
            "uptime": [0.5, 0.9, 0.4],
        }
    )
    frontier = pareto_frontier(
        data, metrics=["cost", "uptime"], minimize=False, higher_is_better=("uptime",)
    )
    assert "B" in set(frontier["technology"])
    assert "C" not in set(frontier["technology"])


# ------------------------------------------------------------------- monte carlo


def test_monte_carlo_is_deterministic_with_seed() -> None:
    profile = load_multimetric_profile(REFERENCE)
    a = monte_carlo_cleanliness(profile, samples=300, seed=7)
    b = monte_carlo_cleanliness(profile, samples=300, seed=7)
    pd.testing.assert_frame_equal(a["score_summary"], b["score_summary"])


def test_rank_stability_probabilities_are_bounded_and_consistent() -> None:
    profile = load_multimetric_profile(REFERENCE)
    out = monte_carlo_cleanliness(profile, samples=500, seed=1)
    stability = out["rank_stability"]
    for column in ("p_top1", "p_top2", "p_top3"):
        assert ((stability[column] >= 0) & (stability[column] <= 1)).all()
    # Exactly one technology is rank 1 per draw, so P(rank 1) sums to one.
    assert stability["p_top1"].sum() == pytest.approx(1.0, abs=1e-9)
    # Monotone: P(top1) <= P(top2) <= P(top3) per technology.
    assert (stability["p_top1"] <= stability["p_top2"] + 1e-12).all()
    assert (stability["p_top2"] <= stability["p_top3"] + 1e-12).all()


def test_monte_carlo_return_draws_shapes() -> None:
    profile = load_multimetric_profile(REFERENCE)
    out = monte_carlo_cleanliness(profile, samples=200, seed=5, return_draws=True)
    techs = sorted(profile["technology"].unique())
    assert out["score_draws"].shape == (200, len(techs))
    assert out["rank_draws"].shape == (200, len(techs))
    # Each draw is a valid permutation of ranks 1..n.
    first = sorted(out["rank_draws"].iloc[0].tolist())
    assert first == list(range(1, len(techs) + 1))


def test_monte_carlo_runs_on_partial_fixture() -> None:
    # The fixture intentionally omits technologies/metrics; MC must still run on it.
    profile = pd.read_csv(FIXTURE_TINY)
    out = monte_carlo_cleanliness(profile, samples=100, seed=3)
    assert set(out["score_summary"]["technology"]) == {"Nuclear", "Wind onshore"}


# ---------------------------------------------------------------------- scenarios


def test_scenarios_define_all_metrics() -> None:
    for name in SCENARIOS:
        weights = get_scenario(name)
        assert set(weights) == set(METRIC_UNITS)


def test_reliability_scenario_favors_dispatchable() -> None:
    profile = load_multimetric_profile(REFERENCE)
    wide = to_wide(profile, value="central")
    higher = higher_is_better_set(profile)
    scores = weighted_cleanliness_score(
        wide, metrics=list(METRIC_UNITS), weights=get_scenario("high_reliability_first"),
        higher_is_better=higher,
    )
    ranking = list(scores["technology"])
    dispatchable = {"Geothermal", "Nuclear", "Hydro", "Gas with CCS", "Biomass"}
    # A dispatchable source leads, and nuclear outranks the variable renewables.
    assert ranking[0] in dispatchable
    assert ranking.index("Nuclear") < ranking.index("Wind onshore")
    assert ranking.index("Nuclear") < ranking.index("Solar PV utility")


def test_cost_scenario_does_not_favor_nuclear() -> None:
    profile = load_multimetric_profile(REFERENCE)
    wide = to_wide(profile, value="central")
    higher = higher_is_better_set(profile)
    scores = weighted_cleanliness_score(
        wide, metrics=list(METRIC_UNITS), weights=get_scenario("low_cost_first"),
        higher_is_better=higher,
    )
    ranking = list(scores["technology"])
    # Cost-first should not favour Nuclear: the cheap renewables lead, nuclear ranks low.
    assert ranking[0] != "Nuclear"
    assert ranking.index("Wind onshore") < ranking.index("Nuclear")
    assert ranking.index("Nuclear") >= len(ranking) // 2


def test_emissions_scenario_favors_wind_over_nuclear() -> None:
    profile = load_multimetric_profile(REFERENCE)
    wide = to_wide(profile, value="central")
    higher = higher_is_better_set(profile)
    scores = weighted_cleanliness_score(
        wide, metrics=list(METRIC_UNITS), weights=get_scenario("low_emissions_first"),
        higher_is_better=higher,
    )
    ranking = list(scores["technology"])
    assert ranking.index("Wind onshore") < ranking.index("Nuclear")


# ------------------------------------------------------------------------ report


def test_report_builds_and_validates() -> None:
    profile = load_multimetric_profile(REFERENCE)
    wide = to_wide(profile, value="central")
    higher = higher_is_better_set(profile)
    frontier = pareto_frontier(
        wide, metrics=list(METRIC_UNITS), minimize=False, higher_is_better=higher
    )
    scenarios = {}
    for name, weights in SCENARIOS.items():
        mc = monte_carlo_cleanliness(profile, weights=weights, samples=100, seed=42)
        scenarios[name] = {
            "weights": weights,
            "score_summary": mc["score_summary"],
            "rank_stability": mc["rank_stability"],
        }
    report = build_report(
        dataset_schema_version="1.0",
        seed=42,
        samples=100,
        scenarios=scenarios,
        pareto_frontier=frontier,
        best_by_metric={"lifecycle_co2e": "Wind onshore"},
    )
    validate_report(report)  # raises on problems
    assert report["report_schema_version"] == "1.0"
    assert set(report["scenarios"]) == set(SCENARIOS)


# ----------------------------------------------------------------------- dashboard


def test_dashboard_html_renders_from_report() -> None:
    profile = load_multimetric_profile(REFERENCE)
    wide = to_wide(profile, value="central")
    higher = higher_is_better_set(profile)
    frontier = pareto_frontier(
        wide, metrics=list(METRIC_UNITS), minimize=False, higher_is_better=higher
    )
    scenarios = {}
    for name, weights in SCENARIOS.items():
        mc = monte_carlo_cleanliness(profile, weights=weights, samples=100, seed=42)
        scenarios[name] = {
            "weights": weights,
            "score_summary": mc["score_summary"],
            "rank_stability": mc["rank_stability"],
        }
    report = build_report(
        dataset_schema_version="1.0",
        seed=42,
        samples=100,
        scenarios=scenarios,
        pareto_frontier=frontier,
        best_by_metric={"lifecycle_co2e": "Wind onshore"},
    )
    # No figures supplied: HTML must still render with tabs, tables and risk section.
    html_text = build_dashboard_html(report, figures={})
    assert html_text.startswith("<!DOCTYPE html>")
    for name in SCENARIOS:
        assert f"panel-{name}" in html_text
    assert "Model risk" in html_text
    assert "Pareto frontier" in html_text
    # Every technology should appear in the rendered tables.
    for tech in profile["technology"].unique():
        assert tech in html_text
