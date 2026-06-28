"""Config-driven multi-region electricity counterfactual runner.

A *region config* (JSON) describes a baseline generation mix and a counterfactual
question: "if we retire one source and its energy is absorbed by an alternative, how do
annual lifecycle emissions change?" The runner conserves total generation (the retired
TWh moves to the replacement) and reports the emissions delta per replacement.

This generalises the original Portugal-only script into a reusable runner over any number
of region configs under ``data/regions/``.

Emissions unit: 1 TWh x 1 gCO2e/kWh = 1e9 g = 1 ktCO2e, so totals are in **ktCO2e/year**.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# IPCC AR5 WG3 Annex III lifecycle median emissions (gCO2e/kWh) for common grid sources.
# Region configs may override any of these via ``lifecycle_overrides``.
DEFAULT_LIFECYCLE_GCO2E_KWH: dict[str, float] = {
    "Nuclear": 12.0,
    "Wind": 11.0,
    "Wind onshore": 11.0,
    "Wind offshore": 12.0,
    "Solar": 48.0,
    "Solar PV utility": 48.0,
    "Solar PV rooftop": 41.0,
    "Hydro": 24.0,
    "Geothermal": 38.0,
    "Biomass": 230.0,
    "Gas": 490.0,
    "Oil": 650.0,
    "Coal": 820.0,
    "Lignite": 1100.0,
    "Storage-backed renewables": 30.0,
}


class RegionConfigError(ValueError):
    """Raised when a region config is missing fields or is internally inconsistent."""


@dataclass(frozen=True)
class RegionConfig:
    """A validated region counterfactual configuration.

    ``retire_sources`` is always a tuple; a config may set ``retire_source`` to a single
    string or a list of strings (e.g. lignite + hard coal retired together).
    """

    name: str
    generation_twh: dict[str, float]
    retire_sources: tuple[str, ...]
    replacements: list[str]
    year: int | None = None
    lifecycle_overrides: dict[str, float] = field(default_factory=dict)


def load_region_config(path: str | Path) -> RegionConfig:
    """Load and validate a single region config from a JSON file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Region config not found: {config_path}")
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return _validate_region_config(raw, source=str(config_path))


def _validate_region_config(raw: dict, source: str) -> RegionConfig:
    required = {"name", "generation_twh", "retire_source", "replacements"}
    missing = required - set(raw)
    if missing:
        raise RegionConfigError(f"{source}: missing fields {sorted(missing)}")

    generation = raw["generation_twh"]
    if not isinstance(generation, dict) or not generation:
        raise RegionConfigError(f"{source}: 'generation_twh' must be a non-empty object")
    generation_twh: dict[str, float] = {}
    for tech, value in generation.items():
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise RegionConfigError(f"{source}: non-numeric generation for '{tech}'") from error
        if number < 0:
            raise RegionConfigError(f"{source}: negative generation for '{tech}'")
        generation_twh[str(tech)] = number

    retire_raw = raw["retire_source"]
    if isinstance(retire_raw, str):
        retire_list = [retire_raw]
    elif isinstance(retire_raw, list) and retire_raw:
        retire_list = [str(item) for item in retire_raw]
    else:
        raise RegionConfigError(
            f"{source}: 'retire_source' must be a non-empty string or list of strings"
        )
    retire_sources = tuple(retire_list)
    for retired in retire_sources:
        if retired not in generation_twh:
            raise RegionConfigError(
                f"{source}: retire_source '{retired}' not present in generation_twh"
            )

    replacements = raw["replacements"]
    if not isinstance(replacements, list) or not replacements:
        raise RegionConfigError(f"{source}: 'replacements' must be a non-empty list")
    replacements = [str(item) for item in replacements]

    overrides = raw.get("lifecycle_overrides", {}) or {}
    if not isinstance(overrides, dict):
        raise RegionConfigError(f"{source}: 'lifecycle_overrides' must be an object")
    lifecycle_overrides = {str(k): float(v) for k, v in overrides.items()}

    year = raw.get("year")
    year = int(year) if year is not None else None

    return RegionConfig(
        name=str(raw["name"]),
        generation_twh=generation_twh,
        retire_sources=retire_sources,
        replacements=replacements,
        year=year,
        lifecycle_overrides=lifecycle_overrides,
    )


def discover_region_configs(directory: str | Path) -> list[Path]:
    """Return sorted region config JSON paths under ``directory``."""
    root = Path(directory)
    if not root.exists():
        raise FileNotFoundError(f"Region config directory not found: {root}")
    return sorted(root.glob("*.json"))


def _factor_for(source: str, config: RegionConfig) -> float:
    if source in config.lifecycle_overrides:
        return config.lifecycle_overrides[source]
    if source in DEFAULT_LIFECYCLE_GCO2E_KWH:
        return DEFAULT_LIFECYCLE_GCO2E_KWH[source]
    raise RegionConfigError(
        f"{config.name}: no lifecycle factor for '{source}'. "
        f"Add it to 'lifecycle_overrides' in the region config."
    )


def total_emissions_ktco2e(generation_twh: dict[str, float], config: RegionConfig) -> float:
    """Annual lifecycle emissions (ktCO2e) for a generation mix under ``config`` factors."""
    return float(sum(twh * _factor_for(source, config) for source, twh in generation_twh.items()))


def build_region_counterfactuals(config: RegionConfig) -> pd.DataFrame:
    """Build the baseline + replacement counterfactual table for one region.

    Total generation is conserved: the retired source's TWh is absorbed by each
    candidate replacement in turn.
    """
    baseline = dict(config.generation_twh)
    baseline_emissions = total_emissions_ktco2e(baseline, config)
    retired_twh = float(sum(baseline[source] for source in config.retire_sources))
    retired_label = "+".join(config.retire_sources)

    records: list[dict[str, object]] = [
        {
            "region": config.name,
            "year": config.year,
            "scenario": "Baseline",
            "retired_source": retired_label,
            "replacement": "",
            "moved_twh": 0.0,
            "annual_ktco2e": round(baseline_emissions, 2),
            "delta_ktco2e": 0.0,
            "pct_change": 0.0,
        }
    ]

    for replacement in config.replacements:
        if replacement in config.retire_sources:
            continue
        adjusted = dict(baseline)
        adjusted[replacement] = adjusted.get(replacement, 0.0) + retired_twh
        for retired in config.retire_sources:
            adjusted[retired] = 0.0
        scenario_emissions = total_emissions_ktco2e(adjusted, config)
        delta = scenario_emissions - baseline_emissions
        pct = (delta / baseline_emissions * 100.0) if baseline_emissions else 0.0
        records.append(
            {
                "region": config.name,
                "year": config.year,
                "scenario": f"Retire {retired_label} -> {replacement}",
                "retired_source": retired_label,
                "replacement": replacement,
                "moved_twh": round(retired_twh, 3),
                "annual_ktco2e": round(scenario_emissions, 2),
                "delta_ktco2e": round(delta, 2),
                "pct_change": round(pct, 1),
            }
        )

    return pd.DataFrame.from_records(records)


def run_region_scenarios(config_dir: str | Path) -> pd.DataFrame:
    """Run counterfactuals for every region config in ``config_dir`` and concatenate."""
    paths = discover_region_configs(config_dir)
    if not paths:
        raise FileNotFoundError(f"No region config JSON files found in {config_dir}")
    frames = [build_region_counterfactuals(load_region_config(path)) for path in paths]
    return pd.concat(frames, ignore_index=True)
