from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.heldout import HeldOutValidationError, validate_heldout_dataset


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    heldout = root / "evaluation/datasets/held_out"
    parser = argparse.ArgumentParser(description="Validate held-out provenance, evidence, annotations, and split separation.")
    parser.add_argument("--dataset", type=Path, default=heldout / "questions.jsonl")
    parser.add_argument("--registry", type=Path, default=heldout / "documents.json")
    parser.add_argument("--development-dataset", type=Path, default=root / "evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
    parser.add_argument("--report", type=Path, default=heldout / "readiness_report.json")
    parser.add_argument("--source-inventory", type=Path, default=root / "evaluation/held_out/source_inventory.json")
    args = parser.parse_args()
    try:
        summary = validate_heldout_dataset(args.dataset, args.registry, args.development_dataset, args.source_inventory)
    except HeldOutValidationError as exc:
        parser.exit(1, f"Held-out validation failed:\n{exc}\n")
    args.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Held-out dataset readiness", "",
        "This file is generated from the held-out document registry and annotation JSONL. Synthetic development assets are excluded.", "",
        f"- Genuine documents imported: **{summary['genuine_documents_imported']}**",
        f"- Official documents independently verified: **{summary['official_documents_verified']}**",
        f"- Unofficial reference documents: **{summary['unofficial_reference_documents']}**",
        f"- Valid held-out questions: **{summary['valid_questions']}**",
        f"- Annotated questions: **{summary['annotated_questions']}**",
        f"- Approved questions: **{summary['approved_questions']}**",
        f"- Incomplete annotations: **{summary['incomplete_annotations']}**",
        f"- Category counts: `{json.dumps(summary['category_counts'], sort_keys=True)}`",
        f"- Total discovered sources: **{summary.get('total_discovered_sources', 0)}**",
        f"- Official verified source records: **{summary.get('official_verified_sources', 0)}**",
        f"- Official unverified source records: **{summary.get('official_unverified_sources', 0)}**",
        f"- Wrong-institution source records: **{summary.get('wrong_institution_sources', 0)}**",
        f"- Third-party reference records: **{summary.get('third_party_reference_sources', 0)}**",
        f"- Rejected source records: **{summary.get('rejected_sources', 0)}**",
        f"- Downloaded PDFs: **{summary.get('downloaded_pdfs', 0)}**",
        f"- PDFs opened: **{summary.get('successfully_opened_pdfs', 0)}**",
        f"- PDFs with text extracted: **{summary.get('successfully_text_extracted_pdfs', 0)}**",
        f"- PDFs with extraction warnings: **{summary.get('documents_with_extraction_warnings', 0)}**",
        f"- Proposed questions: **{summary.get('proposed_questions', summary['valid_questions'])}**",
        f"- Completed annotations: **{summary.get('completed_annotations', summary['annotated_questions'])}**",
        f"- Approved annotations: **{summary.get('approved_annotations', summary['approved_questions'])}**",
        f"- Rejected annotations: **{summary.get('rejected_annotations', 0)}**",
        f"- Pending annotations: **{summary.get('pending_annotations', summary['incomplete_annotations'])}**",
        f"- Phase 8B ready: **{'YES' if summary['ready_for_phase_8b'] else 'NO'}**",
        f"- Phase 8C ready (40+ approved): **{'YES' if summary['ready_for_phase_8c'] else 'NO'}**",
        f"- Current status: **{summary['dataset_readiness']}**",
        "", summary["status_note"], "",
    ]
    (args.report.parent / "readiness_report.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Readiness reports written: {args.report}, {args.report.parent / 'readiness_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
