"""Structured JSON report assembly for multi-metric cleanliness analysis.

Produces a single, versioned JSON document that downstream dashboards or APIs can
consume without re-running the analysis. The shape is documented in
``docs/report_schema.json`` (a JSON Schema). :func:`validate_report` performs a
light structural check without requiring the optional ``jsonschema`` dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPORT_SCHEMA_VERSION = "1.0"


def _records(frame: pd.DataFrame) -> list[dict]:
    """Convert a dataframe to JSON-safe records (numpy types -> python types)."""
    return json.loads(frame.to_json(orient="records"))


def build_report(
    *,
    dataset_schema_version: str,
    seed: int,
    samples: int,
    scenarios: dict[str, dict],
    pareto_frontier: pd.DataFrame,
    best_by_metric: dict[str, str],
) -> dict:
    """Assemble the structured multi-metric report dictionary.

    ``scenarios`` maps a scenario name to a dict with ``weights`` (dict),
    ``score_summary`` (DataFrame) and ``rank_stability`` (DataFrame).
    """
    report = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "dataset_schema_version": str(dataset_schema_version),
        "method": {
            "normalization": "minmax_cleaner_is_higher",
            "uncertainty": "triangular(low, central, high) Monte Carlo",
            "samples": int(samples),
            "seed": int(seed),
        },
        "pareto_frontier": list(pareto_frontier["technology"]),
        "best_by_metric": dict(best_by_metric),
        "scenarios": {},
    }
    for name, payload in scenarios.items():
        report["scenarios"][name] = {
            "weights": {k: float(v) for k, v in payload["weights"].items()},
            "score_summary": _records(payload["score_summary"]),
            "rank_stability": _records(payload["rank_stability"]),
        }
    return report


def validate_report(report: dict) -> None:
    """Light structural validation of a report dict; raises ValueError on problems."""
    required_top = {
        "report_schema_version",
        "dataset_schema_version",
        "method",
        "pareto_frontier",
        "best_by_metric",
        "scenarios",
    }
    missing = required_top - set(report)
    if missing:
        raise ValueError(f"Report missing top-level keys: {sorted(missing)}")
    if report["report_schema_version"] != REPORT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported report_schema_version: {report['report_schema_version']}"
        )
    if not isinstance(report["scenarios"], dict) or not report["scenarios"]:
        raise ValueError("Report must contain at least one scenario.")
    for name, scenario in report["scenarios"].items():
        for key in ("weights", "score_summary", "rank_stability"):
            if key not in scenario:
                raise ValueError(f"Scenario '{name}' missing key '{key}'.")


def write_report(report: dict, output_path: str | Path) -> None:
    """Validate and write the report as pretty-printed, deterministic JSON."""
    validate_report(report)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
