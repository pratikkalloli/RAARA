from __future__ import annotations

import math


def total_latency_ms(retrieval_latency_ms: float | None, generation_latency_ms: float | None) -> float | None:
    """Return a total only when both phase timings are known; unavailable is not zero."""
    if retrieval_latency_ms is None or generation_latency_ms is None:
        return None
    if not math.isfinite(retrieval_latency_ms) or not math.isfinite(generation_latency_ms):
        raise ValueError("Latency values must be finite.")
    if retrieval_latency_ms < 0 or generation_latency_ms < 0:
        raise ValueError("Latency values must be non-negative.")
    return retrieval_latency_ms + generation_latency_ms


def estimate_api_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    input_usd_per_million_tokens: float | None,
    output_usd_per_million_tokens: float | None,
) -> float | None:
    """Estimate cost only when usage and an explicit rate snapshot are supplied."""
    values = (input_tokens, output_tokens, input_usd_per_million_tokens, output_usd_per_million_tokens)
    if any(value is None for value in values):
        return None
    assert input_tokens is not None and output_tokens is not None
    assert input_usd_per_million_tokens is not None and output_usd_per_million_tokens is not None
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative.")
    if not math.isfinite(input_usd_per_million_tokens) or not math.isfinite(output_usd_per_million_tokens):
        raise ValueError("Token rates must be finite.")
    if input_usd_per_million_tokens < 0 or output_usd_per_million_tokens < 0:
        raise ValueError("Token rates must be non-negative.")
    return (
        input_tokens * input_usd_per_million_tokens
        + output_tokens * output_usd_per_million_tokens
    ) / 1_000_000
