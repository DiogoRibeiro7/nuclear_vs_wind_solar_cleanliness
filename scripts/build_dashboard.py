"""Build the static HTML cleanliness dashboard from the structured JSON report.

This demonstrates the purpose of ``reports/multimetric_report.json``: a downstream
consumer (here, a dashboard) rebuilds figures and tables from the report alone. If the
report is missing, the multi-metric analysis is run first to produce it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
SCRIPTS_PATH = Path(__file__).resolve().parent
for extra_path in (SRC_PATH, SCRIPTS_PATH):
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

from energy_cleanliness.dashboard import write_dashboard  # noqa: E402
from energy_cleanliness.plotting import plot_rank_stability, plot_scenario_scores  # noqa: E402
from energy_cleanliness.reporting import validate_report  # noqa: E402

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORT_PATH = REPORTS_DIR / "multimetric_report.json"
FIGURES_DIR = REPORTS_DIR / "figures"
OUTPUT_PATH = REPORTS_DIR / "dashboard.html"


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from run_multimetric_analysis import run as run_multimetric

        run_multimetric()
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    validate_report(report)
    return report


def _scenario_figures(report: dict) -> dict[str, dict[str, str]]:
    """Regenerate per-scenario figures from the report and return their paths."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figures: dict[str, dict[str, str]] = {}
    for name, scenario in report["scenarios"].items():
        score_summary = pd.DataFrame(scenario["score_summary"])
        rank_stability = pd.DataFrame(scenario["rank_stability"])
        scores_png = FIGURES_DIR / f"scores_{name}.png"
        rank_png = FIGURES_DIR / f"rank_stability_{name}.png"
        plot_scenario_scores(score_summary, scores_png, title=f"Scores — {name}")
        plot_rank_stability(rank_stability, rank_png, title=f"Rank stability — {name}")
        figures[name] = {"scores": str(scores_png), "rank": str(rank_png)}
    return figures


def main() -> None:
    report = _ensure_report()
    figures = _scenario_figures(report)
    write_dashboard(report, figures, OUTPUT_PATH)
    print(f"Wrote dashboard to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
