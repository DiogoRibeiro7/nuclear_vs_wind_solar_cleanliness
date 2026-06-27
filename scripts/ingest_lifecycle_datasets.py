"""Build normalized lifecycle dataset from supported raw sources."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from energy_cleanliness.data_ingestion import build_normalized_dataset

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "lifecycle_emissions_normalized.csv"


def main() -> None:
    """Create processed lifecycle dataset."""
    DATA = build_normalized_dataset(RAW_DIR, OUTPUT_PATH)
    print(f"Processed records: {len(DATA)}")
    print(f"Written: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
