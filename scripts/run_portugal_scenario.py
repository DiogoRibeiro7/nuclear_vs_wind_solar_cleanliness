"""Run Portugal-specific lifecycle emission counterfactual scenarios."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.portugal import run_portugal_scenario
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    scenarios = run_portugal_scenario()
    scenarios.to_csv(REPORTS_DIR / "portugal_counterfactuals.csv", index=False)
    print("Wrote reports/portugal_counterfactuals.csv")


if __name__ == "__main__":
    main()
