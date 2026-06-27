
"""Generate figures for the lifecycle cleanliness analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.analysis import estimate_pairwise_probabilities, simulate_uncertainty
from energy_cleanliness.data import load_lifecycle_data
from energy_cleanliness.plotting import plot_lifecycle_ranges, plot_probability_matrix

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "lifecycle_emissions_normalized.csv"
LEGACY_DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    """Create plots and save them to the reports directory."""
    REPORTS_DIR.mkdir(exist_ok=True)
    data_path = DATA_PATH if DATA_PATH.exists() else LEGACY_DATA_PATH
    data = load_lifecycle_data(data_path)

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
