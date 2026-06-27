"""Small rule-based classifier for social-energy claims."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimClassification:
    label: str
    reason: str


def classify_claim(text: str) -> ClaimClassification:
    """Classify a short claim into one of five categories."""
    if not text or not text.strip():
        return ClaimClassification("ambiguous because of undefined metrics", "Empty or non-informative claim.")
    normalized = text.lower()

    cleanliness_tokens = [
        "cleaner",
        "cleaner than",
        "cleanest",
        "clean",
        "limpo",
        "mais limpo",
        "menos sujo",
        "limpa",
        "limpeza",
    ]

    metric_tokens = [
        "gco2e",
        "gco2",
        "co2",
        "twh",
        "gwh",
        "%",
        "percent",
        "kg",
        "ton",
        "deaths",
    ]

    uncertainty_tokens = [
        "myth",
        "always better",
        "guaranteed",
        "no downside",
        "one thing only",
        "sempre melhor",
        "sem risco",
        "sem incerteza",
    ]

    absolute_tokens = [
        "always",
        "never",
        "all",
        "all of the",
        "zero",
        "all of",
        "sem exceção",
        "nunca",
    ]

    source_tokens = [
        "study",
        "studies",
        "report",
        "source",
        "according to",
        "segundo",
        "de acordo",
    ]

    if any(token in normalized for token in cleanliness_tokens):
        if any(token in normalized for token in metric_tokens):
            return ClaimClassification(
                "factual_and_testable",
                "Defined metric appears in text.",
            )
        if any(token in normalized for token in uncertainty_tokens):
            return ClaimClassification(
                "misleading framing",
                "Uses framing that suppresses uncertainty and competing dimensions.",
            )
        if any(token in normalized for token in absolute_tokens):
            return ClaimClassification(
                "overconfident because uncertainty is ignored",
                "Metric is absolute and likely overconfident.",
            )
        return ClaimClassification(
            "ambiguous because of undefined metrics",
            "Uses cleanliness framing without a precise measurable metric.",
        )

    if any(token in normalized for token in source_tokens):
        return ClaimClassification(
            "factual_and_testable",
            "Contains reference to source or study context.",
        )

    return ClaimClassification(
        "unsupported by cited data",
        "No explicit metric and no source citation detected.",
    )


def classify_claims_batch(claims: list[str]) -> list[ClaimClassification]:
    """Classify a list of claims."""
    return [classify_claim(claim) for claim in claims]
