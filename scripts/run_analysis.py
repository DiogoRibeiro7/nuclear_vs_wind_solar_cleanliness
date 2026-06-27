
"""Run lifecycle cleanliness analysis and write report files."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.analysis import (
    build_markdown_summary,
    compare_to_baseline,
    estimate_pairwise_probabilities,
    simulate_uncertainty,
    bootstrap_confidence_intervals,
)
from energy_cleanliness.data import load_lifecycle_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "lifecycle_emissions_normalized.csv"
LEGACY_DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    """Execute the full analysis pipeline."""
    REPORTS_DIR.mkdir(exist_ok=True)

    data_path = DATA_PATH if DATA_PATH.exists() else LEGACY_DATA_PATH
    data = load_lifecycle_data(data_path)
    median_comparison = compare_to_baseline(data, baseline="Nuclear")
    samples = simulate_uncertainty(data, draws=50_000, seed=42)
    probability_matrix = estimate_pairwise_probabilities(samples)
    ci = bootstrap_confidence_intervals(samples)

    median_comparison.to_csv(REPORTS_DIR / "median_comparison.csv", index=False)
    probability_matrix.to_csv(REPORTS_DIR / "probability_matrix.csv")
    ci.to_csv(REPORTS_DIR / "bootstrap_ci.csv", index=False)

    summary = build_markdown_summary(
        data=data,
        median_comparison=median_comparison,
        probability_matrix=probability_matrix,
        baseline="Nuclear",
    )
    (REPORTS_DIR / "summary.md").write_text(summary, encoding="utf-8")

    print(summary)


if __name__ == "__main__":
    main()
