"""Tests for the region-aware financing / LCOE model."""

from __future__ import annotations

import pytest

from energy_cleanliness.financing import (
    DEFAULT_TECHNO_ECONOMICS,
    FinancingEnvironment,
    capital_recovery_factor,
    lcoe,
    lcoe_table,
    wacc_sensitivity,
)


def test_crf_zero_wacc_is_inverse_lifetime() -> None:
    assert capital_recovery_factor(0.0, 20) == pytest.approx(1 / 20)


def test_crf_known_value() -> None:
    # 7% over 30 years -> ~0.0806.
    assert capital_recovery_factor(0.07, 30) == pytest.approx(0.0806, abs=1e-3)


def test_crf_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        capital_recovery_factor(-0.01, 30)
    with pytest.raises(ValueError):
        capital_recovery_factor(0.05, 0)


def test_lcoe_increases_with_cost_of_capital() -> None:
    nuclear = DEFAULT_TECHNO_ECONOMICS["Nuclear"]
    assert lcoe(nuclear, 0.03) < lcoe(nuclear, 0.07) < lcoe(nuclear, 0.10)


def test_capital_intensive_is_more_wacc_sensitive_than_gas() -> None:
    nuclear = DEFAULT_TECHNO_ECONOMICS["Nuclear"]
    gas = DEFAULT_TECHNO_ECONOMICS["Gas"]

    def pct_rise(te) -> float:
        low, high = lcoe(te, 0.03), lcoe(te, 0.10)
        return (high - low) / low

    assert pct_rise(nuclear) > pct_rise(gas)


def test_financing_environment_wacc_sums_components() -> None:
    env = FinancingEnvironment("x", base_real_rate=0.03, sovereign_risk_premium=0.01, policy_risk_premium=0.02)
    assert env.wacc == pytest.approx(0.06)


def test_financing_from_dict_defaults_when_missing() -> None:
    env = FinancingEnvironment.from_dict("noinfo", None)
    assert env.wacc > 0


def test_lcoe_table_is_sorted_and_complete() -> None:
    env = FinancingEnvironment("test", 0.05)
    table = lcoe_table(env)
    assert set(table["technology"]) == set(DEFAULT_TECHNO_ECONOMICS)
    assert list(table["lcoe_usd_mwh"]) == sorted(table["lcoe_usd_mwh"])


def test_wacc_sensitivity_ranks_hydro_and_nuclear_above_gas() -> None:
    sens = wacc_sensitivity()
    order = list(sens["technology"])  # sorted by pct_increase desc
    assert order.index("Hydro") < order.index("Gas")
    assert order.index("Nuclear") < order.index("Gas")
