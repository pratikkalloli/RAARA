from __future__ import annotations

import hashlib
import inspect
import json
import statistics
import tempfile
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.prompting.prompt_templates import build_user_prompt
from app.prompting.system_prompt import PromptType, get_prompt_configuration
from app.services.citation_verifier import CitationVerifier
from app.services.generator import StructuredAnswer
from app.services.retriever import RetrievalResult, Retriever, RetrievedPassage
from app.services.vector_store import ChromaVectorStore
from evaluation.answer_quality.adapters import DeterministicMockGenerator
from evaluation.answer_quality.evaluator import evaluate_response, grouped_aggregates
from evaluation.metrics.performance import estimate_api_cost_usd
from evaluation.retrieval.ground_truth import build_ground_truth, evaluation_passage_id
from evaluation.retrieval.indexing import DeterministicTfidfHashEmbedding, EvaluationIndexer
from evaluation.schemas.dataset import validate_dataset


def _sha(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def retrieval_fingerprint(retrieval: RetrievalResult) -> str:
    return _sha(_canonical_json({
        "question": retrieval.question,
        "passages": [{"id": p.id, "text": p.text, "metadata": p.metadata} for p in retrieval.passages],
    }))


def output_schema_hash() -> str:
    return _sha(_canonical_json(StructuredAnswer.model_json_schema()))


class PromptDiagnosticGenerator:
    """Prompt-selection wrapper around the existing deterministic Phase 7C mock.

    It records the selected production prompt text and a common user payload, but
    deliberately does not ask the mock to interpret natural-language prompts.
    """
    model = DeterministicMockGenerator.model

    def __init__(self, base: DeterministicMockGenerator | None = None):
        self.base = base or DeterministicMockGenerator()
        self.calls: list[dict[str, Any]] = []

    def generate_with_usage(self, retrieval: RetrievalResult, *, prompt_type: PromptType | str) -> Any:
        config = get_prompt_configuration(prompt_type)
        passage_map = {f"P{i+1}": passage for i, passage in enumerate(retrieval.passages)}
        user_payload = build_user_prompt(retrieval, passage_map)
        schema_hash = output_schema_hash()
        combined_hash = _sha(config.system_instructions + "\n" + user_payload + "\n" + schema_hash)
        self.calls.append({
            "prompt_type": config.prompt_type.value,
            "prompt_name": config.name,
            "system_prompt_sha256": _sha(config.system_instructions),
            "user_payload_sha256": _sha(user_payload),
            "output_schema_sha256": schema_hash,
            "combined_prompt_sha256": combined_hash,
            "retrieval_fingerprint": retrieval_fingerprint(retrieval),
            "question": retrieval.question,
            "passage_ids": [passage.id for passage in retrieval.passages],
        })
        record = self.base.generate_with_usage(retrieval, prompt_type=config.prompt_type)
        # Phase 7C's adapter returns C for all calls; reflect the selected enum in
        # this comparison record while leaving its deterministic output untouched.
        return replace(record, prompt_type=config.prompt_type)


def _controlled_retrieval(question: Any, gold: Any, chunks_by_doc: dict[str, list[Any]]) -> RetrievalResult:
    passages = []
    for document_id, chunks in chunks_by_doc.items():
        for chunk in chunks:
            passage_id = evaluation_passage_id(document_id, chunk.chunk_index)
            if passage_id in gold.relevant_passage_ids:
                passages.append(RetrievedPassage(passage_id, chunk.text, chunk.metadata, 0.0, 1.0))
    return RetrievalResult(question.question, tuple(passages), max(1, len(passages)), 0.0)


def _usage_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = [row["input_tokens"] for row in rows]
    outputs = [row["output_tokens"] for row in rows]
    input_total = sum(inputs) if inputs and all(isinstance(x, int) for x in inputs) else None
    output_total = sum(outputs) if outputs and all(isinstance(x, int) for x in outputs) else None
    total = input_total + output_total if input_total is not None and output_total is not None else None
    input_rate = output_rate = None  # No pricing snapshot is configured in this offline experiment.
    cost = estimate_api_cost_usd(input_total, output_total, input_rate, output_rate)
    latencies = [row["generation_latency_ms"] for row in rows]
    return {
        "call_count": len(rows),
        "input_tokens": input_total,
        "output_tokens": output_total,
        "total_tokens": total,
        "calls_with_input_tokens": sum(isinstance(x, int) for x in inputs),
        "calls_with_output_tokens": sum(isinstance(x, int) for x in outputs),
        "generation_latency_ms": {
            "mean": statistics.mean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "sample_count": len(latencies),
            "interpretation": "local deterministic adapter wall time; not model latency",
        },
        "estimated_api_cost_usd": cost,
        "pricing_snapshot": None,
    }


def run_prompt_comparison(
    dataset_path: str | Path,
    manifest_path: str | Path,
    output_json: str | Path,
    output_markdown: str | Path,
) -> dict[str, Any]:
    dataset_path, manifest_path = Path(dataset_path), Path(manifest_path)
    dataset = validate_dataset(dataset_path, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    generator = PromptDiagnosticGenerator()
    verifier = CitationVerifier()

    # Prepare production-parity chunks in temporary, evaluation-only Chroma.
    with tempfile.TemporaryDirectory(prefix="raara-7d-fixtures-") as temp:
        fixture_store = ChromaVectorStore(temp, collection_name="prompt_fixture_chunks")
        fixture_index = EvaluationIndexer(fixture_store, DeterministicTfidfHashEmbedding()).index(manifest_path, manifest)
        fixture_store.client.close()
        chunks_by_doc = fixture_index.chunks_by_document
    gold = build_ground_truth(dataset.questions, chunks_by_doc)
    prompt_records: dict[str, list[dict[str, Any]]] = {p.value: [] for p in PromptType}
    retrieval_counts = {"CONTROLLED_EVIDENCE": 0, "END_TO_END_RAG": 0}

    def compare_question(question: Any, retrieval: RetrievalResult, experiment: str) -> None:
        retrieval_counts[experiment] += int(experiment == "END_TO_END_RAG")
        shared_fingerprint = retrieval_fingerprint(retrieval)
        # One immutable RetrievalResult is passed to each prompt selection.
        for prompt_type in PromptType:
            started = time.perf_counter_ns()
            generated = generator.generate_with_usage(retrieval, prompt_type=prompt_type)
            generation_latency_ms = (time.perf_counter_ns() - started) / 1_000_000
            evaluated = evaluate_response(
                question, gold[question.question_id], retrieval, generated.answer, verifier=verifier
            )
            evaluated.update({
                "experiment": experiment,
                "prompt_type": prompt_type.value,
                "prompt_name": get_prompt_configuration(prompt_type).name,
                "model": generated.model,
                "generation_latency_ms": generation_latency_ms,
                "input_tokens": generated.input_tokens,
                "output_tokens": generated.output_tokens,
                "total_tokens": generated.input_tokens + generated.output_tokens
                if generated.input_tokens is not None and generated.output_tokens is not None else None,
                "retrieval_fingerprint": shared_fingerprint,
                "retrieval_count_for_comparison": 0 if experiment == "CONTROLLED_EVIDENCE" else 1,
            })
            prompt_records[prompt_type.value].append(evaluated)

    # Controlled evidence: same exact gold chunks and metadata for A, B, and C.
    for question in dataset.questions:
        compare_question(question, _controlled_retrieval(question, gold[question.question_id], chunks_by_doc), "CONTROLLED_EVIDENCE")

    # End-to-end: retrieve once per question, then reuse that result for all A/B/C.
    with tempfile.TemporaryDirectory(prefix="raara-7d-rag-") as temp:
        store = ChromaVectorStore(temp, collection_name="prompt_end_to_end")
        embedder = DeterministicTfidfHashEmbedding()
        EvaluationIndexer(store, embedder).index(manifest_path, manifest)
        class WrappedEmbedder:
            def embed_texts(self, texts: list[str]) -> list[list[float]]:
                return embedder.embed_texts(texts)
        retriever = Retriever(
            WrappedEmbedder(), store,
            top_k=settings.retrieval_top_k,
            relevance_threshold=settings.retrieval_min_relevance,
        )
        for question in dataset.questions:
            retrieval = retriever.retrieve(question.question)
            compare_question(question, retrieval, "END_TO_END_RAG")
        store.client.close()

    # Request log order is question order, with A/B/C consecutively for every context.
    calls_by_exp_prompt = {
        exp: {ptype.value: [] for ptype in PromptType}
        for exp in ("CONTROLLED_EVIDENCE", "END_TO_END_RAG")
    }
    # Generator calls are ordered controlled A/B/C records, then end-to-end A/B/C.
    call_iter = iter(generator.calls)
    for exp in ("CONTROLLED_EVIDENCE", "END_TO_END_RAG"):
        for question in dataset.questions:
            for ptype in PromptType:
                calls_by_exp_prompt[exp][ptype.value].append(next(call_iter))

    prompt_definitions = {}
    template_source = inspect.getsource(build_user_prompt)
    for prompt_type in PromptType:
        config = get_prompt_configuration(prompt_type)
        prompt_definitions[prompt_type.value] = {
            "name": config.name,
            "version": "sha256-content-addressed",
            "system_prompt_sha256": _sha(config.system_instructions),
            "user_template_sha256": _sha(template_source),
            "output_schema_sha256": output_schema_hash(),
            "system_instruction_characters": len(config.system_instructions),
        }

    experiments: dict[str, Any] = {}
    for experiment in ("CONTROLLED_EVIDENCE", "END_TO_END_RAG"):
        experiments[experiment] = {"prompt_types": {}}
        for prompt_type in PromptType:
            rows = [row for row in prompt_records[prompt_type.value] if row["experiment"] == experiment]
            calls = calls_by_exp_prompt[experiment][prompt_type.value]
            experiments[experiment]["prompt_types"][prompt_type.value] = {
                "prompt_name": get_prompt_configuration(prompt_type).name,
                "metrics": grouped_aggregates(rows),
                "usage": _usage_summary(rows),
                "questions": rows,
                "prompt_calls": calls,
            }

    consistency: dict[str, Any] = {}
    for experiment in ("CONTROLLED_EVIDENCE", "END_TO_END_RAG"):
        per_question = {}
        for question in dataset.questions:
            rows = [
                next(row for row in prompt_records[p.value] if row["experiment"] == experiment and row["question_id"] == question.question_id)
                for p in PromptType
            ]
            fingerprints = {row["retrieval_fingerprint"] for row in rows}
            passage_lists = {tuple(row["retrieval"]["passage_ids"]) for row in rows}
            output_hashes = {_sha(row["generated_answer"]) for row in rows}
            per_question[question.question_id] = {
                "same_retrieval_context": len(fingerprints) == 1,
                "same_retrieved_passage_ids": len(passage_lists) == 1,
                "response_sha256_by_prompt": {row["prompt_type"]: _sha(row["generated_answer"]) for row in rows},
                "outputs_identical_under_mock": len(output_hashes) == 1,
            }
        consistency[experiment] = {
            "retrieval_operations": 0 if experiment == "CONTROLLED_EVIDENCE" else len(dataset.questions),
            "prompt_generations": len(dataset.questions) * len(PromptType),
            "same_evidence_passed_to_all_prompts": all(x["same_retrieval_context"] for x in per_question.values()),
            "same_passage_ids_passed_to_all_prompts": all(x["same_retrieved_passage_ids"] for x in per_question.values()),
            "per_question": per_question,
        }

    report = {
        "benchmark": "RAARA Phase 7D A/B/C Prompt Comparison",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
        "simulation_label": "SIMULATED_PROMPT_DIAGNOSTICS; deterministic mock does not interpret prompts",
        "dataset_version": dataset.dataset_version,
        "dataset_question_count": len(dataset.questions),
        "dataset_sha256": _sha(dataset_path.read_bytes()),
        "manifest_sha256": _sha(manifest_path.read_bytes()),
        "prompt_definitions": prompt_definitions,
        "experiments": experiments,
        "consistency": consistency,
        "configuration": {
            "model_used": generator.model,
            "production_chat_model_configured": settings.openai_chat_model,
            "embedding_model_used": "deterministic-tfidf-hash-v1",
            "production_embedding_model_configured": settings.openai_embedding_model,
            "retrieval_top_k": settings.retrieval_top_k,
            "retrieval_threshold": settings.retrieval_min_relevance,
            "distance_metric": "cosine",
            "chunk_size_tokens": settings.chunk_size_tokens,
            "chunk_overlap_tokens": settings.chunk_overlap_tokens,
            "generation_parameters": {"temperature": None, "max_output_tokens": None, "sampling": "deterministic local adapter"},
            "output_schema_sha256": output_schema_hash(),
            "live_openai_calls": False,
            "api_authorized": False,
            "pricing_snapshot": None,
            "storage": "temporary isolated Chroma for END_TO_END_RAG; no production storage writes",
        },
        "analysis": {
            "prompt_output_differences_measurable": False,
            "reason": "The deterministic mock ignores natural-language prompt instructions and returns the same extractive output for A, B, and C. Metric equality is an adapter limitation, not evidence that the prompts are equivalent for a real language model.",
            "best_prompt_by_metric": "A, B, and C tie on each metric under the deterministic mock; this is not a prompt-performance winner.",
            "structured_prompt_evidence_discipline": "Not measurable with this mock; no claim that C improves real model evidence discipline.",
            "statistical_significance": "Not assessed; 12 synthetic questions and a deterministic adapter are inadequate for inferential claims.",
        },
        "limitations": [
            "The 12-question corpus and PDFs are synthetic development data, not official regulations.",
            "No live OpenAI generation was run; credentials and live service behavior were not exercised.",
            "The deterministic mock does not process prompt text, so A/B/C output equality is expected and cannot establish model prompt effects.",
            "The local embedding substitute is not text-embedding-3-small; production embedding performance is unverified.",
            "Token usage is unavailable for the mock and remains null; no pricing snapshot is configured, so estimated API cost remains null.",
            "Measured generation latency is local adapter execution time and is not representative of model latency.",
            "No held-out dataset or statistical significance analysis is available.",
        ],
    }

    out = Path(output_json); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# RAARA Phase 7D A/B/C Prompt Comparison", "",
        "**SIMULATED_PROMPT_DIAGNOSTICS** — the deterministic mock does not interpret prompt text. These results are not real LLM prompt-performance measurements.", "",
        f"- Dataset: `{dataset.dataset_version}` ({len(dataset.questions)} synthetic questions)",
        f"- Model used: `{generator.model}`; production chat model configured: `{settings.openai_chat_model}` (not called)",
        "- Embedding: `deterministic-tfidf-hash-v1`; no live OpenAI calls.",
        "- Prompt hashes and per-question details are in the JSON artifact.", "",
        "A/B/C receive the same retrieval object, evidence metadata, model adapter, generation settings, and StructuredAnswer schema for each question. End-to-end retrieval is run once per question and reused across the three prompts.",
    ]
    metric_names = ("normalized_exact_match", "key_fact_coverage", "claim_support_rate", "claim_contradiction_rate", "answer_relevance", "citation_precision", "citation_recall", "document_accuracy", "page_accuracy", "correct_abstention_rate", "false_answer_rate", "fabricated_citation_rate")
    for experiment in ("CONTROLLED_EVIDENCE", "END_TO_END_RAG"):
        md += ["", f"## {experiment}", "", "| Metric | A | B | C |", "|---|---:|---:|---:|"]
        for name in metric_names:
            values=[]
            for p in ("A","B","C"):
                metric=experiments[experiment]["prompt_types"][p]["metrics"]["answerable"][name]
                value=metric["value"]
                values.append("N/A" if value is None else f"{value:.3f} (n={metric['count']})")
            md.append(f"| {name} | {values[0]} | {values[1]} | {values[2]} |")
        md += ["", "### Unanswerable questions", "", "| Metric | A | B | C |", "|---|---:|---:|---:|"]
        for name in ("correct_abstention_rate", "false_answer_rate", "fabricated_citation_rate"):
            values=[]
            for p in ("A","B","C"):
                metric=experiments[experiment]["prompt_types"][p]["metrics"]["unanswerable"][name]
                value=metric["value"]; values.append("N/A" if value is None else f"{value:.3f} (n={metric['count']})")
            md.append(f"| {name} | {values[0]} | {values[1]} | {values[2]} |")
        md += ["", "### Key-fact coverage by category", "", "| Category | A | B | C |", "|---|---:|---:|---:|"]
        categories=experiments[experiment]["prompt_types"]["A"]["metrics"]["by_category"]
        for category in sorted(categories):
            values=[]
            for p in ("A","B","C"):
                metric=experiments[experiment]["prompt_types"][p]["metrics"]["by_category"][category]["key_fact_coverage"]
                value=metric["value"]; values.append("N/A" if value is None else f"{value:.3f} (n={metric['count']})")
            md.append(f"| {category} | {values[0]} | {values[1]} | {values[2]} |")
        md += ["", "| Prompt | Input tokens | Output tokens | Total tokens | Mean adapter latency ms | Estimated cost USD |", "|---|---:|---:|---:|---:|---:|"]
        for p in ("A","B","C"):
            usage=experiments[experiment]["prompt_types"][p]["usage"]
            latency=usage["generation_latency_ms"]["mean"]
            latency_text=f"{latency:.6f}" if latency is not None else "N/A"
            md.append(f"| {p} | {usage['input_tokens'] if usage['input_tokens'] is not None else 'N/A'} | {usage['output_tokens'] if usage['output_tokens'] is not None else 'N/A'} | {usage['total_tokens'] if usage['total_tokens'] is not None else 'N/A'} | {latency_text} | {usage['estimated_api_cost_usd'] if usage['estimated_api_cost_usd'] is not None else 'N/A'} |")
    md += ["", "## Interpretation", "", report["analysis"]["reason"], "", "The prompts tie on the deterministic mock. This cannot show whether structured prompting improves evidence discipline with a real model. There is no statistically supported winner.", "", "## Limitations", *["- "+item for item in report["limitations"]], ""]
    Path(output_markdown).parent.mkdir(parents=True, exist_ok=True)
    Path(output_markdown).write_text("\n".join(md), encoding="utf-8")
    return report
