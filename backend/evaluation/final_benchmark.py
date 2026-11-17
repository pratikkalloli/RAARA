"""Build a provenance-preserving consolidation of the Phase 6E–7D artifacts."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from evaluation.live_eval_gate import inspect_live_eval_readiness


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric_values(metric_group: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metric_group.items()}


def build_final_benchmark(root: Path) -> dict[str, Any]:
    results = root / "evaluation" / "results"
    dataset = root / "evaluation" / "datasets" / "development" / "raara_synthetic_starter_v0.1.0.jsonl"
    manifest = root / "evaluation" / "datasets" / "development" / "manifest.json"
    retrieval = json.loads((results / "retrieval_benchmark.json").read_text(encoding="utf-8"))
    quality = json.loads((results / "answer_quality_benchmark.json").read_text(encoding="utf-8"))
    prompt = json.loads((results / "prompt_comparison.json").read_text(encoding="utf-8"))
    prompt_groups: dict[str, Any] = {}
    for experiment, payload in prompt["experiments"].items():
        prompt_groups[experiment] = {
            prompt_id: {
                "name": item["prompt_name"],
                "metrics": item["metrics"]["all"],
                "answerable_metrics": item["metrics"]["answerable"],
                "unanswerable_metrics": item["metrics"]["unanswerable"],
                "by_category": item["metrics"]["by_category"],
                "usage": item["usage"],
            }
            for prompt_id, item in payload["prompt_types"].items()
        }

    source_paths = [
        "PHASE_6E_ACCEPTANCE_REPORT.md",
        "PHASE_7A_REPORT.md",
        "PHASE_7B_REPORT.md",
        "PHASE_7C_REPORT.md",
        "PHASE_7D_REPORT.md",
        "evaluation/results/retrieval_benchmark.json",
        "evaluation/results/answer_quality_benchmark.json",
        "evaluation/results/prompt_comparison.json",
        "evaluation/final_benchmark_config.json",
    ]
    source_artifacts = []
    for relative in source_paths:
        path = root / relative
        if path.is_file():
            source_artifacts.append({"path": relative.replace("\\", "/"), "sha256": sha256_file(path)})

    gate = inspect_live_eval_readiness()
    return {
        "report": "RAARA Final Benchmark Consolidation",
        "phase": "7E",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": "EVALUATION FRAMEWORK COMPLETE — LIVE EXPERIMENTS PENDING",
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine_architecture": platform.machine(),
            "processor": platform.processor() or None,
            "logical_cpu_count": __import__("os").cpu_count(),
        },
        "dataset": {
            "version": "0.1.0",
            "split": "development",
            "question_count": 12,
            "synthetic_only": True,
            "official_regulations": False,
            "sha256": sha256_file(dataset),
            "manifest_sha256": sha256_file(manifest),
            "held_out": {"status": "NOT AVAILABLE", "question_count": 0, "benchmark_status": "BLOCKED"},
        },
        "model_and_run_status": {
            "production_chat_model_configured": settings.openai_chat_model,
            "production_embedding_model_configured": settings.openai_embedding_model,
            "live_openai_used_in_phases_6e_7a_7d": False,
            "live_openai_validation": "NOT RUN",
            "openai_api_key_configured_at_finalization": bool(settings.openai_api_key),
            "live_eval_gate_ready": gate.ready,
            "live_eval_gate_blockers": list(gate.blockers),
            "embedding_used_in_7b_7c_7d": retrieval["configuration"]["embedding_model_used"],
            "generation_used_in_7c_7d": "deterministic-extractive-mock-v1",
            "generation_model_per_prompt": "deterministic-extractive-mock-v1",
            "generation_latency_scope": "local mock adapter execution only; not model latency",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "estimated_api_cost_usd": None,
            "semantic_faithfulness": "NOT TESTED",
        },
        "phase_6e": {
            "backend_regression": {"passed": 105, "failed": 0},
            "frontend_tests": {"passed": 7, "failed": 0},
            "frontend_production_build": "PASSED",
            "isolated_api_acceptance_checks": {"passed": 48, "failed": 0},
            "live_openai": "NOT TESTED",
            "browser_acceptance": "NOT TESTED",
            "semantic_faithfulness": "NOT TESTED",
        },
        "phase_7a": {
            "dataset_validator": "PASSED; 12 synthetic development questions",
            "evaluation_tests": {"passed": 24, "failed": 0},
            "full_backend_tests": {"passed": 129, "failed": 0},
        },
        "phase_7b": {
            "retrieval_metrics": retrieval["metrics"],
            "latency_ms_by_k": retrieval["latency_ms_by_k"],
            "configuration": retrieval["configuration"],
            "ground_truth_span_count": 15,
            "ground_truth_mapping": "exact document, page and section; each span mapped exactly once",
            "answerable_questions_with_relevant_retrieval": 1,
            "answerable_question_count": 10,
            "full_backend_tests": {"passed": 135, "failed": 0},
        },
        "phase_7c": {
            experiment: {
                "purpose": data["purpose"],
                "answerable": _metric_values(data["metrics"]["answerable"]),
                "unanswerable": _metric_values(data["metrics"]["unanswerable"]),
                "by_category": data["metrics"]["by_category"],
                "denominators": data["metrics"]["denominators"],
            }
            for experiment, data in quality["experiments"].items()
        },
        "phase_7d": {
            "simulation": True,
            "simulation_label": prompt["simulation_label"],
            "prompt_definitions": prompt["prompt_definitions"],
            "experiments": prompt_groups,
            "consistency": prompt["consistency"],
            "full_backend_tests": {"passed": 152, "failed": 0},
        },
        "phase_7e_verification": {
            "dataset_validation": {"status": "PASSED", "questions": 12},
            "evaluation_tests": {"passed": 52, "failed": 0},
            "full_backend_tests": {"passed": 157, "failed": 0},
            "live_openai_calls": 0,
        },
        "source_artifacts": source_artifacts,
        "consolidation_notes": [
            "Historical phase outputs are referenced and summarized without rewriting them.",
            "No production database, Chroma collection, or application setting was modified by finalization.",
            "No OpenAI requests were issued in Phase 7E.",
        ],
    }
