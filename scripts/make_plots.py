
"""Generate figures for the lifecycle cleanliness analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from energy_cleanliness.analysis import estimate_pairwise_probabilities, simulate_uncertainty
from energy_cleanliness.data import load_lifecycle_data
from energy_cleanliness.plotting import plot_lifecycle_ranges, plot_probability_matrix

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    """Create plots and save them to the reports directory."""
    REPORTS_DIR.mkdir(exist_ok=True)
    data = load_lifecycle_data(DATA_PATH)

    probability_csv = REPORTS_DIR / "probability_matrix.csv"
    if probability_csv.exists():
        probability_matrix = pd.read_csv(probability_csv, index_col=0)
    else:
        samples = simulate_uncertainty(data, draws=50_000, seed=42)
        probability_matrix = estimate_pairwise_probabilities(samples)

    range_path = plot_lifecycle_ranges(data, REPORTS_DIR / "lifecycle_ranges.png")
    probability_path = plot_probability_matrix(probability_matrix, REPORTS_DIR / "probability_matrix.png")

    print(f"Wrote {range_path}")
    print(f"Wrote {probability_path}")


if __name__ == "__main__":
    main()
