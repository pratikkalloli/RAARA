"""Command-line entry point for the Phase 9A corpus and dataset validator."""
from __future__ import annotations

from evaluation.synthetic_project_data.validation import validate_synthetic_dataset


def main() -> int:
    report = validate_synthetic_dataset()
    import json

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
