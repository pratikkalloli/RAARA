from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from evaluation.schemas.dataset import DatasetValidationError, validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a versioned RAARA evaluation JSONL dataset.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        dataset = validate_dataset(args.dataset, args.manifest)
    except DatasetValidationError as exc:
        parser.exit(1, f"Dataset validation failed:\n{exc}\n")
    counts = Counter(question.category for question in dataset.questions)
    print(f"Dataset version: {dataset.dataset_version}")
    print(f"Questions validated: {len(dataset.questions)}")
    for category, count in sorted(counts.items()):
        print(f"{category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
