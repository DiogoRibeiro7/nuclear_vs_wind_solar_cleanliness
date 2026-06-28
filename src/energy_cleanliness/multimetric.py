"""Loading, schema validation and reshaping of the multi-metric cleanliness profile.

The multi-metric reference dataset is a long/tidy table (one row per
``(technology, metric)``) carrying an explicit uncertainty range (``low/central/high``)
and a ``schema_version``. Validation fails fast when columns, units, technologies or
metrics are missing or misaligned, which prevents the class of silent column-shift bug
that the earlier wide CSV allowed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED_SCHEMA_VERSIONS: set[str] = {"1.0"}

REQUIRED_COLUMNS: list[str] = [
    "schema_version",
    "technology",
    "metric",
    "unit",
    "direction",
    "low",
    "central",
    "high",
    "year",
    "source_id",
    "notes",
]

VALID_DIRECTIONS: set[str] = {"lower_better", "higher_better"}

# Canonical metric -> expected unit. Acts as both a known-metric whitelist and a
# unit-consistency check.
METRIC_UNITS: dict[str, str] = {
    "lifecycle_co2e": "gco2e_kwh",
    "direct_deaths": "deaths_per_twh",
    "air_pollution_deaths": "deaths_per_twh",
    "waste_persistence": "index_0_15",
    "water_use": "m3_mwh",
    "land_use": "m2_mwh",
    "material_intensity": "index_rel",
    "construction_time": "years",
    "capacity_factor": "fraction",
    "grid_integration": "index_0_1",
    "levelized_cost": "usd_mwh",
    "financing_risk": "index_0_1",
}

EXPECTED_TECHNOLOGIES: set[str] = {
    "Nuclear",
    "Wind onshore",
    "Wind offshore",
    "Solar PV rooftop",
    "Solar PV utility",
}


class SchemaValidationError(ValueError):
    """Raised when the multi-metric profile violates the documented schema."""


def load_multimetric_profile(path: str | Path) -> pd.DataFrame:
    """Load and validate the long-format multi-metric cleanliness profile.

    Returns the validated long dataframe with numeric ``low/central/high`` columns.
    Raises :class:`SchemaValidationError` on any schema violation.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Multi-metric profile not found: {csv_path}")

    data = pd.read_csv(csv_path)
    return validate_multimetric_profile(data)


def validate_multimetric_profile(data: pd.DataFrame) -> pd.DataFrame:
    """Validate a long-format multi-metric profile against the documented schema."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        raise SchemaValidationError(f"Missing required columns: {missing_columns}")

    profile = data[REQUIRED_COLUMNS].copy()

    versions = set(profile["schema_version"].astype(str).unique())
    unsupported = versions - SUPPORTED_SCHEMA_VERSIONS
    if unsupported:
        raise SchemaValidationError(
            f"Unsupported schema_version(s) {sorted(unsupported)}; "
            f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    text_columns = ("schema_version", "technology", "metric", "unit", "direction", "source_id")
    for column in text_columns:
        profile[column] = profile[column].astype(str).str.strip()

    bad_direction = sorted(set(profile["direction"]) - VALID_DIRECTIONS)
    if bad_direction:
        raise SchemaValidationError(f"Invalid direction value(s): {bad_direction}")

    unknown_metrics = sorted(set(profile["metric"]) - set(METRIC_UNITS))
    if unknown_metrics:
        raise SchemaValidationError(f"Unknown metric key(s): {unknown_metrics}")

    # Unit consistency per metric.
    for metric, group in profile.groupby("metric"):
        expected_unit = METRIC_UNITS[metric]
        bad_units = sorted(set(group["unit"]) - {expected_unit})
        if bad_units:
            raise SchemaValidationError(
                f"Metric '{metric}' expects unit '{expected_unit}', got {bad_units}"
            )

    for column in ("low", "central", "high", "year"):
        profile[column] = pd.to_numeric(profile[column], errors="coerce")
    if profile[["low", "central", "high"]].isna().to_numpy().any():
        raise SchemaValidationError("Non-numeric value in low/central/high columns.")

    if (profile[["low", "central", "high"]] < 0).to_numpy().any():
        raise SchemaValidationError("Negative low/central/high values are not allowed.")

    ordered = (profile["low"] <= profile["central"]) & (profile["central"] <= profile["high"])
    if not ordered.all():
        offenders = profile.loc[~ordered, ["technology", "metric"]].to_dict("records")
        raise SchemaValidationError(f"Range must satisfy low<=central<=high. Offenders: {offenders}")

    # Completeness: every expected technology must carry every known metric exactly once.
    duplicates = profile.duplicated(subset=["technology", "metric"], keep=False)
    if duplicates.any():
        dup = profile.loc[duplicates, ["technology", "metric"]].to_dict("records")
        raise SchemaValidationError(f"Duplicate (technology, metric) rows: {dup}")

    present = set(zip(profile["technology"], profile["metric"]))
    required = {(tech, metric) for tech in EXPECTED_TECHNOLOGIES for metric in METRIC_UNITS}
    missing_cells = sorted(required - present)
    if missing_cells:
        raise SchemaValidationError(f"Missing (technology, metric) cells: {missing_cells}")
    unexpected_tech = sorted(set(profile["technology"]) - EXPECTED_TECHNOLOGIES)
    if unexpected_tech:
        raise SchemaValidationError(f"Unexpected technology label(s): {unexpected_tech}")

    return profile.reset_index(drop=True)


def metric_directions(profile: pd.DataFrame) -> dict[str, str]:
    """Return a ``{metric: direction}`` mapping from a validated profile."""
    return (
        profile.drop_duplicates("metric").set_index("metric")["direction"].to_dict()
    )


def higher_is_better_set(profile: pd.DataFrame) -> set[str]:
    """Return the set of metrics where larger values are cleaner."""
    directions = metric_directions(profile)
    return {metric for metric, direction in directions.items() if direction == "higher_better"}


def to_wide(profile: pd.DataFrame, value: str = "central") -> pd.DataFrame:
    """Pivot the long profile into a wide ``technology`` x ``metric`` table.

    ``value`` selects which of ``low/central/high`` populates the cells. The returned
    frame has a ``technology`` column plus one column per metric, suitable for the
    point-estimate functions in :mod:`energy_cleanliness.cleanliness_index`.
    """
    if value not in {"low", "central", "high"}:
        raise ValueError("value must be one of 'low', 'central', 'high'")
    wide = profile.pivot(index="technology", columns="metric", values=value)
    wide = wide.reset_index()
    wide.columns.name = None
    return wide
