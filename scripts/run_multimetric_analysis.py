"""Run multi-metric cleanliness index analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.cleanliness_index import (
    pareto_frontier,
    sensitivity_analysis,
    weighted_cleanliness_score,
)
from energy_cleanliness.data import load_lifecycle_data

DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
MULTI_METRIC_PROFILE = PROJECT_ROOT / "data" / "multimetric_cleanliness_reference.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"
METRICS = [
    "median_gco2e_kwh",
    "direct_deaths_per_twh",
    "air_pollution_deaths_per_twh",
    "waste_persistence",
    "water_use",
    "land_use",
    "material_intensity",
    "construction_time",
    "capacity_factor",
    "grid_integration_score",
    "levelized_cost",
    "financing_risk",
]
HIGHER_IS_BETTER = {"capacity_factor", "grid_integration_score"}


def main() -> None:
    """Build a broader cleanliness score including non-carbon metrics."""
    if not MULTI_METRIC_PROFILE.exists():
        raise FileNotFoundError(f"Missing multi-metric profile file: {MULTI_METRIC_PROFILE}")

    data = load_lifecycle_data(DATA_PATH)
    profile = pd.read_csv(MULTI_METRIC_PROFILE)
    metrics_input = data.merge(profile, on="technology", how="left")
    missing_metrics = [column for column in METRICS if column not in metrics_input.columns]
    if missing_metrics:
        raise ValueError(f"Missing multi-metric columns in profile: {missing_metrics}")

    missing_rows = metrics_input[["technology"] + METRICS].copy()
    if missing_rows.isna().to_numpy().any():
        missing_values = missing_rows[missing_rows.isna().any(axis=1)]["technology"].tolist()
        raise ValueError(f"Missing metric values for: {', '.join(missing_values)}")

    scores = weighted_cleanliness_score(
        metrics_input,
        metrics=METRICS,
        higher_is_better=HIGHER_IS_BETTER,
        method="minmax",
    )
    sensitivity = sensitivity_analysis(
        metrics_input,
        metrics=METRICS,
        higher_is_better=HIGHER_IS_BETTER,
        samples=500,
        seed=42,
    )
    frontier = pareto_frontier(
        metrics_input,
        metrics=METRICS,
        minimize=False,
        higher_is_better=HIGHER_IS_BETTER,
    )

    top_by_metric = []
    for metric in METRICS:
        if metric in HIGHER_IS_BETTER:
            winner = metrics_input.loc[metrics_input[metric].idxmax(), "technology"]
        else:
            winner = metrics_input.loc[metrics_input[metric].idxmin(), "technology"]
        top_by_metric.append((metric, winner))

    REPORTS_DIR.mkdir(exist_ok=True)
    with open(REPORTS_DIR / "multimetric_summary.md", "w", encoding="utf-8") as summary:
        summary.write("# Multi-metric cleanliness summary\n\n")
        summary.write("Broader interpretation: this is a proxy profile, not a definitive ranking.\n\n")
        summary.write(f"Technologies on Pareto frontier: {', '.join(frontier['technology'])}\n\n")
        summary.write("- No single source is best for every metric in this profile.\n\n")
        summary.write("Best-by-metric leaders:\n")
        for metric, winner in top_by_metric:
            summary.write(f"- {metric}: {winner}\n")

    scores.to_csv(REPORTS_DIR / "cleanliness_scores.csv", index=False)
    sensitivity.to_csv(REPORTS_DIR / "cleanliness_sensitivity.csv", index=False)
    frontier.to_csv(REPORTS_DIR / "cleanliness_frontier.csv", index=False)
    print("Wrote multi-metric outputs to reports/")


if __name__ == "__main__":
    main()
