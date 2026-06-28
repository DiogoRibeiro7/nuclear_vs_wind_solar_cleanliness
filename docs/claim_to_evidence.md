# Claim-to-evidence map

Each conclusion statement in this repository is linked here to the exact data rows,
code and report sections that support it. This makes every claim auditable.

| # | Conclusion statement | Evidence (data) | Evidence (code) | Evidence (report) |
|---|---|---|---|---|
| C1 | Onshore wind has a lower median lifecycle carbon intensity than nuclear (11 vs 12 gCO2e/kWh). | `data/lifecycle_emissions_ipcc_ar5.csv` rows for Nuclear, Wind onshore (`ipcc_ar5`) | `analysis.compare_to_baseline` | `reports/median_comparison.csv`; README "Core result" table |
| C2 | Offshore wind is approximately tied with nuclear on lifecycle carbon. | same dataset, Wind offshore (median 12) | `analysis.compare_to_baseline` | `reports/median_comparison.csv` |
| C3 | Nuclear is usually lower-carbon than solar PV. | dataset rows for Solar PV rooftop/utility (median 41/48) | `analysis.compare_to_baseline` | `reports/median_comparison.csv` |
| C4 | Uncertainty ranges overlap, so the carbon ranking is not certain. | min/median/max columns | `analysis.simulate_uncertainty`, `analysis.estimate_pairwise_probabilities` | `reports/probability_matrix.csv`, `reports/bootstrap_ci.csv` |
| C5 | There is no universal "cleanest" technology across the twelve metrics. | `data/multimetric_cleanliness_reference.csv` (all rows) | `cleanliness_index.pareto_frontier`, `weighted_cleanliness_score` | `reports/cleanliness_frontier.csv`, `reports/multimetric_summary.md` |
| C6 | The leader depends on policy intent: reliability-first favours nuclear. | `capacity_factor`, `grid_integration` rows | `scenarios.high_reliability_first`, `cleanliness_index.monte_carlo_cleanliness` | `reports/multimetric_report.json` (`scenarios.high_reliability_first`); `multimetric_summary.md` |
| C7 | Cost-first and emissions-first favour wind, not nuclear. | `levelized_cost` (`lazard_v17`), `lifecycle_co2e` (`ipcc_ar5`) rows | `scenarios.low_cost_first`, `scenarios.low_emissions_first` | `reports/multimetric_report.json`; `multimetric_summary.md` |
| C8 | Rankings carry wide uncertainty; rank order is not stable across draws. | `low/central/high` columns for every metric | `cleanliness_index.monte_carlo_cleanliness` (rank stability) | `reports/cleanliness_rank_stability.csv`; `multimetric_report.json` (`rank_stability`) |
| C9 | The strong social-media claim is overconfident/ambiguous, not a scientific conclusion. | n/a (linguistic) | `claim_classifier.classify_claim` | `reports/` classifier outputs |

## How to regenerate the evidence

```bash
python scripts/run_analysis.py            # C1–C4
python scripts/run_multimetric_analysis.py # C5–C8 (+ multimetric_report.json)
python scripts/run_claim_classifier.py     # C9
```

Every value's provenance (`source_id`) is documented in
[`../data/data_sources.md`](../data/data_sources.md).
