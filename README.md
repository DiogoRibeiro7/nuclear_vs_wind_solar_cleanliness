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
python scripts/run_claim_classifier.py
python scripts/generate_social_article.py
```

## Run tests

```bash
pytest
```

## Data sources

Primary source used in the seed dataset:

- IPCC AR5 Working Group III, Annex III, lifecycle greenhouse-gas emissions table.

Recommended extensions:

- UNECE, *Life Cycle Assessment of Electricity Generation Options*.
- NREL / Open Energy Data Initiative lifecycle electricity generation emissions datasets.
- Our World in Data, death rates from energy production per TWh.

Additional outputs for the wider interpretation run:

- `reports/cleanliness_scores.csv`
- `reports/cleanliness_sensitivity.csv`
- `reports/cleanliness_frontier.csv`
- `reports/multimetric_summary.md`

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
