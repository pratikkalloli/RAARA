from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from evaluation.heldout import HeldOutValidationError, update_annotation_review


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    heldout = root / "evaluation/datasets/held_out"
    parser = argparse.ArgumentParser(description="Record an independent annotation review, approval, rejection, or correction request.")
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--status", choices=["APPROVED", "REJECTED", "NEEDS_CORRECTION", "reviewed", "approved"], required=True)
    parser.add_argument("--reviewed-at", default=date.today().isoformat())
    parser.add_argument("--dataset", type=Path, default=heldout / "questions.jsonl")
    parser.add_argument("--registry", type=Path, default=heldout / "documents.json")
    parser.add_argument("--development-dataset", type=Path, default=root / "evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
    args = parser.parse_args()
    try:
        summary = update_annotation_review(args.question_id, args.status, args.reviewer_id, args.dataset,
                                           args.registry, args.development_dataset, args.reviewed_at)
    except HeldOutValidationError as exc:
        parser.exit(1, f"Review was not recorded:\n{exc}\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
