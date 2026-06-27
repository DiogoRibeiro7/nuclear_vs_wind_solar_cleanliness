# Roadmap

## 1) Data foundation (Next 2 weeks)
- Replace proxy multi-metric values with sourced, citable values for each technology and metric.
- Add `data_sources.md` documenting provenance, units, year, and uncertainty for every metric and row.
- Add schema/version validation so new datasets fail fast when columns or units are missing/misaligned.
- Create a data dictionary at repo level for reproducible metric definitions.

## 2) Model quality (Next 2–4 weeks)
- Expand multi-metric scoring to support uncertainty inputs per metric (ranges/distributions), not only point estimates.
- Implement confidence-aware weighted scores with Monte Carlo propagation across all metrics.
- Keep Pareto frontier and sensitivity outputs, and add rank-stability diagnostics (frequency in top-k).
- Add scenario profiles for policy intents, e.g., low-cost-first, low-emissions-first, and high-reliability-first.

## 3) Reproducibility and reliability (Next 1 month)
- Add reproducible fixtures and expected-output snapshots for smoke tests.
- Add regression tests for score directionality and Pareto behavior (higher-is-better vs lower-is-better).
- Add a CI job that regenerates report artifacts with fixed seeds and validates deterministic output constraints.
- Document migration requirements for any dataset/schema changes in README and `changelog`.

## 4) Transparency and UX (Next 1–2 months)
- Add a structured JSON output schema for core reports to support reuse in dashboards and APIs.
- Publish a one-page methods note with explicit definitions and rationale for each metric.
- Add a notebook and a lightweight dashboard for comparing technologies by metric bundles.
- Add a claim-to-evidence map linking conclusion statements to exact source rows and report sections.

## 5) Analysis expansion (Next quarter)
- Add additional technologies (hydro, gas with CCS, geothermal, biomass with/without CCS).
- Extend lifecycle and non-carbon metrics by geography, grid context, and deployment year.
- Add region-aware financing and risk modeling (policy regime, interest-rate bands, sovereign risk).
- Generalize Portugal counterfactual into a config-driven multi-region scenario runner.

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
