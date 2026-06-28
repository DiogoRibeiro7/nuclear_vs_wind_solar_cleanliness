"""Regenerate every analysis artifact with one command.

Runs each report-generating script in dependency order and prints a pass/fail summary.
Useful for refreshing ``reports/`` locally and as a single end-to-end check.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
for extra_path in (SRC_PATH, SCRIPTS_PATH):
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

# Ordered so that producers run before consumers (e.g. the report before the dashboard).
PIPELINE: list[str] = [
    "ingest_lifecycle_datasets",
    "run_analysis",
    "make_plots",
    "run_multimetric_analysis",
    "run_region_scenarios",
    "run_financing_analysis",
    "run_geography_analysis",
    "build_dashboard",
    "run_claim_classifier",
    "generate_social_article",
]


def main() -> int:
    """Run the full pipeline; return a non-zero exit code if any step fails."""
    failures: list[str] = []
    for name in PIPELINE:
        print(f"\n=== {name} ===")
        try:
            module = importlib.import_module(name)
            module.main()
        except Exception:  # noqa: BLE001 - report and continue so one failure isn't fatal
            failures.append(name)
            traceback.print_exc()

    print("\n" + "=" * 40)
    ran = len(PIPELINE) - len(failures)
    print(f"Completed {ran}/{len(PIPELINE)} steps.")
    if failures:
        print("Failed:", ", ".join(failures))
        return 1
    print("All analysis artifacts regenerated in reports/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
