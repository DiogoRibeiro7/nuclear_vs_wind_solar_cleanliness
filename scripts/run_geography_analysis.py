"""Geography-, grid-context- and deployment-year-aware abatement analysis.

Shows how the marginal carbon abatement of a clean build depends on the region, the grid
it displaces, and the deployment year. Lifecycle intensities for the clean technologies
are read from the multi-metric profile (IPCC AR5 carbon).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.geography import (  # noqa: E402
    abatement_table,
    load_grid_intensity,
    trajectory_table,
)
from energy_cleanliness.model_risk import model_risk_markdown  # noqa: E402
from energy_cleanliness.multimetric import load_multimetric_profile  # noqa: E402

GRID_PATH = PROJECT_ROOT / "data" / "grid_carbon_intensity.csv"
PROFILE_PATH = PROJECT_ROOT / "data" / "multimetric_cleanliness_reference.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

CLEAN_TECHS = ["Nuclear", "Wind onshore", "Solar PV utility", "Hydro"]
REGIONS = ["France", "Germany", "Portugal", "EU"]
YEARS = [2015, 2023]


def _clean_tech_lifecycle() -> dict[str, float]:
    profile = load_multimetric_profile(PROFILE_PATH)
    carbon = profile[profile["metric"] == "lifecycle_co2e"].set_index("technology")["central"]
    return {tech: float(carbon[tech]) for tech in CLEAN_TECHS}


def main() -> None:
    grid = load_grid_intensity(GRID_PATH)
    technologies = _clean_tech_lifecycle()

    trajectory = trajectory_table(grid)
    abatement = abatement_table(technologies, REGIONS, YEARS, grid)

    REPORTS_DIR.mkdir(exist_ok=True)
    trajectory.to_csv(REPORTS_DIR / "grid_intensity_trajectory.csv", index=False)
    abatement.to_csv(REPORTS_DIR / "marginal_abatement.csv", index=False)

    lines = ["# Geography, grid-context and deployment-year analysis", ""]
    lines.append(
        "Marginal carbon abatement (gCO2/kWh) of a clean build = grid intensity it "
        "displaces minus the technology's lifecycle intensity. It depends on the region, "
        "the grid context, and the deployment year as grids decarbonise."
    )
    lines.append("")
    lines.append("## Grid carbon-intensity trajectory (gCO2/kWh)")
    lines.append("")
    lines.append("| region | first year | latest year | change |")
    lines.append("|---|---:|---:|---:|")
    for region, group in trajectory.groupby("region", sort=True):
        first = group.iloc[0]
        last = group.iloc[-1]
        lines.append(
            f"| {region} | {first['grid_gco2_kwh']:.0f} ({first['year']}) | "
            f"{last['grid_gco2_kwh']:.0f} ({last['year']}) | "
            f"{last['pct_change_from_first']:+.0f}% |"
        )
    lines.append("")
    lines.append("## Marginal abatement of new nuclear by region and year")
    lines.append("")
    lines.append("| region | year | grid | nuclear lifecycle | abatement |")
    lines.append("|---|---:|---:|---:|---:|")
    nuclear = abatement[abatement["technology"] == "Nuclear"].sort_values(["region", "year"])
    for _, row in nuclear.iterrows():
        lines.append(
            f"| {row['region']} | {row['year']} | {row['grid_gco2_kwh']:.0f} | "
            f"{row['lifecycle_gco2_kwh']:.0f} | {row['abatement_gco2_kwh']:.0f} |"
        )
    lines.append("")
    lines.append(
        "The same clean build avoids far more carbon in a coal-heavy grid (Germany) than "
        "in an already-clean one (France), and the benefit shrinks over time everywhere."
    )
    lines.append("")
    lines.append(model_risk_markdown(context="region", level=2))
    (REPORTS_DIR / "grid_intensity_trajectory.md").write_text("\n".join(lines), encoding="utf-8")

    print("Wrote reports/grid_intensity_trajectory.{csv,md} and reports/marginal_abatement.csv")


if __name__ == "__main__":
    main()
