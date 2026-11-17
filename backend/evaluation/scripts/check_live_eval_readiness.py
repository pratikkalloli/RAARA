from __future__ import annotations

import json
from dataclasses import asdict

from evaluation.live_eval_gate import inspect_live_eval_readiness


def main() -> int:
    readiness = inspect_live_eval_readiness()
    print(json.dumps(asdict(readiness), indent=2))
    print("No OpenAI client is created and no API call is made by this check.")
    return 0 if readiness.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
