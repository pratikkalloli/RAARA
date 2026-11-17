"""Fail-closed configuration checks for a future, explicitly authorized live run.

This module never creates an OpenAI client or makes network calls.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class LiveEvalReadiness:
    ready: bool
    blockers: tuple[str, ...]
    model: str | None
    max_calls: int | None
    max_budget_usd: float | None


def inspect_live_eval_readiness(env: Mapping[str, str] | None = None) -> LiveEvalReadiness:
    """Inspect opt-in and limits without exposing credentials or performing a run."""
    values = env if env is not None else os.environ
    blockers: list[str] = []
    if values.get("RAARA_ENABLE_LIVE_EVAL", "").strip().lower() != "true":
        blockers.append("RAARA_ENABLE_LIVE_EVAL=true explicit opt-in is missing")
    if not values.get("OPENAI_API_KEY", "").strip():
        blockers.append("OPENAI_API_KEY is not configured")
    model = values.get("RAARA_EVAL_MODEL", "").strip() or None
    if model is None:
        blockers.append("RAARA_EVAL_MODEL is not configured")
    try:
        max_calls = int(values.get("RAARA_EVAL_MAX_CALLS", ""))
        if max_calls <= 0:
            raise ValueError
    except (TypeError, ValueError):
        max_calls = None
        blockers.append("RAARA_EVAL_MAX_CALLS must be a positive integer")
    try:
        max_budget_usd = float(values.get("RAARA_EVAL_MAX_BUDGET_USD", ""))
        if not math.isfinite(max_budget_usd) or max_budget_usd <= 0:
            raise ValueError
    except (TypeError, ValueError):
        max_budget_usd = None
        blockers.append("RAARA_EVAL_MAX_BUDGET_USD must be a positive finite amount")
    return LiveEvalReadiness(not blockers, tuple(blockers), model, max_calls, max_budget_usd)
