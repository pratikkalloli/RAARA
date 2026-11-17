"""Interactive and one-shot CLI for the isolated, offline policy demo."""
from __future__ import annotations

import argparse
import json
import sys

from evaluation.generic_policy_demo.pipeline import GenericPolicyDemo
from evaluation.generic_policy_demo.retriever import DEFAULT_MIN_RELEVANCE, DEFAULT_TOP_K


DISCLAIMER = (
    "RAARA GENERIC POLICY DEMONSTRATION - project-authored examples only. "
    "Not official PES University policy or universal academic requirements."
)


def _render(run) -> str:
    data = {
        "question": run.question,
        "retrieved_evidence": [
            {
                "policy_id": row.policy_id,
                "evidence_id": row.evidence_id,
                "title": row.title,
                "category": row.category,
                "version": row.version,
                "provenance": row.provenance,
                "source_type": row.source_type,
                "authority_status": row.authority_status,
                "is_official_university_policy": row.is_official_university_policy,
                "score": row.score,
                "context_label": row.context_label,
                "exact_text": row.exact_text,
            }
            for row in run.retrieved
        ],
        "answer": run.answer.answer,
        "status": run.answer.status,
        "citations": [citation.__dict__ for citation in run.answer.citations],
        "citations_validated": run.citations_validated,
        "disclaimer": run.answer.disclaimer,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline RAARA generic academic-policy RAG demonstration.")
    parser.add_argument("--question", help="Run one question and exit; omit for interactive mode.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--min-relevance", type=float, default=DEFAULT_MIN_RELEVANCE)
    args = parser.parse_args()
    try:
        demo = GenericPolicyDemo(top_k=args.top_k, min_relevance=args.min_relevance)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Cannot initialize isolated demo: {exc}\n")

    print(DISCLAIMER)
    print("Answerer: deterministic local templates/calculations; no LLM or network calls.")
    if args.question is not None:
        try:
            print(_render(demo.ask(args.question)))
        except ValueError as exc:
            parser.exit(2, f"Invalid question/calculation: {exc}\n")
        return 0

    print("Ask a question; enter 'exit' or 'quit' to stop.")
    while True:
        try:
            question = input("RAARA demo> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.casefold() in {"exit", "quit"}:
            break
        if not question:
            continue
        try:
            print(_render(demo.ask(question)))
        except ValueError as exc:
            print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
