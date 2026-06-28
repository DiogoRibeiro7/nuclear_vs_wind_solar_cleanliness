# Data dictionary

Canonical, reproducible definitions for every metric and schema used in this project.
Provenance for each value lives in [`data/data_sources.md`](data/data_sources.md).

## Schema versions

| dataset | current `schema_version` | file |
|---|---|---|
| Multi-metric cleanliness reference | `1.0` | `data/multimetric_cleanliness_reference.csv` |
| Lifecycle emissions (carbon-only) | n/a (column-validated) | `data/lifecycle_emissions_ipcc_ar5.csv` |

Bump `schema_version` (major) when columns or units change; the loader rejects any
file whose `schema_version` is not in the supported set, so consumers fail fast rather
than silently misreading a changed layout.

## Multi-metric reference schema (`1.0`)

Long/tidy: one row per `(technology, metric)`.

| column | type | definition |
|---|---|---|
| `schema_version` | string | Must equal a supported version (`1.0`). |
| `technology` | string | One of: Nuclear, Wind onshore, Wind offshore, Solar PV rooftop, Solar PV utility, Hydro, Geothermal, Biomass, Gas with CCS, Biomass with CCS. |
| `metric` | string | One of the metric keys below. |
| `unit` | string | Unit of `low/central/high`. |
| `direction` | enum | `lower_better` (cleaner = smaller) or `higher_better` (cleaner = larger). |
| `low` | float | Low end of the plausible range. Non-negative except for `lifecycle_co2e`. |
| `central` | float | Central estimate used for point-estimate scoring. |
| `high` | float | High end of the plausible range. Must satisfy `low ≤ central ≤ high`. |

> Most metrics must be non-negative. The one exception is `lifecycle_co2e`, which may be
> negative for carbon-removal technologies (e.g. Biomass with CCS / BECCS). The validator
> enforces this via `NEGATIVE_ALLOWED_METRICS`.
| `year` | int | Representative year. |
| `source_id` | string | Key into the source registry in `data/data_sources.md`. |
| `notes` | string | Short provenance note. |

### Metric definitions

| metric key | unit | direction | definition |
|---|---|---|---|
| `lifecycle_co2e` | `gco2e_kwh` | lower_better | Lifecycle greenhouse-gas emissions per kWh delivered. |
| `direct_deaths` | `deaths_per_twh` | lower_better | Accident + occupational deaths per TWh generated. |
| `air_pollution_deaths` | `deaths_per_twh` | lower_better | Deaths attributable to air pollution per TWh. |
| `waste_persistence` | `index_0_15` | lower_better | Relative persistence/hazard of solid waste streams (higher = longer-lived/more hazardous). |
| `water_use` | `m3_mwh` | lower_better | Consumptive water use per MWh. |
| `land_use` | `m2_mwh` | lower_better | Direct land footprint per MWh. |
| `material_intensity` | `index_rel` | lower_better | Per-energy bulk + critical-material intensity, normalised index. |
| `construction_time` | `years` | lower_better | Typical site-to-commissioning duration. |
| `capacity_factor` | `fraction` | higher_better | Average delivered energy / nameplate energy. |
| `grid_integration` | `index_0_1` | higher_better | Ease of grid integration / dispatchability (higher = easier). |
| `levelized_cost` | `usd_mwh` | lower_better | Unsubsidized levelized cost of energy. |
| `financing_risk` | `index_0_1` | lower_better | Relative capex/schedule/market financing risk. |

## Cleanliness scoring conventions

- All metrics are min-max normalised across technologies into a **cleaner-is-higher**
  score in `[0, 1]` before weighting. `lower_better` metrics are inverted.
- Weights are scenario-defined (see `energy_cleanliness.scenarios`) and renormalised to
  sum to 1.
- Uncertainty is propagated by sampling each metric from a triangular distribution
  `triangular(low, central, high)` per Monte Carlo draw, normalising within the draw,
  then weighting. This keeps uncertainty visible rather than collapsing to point values.
- **Rank stability** reports, per technology, the fraction of Monte Carlo draws in which
  it lands at rank 1 and within the top-k.
