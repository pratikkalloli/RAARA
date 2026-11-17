"""Interactive, explicit human review for one held-out policy evidence candidate."""
from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.policy_evidence_review import EvidenceReviewValidationError, inspect_evidence_candidate, record_evidence_review


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    held_out = root / "evaluation/held_out"
    parser = argparse.ArgumentParser(description="Display a source page and append an explicit human evidence review decision.")
    parser.add_argument("--evidence-id", required=True)
    parser.add_argument("--evidence", type=Path, default=held_out / "evidence_candidates.jsonl")
    parser.add_argument("--inventory", type=Path, default=held_out / "source_inventory.json")
    parser.add_argument("--review-log", type=Path, default=held_out / "evidence_reviews.jsonl")
    parser.add_argument("--files-root", type=Path, default=held_out)
    args = parser.parse_args()
    try:
        context = inspect_evidence_candidate(
            args.evidence_id,
            evidence_path=args.evidence,
            inventory_path=args.inventory,
            files_root=args.files_root,
        )
    except EvidenceReviewValidationError as exc:
        parser.exit(2, f"Evidence cannot be reviewed: {exc}\n")

    record = context["record"]
    source = context["source"]
    print("HUMAN EVIDENCE REVIEW — source evidence is read-only")
    print(f"Evidence ID: {record.evidence_id}")
    print(f"Document: {source.get('document_title') or source.get('title')}")
    print(f"Source URL: {record.source_url}")
    print(f"Local source: {context['pdf_path']}")
    print(f"SHA-256: {context['source_pdf_sha256']}")
    print(f"Issuing authority: {source.get('issuing_authority')}")
    print(f"Authority classification: {record.authority_status}")
    print(f"Publication/effective date: {source.get('publication_date')} / {record.effective_date}")
    print(f"Programme/campus/batch: {source.get('programme')} / {source.get('campus')} / {source.get('admission_batch')}")
    print(f"Version/supersession: {record.document_version} / {record.supersession_status}")
    print(f"Original PDF page: {record.page_number}; section: {record.section_heading}; subsection: {record.subsection}")
    print("\nExact candidate evidence passage:\n" + record.exact_text)
    print("\nExtracted text from the same original PDF page:\n" + context["page_text"])

    reviewer_id = input("Reviewer identity (as supplied by human reviewer): ").strip()
    decision = input("Decision: type APPROVE or REJECT: ").strip().upper()
    if decision not in {"APPROVE", "REJECT"}:
        parser.exit(2, "No decision recorded: decision must be APPROVE or REJECT.\n")
    rationale = input("Decision rationale (minimum 5 characters): ").strip()
    confirmation = input(f"Type {decision} again to record this decision: ").strip().upper()
    if confirmation != decision:
        parser.exit(2, "No decision recorded: confirmation did not match.\n")
    try:
        event = record_evidence_review(
            args.evidence_id,
            decision=decision,
            reviewer_id=reviewer_id,
            rationale=rationale,
            evidence_path=args.evidence,
            inventory_path=args.inventory,
            review_log_path=args.review_log,
            files_root=args.files_root,
        )
    except EvidenceReviewValidationError as exc:
        parser.exit(2, f"No decision recorded: {exc}\n")
    print(f"Review decision recorded: {event.decision}; reviewer={event.reviewer_id}; event={event.event_id}")
    print(f"Audit ledger: {args.review_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
