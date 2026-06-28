"""Run config-driven multi-region electricity counterfactual scenarios.

Reads every region config under ``data/regions/`` and writes a combined counterfactual
table plus a short markdown summary to ``reports/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.model_risk import model_risk_markdown  # noqa: E402
from energy_cleanliness.regions import run_region_scenarios  # noqa: E402

REGIONS_DIR = PROJECT_ROOT / "data" / "regions"
REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    table = run_region_scenarios(REGIONS_DIR)
    REPORTS_DIR.mkdir(exist_ok=True)
    table.to_csv(REPORTS_DIR / "region_counterfactuals.csv", index=False)

    lines = ["# Multi-region counterfactual summary", ""]
    lines.append("Annual lifecycle emissions in ktCO2e/year. Total generation is conserved:")
    lines.append("the retired source's energy is absorbed by each candidate replacement.\n")
    for region, group in table.groupby("region", sort=True):
        baseline = group.loc[group["scenario"] == "Baseline", "annual_ktco2e"].iloc[0]
        moves = group[group["replacement"] != ""].sort_values("delta_ktco2e")
        best = moves.iloc[0]
        worst = moves.iloc[-1]
        lines.append(f"## {region}")
        lines.append(f"Baseline: **{baseline:,.0f} ktCO2e/year**.\n")
        lines.append(
            f"- Lowest-emission replacement: **{best['replacement']}** "
            f"({best['delta_ktco2e']:+,.0f} ktCO2e, {best['pct_change']:+.1f}%)."
        )
        lines.append(
            f"- Highest-emission replacement: **{worst['replacement']}** "
            f"({worst['delta_ktco2e']:+,.0f} ktCO2e, {worst['pct_change']:+.1f}%)."
        )
        lines.append("")
    lines.append(model_risk_markdown(context="region", level=2))
    (REPORTS_DIR / "region_counterfactuals.md").write_text("\n".join(lines), encoding="utf-8")

    print("Wrote reports/region_counterfactuals.csv and reports/region_counterfactuals.md")


if __name__ == "__main__":
    main()
