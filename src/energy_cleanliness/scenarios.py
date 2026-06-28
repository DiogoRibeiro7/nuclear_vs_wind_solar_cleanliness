"""Policy-intent scenario weight profiles for multi-metric cleanliness scoring.

Each scenario is a set of relative weights over metric keys. Weights are renormalised
to sum to one at scoring time, so only the relative emphasis matters. Metrics not named
in a scenario receive the ``default`` weight.
"""

from __future__ import annotations

from energy_cleanliness.multimetric import METRIC_UNITS

ALL_METRICS: tuple[str, ...] = tuple(METRIC_UNITS)


def _profile(default: float, **overrides: float) -> dict[str, float]:
    """Build a full weight dict over all metrics from a default plus overrides."""
    unknown = set(overrides) - set(ALL_METRICS)
    if unknown:
        raise ValueError(f"Scenario references unknown metric(s): {sorted(unknown)}")
    return {metric: float(overrides.get(metric, default)) for metric in ALL_METRICS}


# Named policy intents. Higher weight = the scenario cares more about that metric.
SCENARIOS: dict[str, dict[str, float]] = {
    "balanced": _profile(1.0),
    "low_emissions_first": _profile(
        0.5,
        lifecycle_co2e=4.0,
        air_pollution_deaths=2.0,
        land_use=1.0,
    ),
    "low_cost_first": _profile(
        0.5,
        levelized_cost=4.0,
        financing_risk=2.0,
        construction_time=1.5,
    ),
    "high_reliability_first": _profile(
        0.5,
        capacity_factor=4.0,
        grid_integration=3.0,
        construction_time=1.0,
    ),
}


def get_scenario(name: str) -> dict[str, float]:
    """Return a copy of the named scenario weight profile."""
    if name not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{name}'. Available: {sorted(SCENARIOS)}")
    return dict(SCENARIOS[name])


def scenario_names() -> list[str]:
    """Return the available scenario names in a stable order."""
    return list(SCENARIOS)
