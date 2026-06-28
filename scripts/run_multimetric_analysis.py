"""Run multi-metric cleanliness index analysis.

Loads the validated long-format multi-metric profile (with per-metric uncertainty),
scores every policy scenario with point estimates and Monte Carlo uncertainty
propagation, computes rank-stability diagnostics and the Pareto frontier, and writes
both human-readable and structured JSON outputs to ``reports/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.cleanliness_index import (  # noqa: E402
    monte_carlo_cleanliness,
    pareto_frontier,
    weighted_cleanliness_score,
)
from energy_cleanliness.multimetric import (  # noqa: E402
    METRIC_UNITS,
    SUPPORTED_SCHEMA_VERSIONS,
    higher_is_better_set,
    load_multimetric_profile,
    to_wide,
)
from energy_cleanliness.reporting import build_report, write_report  # noqa: E402
from energy_cleanliness.scenarios import SCENARIOS  # noqa: E402

MULTI_METRIC_PROFILE = PROJECT_ROOT / "data" / "multimetric_cleanliness_reference.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"
METRICS = list(METRIC_UNITS)
SAMPLES = 2_000
SEED = 42


def run(samples: int = SAMPLES, seed: int = SEED) -> None:
    """Build a broader, uncertainty-aware cleanliness score across policy scenarios."""
    profile = load_multimetric_profile(MULTI_METRIC_PROFILE)
    higher = higher_is_better_set(profile)
    wide = to_wide(profile, value="central")

    frontier = pareto_frontier(
        wide, metrics=METRICS, minimize=False, higher_is_better=higher
    )

    best_by_metric: dict[str, str] = {}
    for metric in METRICS:
        if metric in higher:
            best_by_metric[metric] = wide.loc[wide[metric].idxmax(), "technology"]
        else:
            best_by_metric[metric] = wide.loc[wide[metric].idxmin(), "technology"]

    scenario_outputs: dict[str, dict] = {}
    for name, weights in SCENARIOS.items():
        point = weighted_cleanliness_score(
            wide, metrics=METRICS, weights=weights, higher_is_better=higher
        )
        mc = monte_carlo_cleanliness(profile, weights=weights, samples=samples, seed=seed)
        scenario_outputs[name] = {
            "weights": weights,
            "point_scores": point,
            "score_summary": mc["score_summary"],
            "rank_stability": mc["rank_stability"],
        }

    REPORTS_DIR.mkdir(exist_ok=True)

    # Backward-compatible flat CSVs for the balanced scenario.
    balanced = scenario_outputs["balanced"]
    balanced["point_scores"].to_csv(REPORTS_DIR / "cleanliness_scores.csv", index=False)
    balanced["score_summary"].to_csv(REPORTS_DIR / "cleanliness_sensitivity.csv", index=False)
    balanced["rank_stability"].to_csv(REPORTS_DIR / "cleanliness_rank_stability.csv", index=False)
    frontier.to_csv(REPORTS_DIR / "cleanliness_frontier.csv", index=False)

    _write_markdown(frontier, best_by_metric, scenario_outputs)

    report = build_report(
        dataset_schema_version=sorted(SUPPORTED_SCHEMA_VERSIONS)[-1],
        seed=seed,
        samples=samples,
        scenarios=scenario_outputs,
        pareto_frontier=frontier,
        best_by_metric=best_by_metric,
    )
    write_report(report, REPORTS_DIR / "multimetric_report.json")

    print(
        "Wrote multi-metric outputs to reports/ "
        "(CSVs, multimetric_summary.md, multimetric_report.json)"
    )


def _write_markdown(frontier, best_by_metric, scenario_outputs) -> None:
    lines: list[str] = []
    lines.append("# Multi-metric cleanliness summary\n")
    lines.append(
        "Broader interpretation using literature-informed values with explicit "
        "uncertainty ranges. This is a sensitivity profile, not a definitive ranking.\n"
    )
    lines.append(f"Technologies on the Pareto frontier: {', '.join(frontier['technology'])}\n")
    lines.append("No single source is best for every metric.\n")

    lines.append("## Best-by-metric leaders\n")
    for metric, winner in best_by_metric.items():
        lines.append(f"- `{metric}`: {winner}")
    lines.append("")

    lines.append("## Scenario rankings (Monte Carlo)\n")
    for name, payload in scenario_outputs.items():
        summary = payload["score_summary"]
        stability = payload["rank_stability"]
        top = summary.iloc[0]
        p_top1 = float(
            stability.loc[stability["technology"] == top["technology"], "p_top1"].iloc[0]
        )
        lines.append(f"### {name}")
        lines.append(
            f"Leader: **{top['technology']}** "
            f"(mean score {top['mean_score']:.3f}, 95% CI "
            f"[{top['ci_low']:.3f}, {top['ci_high']:.3f}], "
            f"rank-1 in {p_top1:.0%} of draws).\n"
        )
        lines.append("| technology | mean | 95% CI | P(rank 1) | P(top 3) |")
        lines.append("|---|---:|---|---:|---:|")
        merged = summary.merge(stability, on="technology")
        for _, row in merged.iterrows():
            lines.append(
                f"| {row['technology']} | {row['mean_score']:.3f} | "
                f"[{row['ci_low']:.3f}, {row['ci_high']:.3f}] | "
                f"{row['p_top1']:.0%} | {row['p_top3']:.0%} |"
            )
        lines.append("")

    (REPORTS_DIR / "multimetric_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
