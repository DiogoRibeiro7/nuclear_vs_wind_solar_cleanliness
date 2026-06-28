"""Small rule-based classifier for social-energy claims."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimClassification:
    label: str
    reason: str


def classify_claim(text: str) -> ClaimClassification:
    """Classify a short claim into one of five categories.

    Precedence (checked in order):
    1. a defined metric or a cited source -> factual and testable;
    2. myth/perfection framing -> misleading framing;
    3. absolute "always/never" language -> overconfident;
    4. comparative cleanliness without a metric -> ambiguous;
    5. otherwise -> unsupported by cited data.
    """
    if not text or not text.strip():
        return ClaimClassification(
            "ambiguous because of undefined metrics", "Empty or non-informative claim."
        )
    normalized = text.lower()

    metric_tokens = [
        "gco2e",
        "gco2",
        "co2",
        "twh",
        "gwh",
        "%",
        "percent",
        "deaths",
    ]

    # Citation/reference cues. Avoid the bare word "source" since it also matches
    # phrases like "energy source".
    source_tokens = [
        "study",
        "studies",
        "according to",
        "data source",
        "cited",
        "segundo o estudo",
        "de acordo com",
    ]

    # Myth / "perfect, no flaws" framing that suppresses competing dimensions.
    misleading_tokens = [
        "myth",
        "mito",
        "perfeita",
        "perfeito",
        "sem falhas",
        "sem defeitos",
        "no flaws",
        "no downside",
    ]

    # Absolute language that collapses uncertainty.
    absolute_tokens = [
        "always",
        "never",
        "everything",
        "every ",
        "all of",
        "sem exceção",
        "sempre",
        "nunca",
    ]

    # Comparative cleanliness ("cleaner than", "mais limpo que") with no metric.
    comparative_clean_tokens = [
        "cleaner",
        "cleanest",
        "mais limpo",
        "mais limpa",
        "menos sujo",
        "more clean",
    ]

    if any(token in normalized for token in metric_tokens) or any(
        token in normalized for token in source_tokens
    ):
        return ClaimClassification(
            "factual_and_testable",
            "Contains a defined metric or a cited source.",
        )

    if any(token in normalized for token in misleading_tokens):
        return ClaimClassification(
            "misleading framing",
            "Uses myth or perfection framing that suppresses competing dimensions.",
        )

    if any(token in normalized for token in absolute_tokens):
        return ClaimClassification(
            "overconfident because uncertainty is ignored",
            "Uses absolute always/never language that ignores uncertainty.",
        )

    if any(token in normalized for token in comparative_clean_tokens):
        return ClaimClassification(
            "ambiguous because of undefined metrics",
            "Comparative cleanliness claim without a precise measurable metric.",
        )

    return ClaimClassification(
        "unsupported by cited data",
        "No explicit metric, source, or comparative metric detected.",
    )


def classify_claims_batch(claims: list[str]) -> list[ClaimClassification]:
    """Classify a list of claims."""
    return [classify_claim(claim) for claim in claims]
