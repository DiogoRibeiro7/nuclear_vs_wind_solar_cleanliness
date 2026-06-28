"""Source-specific parsers and normalized lifecycle dataset writers."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from energy_cleanliness.data import validate_and_normalize_lifecycle_data


def parse_unece_csv(path: str | Path, publication_year: int = 2026) -> pd.DataFrame:
    """Parse UNECE exports with a common emissions-column naming style."""
    df = _read_csv(path)
    column_map = {
        "Technology": "technology",
        "Tech": "technology",
        "Family": "technology_family",
        "Family of technology": "technology_family",
        "Lifecycle stage": "lifecycle_stage",
        "Source": "source",
        "Year": "publication_year",
        "Min gCO2e/kWh": "min_gco2e_kwh",
        "Q1 gCO2e/kWh": "q1_gco2e_kwh",
        "Median gCO2e/kWh": "median_gco2e_kwh",
        "Mean gCO2e/kWh": "mean_gco2e_kwh",
        "Q3 gCO2e/kWh": "q3_gco2e_kwh",
        "Max gCO2e/kWh": "max_gco2e_kwh",
        "Notes": "notes",
    }
    df = _rename_known_columns(df, column_map)
    df["publication_year"] = df.get("publication_year", pd.Series([publication_year] * len(df)))
    return validate_and_normalize_lifecycle_data(df, default_publication_year=publication_year)


def parse_oedi_csv(path: str | Path, publication_year: int = 2026) -> pd.DataFrame:
    """Parse NREL / OEDI-style lifecycle exports."""
    df = _read_csv(path)
    column_map = {
        "tech": "technology",
        "technology_name": "technology",
        "technology_family": "technology_family",
        "lifecycle_scope": "lifecycle_stage",
        "source_name": "source",
        "year": "publication_year",
        "min": "min_gco2e_kwh",
        "q25": "q1_gco2e_kwh",
        "median": "median_gco2e_kwh",
        "mean": "mean_gco2e_kwh",
        "q75": "q3_gco2e_kwh",
        "max": "max_gco2e_kwh",
        "comment": "notes",
    }
    df = _rename_known_columns(df, column_map)
    df["publication_year"] = df.get("publication_year", pd.Series([publication_year] * len(df)))
    return validate_and_normalize_lifecycle_data(df, default_publication_year=publication_year)


def parse_owid_csv(path: str | Path, publication_year: int = 2025) -> pd.DataFrame:
    """Parse Our World in Data-style export files."""
    df = _read_csv(path)
    column_map = {
        "Entity": "technology",
        "Code": "source",
        "Year": "publication_year",
        "technology_family": "technology_family",
        "Minimum": "min_gco2e_kwh",
        "Q1": "q1_gco2e_kwh",
        "Median": "median_gco2e_kwh",
        "Mean": "mean_gco2e_kwh",
        "Q3": "q3_gco2e_kwh",
        "Maximum": "max_gco2e_kwh",
        "Comments": "notes",
    }
    df = _rename_known_columns(df, column_map)
    df["publication_year"] = df.get("publication_year", pd.Series([publication_year] * len(df)))
    return validate_and_normalize_lifecycle_data(df, default_publication_year=publication_year)


def load_legacy_seed_dataset(path: str | Path) -> pd.DataFrame:
    """Normalize the original repo seed CSV into the expanded schema."""
    df = _read_csv(path)
    df = df.rename(columns={"group": "technology_family"})
    df["publication_year"] = df.get("publication_year", 2014)
    df["lifecycle_stage"] = "full_lifecycle"
    return validate_and_normalize_lifecycle_data(df, default_publication_year=2014)


def merge_normalized_sources(*datasets: pd.DataFrame) -> pd.DataFrame:
    """Merge multiple normalized lifecycle tables and sort by median emissions."""
    if not datasets:
        raise ValueError("At least one dataset is required.")
    merged = pd.concat(datasets, ignore_index=True)
    return merged.sort_values("median_gco2e_kwh").reset_index(drop=True)


def write_processed_dataset(data: pd.DataFrame, output_path: str | Path) -> None:
    """Write processed normalized CSV for downstream analysis."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False)


def discover_raw_sources(raw_dir: str | Path) -> dict[str, list[Path]]:
    """Map supported data sources in a raw directory by filename heuristic."""
    root = Path(raw_dir)
    discovered = {"unece": [], "oedi": [], "owid": [], "legacy": []}
    for file in sorted(root.glob("*.csv")):
        name = file.name.lower()
        if re.search(r"unece|united|epl", name):
            discovered["unece"].append(file)
        elif re.search(r"oedi|nrel", name):
            discovered["oedi"].append(file)
        elif re.search(r"owid|our", name):
            discovered["owid"].append(file)
        elif "ipcc" in name or "lifecycle" in name:
            discovered["legacy"].append(file)
    return discovered


def build_normalized_dataset(
    raw_dir: str | Path,
    output_path: str | Path,
    publication_years: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Build one normalized dataset from every available raw source."""
    publication_years = publication_years or {}
    sources = discover_raw_sources(raw_dir)
    frames = []

    for file in sources["legacy"]:
        frames.append(load_legacy_seed_dataset(file))
    for file in sources["unece"]:
        frames.append(parse_unece_csv(file, publication_year=publication_years.get("unece", 2024)))
    for file in sources["oedi"]:
        frames.append(parse_oedi_csv(file, publication_year=publication_years.get("oedi", 2024)))
    for file in sources["owid"]:
        frames.append(parse_owid_csv(file, publication_year=publication_years.get("owid", 2024)))

    if not frames:
        raise FileNotFoundError(f"No supported lifecycle source files found in {raw_dir}")

    merged = merge_normalized_sources(*frames)
    merged = merged.drop_duplicates(
        subset=["source", "publication_year", "technology", "technology_family", "lifecycle_stage"]
    )
    write_processed_dataset(merged, output_path)
    return merged


def _rename_known_columns(data: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    return data.rename(columns=column_map)


def _read_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Raw source file not found: {csv_path}")
    return pd.read_csv(csv_path)
