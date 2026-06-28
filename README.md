# Nuclear vs Wind/Solar: A Data Science Rebuttal

This repository tests the claim:

> "Nuclear power plants produce cleaner energy than wind or solar panels, and the data confirm it."

The goal is not to argue that nuclear energy is bad. It is not. Nuclear is a low-carbon electricity source. The goal is to test whether the stronger claim is supported by data.

Using lifecycle greenhouse-gas emissions, the claim is **too broad** and **false for wind**. IPCC lifecycle estimates place nuclear and wind in the same low-carbon range, with onshore wind having a slightly lower median lifecycle carbon intensity than nuclear.

## Core result

Using IPCC AR5 Annex III lifecycle emission estimates, in gCO2e/kWh:

| Technology | Min | Median | Max |
|---|---:|---:|---:|
| Nuclear | 3.7 | 12 | 110 |
| Wind onshore | 7 | 11 | 56 |
| Wind offshore | 8 | 12 | 35 |
| Solar PV rooftop | 26 | 41 | 60 |
| Solar PV utility | 18 | 48 | 180 |

This means:

- Nuclear is not cleaner than onshore wind under the IPCC median estimate.
- Nuclear and offshore wind are approximately tied under the IPCC median estimate.
- Nuclear is usually lower-carbon than solar PV under this dataset.
- All four technologies are low-carbon compared with fossil electricity.
- The strong social-media claim is not a scientific conclusion because it collapses uncertainty and uses an undefined word, "clean".

A more defensible sentence would be:

> Nuclear, wind and solar are all low-carbon electricity sources. Nuclear is often lower-carbon than solar PV, but it is not clearly cleaner than wind, and uncertainty ranges overlap.

## Repository structure

```text
.
├── data/
│   ├── raw/
│   │   └── lifecycle_emissions_ipcc_ar5.csv
│   ├── processed/
│   │   └── lifecycle_emissions_normalized.csv
│   └── lifecycle_emissions_ipcc_ar5.csv
├── notebooks/
│   └── 01_lifecycle_rebuttal.ipynb
├── reports/
│   └── .gitkeep
├── scripts/
│   ├── make_plots.py
│   └── run_analysis.py
├── src/
│   └── energy_cleanliness/
│       ├── __init__.py
│       ├── analysis.py
│       ├── data.py
│       └── plotting.py
├── tests/
│   └── test_analysis.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Method

The analysis uses two levels.

### 1. Direct median comparison

The first test is deterministic. It checks whether nuclear has lower lifecycle emissions than wind and solar using the reported median values.

This is enough to reject the broad claim that nuclear is cleaner than wind.

### 2. Uncertainty simulation

The second test treats the reported min / median / max values as an uncertainty range. It samples from a triangular proxy distribution with the reported median used as the central value.

This does **not** claim to recover the original literature distribution. It is a sensitivity check that makes the uncertainty visible.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or with Poetry:

```bash
poetry install
```

## Documentation

- **[`REPORT.md`](REPORT.md) — the synthesized findings (start here).**
- [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) — canonical metric definitions and schema versions.
- [`data/data_sources.md`](data/data_sources.md) — provenance, units, year and uncertainty per source.
- [`docs/methods_note.md`](docs/methods_note.md) — one-page methods summary.
- [`docs/claim_to_evidence.md`](docs/claim_to_evidence.md) — every conclusion linked to its source rows and report sections.
- [`docs/report_schema.json`](docs/report_schema.json) — JSON Schema for the structured multi-metric report.
- [`CHANGELOG.md`](CHANGELOG.md) — data, schema and scoring-logic changes.

## Data ingestion tasks

```bash
python scripts/ingest_lifecycle_datasets.py
```

This builds `data/processed/lifecycle_emissions_normalized.csv` from files under `data/raw`.

## Run the analysis

```bash
python scripts/run_analysis.py
python scripts/make_plots.py
```

Outputs are written to `reports/`.

Expected outputs:

```text
reports/median_comparison.csv
reports/probability_matrix.csv
reports/summary.md
reports/lifecycle_ranges.png
reports/probability_matrix.png
reports/bootstrap_ci.csv
```

## Workflow bundle

```bash
python scripts/run_analysis_suite.py
python scripts/run_multimetric_analysis.py
python scripts/run_portugal_scenario.py
python scripts/run_region_scenarios.py
python scripts/run_financing_analysis.py
python scripts/run_geography_analysis.py
python scripts/run_claim_classifier.py
python scripts/generate_social_article.py
python scripts/build_dashboard.py
```

`build_dashboard.py` reads `reports/multimetric_report.json` and writes a self-contained
`reports/dashboard.html` (scenario tabs, ranking tables with confidence intervals,
embedded figures, and a model-risk section) — no server or extra dependency required.

`run_region_scenarios.py` runs config-driven counterfactuals over every region config in
`data/regions/` (Portugal, France, Germany ship by default) and writes
`reports/region_counterfactuals.{csv,md}`. Each config asks: if one source is retired and
its energy is absorbed by an alternative, how do annual lifecycle emissions (ktCO2e/year)
change? Add a new region by dropping a JSON file into `data/regions/`.

`run_financing_analysis.py` models how the **cost of capital** reshapes levelized cost
(`reports/financing_lcoe.{csv,md}`). Capital-intensive low-carbon options (nuclear, hydro,
offshore wind) are penalised most by a high WACC, while fuel-heavy gas is barely affected,
so a region's financing environment changes which clean option is cheapest. Each region
config carries an optional `financing` block (base rate + sovereign and policy risk
premia) that sets its WACC.

`run_geography_analysis.py` adds the **geography / grid-context / deployment-year**
dimension (`reports/grid_intensity_trajectory.{csv,md}`, `reports/marginal_abatement.csv`).
Using a sourced region×year grid carbon-intensity dataset (`data/grid_carbon_intensity.csv`),
it computes the marginal carbon a clean build avoids = grid intensity displaced − the
technology's lifecycle intensity. New nuclear avoids ~359 gCO2/kWh in Germany's grid but
only ~44 in France's already-clean grid, and the benefit shrinks as grids decarbonise.

## Regenerate everything

```bash
python scripts/run_all.py   # runs every analysis script and rewrites reports/
```

## Run tests

```bash
pytest
```

The suite includes end-to-end smoke tests (`tests/test_scripts_smoke.py`) that run each
analysis script and assert its primary outputs, plus a `lint` job in CI (`ruff check`).

## Data sources

Primary source used in the seed dataset:

- IPCC AR5 Working Group III, Annex III, lifecycle greenhouse-gas emissions table.

Recommended extensions:

- UNECE, *Life Cycle Assessment of Electricity Generation Options*.
- NREL / Open Energy Data Initiative lifecycle electricity generation emissions datasets.
- Our World in Data, death rates from energy production per TWh.

Additional outputs for the wider interpretation run:

- `reports/cleanliness_scores.csv` — balanced-scenario point scores.
- `reports/cleanliness_sensitivity.csv` — Monte Carlo score summary (mean, std, 95% CI).
- `reports/cleanliness_rank_stability.csv` — P(rank 1) and P(top-k) per technology.
- `reports/cleanliness_frontier.csv` — Pareto frontier.
- `reports/multimetric_summary.md` — per-scenario rankings with confidence intervals.
- `reports/multimetric_report.json` — versioned structured report (see `docs/report_schema.json`).

## Multi-metric model

The multi-metric profile is a validated long/tidy dataset with a `schema_version` and an
explicit `low/central/high` uncertainty range per `(technology, metric)`. Scoring:

- min-max normalises each metric to a cleaner-is-higher score (direction declared in the data);
- weights metrics by a policy scenario (`balanced`, `low_emissions_first`, `low_cost_first`,
  `high_reliability_first`);
- propagates uncertainty via `triangular(low, central, high)` Monte Carlo and reports
  rank-stability diagnostics.

The profile covers ten technologies — nuclear, onshore/offshore wind, rooftop/utility
solar, hydro, geothermal, biomass, gas with CCS and biomass with CCS (BECCS, whose
lifecycle carbon is net-negative). There is no universal winner: the leader flips with
the policy intent — reliability-first favours dispatchable sources (geothermal, nuclear),
while cost-first and emissions-first favour wind, solar and geothermal.

## Interpretation note

This project now includes a broader cleanliness profile beyond carbon:

- lifecycle greenhouse-gas emissions;
- direct deaths and air-pollution deaths per TWh;
- waste profile and persistence;
- water use;
- land use;
- material intensity;
- construction time;
- capacity factor and grid integration;
- cost and financing risk.

Under that wider definition there is still no universal winner. Nuclear, wind and solar are all part of the low-carbon electricity family, and which option is cleaner depends on the metric and weighting choices.
