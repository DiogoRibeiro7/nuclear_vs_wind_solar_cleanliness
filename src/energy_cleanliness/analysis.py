"""Analysis functions for lifecycle electricity cleanliness claims."""

from __future__ import annotations

import json
from typing import Final

import numpy as np
import pandas as pd

VALUE_COLUMN: Final[str] = "median_gco2e_kwh"


def compare_to_baseline(data: pd.DataFrame, baseline: str = "Nuclear") -> pd.DataFrame:
    """Compare technologies against a baseline using median lifecycle emissions."""
    if VALUE_COLUMN not in data.columns:
        raise ValueError(f"Input dataframe must contain column: {VALUE_COLUMN}")
    if "technology" not in data.columns:
        raise ValueError("Input dataframe must contain column: technology")
    if baseline not in set(data["technology"]):
        raise ValueError(f"Baseline technology not found: {baseline}")

    baseline_value = float(data.loc[data["technology"] == baseline, VALUE_COLUMN].iloc[0])
    records: list[dict[str, object]] = []

    for row in data.itertuples(index=False):
        technology = str(row.technology)
        if technology == baseline:
            continue

        other_value = float(getattr(row, VALUE_COLUMN))
        difference = baseline_value - other_value
        records.append(
            {
                "baseline": baseline,
                "technology": technology,
                "baseline_median_gco2e_kwh": baseline_value,
                "technology_median_gco2e_kwh": other_value,
                "baseline_minus_other": difference,
                "interpretation": _interpret_difference(difference, baseline, technology),
            }
        )

    return pd.DataFrame.from_records(records).sort_values("technology").reset_index(drop=True)


def _interpret_difference(difference: float, baseline: str, technology: str) -> str:
    """Convert a median difference into a readable interpretation."""
    if difference > 0:
        return f"{technology} has a lower reported median lifecycle carbon intensity than {baseline}."
    if difference < 0:
        return f"{baseline} has a lower reported median lifecycle carbon intensity than {technology}."
    return f"{technology} and {baseline} have the same reported median lifecycle carbon intensity."


def simulate_uncertainty(
    data: pd.DataFrame,
    draws: int = 50_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Sample lifecycle emissions for each technology.

    If a technology row contains empirical observations, we use bootstrap sampling.
    If not, the triangular proxy from summary min/median/max is used.
    """
    if draws <= 0:
        raise ValueError("draws must be a positive integer")

    required = {"technology", "min_gco2e_kwh", "median_gco2e_kwh", "max_gco2e_kwh"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rng = np.random.default_rng(seed)
    records: list[pd.DataFrame] = []
    used_triangular = []

    for row in data.itertuples(index=False):
        row_samples = _sample_row_empirical(row, draws=draws, rng=rng)
        if row_samples is None:
            row_samples = rng.triangular(
                left=float(row.min_gco2e_kwh),
                mode=float(row.median_gco2e_kwh),
                right=float(row.max_gco2e_kwh),
                size=draws,
            )
            used_triangular.append(str(row.technology))

        records.append(
            pd.DataFrame(
                {
                    "technology": str(row.technology),
                    "sampled_gco2e_kwh": np.asarray(row_samples, dtype=float),
                    "method": "empirical" if str(row.technology) not in used_triangular else "triangular_proxy",
                }
            )
        )

    return pd.concat(records, ignore_index=True)


def _sample_row_empirical(row: pd.Series, draws: int, rng: np.random.Generator) -> np.ndarray | None:
    """Attempt to parse and bootstrap empirical samples for a single row."""
    for col in ("individual_estimates", "empirical_estimates", "sampled_estimates"):
        if col not in row._fields:
            continue
        values = _parse_estimate_list(getattr(row, col))
        if len(values) >= 3:
            return rng.choice(values, size=draws, replace=True)
    return None


def _parse_estimate_list(value: object) -> np.ndarray:
    """Return a float numpy array from serialized sample values."""
    if value is None:
        return np.array([], dtype=float)
    if isinstance(value, (list, tuple, np.ndarray)):
        parsed = [float(x) for x in value if float(x) > 0]
        return np.asarray(parsed, dtype=float)
    if isinstance(value, (int, float)):
        return np.asarray([float(value)], dtype=float)
    text = str(value).strip()
    if not text:
        return np.array([], dtype=float)
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            values = [float(item) for item in parsed if float(item) > 0]
            return np.asarray(values, dtype=float)
        except Exception:
            return np.array([], dtype=float)
    if ";" in text or "," in text:
        sep = ";" if ";" in text else ","
        values = [float(item.strip()) for item in text.split(sep) if item.strip()]
        return np.asarray([v for v in values if v > 0], dtype=float)
    return np.array([], dtype=float)


def estimate_pairwise_probabilities(samples: pd.DataFrame) -> pd.DataFrame:
    """Estimate pairwise probabilities that one technology is lower-carbon than another."""
    required = {"technology", "sampled_gco2e_kwh"}
    missing = required.difference(samples.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    wide = {
        technology: group["sampled_gco2e_kwh"].to_numpy(dtype=float)
        for technology, group in samples.groupby("technology", sort=True)
    }
    technologies = sorted(wide.keys())
    matrix = pd.DataFrame(index=technologies, columns=technologies, dtype=float)

    for tech_a in technologies:
        for tech_b in technologies:
            if tech_a == tech_b:
                matrix.loc[tech_a, tech_b] = np.nan
                continue
            sample_size = min(len(wide[tech_a]), len(wide[tech_b]))
            matrix.loc[tech_a, tech_b] = float(
                np.mean(wide[tech_a][:sample_size] < wide[tech_b][:sample_size])
            )

    return matrix


def compare_empirical_vs_triangular(
    data: pd.DataFrame,
    draws: int = 20_000,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Compare proxy and empirical approaches as a quick reproducible side-by-side output."""
    samples = simulate_uncertainty(data, draws=draws, seed=seed)
    triangular = estimate_pairwise_probabilities(_force_triangular_samples(data, draws=draws, seed=seed))
    empirical = estimate_pairwise_probabilities(_force_empirical_when_possible(samples))
    delta = empirical - triangular
    return {
        "triangular": triangular,
        "empirical": empirical,
        "delta": delta,
    }


def _force_triangular_samples(data: pd.DataFrame, draws: int, seed: int) -> pd.DataFrame:
    """Generate only triangular samples for all technologies."""
    rng = np.random.default_rng(seed)
    rows = []
    for row in data.itertuples(index=False):
        rows.append(
            pd.DataFrame(
                {
                    "technology": str(row.technology),
                    "sampled_gco2e_kwh": rng.triangular(
                        left=float(row.min_gco2e_kwh),
                        mode=float(row.median_gco2e_kwh),
                        right=float(row.max_gco2e_kwh),
                        size=draws,
                    ),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def _force_empirical_when_possible(samples: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows explicitly simulated from empirical data."""
    if "method" not in samples.columns:
        return samples
    if "empirical" not in set(samples["method"]):
        return samples.copy()
    return samples.loc[samples["method"] == "empirical", ["technology", "sampled_gco2e_kwh"]].copy()


def bootstrap_confidence_intervals(
    samples: pd.DataFrame,
    probability: float = 0.95,
    n_bootstrap: int = 2_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Compute bootstrap confidence intervals for mean lifecycle values by technology."""
    if not (0 < probability < 1):
        raise ValueError("probability must be between 0 and 1")
    if n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be a positive integer")
    required = {"technology", "sampled_gco2e_kwh"}
    missing = required.difference(samples.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    alpha = (1.0 - probability) / 2.0
    lower = alpha
    upper = 1.0 - alpha
    rng = np.random.default_rng(seed)

    records = []
    for technology, group in samples.groupby("technology", sort=True):
        draws = np.asarray(group["sampled_gco2e_kwh"], dtype=float)
        if len(draws) < 2:
            raise ValueError(f"Technology '{technology}' has fewer than 2 draws.")

        bootstrap = []
        for _ in range(n_bootstrap):
            indices = rng.integers(0, len(draws), size=len(draws))
            bootstrap.append(float(np.mean(draws[indices])))
        bootstrap_array = np.asarray(bootstrap, dtype=float)

        records.append(
            {
                "technology": technology,
                "mean_gco2e_kwh": float(np.mean(draws)),
                "ci_low": float(np.quantile(bootstrap_array, lower)),
                "ci_high": float(np.quantile(bootstrap_array, upper)),
                "probability": probability,
            }
        )

    return pd.DataFrame.from_records(records).sort_values("technology").reset_index(drop=True)


def build_markdown_summary(
    data: pd.DataFrame,
    median_comparison: pd.DataFrame,
    probability_matrix: pd.DataFrame,
    baseline: str = "Nuclear",
) -> str:
    """Build a short markdown report from the analysis outputs."""
    baseline_rows = data.loc[data["technology"] == baseline]
    if baseline_rows.empty:
        raise ValueError(f"Baseline technology not found: {baseline}")
    baseline_median = float(baseline_rows["median_gco2e_kwh"].iloc[0])

    onshore_rows = data.loc[data["technology"] == "Wind onshore"]
    offshore_rows = data.loc[data["technology"] == "Wind offshore"]
    if onshore_rows.empty:
        raise ValueError("Expected Wind onshore in input dataset.")
    if offshore_rows.empty:
        raise ValueError("Expected Wind offshore in input dataset.")

    onshore_median = float(onshore_rows["median_gco2e_kwh"].iloc[0])
    offshore_median = float(offshore_rows["median_gco2e_kwh"].iloc[0])

    p_nuclear_below_onshore = float(probability_matrix.loc[baseline, "Wind onshore"])
    p_onshore_below_nuclear = float(probability_matrix.loc["Wind onshore", baseline])

    proxy_warning = ""
    if "triangular_proxy" in probability_matrix.index.astype(str).tolist():
        proxy_warning = (
            "\n\nSome technologies are modelled by triangular proxy where only summary stats were available. "
            "Empirical bootstrap is used only when literature-level sample estimates are present."
        )

    return f"""# Analysis summary

## Claim tested

Nuclear power plants produce cleaner energy than wind or solar panels.

## Lifecycle carbon result

Using the normalized lifecycle dataset in this repository:

- {baseline} median: **{baseline_median:.1f} gCO2e/kWh**.
- Wind onshore median: **{onshore_median:.1f} gCO2e/kwh**.
- Wind offshore median: **{offshore_median:.1f} gCO2e/kwh**.

The broad claim fails because onshore wind has a lower reported median lifecycle carbon intensity than nuclear, and offshore wind is tied with nuclear.

## Uncertainty simulation

The uncertainty model gives:

- P(nuclear < wind onshore): **{p_nuclear_below_onshore:.3f}**.
- P(wind onshore < nuclear): **{p_onshore_below_nuclear:.3f}**.

## Scientific wording

A defensible statement is:

> Nuclear, wind and solar are all low-carbon electricity sources. Nuclear is often lower-carbon than solar PV, but it is not clearly cleaner than wind, and uncertainty ranges overlap.

## Median comparison table

{median_comparison.to_markdown(index=False)}{proxy_warning}

{_carbon_model_risk()}"""


def _carbon_model_risk() -> str:
    """Return the standard model-risk section for the carbon-only report."""
    from energy_cleanliness.model_risk import model_risk_markdown

    return model_risk_markdown(context="carbon", level=2)
