from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from evaluation.heldout import HeldOutValidationError, append_heldout_question, load_registry
from evaluation.schemas.held_out import HeldOutQuestion
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[2]
HELDOUT = ROOT / "evaluation/datasets/held_out"
CATEGORIES = [
    "direct_factual", "multi_passage", "multi_document", "unanswerable", "conflicting_policy",
    "version_sensitive", "academic_eligibility", "examination_assessment", "grading_academic_performance", "policy_interpretation", "prompt_injection",
]


def _ask(label: str) -> str:
    return input(f"{label}: ").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactively create a pending-review held-out annotation from a registered source PDF.")
    parser.add_argument("--registry", type=Path, default=HELDOUT / "documents.json")
    parser.add_argument("--dataset", type=Path, default=HELDOUT / "questions.jsonl")
    parser.add_argument("--development-dataset", type=Path, default=ROOT / "evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
    args = parser.parse_args()
    registry_path = args.registry
    dataset_path = args.dataset
    registry = load_registry(registry_path)
    if not registry.documents:
        print("No held-out documents are registered. Import and review an authorized PDF first.")
        return 2
    print("Registered documents:")
    for doc in registry.documents:
        print(f"- {doc.document_id}: {doc.document_title}; version={doc.version}; pages={doc.page_count}; "
              f"authority={doc.authority_status}/{doc.authority_review_status}; source={doc.provenance.source_url or doc.provenance.source_description}")
    question_id = _ask("Unique question ID")
    question_text = _ask("Question")
    print("Categories: " + ", ".join(CATEGORIES))
    category = _ask("Category")
    if category not in CATEGORIES:
        print("Unknown category.")
        return 2
    annotator = _ask("Annotator ID")
    answerable_input = _ask("Answerable? [y/n]").casefold()
    if answerable_input not in {"y", "yes", "n", "no"}:
        print("Enter y or n; no annotation was saved.")
        return 2
    answerable = answerable_input in {"y", "yes"}
    expected = None
    status = "NOT_FOUND"
    doc_ids: list[str] = []
    pages: list[dict] = []
    evidence: list[dict] = []
    claims: list[str] = []
    attack = "none"
    if answerable:
        expected = _ask("Expected answer, supported only by source evidence")
        print("Expected status: SUPPORTED, PARTIALLY_SUPPORTED, or CONFLICTING_SOURCES")
        status = _ask("Expected status")
        if status not in {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONFLICTING_SOURCES"}:
            print("Invalid expected status; no annotation was saved.")
            return 2
        try:
            count = int(_ask("Number of exact evidence spans"))
            if count < 1:
                raise ValueError
        except ValueError:
            print("Evidence count must be a positive integer.")
            return 2
        by_id = {doc.document_id: doc for doc in registry.documents}
        for index in range(count):
            evidence_doc_id = _ask(f"Evidence {index+1} document ID").strip()
            doc = by_id.get(evidence_doc_id)
            if doc is None:
                print("That document ID is not registered.")
                return 2
            try:
                page_number = int(_ask(f"Evidence {index+1} one-based page number"))
            except ValueError:
                print("Page number must be an integer.")
                return 2
            section = _ask(f"Evidence {index+1} section heading (blank if none)")
            evidence_id = _ask(f"Evidence {index+1} stable unique evidence ID")
            text = _ask(f"Evidence {index+1} exact source span")
            evidence.append({"document_id": doc.document_id, "document_version": doc.version, "page_number": page_number,
                             "section": section, "evidence_id": evidence_id, "text": text})
            page_ref = {"document_id": doc.document_id, "page_number": page_number, "section": section}
            if page_ref not in pages:
                pages.append(page_ref)
            if doc.document_id not in doc_ids:
                doc_ids.append(doc.document_id)
        while True:
            claim = _ask("Expected atomic claim (blank to finish)")
            if not claim:
                break
            claims.append(claim)
        if category == "prompt_injection":
            print("Attack surfaces: question, retrieved_document, both")
            attack = _ask("Attack surface")
    try:
        question = HeldOutQuestion.model_validate({
            "question_id": question_id, "question": question_text, "category": category,
            "expected_status": status, "answerable": answerable, "expected_answer": expected,
            "relevant_document_ids": doc_ids, "relevant_pages": pages, "relevant_evidence": evidence,
            "expected_claims": claims, "annotation_notes": _ask("Annotation notes"),
            "annotation_status": "PENDING_REVIEW", "annotator_id": annotator, "annotated_at": date.today().isoformat(),
            "reviewer_id": None, "reviewed_at": None, "attack_surface": attack, "dataset_version": "held_out-1.0",
        })
    except ValidationError as exc:
        print(f"Annotation is incomplete or inconsistent; no record was saved: {exc}")
        return 2
    try:
        summary = append_heldout_question(question, dataset_path, registry_path, args.development_dataset)
    except (HeldOutValidationError, ValueError) as exc:
        print(f"Draft was not saved: {exc}")
        return 2
    print(json.dumps({"saved_question_id": question.question_id, "annotation_status": "PENDING_REVIEW", "dataset_summary": summary}, indent=2))
    print("This item is pending and cannot be counted as approved until an independent reviewer completes review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
