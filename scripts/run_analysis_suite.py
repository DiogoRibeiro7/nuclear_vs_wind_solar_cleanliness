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
from energy_cleanliness.cleanliness_index import pareto_frontier, sensitivity_analysis, weighted_cleanliness_score
from energy_cleanliness.claim_classifier import classify_claims_batch
from energy_cleanliness.data import load_lifecycle_data
from energy_cleanliness.portugal import run_portugal_scenario


DATA_PATH = PROJECT_ROOT / "data" / "processed" / "lifecycle_emissions_normalized.csv"
LEGACY_DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
MULTI_METRIC_PROFILE = PROJECT_ROOT / "data" / "multimetric_cleanliness_reference.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"
MULTI_METRIC_COLUMNS = [
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


def _build_multi_metric_inputs() -> pd.DataFrame:
    """Load lifecycle data and merge it with broader cleanliness metrics."""
    data_path = DATA_PATH if DATA_PATH.exists() else LEGACY_DATA_PATH
    lifecycle_data = load_lifecycle_data(data_path)
    if not MULTI_METRIC_PROFILE.exists():
        raise FileNotFoundError(f"Missing multi-metric profile file: {MULTI_METRIC_PROFILE}")

    profile = pd.read_csv(MULTI_METRIC_PROFILE)
    merged = lifecycle_data.merge(profile, on="technology", how="left")
    missing = merged[["technology"] + MULTI_METRIC_COLUMNS].isna()
    if missing.to_numpy().any():
        missing_tech = merged.loc[missing.any(axis=1), "technology"].tolist()
        raise ValueError(f"Missing multi-metric profile values for: {', '.join(missing_tech)}")
    return merged


def _write_multimetric_summary(merged: pd.DataFrame, score: pd.DataFrame, frontier: pd.DataFrame) -> None:
    """Write an explicit wider-metric interpretation result."""
    top = score.sort_values("cleanliness_score", ascending=False).head(3)["technology"].tolist()
    metric_leaders = []
    for metric in MULTI_METRIC_COLUMNS:
        if metric in HIGHER_IS_BETTER:
            winner_mask = merged[metric] == merged[metric].max()
        else:
            winner_mask = merged[metric] == merged[metric].min()
        winners = ", ".join(merged.loc[winner_mask, "technology"].tolist())
        metric_leaders.append(f"- {metric}: {winners}")

    lines = [
        "# Multi-metric interpretation",
        "",
        "Broader cleanliness score dimensions used in this run:",
        "- lifecycle greenhouse-gas emissions (lower is better)",
        "- direct deaths per TWh (lower is better)",
        "- air-pollution deaths per TWh (lower is better)",
        "- waste persistence (lower is better)",
        "- water use (lower is better)",
        "- land use (lower is better)",
        "- material intensity (lower is better)",
        "- construction time (lower is better)",
        "- capacity factor (higher is better)",
        "- grid integration score (higher is better)",
        "- levelized cost (lower is better)",
        "- financing risk (lower is better)",
        "",
        f"Top ranked technologies by weighted score: {', '.join(top)}",
        f"Technologies on the Pareto frontier: {', '.join(frontier['technology'])}",
        "",
        "Result:",
    ]

    if len(frontier) > 1:
        lines.append(
            "Under this wider definition, there is no universal winner. Nuclear, wind and solar remain all low-carbon options with different strengths."
        )
    else:
        lines.append("One technology dominates all listed multi-metric dimensions in this profile.")

    lines.extend(["", "Metric leaders:", *metric_leaders])
    (REPORTS_DIR / "multimetric_summary.md").write_text("\n".join(lines), encoding="utf-8")


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
    multi_metric = _build_multi_metric_inputs()
    score = weighted_cleanliness_score(
        multi_metric,
        metrics=MULTI_METRIC_COLUMNS,
        method="minmax",
        higher_is_better=HIGHER_IS_BETTER,
    )
    sensitivity = sensitivity_analysis(
        multi_metric,
        metrics=MULTI_METRIC_COLUMNS,
        method="minmax",
        samples=100,
        seed=123,
        higher_is_better=HIGHER_IS_BETTER,
    )
    frontier = pareto_frontier(
        multi_metric,
        metrics=MULTI_METRIC_COLUMNS,
        minimize=False,
        higher_is_better=HIGHER_IS_BETTER,
    )
    score.to_csv(REPORTS_DIR / "cleanliness_scores.csv", index=False)
    sensitivity.to_csv(REPORTS_DIR / "cleanliness_sensitivity.csv", index=False)
    frontier.to_csv(REPORTS_DIR / "cleanliness_frontier.csv", index=False)
    _write_multimetric_summary(multi_metric, score, frontier)

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
        figures=[str(REPORTS_DIR / "lifecycle_ranges.png"), str(REPORTS_DIR / "probability_matrix.png")],
    )
    print(f"Suite completed. Results in {REPORTS_DIR}")


if __name__ == "__main__":
    main()
