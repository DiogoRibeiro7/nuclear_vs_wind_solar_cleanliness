"""Generate social-article drafts from the latest analysis summary."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.article_generator import write_article_outputs
REPORTS_DIR = PROJECT_ROOT / "reports"
SUMMARY_PATH = PROJECTS_DIR = PROJECT_ROOT / "reports" / "summary.md"


def main() -> None:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError("Run run_analysis.py first to generate reports/summary.md")
    outputs = write_article_outputs(
        summary_file=SUMMARY_PATH,
        output_dir=REPORTS_DIR / "generated",
        figures=[
            str(REPORTS_DIR / "lifecycle_ranges.png"),
            str(REPORTS_DIR / "probability_matrix.png"),
        ],
    )
    print(f"Wrote: {outputs[0]}")
    print(f"Wrote: {outputs[1]}")


if __name__ == "__main__":
    main()
