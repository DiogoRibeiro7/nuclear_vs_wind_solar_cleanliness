"""Run all workflow tasks for lifecycle analysis in one command."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.article_generator import write_article_outputs
from energy_cleanliness.analysis import (
    bootstrap_confidence_intervals,
    build_markdown_summary,
    compare_empirical_vs_triangular,
    compare_to_baseline,
    estimate_pairwise_probabilities,
    simulate_uncertainty,
)
from energy_cleanliness.cleanliness_index import sensitivity_analysis, weighted_cleanliness_score
from energy_cleanliness.claim_classifier import classify_claims_batch
from energy_cleanliness.data import load_lifecycle_data
from energy_cleanliness.portugal import run_portugal_scenario


DATA_PATH = PROJECT_ROOT / "data" / "processed" / "lifecycle_emissions_normalized.csv"
LEGACY_DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    # Baseline data and uncertainty tasks
    data_path = DATA_PATH if DATA_PATH.exists() else LEGACY_DATA_PATH
    data = load_lifecycle_data(data_path)
    median_comparison = compare_to_baseline(data, baseline="Nuclear")
    samples = simulate_uncertainty(data, draws=25_000, seed=123)
    probability_matrix = estimate_pairwise_probabilities(samples)
    ci = bootstrap_confidence_intervals(samples, probability=0.95, n_bootstrap=1_000, seed=123)
    print("Bootstrap CI rows:", len(ci))
    comparison = compare_empirical_vs_triangular(data, draws=5_000, seed=123)
    comparison["triangular"].to_csv(REPORTS_DIR / "pairwise_triangular.csv")
    comparison["empirical"].to_csv(REPORTS_DIR / "pairwise_empirical.csv")
    comparison["delta"].to_csv(REPORTS_DIR / "pairwise_delta.csv")

    summary = build_markdown_summary(
        data=data,
        median_comparison=median_comparison,
        probability_matrix=probability_matrix,
        baseline="Nuclear",
    )
    (REPORTS_DIR / "summary.md").write_text(summary, encoding="utf-8")

    # Multi-metric scoring
    multi_metric = pd.DataFrame(
        {
            "technology": data["technology"],
            "lifecycle_gco2e_kwh": data["median_gco2e_kwh"],
            "deaths_per_twh": [0.02] * len(data),
            "land_use": [15] * len(data),
            "water_consumption": [5] * len(data),
            "material_intensity": [1] * len(data),
            "waste_persistence": [1] * len(data),
            "construction_time": [5] * len(data),
            "levelized_cost": [70] * len(data),
        }
    )
    metrics = [
        "lifecycle_gco2e_kwh",
        "deaths_per_twh",
        "land_use",
        "water_consumption",
        "material_intensity",
        "waste_persistence",
        "construction_time",
        "levelized_cost",
    ]
    score = weighted_cleanliness_score(multi_metric, metrics=metrics)
    sensitivity = sensitivity_analysis(multi_metric, metrics=metrics, samples=100, seed=123)
    score.to_csv(REPORTS_DIR / "cleanliness_scores.csv", index=False)
    sensitivity.to_csv(REPORTS_DIR / "cleanliness_sensitivity.csv", index=False)

    # Portugal counterfactuals
    scenarios = run_portugal_scenario()
    scenarios.to_csv(REPORTS_DIR / "portugal_counterfactuals.csv", index=False)

    # Claim classification
    claims = [
        "Nuclear is cleaner than wind and solar.",
        "Nuclear emits 0 emissions during operation.",
        "The claim is based on peer-reviewed lifecycle data.",
        "Nuclear is the cleanest energy source.",
    ]
    classifications = classify_claims_batch(claims)
    for claim, item in zip(claims, classifications):
        print(f"{claim} -> {item.label} ({item.reason})")

    # Article outputs
    write_article_outputs(
        summary_file=REPORTS_DIR / "summary.md",
        output_dir=REPORTS_DIR / "generated",
        figures=[
            str(REPORTS_DIR / "lifecycle_ranges.png"),
            str(REPORTS_DIR / "probability_matrix.png"),
        ],
    )
    print(f"Suite completed. Results in {REPORTS_DIR}")


if __name__ == "__main__":
    main()
