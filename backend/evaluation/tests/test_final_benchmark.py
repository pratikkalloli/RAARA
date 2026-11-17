from __future__ import annotations

import json
from pathlib import Path

from evaluation.final_benchmark import build_final_benchmark
from evaluation.live_eval_gate import inspect_live_eval_readiness


ROOT = Path(__file__).resolve().parents[2]


def test_live_gate_is_closed_by_default_and_never_returns_secret():
    readiness = inspect_live_eval_readiness({})
    assert not readiness.ready
    assert any("opt-in" in blocker for blocker in readiness.blockers)
    assert any("OPENAI_API_KEY" in blocker for blocker in readiness.blockers)


def test_live_gate_requires_explicit_opt_in_model_and_limits():
    ready = inspect_live_eval_readiness({
        "RAARA_ENABLE_LIVE_EVAL": "true",
        "OPENAI_API_KEY": "synthetic-test-secret",
        "RAARA_EVAL_MODEL": "test-model",
        "RAARA_EVAL_MAX_CALLS": "12",
        "RAARA_EVAL_MAX_BUDGET_USD": "1.25",
    })
    assert ready.ready
    assert ready.model == "test-model"
    assert ready.max_calls == 12
    assert ready.max_budget_usd == 1.25
    assert "synthetic-test-secret" not in repr(ready)


def test_live_gate_rejects_invalid_call_or_budget_limits():
    readiness = inspect_live_eval_readiness({
        "RAARA_ENABLE_LIVE_EVAL": "true",
        "OPENAI_API_KEY": "test",
        "RAARA_EVAL_MODEL": "test-model",
        "RAARA_EVAL_MAX_CALLS": "0",
        "RAARA_EVAL_MAX_BUDGET_USD": "NaN",
    })
    assert not readiness.ready
    assert any("MAX_CALLS" in blocker for blocker in readiness.blockers)
    assert any("MAX_BUDGET" in blocker for blocker in readiness.blockers)


def test_final_consolidation_preserves_separate_results_and_null_usage():
    data = build_final_benchmark(ROOT)
    assert data["dataset"]["question_count"] == 12
    assert data["dataset"]["held_out"]["question_count"] == 0
    assert data["dataset"]["held_out"]["benchmark_status"] == "BLOCKED"
    assert data["phase_7b"]["answerable_questions_with_relevant_retrieval"] == 1
    assert data["phase_7e_verification"]["evaluation_tests"] == {"passed": 52, "failed": 0}
    assert data["phase_7e_verification"]["full_backend_tests"] == {"passed": 157, "failed": 0}
    assert set(data["phase_7c"]) == {"CONTROLLED_EVIDENCE", "END_TO_END_RAG"}
    assert set(data["phase_7d"]["experiments"]) == {"CONTROLLED_EVIDENCE", "END_TO_END_RAG"}
    for experiment in data["phase_7d"]["experiments"].values():
        for prompt in experiment.values():
            usage = prompt["usage"]
            assert usage["input_tokens"] is None
            assert usage["output_tokens"] is None
            assert usage["total_tokens"] is None
            assert usage["estimated_api_cost_usd"] is None
    assert data["model_and_run_status"]["live_openai_validation"] == "NOT RUN"


def test_final_config_and_heldout_material_are_preparatory_only():
    config = json.loads((ROOT / "evaluation/final_benchmark_config.json").read_text(encoding="utf-8"))
    template = json.loads((ROOT / "evaluation/datasets/held_out/annotation_template.json").read_text(encoding="utf-8"))
    assert config["experiment_conditions"]["live_openai_authorized"] is False
    assert config["experiment_conditions"]["live_openai_calls"] == 0
    assert config["held_out"]["scoring_status"] == "BLOCKED"
    assert template["template_only"] is True
