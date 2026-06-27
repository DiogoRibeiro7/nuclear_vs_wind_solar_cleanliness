"""Run multi-metric cleanliness index analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.cleanliness_index import sensitivity_analysis, weighted_cleanliness_score
from energy_cleanliness.data import load_lifecycle_data

DATA_PATH = PROJECT_ROOT / "data" / "lifecycle_emissions_ipcc_ar5.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    data = load_lifecycle_data(DATA_PATH)
    metrics_input = pd.DataFrame(
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
    scores = weighted_cleanliness_score(metrics_input, metrics=metrics, method="minmax")
    sensitivity = sensitivity_analysis(metrics_input, metrics=metrics, samples=200, seed=42)
    REPORTS_DIR.mkdir(exist_ok=True)
    scores.to_csv(REPORTS_DIR / "cleanliness_scores.csv", index=False)
    sensitivity.to_csv(REPORTS_DIR / "cleanliness_sensitivity.csv", index=False)
    print("Wrote multi-metric outputs to reports/")


if __name__ == "__main__":
    main()
