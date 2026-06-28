"""Region-aware financing and levelized-cost modelling.

The levelized cost of capital-intensive low-carbon technologies (nuclear, hydro,
offshore wind) is dominated by the cost of capital, while fuel-heavy technologies (gas)
are barely affected. A region's financing environment -- set by its base interest rate,
sovereign-risk premium and policy-risk premium -- therefore reshuffles which clean option
is cheapest. This module computes that effect.

LCOE is in USD/MWh. Capital cost is annualised with a capital-recovery factor (CRF) at the
region's weighted-average cost of capital (WACC).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TechnoEconomics:
    """Representative techno-economic parameters for a build-ready technology.

    Values are illustrative midpoints from public techno-economic syntheses
    (NREL ATB, IEA), not a single sourced figure; ranges in cost of capital dominate.
    """

    name: str
    capex_usd_per_kw: float
    fixed_om_usd_per_kw_yr: float
    var_om_usd_per_mwh: float
    fuel_usd_per_mwh: float
    capacity_factor: float
    lifetime_years: int


# Illustrative parameters (USD, real). Fuel cost folds in plant efficiency.
DEFAULT_TECHNO_ECONOMICS: dict[str, TechnoEconomics] = {
    "Nuclear": TechnoEconomics("Nuclear", 6500, 130, 2.0, 7.0, 0.90, 60),
    "Wind onshore": TechnoEconomics("Wind onshore", 1400, 40, 0.0, 0.0, 0.40, 25),
    "Wind offshore": TechnoEconomics("Wind offshore", 3500, 90, 0.0, 0.0, 0.45, 25),
    "Solar PV utility": TechnoEconomics("Solar PV utility", 1100, 18, 0.0, 0.0, 0.25, 30),
    "Hydro": TechnoEconomics("Hydro", 3000, 40, 0.0, 0.0, 0.45, 80),
    "Geothermal": TechnoEconomics("Geothermal", 4500, 130, 1.0, 0.0, 0.78, 30),
    "Gas": TechnoEconomics("Gas", 1100, 25, 3.0, 40.0, 0.55, 30),
    "Gas with CCS": TechnoEconomics("Gas with CCS", 2300, 60, 6.0, 45.0, 0.55, 30),
}


@dataclass(frozen=True)
class FinancingEnvironment:
    """A region's financing environment. WACC = base + sovereign + policy premia."""

    name: str
    base_real_rate: float
    sovereign_risk_premium: float = 0.0
    policy_risk_premium: float = 0.0

    @property
    def wacc(self) -> float:
        """Weighted-average cost of capital (real)."""
        return self.base_real_rate + self.sovereign_risk_premium + self.policy_risk_premium

    @classmethod
    def from_dict(cls, name: str, data: dict | None) -> "FinancingEnvironment":
        """Build from a region-config ``financing`` block, falling back to a default."""
        if not data:
            return cls(name, base_real_rate=0.03, sovereign_risk_premium=0.01, policy_risk_premium=0.01)
        return cls(
            name=name,
            base_real_rate=float(data.get("base_real_rate", 0.03)),
            sovereign_risk_premium=float(data.get("sovereign_risk_premium", 0.0)),
            policy_risk_premium=float(data.get("policy_risk_premium", 0.0)),
        )


# Illustrative financing environments spanning a realistic cost-of-capital range.
DEFAULT_ENVIRONMENTS: dict[str, FinancingEnvironment] = {
    "Low risk (stable OECD)": FinancingEnvironment("Low risk (stable OECD)", 0.025, 0.0, 0.005),
    "Medium risk": FinancingEnvironment("Medium risk", 0.03, 0.01, 0.01),
    "High risk (emerging/unstable policy)": FinancingEnvironment(
        "High risk (emerging/unstable policy)", 0.04, 0.03, 0.03
    ),
}


def capital_recovery_factor(wacc: float, lifetime_years: int) -> float:
    """Capital-recovery factor for a given WACC and asset lifetime."""
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    if wacc < 0:
        raise ValueError("wacc must be non-negative")
    if wacc == 0:
        return 1.0 / lifetime_years
    growth = (1.0 + wacc) ** lifetime_years
    return wacc * growth / (growth - 1.0)


def lcoe(te: TechnoEconomics, wacc: float) -> float:
    """Levelized cost of electricity (USD/MWh) for a technology at a given WACC."""
    if not 0 < te.capacity_factor <= 1:
        raise ValueError(f"{te.name}: capacity_factor must be in (0, 1]")
    crf = capital_recovery_factor(wacc, te.lifetime_years)
    annual_capital = crf * te.capex_usd_per_kw  # USD/kW-yr
    annual_fixed = annual_capital + te.fixed_om_usd_per_kw_yr  # USD/kW-yr
    mwh_per_kw_yr = 8760.0 * te.capacity_factor / 1000.0
    fixed_per_mwh = annual_fixed / mwh_per_kw_yr
    return fixed_per_mwh + te.var_om_usd_per_mwh + te.fuel_usd_per_mwh


def lcoe_table(
    environment: FinancingEnvironment,
    technologies: dict[str, TechnoEconomics] | None = None,
) -> pd.DataFrame:
    """LCOE for every technology under one financing environment, sorted cheapest first."""
    techs = technologies or DEFAULT_TECHNO_ECONOMICS
    rows = [
        {
            "environment": environment.name,
            "wacc": round(environment.wacc, 4),
            "technology": te.name,
            "lcoe_usd_mwh": round(lcoe(te, environment.wacc), 1),
        }
        for te in techs.values()
    ]
    return pd.DataFrame(rows).sort_values("lcoe_usd_mwh").reset_index(drop=True)


def wacc_sensitivity(
    technologies: dict[str, TechnoEconomics] | None = None,
    low_wacc: float = 0.03,
    high_wacc: float = 0.10,
) -> pd.DataFrame:
    """How much each technology's LCOE rises from a low to a high cost of capital.

    Capital-intensive technologies show the largest percentage increase; fuel-heavy
    technologies the smallest.
    """
    techs = technologies or DEFAULT_TECHNO_ECONOMICS
    rows = []
    for te in techs.values():
        low = lcoe(te, low_wacc)
        high = lcoe(te, high_wacc)
        rows.append(
            {
                "technology": te.name,
                f"lcoe_at_{int(low_wacc * 100)}pct": round(low, 1),
                f"lcoe_at_{int(high_wacc * 100)}pct": round(high, 1),
                "pct_increase": round((high - low) / low * 100.0, 1),
            }
        )
    return pd.DataFrame(rows).sort_values("pct_increase", ascending=False).reset_index(drop=True)
