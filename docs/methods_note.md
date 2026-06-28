# Methods note

A one-page summary of what this repository computes, how, and what each choice means.

## Question

Test the social-media claim: *"Nuclear power plants produce cleaner energy than wind or
solar panels, and the data confirm it."* The aim is not to argue nuclear is bad — it is a
low-carbon source — but to check whether the **strong, universal** claim is supported.

## Two layers of analysis

### 1. Carbon-only (deterministic + uncertainty)

- **Source:** IPCC AR5 Annex III lifecycle GHG estimates (gCO2e/kWh), min/median/max.
- **Direct comparison:** compare reported medians (`compare_to_baseline`). Onshore wind's
  median (11) is below nuclear's (12); offshore wind ties nuclear; both are well below
  solar PV. This alone falsifies the universal "cleaner than wind" claim.
- **Uncertainty simulation:** `simulate_uncertainty` samples each technology from a
  triangular proxy over min/median/max (or bootstraps empirical samples when present) and
  `estimate_pairwise_probabilities` reports P(one < another). This is a sensitivity check,
  not a reconstruction of the original literature distribution.

### 2. Multi-metric cleanliness (beyond carbon)

"Clean" is undefined in the claim. We make it explicit with twelve metrics
(carbon, deaths, air pollution, waste persistence, water, land, materials, construction
time, capacity factor, grid integration, cost, financing risk). Definitions and units are
in [`../DATA_DICTIONARY.md`](../DATA_DICTIONARY.md); provenance in
[`../data/data_sources.md`](../data/data_sources.md).

- **Normalization.** Each metric is min-max normalised across technologies into a
  cleaner-is-higher score in `[0, 1]`; `lower_better` metrics are inverted. Direction is
  declared per metric in the dataset, never hard-coded in the analysis.
- **Weighting and scenarios.** Weights encode a *policy intent*. We ship four:
  `balanced`, `low_emissions_first`, `low_cost_first`, `high_reliability_first`. Weights
  are renormalised to sum to one, so only relative emphasis matters.
- **Uncertainty propagation.** Every metric carries a `low/central/high` range. Monte
  Carlo (`monte_carlo_cleanliness`, fixed seed) samples each cell from
  `triangular(low, central, high)`, normalises within the draw, weights and sums. We
  report the mean score, a 95% credible interval, and **rank stability** — the fraction of
  draws in which each technology is rank 1 or within the top-k.
- **Pareto frontier.** `pareto_frontier` reports the non-dominated set, respecting each
  metric's direction, so we can see which technologies are never strictly beaten on all
  metrics at once.

## What the results say

- There is **no universal winner**. The leader flips with the policy intent:
  reliability-first favours nuclear; cost-first and emissions-first favour wind; solar PV
  is competitive on several non-carbon metrics (deaths, water, construction time).
- Confidence intervals overlap substantially, so single-number rankings overstate
  certainty. Rank-stability percentages make this explicit.

## Honest limitations

- Carbon values are sourced directly (IPCC AR5); cost values are sourced directly
  (Lazard v17). The remaining non-carbon metrics are **literature-informed central
  estimates with deliberately wide ranges**, not a per-cell systematic review. Tightening
  every cell to a single primary citation is tracked in
  [`../ROADMAP.md`](../ROADMAP.md) item 1.
- The triangular distribution is a transparent proxy for uncertainty, not the true
  literature distribution.
- Index-style metrics (waste persistence, material intensity, grid integration) are
  relative, not absolute physical quantities.

## Defensible one-sentence conclusion

> Nuclear, wind and solar are all low-carbon electricity sources. Nuclear is often
> lower-carbon than solar PV and is the most reliable, but it is not clearly cleaner than
> wind, and which option is "cleanest" depends on the metric and weighting choices.
