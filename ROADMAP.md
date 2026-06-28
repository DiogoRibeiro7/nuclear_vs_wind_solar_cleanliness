# Roadmap

Legend: `[x]` done, `[~]` partially done, `[ ]` not started.

## 1) Data foundation (Next 2 weeks)
- [~] Replace proxy multi-metric values with sourced, citable values for each technology and metric. *(Carbon from IPCC AR5 and cost from Lazard v17 are sourced; remaining non-carbon metrics are literature-informed central estimates with ranges — full per-cell sourcing ongoing.)*
- [x] Add `data_sources.md` documenting provenance, units, year, and uncertainty for every metric and row.
- [x] Add schema/version validation so new datasets fail fast when columns or units are missing/misaligned. *(`energy_cleanliness.multimetric`.)*
- [x] Create a data dictionary at repo level for reproducible metric definitions. *(`DATA_DICTIONARY.md`.)*

## 2) Model quality (Next 2–4 weeks)
- [x] Expand multi-metric scoring to support uncertainty inputs per metric (ranges/distributions), not only point estimates. *(`low/central/high` per cell.)*
- [x] Implement confidence-aware weighted scores with Monte Carlo propagation across all metrics. *(`monte_carlo_cleanliness`.)*
- [x] Keep Pareto frontier and sensitivity outputs, and add rank-stability diagnostics (frequency in top-k).
- [x] Add scenario profiles for policy intents, e.g., low-cost-first, low-emissions-first, and high-reliability-first. *(`energy_cleanliness.scenarios`.)*

## 3) Reproducibility and reliability (Next 1 month)
- [x] Add reproducible fixtures and expected-output snapshots for smoke tests. *(`tests/fixtures/`, deterministic JSON report.)*
- [x] Add regression tests for score directionality and Pareto behavior (higher-is-better vs lower-is-better). *(`tests/test_multimetric.py`.)*
- [x] Add a CI job that regenerates report artifacts with fixed seeds and validates deterministic output constraints. *(`.github/workflows/ci.yml`.)*
- [x] Document migration requirements for any dataset/schema changes in README and `changelog`. *(`CHANGELOG.md`, `data_sources.md` "Updating values".)*

## 4) Transparency and UX (Next 1–2 months)
- [x] Add a structured JSON output schema for core reports to support reuse in dashboards and APIs. *(`docs/report_schema.json`, `reports/multimetric_report.json`.)*
- [x] Publish a one-page methods note with explicit definitions and rationale for each metric. *(`docs/methods_note.md`.)*
- [x] Add a notebook and a lightweight dashboard for comparing technologies by metric bundles. *(`notebooks/01_lifecycle_rebuttal.ipynb`, `scripts/build_dashboard.py` → `reports/dashboard.html`.)*
- [x] Add a claim-to-evidence map linking conclusion statements to exact source rows and report sections. *(`docs/claim_to_evidence.md`.)*

## 5) Analysis expansion (Next quarter)
- [ ] Add additional technologies (hydro, gas with CCS, geothermal, biomass with/without CCS).
- [ ] Extend lifecycle and non-carbon metrics by geography, grid context, and deployment year.
- [ ] Add region-aware financing and risk modeling (policy regime, interest-rate bands, sovereign risk).
- [x] Generalize Portugal counterfactual into a config-driven multi-region scenario runner. *(`energy_cleanliness.regions`, configs under `data/regions/`, `scripts/run_region_scenarios.py`; `portugal.py` is now a thin wrapper.)*

## 6) Community and quality gates (Ongoing)
- Add issue templates for metric updates, source corrections, and interpretation review.
- Add a standard model-risk section to every public report.
- Maintain a changelog entry for each scoring-logic or dataset update.

## Delivery order
- Foundation first (`Data foundation`) to avoid silent metric errors.
- Then model upgrades (`Model quality`) on a validated dataset.
- Then reproducibility (`Reproducibility and reliability`) so everything can be trusted.
- Then productization (`Transparency/UX`) for stakeholders.
- Expansion and governance items can be parallelized as they depend less on core pipeline churn.
