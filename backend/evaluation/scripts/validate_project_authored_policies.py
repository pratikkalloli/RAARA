"""Validate the isolated generic project-authored academic policy dataset."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from evaluation.project_authored_policies import ProjectPolicyDatasetError, load_project_policy_dataset


def main() -> int:
    default_path = Path(__file__).resolve().parents[1] / "datasets/project_authored_academic_policy/generic_academic_policy_dataset.json"
    parser = argparse.ArgumentParser(description="Validate nonofficial project-authored demonstration policies and questions.")
    parser.add_argument("--dataset", type=Path, default=default_path)
    args = parser.parse_args()
    try:
        dataset = load_project_policy_dataset(args.dataset)
    except ProjectPolicyDatasetError as exc:
        parser.exit(1, f"Generic project policy validation failed: {exc}\n")
    report = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "policy_count": len(dataset.policies),
        "question_count": len(dataset.questions),
        "policy_categories": dict(sorted(Counter(p.category for p in dataset.policies).items())),
        "question_categories": dict(sorted(Counter(q.category for q in dataset.questions).items())),
        "provenance": dataset.provenance,
        "source_type": dataset.source_type,
        "is_official_university_policy": dataset.is_official_university_policy,
        "official_university_approvals": 0,
        "numerical_examples": "PASS",
        "held_out_registry_imported": False,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
