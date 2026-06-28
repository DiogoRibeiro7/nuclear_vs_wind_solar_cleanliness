"""Tests for the config-driven multi-region counterfactual runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from energy_cleanliness.portugal import run_portugal_scenario
from energy_cleanliness.regions import (
    DEFAULT_LIFECYCLE_GCO2E_KWH,
    RegionConfigError,
    build_region_counterfactuals,
    discover_region_configs,
    load_region_config,
    run_region_scenarios,
    total_emissions_ktco2e,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGIONS_DIR = PROJECT_ROOT / "data" / "regions"


def _write_config(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "region.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _base_payload() -> dict:
    return {
        "name": "Testland",
        "year": 2023,
        "generation_twh": {"Gas": 10.0, "Wind": 20.0, "Nuclear": 5.0},
        "retire_source": "Gas",
        "replacements": ["Wind", "Nuclear"],
    }


# --------------------------------------------------------------------------- loading


def test_shipped_region_configs_load() -> None:
    paths = discover_region_configs(REGIONS_DIR)
    assert {p.stem for p in paths} == {"portugal", "france", "germany"}
    for path in paths:
        config = load_region_config(path)
        assert config.retire_sources
        assert all(source in config.generation_twh for source in config.retire_sources)
        assert config.replacements


def test_missing_field_rejected(tmp_path: Path) -> None:
    payload = _base_payload()
    del payload["retire_source"]
    with pytest.raises(RegionConfigError):
        load_region_config(_write_config(tmp_path, payload))


def test_retire_source_must_be_in_mix(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["retire_source"] = "Coal"
    with pytest.raises(RegionConfigError):
        load_region_config(_write_config(tmp_path, payload))


def test_negative_generation_rejected(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["generation_twh"]["Wind"] = -1.0
    with pytest.raises(RegionConfigError):
        load_region_config(_write_config(tmp_path, payload))


def test_empty_replacements_rejected(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["replacements"] = []
    with pytest.raises(RegionConfigError):
        load_region_config(_write_config(tmp_path, payload))


def test_unknown_source_without_factor_raises(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["generation_twh"]["Mystery"] = 3.0
    config = load_region_config(_write_config(tmp_path, payload))
    with pytest.raises(RegionConfigError):
        total_emissions_ktco2e(config.generation_twh, config)


def test_lifecycle_override_used(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["generation_twh"] = {"Gas": 10.0, "Mystery": 0.0}
    payload["retire_source"] = "Gas"
    payload["replacements"] = ["Mystery"]
    payload["lifecycle_overrides"] = {"Mystery": 1.0}
    config = load_region_config(_write_config(tmp_path, payload))
    # Gas factor is the IPCC default; Mystery comes from the override.
    expected = 10.0 * DEFAULT_LIFECYCLE_GCO2E_KWH["Gas"]
    assert total_emissions_ktco2e(config.generation_twh, config) == pytest.approx(expected)


# ----------------------------------------------------------------- counterfactuals


def test_generation_is_conserved_and_retired_twh_moves(tmp_path: Path) -> None:
    config = load_region_config(_write_config(tmp_path, _base_payload()))
    table = build_region_counterfactuals(config)
    retired_twh = sum(config.generation_twh[s] for s in config.retire_sources)
    moves = table[table["replacement"] != ""]
    assert (moves["moved_twh"] == retired_twh).all()
    assert (table["scenario"] == "Baseline").sum() == 1


def test_multiple_retire_sources_move_together(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["generation_twh"] = {"Lignite": 80.0, "Coal": 36.0, "Wind": 100.0}
    payload["retire_source"] = ["Lignite", "Coal"]
    payload["replacements"] = ["Wind"]
    config = load_region_config(_write_config(tmp_path, payload))
    assert config.retire_sources == ("Lignite", "Coal")
    table = build_region_counterfactuals(config)
    wind_row = table[table["replacement"] == "Wind"].iloc[0]
    assert wind_row["moved_twh"] == 116.0  # lignite + hard coal combined
    assert "Lignite+Coal" in wind_row["scenario"]
    assert wind_row["delta_ktco2e"] < 0  # replacing coal with wind cuts emissions


def test_replacing_gas_with_wind_lowers_emissions(tmp_path: Path) -> None:
    config = load_region_config(_write_config(tmp_path, _base_payload()))
    table = build_region_counterfactuals(config)
    wind_row = table[table["replacement"] == "Wind"].iloc[0]
    assert wind_row["delta_ktco2e"] < 0


def test_replacing_nuclear_with_gas_raises_emissions() -> None:
    config = load_region_config(REGIONS_DIR / "france.json")
    table = build_region_counterfactuals(config)
    gas_row = table[table["replacement"] == "Gas"].iloc[0]
    wind_row = table[table["replacement"] == "Wind"].iloc[0]
    assert gas_row["delta_ktco2e"] > 0  # gas is far dirtier than nuclear
    assert wind_row["delta_ktco2e"] < gas_row["delta_ktco2e"]


def test_run_region_scenarios_covers_all_regions() -> None:
    table = run_region_scenarios(REGIONS_DIR)
    assert set(table["region"]) == {"Portugal", "France", "Germany"}
    # Exactly one baseline row per region.
    baselines = table[table["scenario"] == "Baseline"]
    assert len(baselines) == 3


def test_portugal_wrapper_delegates() -> None:
    table = run_portugal_scenario()
    assert set(table["region"]) == {"Portugal"}
    assert (table["scenario"] == "Baseline").sum() == 1
