"""Canonical model-risk caveats shared across every public report.

A single source of truth for the limitations that must accompany any output, so the
dashboard, the carbon-only summary, the multi-metric summary and the region
counterfactuals all carry consistent, context-appropriate caveats.
"""

from __future__ import annotations

# True of every output in this repository.
GENERAL_RISKS: list[str] = [
    "These results are decision-support, not advice or prediction. They depend on the "
    "input data, the chosen method, and the framing of the question.",
    "Uncertainty is modelled with transparent proxy distributions, not the true "
    "underlying literature distributions; ranges are deliberately wide.",
]

# Carbon-only lifecycle analysis (summary.md).
CARBON_RISKS: list[str] = [
    "Only the lifecycle-carbon dimension is considered here; 'clean' has many other "
    "dimensions (deaths, water, land, materials, cost) covered in the multi-metric run.",
    "Min/median/max are turned into a triangular proxy distribution, which is a "
    "sensitivity check rather than a reconstruction of the source distribution.",
]

# Multi-metric cleanliness scoring (multimetric_summary.md, dashboard).
MULTIMETRIC_RISKS: list[str] = [
    "Carbon values are sourced from IPCC AR5 and cost from Lazard v17; the remaining "
    "non-carbon metrics are literature-informed central estimates with wide ranges, not "
    "a per-cell systematic review.",
    "Index-style metrics (waste persistence, material intensity, grid integration) are "
    "relative scores, not absolute physical quantities.",
    "Scenario weights encode a policy intent, not an objective truth. The leader changes "
    "with the weighting, which is the central finding.",
    "Min-max normalization is sensitive to the set of technologies compared; adding or "
    "removing a technology can shift every normalized score.",
]

# Region counterfactuals (region_counterfactuals.md).
REGION_RISKS: list[str] = [
    "Lifecycle emission factors are IPCC AR5 medians (lignite excepted); real plants vary "
    "widely by technology vintage, fuel and grid context.",
    "Counterfactuals conserve total generation and ignore system effects: storage, "
    "transmission, dispatch, reserve margins and demand response are not modelled.",
    "Generation mixes are for a single year; they are not projections of future systems.",
]


def model_risk_markdown(context: str = "general", level: int = 2) -> str:
    """Return a markdown 'Model risk and limitations' section for a report context.

    ``context`` is one of ``"general"``, ``"carbon"``, ``"multimetric"`` or ``"region"``.
    Context-specific risks are appended to the general ones.
    """
    extra = {
        "general": [],
        "carbon": CARBON_RISKS,
        "multimetric": MULTIMETRIC_RISKS,
        "region": REGION_RISKS,
    }
    if context not in extra:
        raise ValueError(f"Unknown model-risk context: {context!r}")

    risks = GENERAL_RISKS + extra[context]
    heading = "#" * max(1, level)
    lines = [f"{heading} Model risk and limitations", ""]
    lines.extend(f"- {risk}" for risk in risks)
    lines.append("")
    return "\n".join(lines)
