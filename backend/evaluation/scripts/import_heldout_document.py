from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.heldout import import_pdf_document


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    heldout = root / "evaluation/datasets/held_out"
    parser = argparse.ArgumentParser(
        description="Copy and register an authorized source PDF byte-for-byte; this never verifies official status automatically."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--authority", required=True, choices=["official", "unofficial_reference"])
    parser.add_argument("--acquisition-method", required=True, choices=["authorized_public_source", "project_owner_supplied"])
    parser.add_argument("--source-description", required=True)
    parser.add_argument("--permission-record", required=True)
    parser.add_argument("--retrieved-at", required=True, help="ISO date YYYY-MM-DD")
    parser.add_argument("--source-url")
    parser.add_argument("--publication-date")
    parser.add_argument("--effective-date")
    parser.add_argument("--supersedes", action="append", default=[])
    parser.add_argument("--registry", type=Path, default=heldout / "documents.json")
    args = parser.parse_args()
    record = import_pdf_document(
        args.source,
        args.registry,
        document_id=args.document_id,
        document_title=args.title,
        version=args.version,
        authority_status=args.authority,
        provenance={
            "acquisition_method": args.acquisition_method,
            "source_url": args.source_url,
            "source_description": args.source_description,
            "retrieved_at": args.retrieved_at,
            "permission_record": args.permission_record,
        },
        publication_date=args.publication_date,
        effective_date=args.effective_date,
        supersedes_document_ids=args.supersedes,
    )
    print(json.dumps({key: record[key] for key in ("document_id", "document_title", "version", "authority_status", "authority_review_status", "relative_path", "page_count", "sha256")}, indent=2))
    if args.authority == "official":
        print("Authority status remains pending independent verification. Update reviewer and review date only after source review.")
    print("No extraction, redaction, PDF modification, embedding, or OpenAI call was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
