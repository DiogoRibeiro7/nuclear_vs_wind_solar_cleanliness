# Changelog

All notable changes to data, schema and scoring logic are recorded here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- **Data foundation.** `data/data_sources.md` (provenance, units, year, uncertainty per
  source) and repo-level `DATA_DICTIONARY.md` (metric definitions and schema versions).
- **Schema validation.** `energy_cleanliness.multimetric` loads the multi-metric profile
  as a validated long/tidy table with a `schema_version`, failing fast on missing or
  misaligned columns, unknown metrics/units, bad directions, or out-of-order ranges.
- **Uncertainty inputs.** The multi-metric reference now carries `low/central/high`
  ranges per `(technology, metric)` instead of single point estimates.
- **Monte Carlo propagation.** `monte_carlo_cleanliness` samples every metric from a
  `triangular(low, central, high)` distribution and propagates uncertainty through the
  weighted cleanliness score, reporting mean, 95% CI and rank-stability diagnostics
  (`P(rank 1)`, `P(top-k)`).
- **Scenario profiles.** `energy_cleanliness.scenarios` adds `balanced`,
  `low_emissions_first`, `low_cost_first` and `high_reliability_first` policy weightings.
- **Structured output.** `energy_cleanliness.reporting` emits a versioned
  `reports/multimetric_report.json` documented by `docs/report_schema.json`.
- **Transparency docs.** `docs/methods_note.md` and `docs/claim_to_evidence.md`.
- **Multi-region runner.** `energy_cleanliness.regions` generalises the Portugal-only
  counterfactual into a config-driven runner over any number of region configs under
  `data/regions/` (Portugal, France, Germany ship by default). Total generation is
  conserved when a source is retired. `scripts/run_region_scenarios.py` writes
  `reports/region_counterfactuals.{csv,md}`. `tests/test_regions.py` covers config
  validation, generation conservation and emission directionality.
- **Notebook + dashboard.** `notebooks/01_lifecycle_rebuttal.ipynb` rebuilt around the
  multi-metric pipeline (scenarios, Monte Carlo, rank stability, Pareto, JSON report).
  `scripts/build_dashboard.py` renders a self-contained `reports/dashboard.html` from the
  JSON report (`energy_cleanliness.dashboard`), with scenario tabs, ranking tables,
  embedded figures and a model-risk section. New plotting helpers `plot_scenario_scores`
  and `plot_rank_stability`.
- **Tests.** `tests/test_multimetric.py` covers schema validation, score directionality,
  Pareto behavior, Monte Carlo determinism, rank stability, scenario rankings and the
  JSON report, with a fixture under `tests/fixtures/`.
- **CI.** `.github/workflows/ci.yml` runs the test suite and regenerates report
  artifacts with fixed seeds on every push and pull request.

### Fixed
- `data/multimetric_cleanliness_reference.csv` previously had one more value per row than
  header columns, so pandas silently shifted `technology` into the index and
  `run_multimetric_analysis.py` failed at merge time. The new long schema plus validation
  makes this class of misalignment impossible to commit unnoticed.
- `pareto_frontier` passed a DataFrame to `pd.to_numeric`, which raised once more than one
  metric was supplied; it now coerces column-wise.

### Changed
- `run_multimetric_analysis.py` now scores all scenarios with point estimates and Monte
  Carlo uncertainty, writes `reports/cleanliness_rank_stability.csv` and
  `reports/multimetric_report.json`, and rewrites `reports/multimetric_summary.md` with
  per-scenario rankings and confidence intervals.
