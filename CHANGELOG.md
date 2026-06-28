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
- **Geography / grid-context / deployment-year.** `energy_cleanliness.geography` plus a
  sourced region×year grid carbon-intensity dataset (`data/grid_carbon_intensity.csv`)
  compute the marginal carbon a clean build avoids = grid intensity displaced − the
  technology's lifecycle intensity. The benefit depends on geography (France's clean grid
  vs Germany's), grid context, and deployment year (grids decarbonise over time).
  `scripts/run_geography_analysis.py` writes `reports/grid_intensity_trajectory.{csv,md}`
  and `reports/marginal_abatement.csv`. Covered by `tests/test_geography.py`.
- **Region-aware financing.** `energy_cleanliness.financing` models levelized cost as a
  function of the cost of capital: capital-intensive low-carbon technologies (nuclear,
  hydro, offshore wind) are penalised most by a high WACC, while fuel-heavy gas is barely
  affected. Region configs gain an optional `financing` block (base rate + sovereign and
  policy risk premia) setting their WACC. `scripts/run_financing_analysis.py` writes
  `reports/financing_lcoe.{csv,md}` and `financing_wacc_sensitivity.csv`. Covered by
  `tests/test_financing.py`.
- **Technology expansion.** The multi-metric profile now covers ten technologies, adding
  hydro, geothermal, biomass, gas with CCS and biomass with CCS (BECCS). Lifecycle carbon
  for the new rows is from IPCC AR5; other metrics are literature-informed proxies. The
  schema validator now permits negative `lifecycle_co2e` (for carbon-removal BECCS) via
  `NEGATIVE_ALLOWED_METRICS`, while keeping all other metrics non-negative. Scenario
  rankings updated accordingly (reliability-first now favours geothermal then nuclear).
- **Model-risk governance.** `energy_cleanliness.model_risk` is the single source of
  truth for limitation caveats; the dashboard and every generated markdown report
  (carbon summary, multi-metric summary, region counterfactuals) now carry a
  context-appropriate "Model risk and limitations" section. Added issue templates for
  metric updates, source corrections and interpretation review.
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
