"""End-to-end smoke tests: every analysis script runs and writes its primary outputs.

These guard against script-level regressions (import errors, schema drift, renamed
outputs) that unit tests on the library would miss.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS = PROJECT_ROOT / "reports"
for extra_path in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))


SCRIPT_OUTPUTS = [
    ("run_multimetric_analysis", ["cleanliness_scores.csv", "multimetric_report.json"]),
    ("run_region_scenarios", ["region_counterfactuals.csv"]),
    ("run_financing_analysis", ["financing_lcoe.csv"]),
    ("run_geography_analysis", ["marginal_abatement.csv"]),
    ("build_dashboard", ["dashboard.html"]),
]


@pytest.mark.parametrize("module_name,outputs", SCRIPT_OUTPUTS)
def test_script_runs_and_writes_outputs(module_name: str, outputs: list[str]) -> None:
    module = importlib.import_module(module_name)
    module.main()
    for filename in outputs:
        assert (REPORTS / filename).exists(), f"{module_name} did not write {filename}"


def test_run_all_pipeline_succeeds() -> None:
    run_all = importlib.import_module("run_all")
    assert run_all.main() == 0
