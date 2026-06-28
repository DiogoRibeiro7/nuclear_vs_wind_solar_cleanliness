# Is nuclear *cleaner* than wind or solar? A decision-analytic rebuttal

**Claim under test:** *“Nuclear power plants produce cleaner energy than wind or solar panels, and the data confirm it.”*

**TL;DR.** Nuclear is a genuinely low-carbon source — this is not an anti-nuclear analysis. But the quoted claim is not a finding the data support. It (i) equates “clean” with lifecycle carbon, where onshore **wind**, not nuclear, is the lower-carbon option in ~71% of draws; (ii) collapses a 12-dimensional, conflicting, uncertain comparison into a single ranking, where nuclear wins **0%** of uniformly-random value-weightings; and (iii) erases context — the right choice moves with the grid, the cost of capital, and the deployment year. The defensible output is a **decision map**, not a winner.

All figures and the executable derivation are in
[`notebooks/01_lifecycle_rebuttal.ipynb`](notebooks/01_lifecycle_rebuttal.ipynb); provenance
is in [`data/data_sources.md`](data/data_sources.md). Numbers below are reproduced by
`python scripts/run_all.py` (fixed seed = 42).

---

## Q1 — Is nuclear unambiguously lower-carbon than wind and solar?

Using IPCC AR5 Annex III lifecycle medians (gCO2e/kWh): **Nuclear 12, Wind onshore 11,
Wind offshore 12, Solar PV rooftop 41, Solar PV utility 48**. Point medians already place
onshore wind below nuclear; propagating each technology's `min/median/max` through a
triangular proxy and reasoning about the full distributions gives:

| quantity | value |
|---|---:|
| P(onshore wind < nuclear) | **0.71** |
| distribution overlap (nuclear vs onshore wind) | 0.63 |
| P(nuclear is the single lowest-carbon of the five) | 0.15 |
| P(nuclear < utility solar) | 0.82 |

Nuclear's higher *mean* and wide interval come from a long upper tail (max 110 gCO2e/kWh).

**Verdict.** “Cleaner than wind **or** solar” is true for solar and false-on-balance for
wind; the disjunction does rhetorical work the data don't support.

## Q2 — Once “clean” is operationalised, is there a single winner?

We score **10 technologies** on **12 metrics** (carbon, accident & air-pollution deaths,
waste persistence, water, land, material intensity, build time, capacity factor, grid
integration, levelized cost, financing risk), each with `low/central/high` ranges and a
declared direction.

- **Score uncertainty.** Under a balanced weighting the per-draw winner is Wind onshore
  ~55% and Geothermal ~40% of the time; winner entropy is **1.25 bits** (of a possible
  3.32) — contested, not decided.
- **Global value sensitivity.** Sampling the entire 12-D weight simplex uniformly,
  **nuclear wins 0% of weightings and is top-3 in only 7%**; the title splits between
  Geothermal, Wind onshore and Solar PV utility (the only technologies with a >5% share).
- **Conflicting objectives.** The metrics genuinely trade off — reliability (capacity
  factor, grid integration) is strongly *anti-correlated* with material intensity
  (r ≈ −0.85 to −0.86), build time and financing risk. No weighting optimises all at once.
- **Carbon–cost frontier.** The non-dominated set on (carbon, cost) is **Biomass with CCS**
  (net-negative carbon) and **Wind onshore** (cheapest); nuclear is dominated.

**Verdict.** With “clean” made explicit there is no dominant technology. A single ranking
is a choice about values dressed as a measurement.

## Q3 — Does the answer survive *where* and *when* you build?

- **Grid context (regional counterfactuals, ktCO2e/yr).** Replacing a low-carbon source
  with gas is far worse than with a renewable: in France, retiring nuclear for **wind** is
  −1.4% but for **gas** is **+660%**. In coal-heavy Germany any clean replacement cuts
  emissions sharply (wind −75%, nuclear ≈ tied). The displaced fuel dominates the result.
- **Cost of capital.** Levelized cost is capital-driven. Nuclear's LCOE runs **$55/MWh at
  3% WACC → $108 at 10%**; across a 1–12% WACC sweep it **never undercuts onshore wind or
  utility solar**, and only beats gas below ~3.9% WACC. Sensitivity to a 3%→10% rise:
  **Hydro +144%, Nuclear +96%** vs **Gas +21%** — capital-intensive low-carbon options are
  the most exposed to financing conditions.
- **Deployment year.** A clean build's value is the carbon it avoids = grid intensity
  displaced − its own lifecycle intensity. New nuclear avoids **~359 gCO2/kWh in Germany's
  grid but only ~44 in France's**; Portugal's benefit fell from ~228 (2015) to ~113 (2023)
  as its grid decarbonised.

**Verdict.** Even fixing a value-weighting, the best option is contingent on geography,
financing and time.

## Synthesis — a decision map, not a ranking

| context | best choice |
|---|---|
| value: low emissions | Geothermal, then Wind onshore |
| value: low cost | Wind onshore |
| value: high reliability | Geothermal, then **Nuclear** |
| cheapest build @ 3% WACC | Solar PV utility / Wind onshore |
| cheapest build @ 10% WACC | Wind onshore |
| displace coal (Germany) | any low-carbon source (nuclear ≈ wind) |
| displace gas in a clean grid (France/Portugal) | wind/solar; nuclear marginal |

Nuclear is the right answer in a *specific* cell of this table — reliability-first with
cheap capital — not as a universal claim.

## Defensible conclusion

> Nuclear, wind and solar are all low-carbon electricity sources. “Nuclear is cleaner, and
> the data confirm it” conflates carbon with cleanliness, suppresses uncertainty, ignores
> conflicting objectives, and erases geography, financing and time. The honest statement is
> a decision map — and on its most-cited axis, carbon, **wind (not nuclear) is the more
> likely lower-carbon choice**.

## Methods & limitations

- Uncertainty uses transparent triangular `(low, central, high)` proxies, not reconstructed
  literature distributions; ranges are deliberately wide.
- Min-max normalisation is relative to the compared set; adding/removing a technology
  shifts every normalised score (a stated property, not a bug).
- **Provenance:** carbon = IPCC AR5; cost = Lazard v17; grid intensity = Ember/EEA-consistent;
  region mixes = REN/RTE/Fraunhofer ISE. Other non-carbon metrics, techno-economics and
  region WACCs are literature-informed proxies — treat directions and magnitudes of
  difference as robust, point values as illustrative. See
  [`data/data_sources.md`](data/data_sources.md).
- Counterfactuals conserve generation and ignore system effects (storage, transmission,
  dispatch, reserves); financing is a CRF/WACC LCOE, not a project model.

## Reproduce

```bash
pip install -r requirements.txt
python scripts/run_all.py     # regenerates every artifact in reports/
pytest                        # 69 tests incl. end-to-end smoke tests
```

Conclusions map to exact source rows and report sections in
[`docs/claim_to_evidence.md`](docs/claim_to_evidence.md).
