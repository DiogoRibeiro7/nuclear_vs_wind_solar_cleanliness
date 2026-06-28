"""Portugal electricity mix scenario modelling.

Thin backward-compatible wrapper over the general, config-driven runner in
:mod:`energy_cleanliness.regions`. New work should use ``energy_cleanliness.regions``
and a region config under ``data/regions/`` directly.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from energy_cleanliness.regions import build_region_counterfactuals, load_region_config

_PORTUGAL_CONFIG = Path(__file__).resolve().parents[2] / "data" / "regions" / "portugal.json"


def run_portugal_scenario(
    config_path: str | Path | None = None,
) -> pd.DataFrame:
    """Run the Portugal counterfactual table via the config-driven region runner.

    Defaults to ``data/regions/portugal.json``; pass ``config_path`` to use a different
    region config. Returns the standard region counterfactual table (ktCO2e/year).
    """
    config = load_region_config(config_path or _PORTUGAL_CONFIG)
    return build_region_counterfactuals(config)
