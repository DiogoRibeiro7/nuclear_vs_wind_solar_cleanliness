"""Region-aware financing / levelized-cost analysis.

Shows how the cost of capital reshapes the levelized cost of each technology:
capital-intensive low-carbon options (nuclear, hydro, offshore wind) are penalised
heavily by a high WACC, while fuel-heavy gas is barely affected. Runs both illustrative
financing environments and the per-region WACC from each region config.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.financing import (  # noqa: E402
    DEFAULT_ENVIRONMENTS,
    FinancingEnvironment,
    lcoe_table,
    wacc_sensitivity,
)
from energy_cleanliness.model_risk import model_risk_markdown  # noqa: E402
from energy_cleanliness.regions import discover_region_configs  # noqa: E402

REGIONS_DIR = PROJECT_ROOT / "data" / "regions"
REPORTS_DIR = PROJECT_ROOT / "reports"


def _region_environments() -> list[FinancingEnvironment]:
    environments = []
    for path in discover_region_configs(REGIONS_DIR):
        raw = json.loads(path.read_text(encoding="utf-8"))
        environments.append(FinancingEnvironment.from_dict(raw["name"], raw.get("financing")))
    return environments


def main() -> None:
    environments = list(DEFAULT_ENVIRONMENTS.values()) + _region_environments()
    tables = [lcoe_table(env) for env in environments]
    combined = pd.concat(tables, ignore_index=True)
    sensitivity = wacc_sensitivity()

    REPORTS_DIR.mkdir(exist_ok=True)
    combined.to_csv(REPORTS_DIR / "financing_lcoe.csv", index=False)
    sensitivity.to_csv(REPORTS_DIR / "financing_wacc_sensitivity.csv", index=False)

    lines = ["# Region-aware financing analysis", ""]
    lines.append(
        "Levelized cost (USD/MWh) depends heavily on the cost of capital. "
        "Capital-intensive low-carbon technologies are penalised most by a high WACC."
    )
    lines.append("")
    lines.append("## Cheapest technology by financing environment")
    lines.append("")
    lines.append("| environment | WACC | cheapest | LCOE | nuclear LCOE |")
    lines.append("|---|---:|---|---:|---:|")
    for env, table in zip(environments, tables):
        cheapest = table.iloc[0]
        nuclear = table.loc[table["technology"] == "Nuclear", "lcoe_usd_mwh"].iloc[0]
        lines.append(
            f"| {env.name} | {env.wacc:.1%} | {cheapest['technology']} | "
            f"{cheapest['lcoe_usd_mwh']:.0f} | {nuclear:.0f} |"
        )
    lines.append("")
    lines.append("## Sensitivity to cost of capital (LCOE rise, 3% -> 10% WACC)")
    lines.append("")
    lines.append("| technology | low WACC | high WACC | % increase |")
    lines.append("|---|---:|---:|---:|")
    for _, row in sensitivity.iterrows():
        cols = [c for c in sensitivity.columns if c.startswith("lcoe_at_")]
        lines.append(
            f"| {row['technology']} | {row[cols[0]]:.0f} | {row[cols[1]]:.0f} | "
            f"{row['pct_increase']:.0f}% |"
        )
    lines.append("")
    lines.append(model_risk_markdown(context="region", level=2))
    (REPORTS_DIR / "financing_lcoe.md").write_text("\n".join(lines), encoding="utf-8")

    print("Wrote reports/financing_lcoe.csv, financing_wacc_sensitivity.csv and financing_lcoe.md")


if __name__ == "__main__":
    main()
