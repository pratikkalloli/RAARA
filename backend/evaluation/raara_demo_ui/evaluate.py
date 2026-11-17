"""Print the reproducible project-authored demo evaluation as JSON."""
from __future__ import annotations

import json

from evaluation.raara_demo_ui.runner import run_dataset_evaluation


def main() -> None:
    print(json.dumps(run_dataset_evaluation(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
