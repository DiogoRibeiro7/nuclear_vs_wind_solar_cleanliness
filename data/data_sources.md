# Data sources and provenance

This file documents the provenance, units, year and uncertainty handling for every
dataset and metric used in this repository. It is the authoritative reference for
where each number comes from. Each row in
[`multimetric_cleanliness_reference.csv`](multimetric_cleanliness_reference.csv)
carries a `source_id` that maps to an entry below.

> Status: the multi-metric values are **literature-informed central estimates with
> explicit uncertainty ranges**, not a per-cell systematic review. Carbon values are
> taken directly from IPCC AR5. Cost values are taken directly from Lazard LCOE v17.
> The remaining non-carbon metrics use representative central values and ranges drawn
> from the source families below; tightening each cell to a single primary citation is
> tracked in [`../ROADMAP.md`](../ROADMAP.md) item 1. Ranges are deliberately wide so
> that Monte Carlo propagation reflects genuine uncertainty rather than false precision.
>
> The profile covers ten technologies: the original five (nuclear, onshore/offshore wind,
> rooftop/utility solar) plus hydro, geothermal, biomass, gas with CCS and biomass with
> CCS (BECCS). For the added five, lifecycle carbon is from IPCC AR5 (including the
> net-negative BECCS value); their non-carbon metrics are literature-informed proxy
> central values with wide ranges, pending per-cell sourcing.

## Schema

The reference file is a **long/tidy** table. One row per `(technology, metric)`:

| column | meaning |
|---|---|
| `schema_version` | dataset schema version (see [`../DATA_DICTIONARY.md`](../DATA_DICTIONARY.md)) |
| `technology` | technology label, must match the lifecycle dataset |
| `metric` | canonical metric key (see data dictionary) |
| `unit` | unit string for the value |
| `direction` | `lower_better` or `higher_better` |
| `low`, `central`, `high` | uncertainty range; must satisfy `low <= central <= high` |
| `year` | representative year of the value |
| `source_id` | key into the source registry below |
| `notes` | short free-text provenance note |

Validation lives in `src/energy_cleanliness/multimetric.py` and fails fast when a
column, unit, technology or metric is missing or misaligned. The previous wide CSV
silently misaligned columns against the header; the long schema plus validation makes
that class of error impossible to commit unnoticed.

## Source registry

| `source_id` | Source | Scope | Year | Notes |
|---|---|---|---|---|
| `ipcc_ar5` | IPCC AR5 WG3, Annex III, Table A.III.2 | Lifecycle GHG (gCO2e/kWh) min/median/max | 2014 | Primary carbon source; also drives the carbon-only analysis. |
| `owid_deaths` | Our World in Data, "Death rates per unit of electricity production" (after Markandya & Wilkinson; Sovacool et al.) | Accident + air-pollution deaths per TWh | 2021 | Death rates split into direct vs air-pollution components. |
| `unece_lca` | UNECE, *Life Cycle Assessment of Electricity Generation Options* | Water use, waste persistence | 2022 | Used for water and waste-persistence indices. |
| `luderer_land` | Luderer et al. (2019) / land-use LCA syntheses | Land use per energy (m²/MWh) | 2022 | Direct footprint, per delivered energy. |
| `pehl_material` | Pehl et al. (2017), *Nature Energy*; IEA critical-minerals syntheses | Per-energy material intensity index | 2019 | Relative index normalised across technologies. |
| `iea_proj` | IEA *Projected Costs of Generating Electricity* and project trackers | Construction time, and LCOE/financing where not in Lazard (hydro, gas-CCS, BECCS) | 2023 | Typical site-to-commissioning durations and projected costs. |
| `eia_cf` | US EIA capacity-factor tables | Capacity factor (fraction) | 2023 | Fleet/representative averages. |
| `nrel_grid` | NREL grid-integration studies | Grid-integration index (0–1) | 2023 | Qualitative dispatchability score; higher is easier to integrate. |
| `lazard_v17` | Lazard *Levelized Cost of Energy* v17.0 | LCOE ($/MWh), financing risk | 2024 | Unsubsidized ranges; financing-risk index derived from capex/schedule profile. |

## Region generation mixes

The region configs under `data/regions/` use 2023 domestic electricity generation by
source (TWh), each with a `source` field citing its origin:

| region | year | source | notes |
|---|---|---|---|
| Portugal | 2023 | REN (Redes Energéticas Nacionais) | Domestic generation (~41 TWh) derived from REN consumption shares (renewables 31.2 TWh = 61%; non-renewable 10 TWh = 19%; the ~20% remainder is net imports from Spain). No nuclear; nuclear is a hypothetical replacement only. |
| France | 2023 | RTE French Annual Electricity Review 2023 | Nuclear ~320, hydro ~58, wind 50.8, solar 21.6, gas 30.0, coal ~2 TWh. |
| Germany | 2023 | Fraunhofer ISE public net generation 2023 | Wind 139.8, PV 59.9, lignite 77.6, hard coal 36.1, gas 45.8, biomass ~42, hydro ~19, nuclear 6.7 TWh. Lignite and hard coal are modelled as separate sources and retired together. |

### Financing parameters

Each region config carries an optional `financing` block (`base_real_rate`,
`sovereign_risk_premium`, `policy_risk_premium`) that sets its real WACC. The values
shipped for Portugal/France/Germany (≈3.5–4.5%) are illustrative OECD-range estimates,
not sourced country figures. Techno-economic inputs in
`energy_cleanliness.financing.DEFAULT_TECHNO_ECONOMICS` (capex, O&M, fuel, capacity
factor, lifetime) are representative midpoints from public syntheses (NREL ATB, IEA),
used to show the *direction and magnitude* of cost-of-capital effects rather than exact
project costs.

Lifecycle emission factors for the region runner are IPCC AR5 medians, except lignite
(~1100 gCO2e/kWh, from lifecycle-assessment literature, since AR5's headline coal median
of 820 reflects hard coal). See
`energy_cleanliness.regions.DEFAULT_LIFECYCLE_GCO2E_KWH`; any factor is overridable per
config via `lifecycle_overrides`.

## Carbon-only dataset

`lifecycle_emissions_ipcc_ar5.csv` and the normalized files under `data/processed/`
come from `ipcc_ar5` above and are validated by
`energy_cleanliness.data.load_lifecycle_data`.

## Updating values

1. Edit the relevant rows in `multimetric_cleanliness_reference.csv`.
2. Keep `low <= central <= high` and a valid `direction`.
3. Add or reuse a `source_id` and document it in the registry above.
4. Bump `schema_version` only when columns/units change (see the data dictionary).
5. Add a `CHANGELOG.md` entry for any value or schema change.
