"""Portugal electricity mix scenario modelling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScenarioResult:
    source: str
    annual_twh: float
    lifetime_factor: float
    mean_gco2e_kwh: float
    ci_low: float
    ci_high: float


def load_portugal_generation(
    source_path: str | Path | None = None,
) -> pd.DataFrame:
    """Load historical Portugal generation if available locally.

    If ``source_path`` is missing, a small fallback dataset is returned so the workflow can run.
    """
    if source_path is None:
        data = {
            "source": ["Nuclear", "Wind", "Solar", "Hydro", "Storage-backed renewables"],
            "annual_twh": [6.0, 10.0, 5.0, 8.0, 1.0],
        }
        return pd.DataFrame(data)

    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Portugal generation file not found: {path}")
    return pd.read_csv(path)


def emissions_for_mix(
    annual_mix_twh: pd.Series,
    lifecycle_factors: pd.Series,
) -> pd.Series:
    """Convert annual generation mix and lifecycle factors to emissions in GgCO2e."""
    return annual_mix_twh * lifecycle_factors


def build_counterfactuals(
    baseline_mix_twh: pd.Series,
    baseline_factors: pd.Series,
    replacement_sources: dict[str, pd.Series],
    lifecycle_lookup: pd.Series,
) -> pd.DataFrame:
    """Build scenario table replacing baseline nuclear with alternatives."""
    baseline_total = float((baseline_mix_twh * baseline_factors).sum())
    records = []
    for source_name, replacement_profile in replacement_sources.items():
        adjusted = baseline_mix_twh.copy()
        if "Nuclear" not in adjusted.index:
            raise ValueError("Baseline must contain 'Nuclear' to build a replacement scenario.")
        adjusted[source_name] = replacement_profile.get(source_name, adjusted.get(source_name, 0.0))
        adjusted["Nuclear"] = 0.0

        replacement_total = float((adjusted * lifecycle_lookup.reindex(adjusted.index).fillna(0)).sum())
        records.append(
            {
                "scenario": f"Replace nuclear by {source_name}",
                "annual_twh": float(adjusted.sum()),
                "lifecycle_gco2e_gwh": replacement_total,
                "baseline_gco2e_gwh": baseline_total,
                "difference_gco2e_gwh": replacement_total - baseline_total,
                "share_nuclear_twh": 0.0,
            }
        )
    return pd.DataFrame.from_records(records)


def compute_uncertainty_band(
    values: pd.Series,
    n_bootstrap: int = 2_000,
    probability: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap a confidence interval for a vector of emissions values."""
    rng = np.random.default_rng(seed)
    if not 0 < probability < 1:
        raise ValueError("probability must be between 0 and 1.")
    if len(values) == 0:
        return (0.0, 0.0)

    alpha = (1 - probability) / 2
    bootstrap = []
    for _ in range(n_bootstrap):
        sample = rng.choice(values.to_numpy(dtype=float), size=len(values), replace=True)
        bootstrap.append(float(sample.mean()))
    arr = np.array(bootstrap, dtype=float)
    return float(np.quantile(arr, alpha)), float(np.quantile(arr, 1 - alpha))


def run_portugal_scenario(
    generation_path: str | Path | None = None,
    lifecycle_path: str | Path | None = None,
) -> pd.DataFrame:
    """Run a default Portugal counterfactual report table."""
    generation = load_portugal_generation(generation_path).set_index("source")
    annual = generation["annual_twh"]

    if lifecycle_path is None:
        lifecycle = pd.Series(
            {
                "Nuclear": 12.0,
                "Wind": 11.0,
                "Solar": 48.0,
                "Hydro": 24.0,
                "Storage-backed renewables": 20.0,
            }
        )
    else:
        lifecycle = pd.read_csv(lifecycle_path).set_index("technology")["median_gco2e_kwh"]

    baseline_total = float((annual * lifecycle.reindex(annual.index).fillna(0)).sum())
    replacement_sources = {
        "Wind": generation["annual_twh"].reindex(annual.index).fillna(0),
        "Solar": generation["annual_twh"].reindex(annual.index).fillna(0),
        "Hydro": generation["annual_twh"].reindex(annual.index).fillna(0),
        "Storage-backed renewables": generation["annual_twh"].reindex(annual.index).fillna(0),
    }
    scenarios = build_counterfactuals(annual, lifecycle, replacement_sources, lifecycle)
    scenarios["baseline_gco2e_gwh"] = baseline_total
    return scenarios
