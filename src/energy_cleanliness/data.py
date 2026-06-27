
"""Data loading and normalization utilities for lifecycle emissions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS: set[str] = {
    "source",
    "publication_year",
    "technology",
    "technology_family",
    "lifecycle_stage",
    "min_gco2e_kwh",
    "q1_gco2e_kwh",
    "median_gco2e_kwh",
    "mean_gco2e_kwh",
    "q3_gco2e_kwh",
    "max_gco2e_kwh",
    "notes",
}


def load_lifecycle_data(path: str | Path) -> pd.DataFrame:
    """Load and validate lifecycle emissions data.

    The repo keeps backward-compatible support for the earlier CSV layout used by the
    original seed dataset (which only had min/median/max columns). When legacy files are
    found, they are normalized to the expanded schema.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Lifecycle data file not found: {csv_path}")

    data = pd.read_csv(csv_path)
    return validate_and_normalize_lifecycle_data(data)


def validate_and_normalize_lifecycle_data(
    data: pd.DataFrame,
    *,
    default_publication_year: int = 2014,
    default_stage: str = "full_lifecycle",
) -> pd.DataFrame:
    """Validate lifecycle data and normalize old/new schemas to canonical columns."""
    normalized = data.copy()

    # Backward compatibility for the original seed columns.
    if "group" in normalized.columns and "technology_family" not in normalized.columns:
        normalized["technology_family"] = normalized["group"]
    if "publication_year" not in normalized.columns:
        normalized["publication_year"] = default_publication_year
    if "lifecycle_stage" not in normalized.columns:
        normalized["lifecycle_stage"] = default_stage
    if "q1_gco2e_kwh" not in normalized.columns:
        normalized["q1_gco2e_kwh"] = pd.NA
    if "mean_gco2e_kwh" not in normalized.columns:
        normalized["mean_gco2e_kwh"] = pd.NA
    if "q3_gco2e_kwh" not in normalized.columns:
        normalized["q3_gco2e_kwh"] = pd.NA
    if "notes" not in normalized.columns:
        normalized["notes"] = ""
    if "source" not in normalized.columns and "references" in normalized.columns:
        normalized["source"] = normalized["references"]

    missing_columns = REQUIRED_COLUMNS.difference(normalized.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    for column in [
        "technology",
        "technology_family",
        "lifecycle_stage",
        "source",
        "notes",
    ]:
        normalized[column] = normalized[column].astype(str).str.strip()

    for column in [
        "min_gco2e_kwh",
        "q1_gco2e_kwh",
        "median_gco2e_kwh",
        "mean_gco2e_kwh",
        "q3_gco2e_kwh",
        "max_gco2e_kwh",
    ]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["publication_year"] = pd.to_numeric(normalized["publication_year"], errors="raise").astype(
        "Int64"
    )

    normalized = _validate_lifecycle_units_and_ranges(normalized)
    normalized = _drop_or_fail_duplicates(normalized)

    return normalized.sort_values("median_gco2e_kwh").reset_index(drop=True)


def _validate_lifecycle_units_and_ranges(data: pd.DataFrame) -> pd.DataFrame:
    """Check units are plausible and numeric ranges are internally consistent."""
    bad_values = data[["min_gco2e_kwh", "q1_gco2e_kwh", "median_gco2e_kwh", "mean_gco2e_kwh", "q3_gco2e_kwh", "max_gco2e_kwh"]]
    if (bad_values.lt(0).any().any()):
        bad_technology = data.loc[bad_values.lt(0).any(axis=1), "technology"].tolist()
        raise ValueError(f"Negative lifecycle emissions values found for: {bad_technology}")

    def _out_of_order(group: pd.Series) -> bool:
        values = group.dropna().sort_values()
        values = values.tolist()
        return values != sorted(values)

    invalid = []
    for _, row in data.iterrows():
        values = pd.Series(
            [
                row["min_gco2e_kwh"],
                row["q1_gco2e_kwh"],
                row["median_gco2e_kwh"],
                row["mean_gco2e_kwh"],
                row["q3_gco2e_kwh"],
                row["max_gco2e_kwh"],
            ],
            dtype="float",
        )
        present = values.dropna()
        if present.empty:
            continue

        if present.iloc[0] != values.loc[0]:
            # min should always be the minimum.
            invalid.append(row["technology"])
            continue
        if values.loc[2] > values.loc[5]:
            invalid.append(row["technology"])
            continue
        # If all of q1/q3/mean present, enforce a basic consistency chain.
        q1, median, mean, q3 = row["q1_gco2e_kwh"], row["median_gco2e_kwh"], row["mean_gco2e_kwh"], row["q3_gco2e_kwh"]
        if pd.notna(q1) and pd.notna(median) and q1 > median:
            invalid.append(row["technology"])
        if pd.notna(mean) and pd.notna(q3) and mean > q3:
            invalid.append(row["technology"])

    if invalid:
        raise ValueError(f"Invalid lifecycle emission sequences for: {sorted(set(invalid))}")
    return data.reset_index(drop=True)


def _drop_or_fail_duplicates(data: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "source",
        "publication_year",
        "technology",
        "technology_family",
        "lifecycle_stage",
    ]
    duplicates = data[data.duplicated(subset=keys, keep=False)]
    if not duplicates.empty:
        raise ValueError(
            "Duplicate records detected in normalized lifecycle dataset for same source/year/technology/family/stage."
        )
    return data


def normalize_empirical_samples(raw: str | list[float] | float) -> list[float]:
    """Normalize a semicolon, comma, or JSON encoded list of sample estimates."""
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, (int, float)):
        return [float(raw)]
    if not isinstance(raw, str):
        return []
    text = raw.strip()
    if not text:
        return []

    for candidate in (",", ";"):
        if candidate in text:
            return [float(item.strip()) for item in text.split(candidate) if item.strip()]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [float(item) for item in parsed if isinstance(item, (int, float, str))]
    except Exception:
        return []
    return []
