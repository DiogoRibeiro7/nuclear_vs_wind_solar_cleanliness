"""Classify a set of energy claims with predefined examples."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.claim_classifier import ClaimClassification, classify_claims_batch


def main() -> None:
    claims = [
        "Nuclear is cleaner than wind and solar.",
        "Nuclear and wind have lower lifecycle emissions than gas and coal.",
        "Nuclear is by definition the cleanest source.",
        "This is a myth because there are no numbers in the post.",
        "According to IPCC, lifecycle emissions are around 12 gCO2e/kWh for nuclear.",
    ]

    classifications: list[ClaimClassification] = classify_claims_batch(claims)
    for claim, item in zip(claims, classifications):
        print(f"{claim}\n  -> {item.label}\n  -> {item.reason}\n")


if __name__ == "__main__":
    main()
