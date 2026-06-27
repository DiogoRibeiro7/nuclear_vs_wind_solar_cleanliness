
"""Analysis functions for lifecycle electricity cleanliness claims."""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

VALUE_COLUMN: Final[str] = "median_gco2e_kwh"


def compare_to_baseline(data: pd.DataFrame, baseline: str = "Nuclear") -> pd.DataFrame:
    """Compare technologies against a baseline using median lifecycle emissions.

    Parameters
    ----------
    data:
        Lifecycle emissions dataframe.
    baseline:
        Technology used as the reference comparison.

    Returns
    -------
    pandas.DataFrame
        One row per non-baseline technology. A positive `baseline_minus_other` means
        the other technology has a lower median lifecycle carbon intensity than the baseline.
    """
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
        return f"{technology} has a lower median lifecycle carbon intensity than {baseline}."
    if difference < 0:
        return f"{baseline} has a lower median lifecycle carbon intensity than {technology}."
    return f"{technology} and {baseline} have the same reported median lifecycle carbon intensity."


def simulate_uncertainty(
    data: pd.DataFrame,
    draws: int = 50_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Sample proxy lifecycle emissions from reported min/median/max ranges.

    The IPCC values are summary statistics from literature estimates. This function uses a
    triangular proxy distribution with the reported median used as the central value. This is
    not a reconstruction of the original empirical distribution. It is a transparent sensitivity
    check to avoid pretending that one median value tells the whole story.

    Parameters
    ----------
    data:
        Lifecycle emissions dataframe.
    draws:
        Number of Monte Carlo samples per technology.
    seed:
        Random seed for reproducibility.

    Returns
    -------
    pandas.DataFrame
        Long dataframe with sampled lifecycle emissions.
    """
    if draws <= 0:
        raise ValueError("draws must be a positive integer")

    required = {"technology", "min_gco2e_kwh", "median_gco2e_kwh", "max_gco2e_kwh"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rng = np.random.default_rng(seed)
    records: list[pd.DataFrame] = []

    for row in data.itertuples(index=False):
        samples = rng.triangular(
            left=float(row.min_gco2e_kwh),
            mode=float(row.median_gco2e_kwh),
            right=float(row.max_gco2e_kwh),
            size=draws,
        )
        records.append(
            pd.DataFrame(
                {
                    "technology": str(row.technology),
                    "sampled_gco2e_kwh": samples,
                }
            )
        )

    return pd.concat(records, ignore_index=True)


def estimate_pairwise_probabilities(samples: pd.DataFrame) -> pd.DataFrame:
    """Estimate pairwise probabilities that one technology is lower-carbon than another.

    Parameters
    ----------
    samples:
        Long dataframe returned by :func:`simulate_uncertainty`.

    Returns
    -------
    pandas.DataFrame
        Square matrix where cell (A, B) is P(A < B), meaning the probability that A has a
        lower sampled lifecycle carbon intensity than B.
    """
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


def build_markdown_summary(
    data: pd.DataFrame,
    median_comparison: pd.DataFrame,
    probability_matrix: pd.DataFrame,
    baseline: str = "Nuclear",
) -> str:
    """Build a short markdown report from the analysis outputs."""
    baseline_median = float(data.loc[data["technology"] == baseline, "median_gco2e_kwh"].iloc[0])
    onshore_median = float(
        data.loc[data["technology"] == "Wind onshore", "median_gco2e_kwh"].iloc[0]
    )
    offshore_median = float(
        data.loc[data["technology"] == "Wind offshore", "median_gco2e_kwh"].iloc[0]
    )

    p_nuclear_below_onshore = float(probability_matrix.loc[baseline, "Wind onshore"])
    p_onshore_below_nuclear = float(probability_matrix.loc["Wind onshore", baseline])

    return f"""# Analysis summary

## Claim tested

Nuclear power plants produce cleaner energy than wind or solar panels.

## Lifecycle carbon result

Using the IPCC AR5 lifecycle greenhouse-gas data included in this repository:

- {baseline} median: **{baseline_median:.1f} gCO2e/kWh**.
- Wind onshore median: **{onshore_median:.1f} gCO2e/kWh**.
- Wind offshore median: **{offshore_median:.1f} gCO2e/kWh**.

The broad claim fails because onshore wind has a lower reported median lifecycle carbon intensity than nuclear, and offshore wind is tied with nuclear.

## Uncertainty simulation

The triangular proxy simulation gives:

- P(nuclear < wind onshore): **{p_nuclear_below_onshore:.3f}**.
- P(wind onshore < nuclear): **{p_onshore_below_nuclear:.3f}**.

This is not a reconstruction of the original literature distribution. It is a sensitivity check using the reported min / median / max ranges.

## Scientific wording

A defensible statement is:

> Nuclear, wind and solar are all low-carbon electricity sources. Nuclear is often lower-carbon than solar PV, but it is not clearly cleaner than wind, and uncertainty ranges overlap.

## Median comparison table

{median_comparison.to_markdown(index=False)}
"""
