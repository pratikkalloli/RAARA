"""Run offline A/B/C diagnostics on development questions and isolated Chroma."""
from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from evaluation.prompt_experiments.runner import run_prompt_comparison
from evaluation.schemas.dataset import EvaluationQuestion
from evaluation.synthetic_project_data.validation import (
    DATASET_PATH,
    MANIFEST_PATH,
    ROOT,
    _load_json,
    validate_synthetic_dataset,
)


def run() -> dict:
    validation = validate_synthetic_dataset()
    master = _load_json(DATASET_PATH)
    development = [EvaluationQuestion.model_validate(row) for row in master["questions"] if row["dataset_split"] == "development"]
    results = ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)
    comparison_json = results / "synthetic_prompt_comparison.json"
    comparison_md = results / "synthetic_prompt_comparison.md"
    with tempfile.TemporaryDirectory(prefix="raara-p9a-dev-") as temp:
        dataset_file = Path(temp) / "development_questions.jsonl"
        dataset_file.write_text("\n".join(q.model_dump_json() for q in development) + "\n", encoding="utf-8")
        comparison = run_prompt_comparison(dataset_file, MANIFEST_PATH, comparison_json, comparison_md)
    report = {
        "report": "RAARA Phase 9A Synthetic Corpus Benchmark Validation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_version": validation["dataset_version"],
        "dataset_classification": {
            "dataset_type": "SYNTHETIC_PROJECT_DATA",
            "source_type": "PROJECT_AUTHORED",
            "is_official_university_policy": False,
        },
        "validation": validation,
        "benchmark_execution": {
            "development_questions_evaluated": len(development),
            "held_out_questions_evaluated": 0,
            "controlled_conflict_questions_evaluated": 0,
            "prompt_comparison_artifact": str(comparison_json.relative_to(ROOT)),
            "experiment_conditions": ["CONTROLLED_EVIDENCE", "END_TO_END_RAG"],
            "prompts": ["A", "B", "C"],
            "model": comparison["configuration"]["model_used"],
            "embedding": comparison["configuration"]["embedding_model_used"],
            "production_retrieval_settings_changed": False,
            "production_storage_touched": False,
            "live_openai_calls": False,
            "semantic_correctness_verified": False,
            "interpretation": comparison["analysis"]["reason"],
        },
        "retrieval_and_answer_diagnostics": {
            experiment: {
                prompt: result["metrics"]
                for prompt, result in comparison["experiments"][experiment]["prompt_types"].items()
            }
            for experiment in comparison["experiments"]
        },
        "artifacts": {
            "master_questions_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
            "primary_manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
            "prompt_comparison_json": str(comparison_json.relative_to(ROOT)),
            "prompt_comparison_markdown": str(comparison_md.relative_to(ROOT)),
        },
        "limitations": [
            "All policies, documents and questions are project-authored synthetic data, not university regulations.",
            "Only development questions were used for the diagnostic run; synthetic held-out questions were not used for tuning or scoring in this run.",
            "Conflict scenarios are kept in a separate corpus and were validated, not merged into the primary current-policy index.",
            "Generation uses a deterministic extractive mock that does not interpret the existing A/B/C prompts.",
            "Retrieval uses deterministic-tfidf-hash-v1 embeddings; production text-embedding-3-small performance is unverified.",
            "Automated exact-span and lexical checks do not establish semantic faithfulness or policy correctness.",
        ],
    }
    out_json = results / "benchmark_validation_report.json"
    out_md = results / "benchmark_validation_report.md"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Phase 9A Synthetic Benchmark Validation",
        "",
        "**Synthetic academic demonstration only — not official PES University policy.**",
        "",
        f"- Corpus documents: {validation['primary_policy_document_count']} current-model policies.",
        f"- Conflict fixtures: {validation['conflict_fixture_document_count']} superseded synthetic documents.",
        f"- Questions: {validation['question_count']} across development ({validation['split_counts']['development']}), synthetic held-out ({validation['split_counts']['held_out']}), and separate conflict ({validation['split_counts']['conflict']}) partitions.",
        f"- Exact page-level evidence references validated: {validation['evidence_reference_count']}.",
        f"- Numeric checks: {validation['validated_question_numeric_calculations']} question calculations and {validation['independently_recomputed_policy_worked_examples']} policy examples independently recomputed.",
        f"- A/B/C development diagnostics: {len(development)} questions; conditions CONTROLLED_EVIDENCE and END_TO_END_RAG.",
        f"- Adapter/model: `{comparison['configuration']['model_used']}`; embedding: `{comparison['configuration']['embedding_model_used']}`.",
        "- Held-out scoring: NOT RUN. Conflict scenarios: kept out of the primary current-policy index.",
        "- Live OpenAI calls: none. Production retrieval settings and storage: unchanged.",
        "",
        "## Interpretation",
        "",
        comparison["analysis"]["reason"],
        "",
        "A/B/C outputs are deterministic mock diagnostics, not real LLM performance. Automated exact-text and lexical metrics do not verify semantic faithfulness.",
        "",
        "## Artifacts",
        "",
        f"- `{comparison_json.relative_to(ROOT).as_posix()}` and `.md`: existing prompt experiment runner output over development questions only.",
        "- This report's JSON companion contains metric values and dataset checksums.",
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["validation"]["status"], "documents": result["validation"]["primary_policy_document_count"], "questions": result["validation"]["question_count"], "benchmark_questions": result["benchmark_execution"]["development_questions_evaluated"], "report": "results/benchmark_validation_report.json"}, indent=2))
