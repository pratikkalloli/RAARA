"""Re-index retained PDFs into RAARA's separate local 384d collection.

Default behavior is a read-only preflight. Pass --apply to write vectors and
update document synchronization metadata. The previous Gemini collection is
never opened or deleted.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database.db import SessionLocal
from app.database.models import Document
from app.services.chunker import TokenChunker
from app.services.embeddings import create_embedding_service
from app.services.reindex import ReindexError, read_managed_source, reindex_document
from app.services.vector_store import ChromaVectorStore

logger = logging.getLogger("raara.reindex")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write local vectors and update document sync state")
    parser.add_argument("--limit", type=int, default=None, help="preflight or process at most this many documents")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    try:
        settings.validate_runtime_configuration()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if settings.active_embedding_collection_name != "raara_documents_groq_local_384":
        print("Configuration error: active collection is not the isolated local 384d collection.", file=sys.stderr)
        return 2

    upload_root = Path(settings.upload_dir).resolve()
    with SessionLocal() as session:
        statement = select(Document).order_by(Document.id)
        if args.limit is not None:
            statement = statement.limit(args.limit)
        documents = list(session.scalars(statement))
        prepared: list[tuple[Document, bytes]] = []
        blocked: list[tuple[int, str]] = []
        for document in documents:
            try:
                prepared.append((document, read_managed_source(document, upload_root)))
            except ReindexError as exc:
                blocked.append((document.id, str(exc)))

        print(
            f"documents={len(documents)} ready={len(prepared)} blocked={len(blocked)} "
            f"collection={settings.active_embedding_collection_name} mode={'apply' if args.apply else 'dry-run'}"
        )
        if blocked:
            for document_id, reason in blocked:
                print(f"blocked_document_id={document_id} reason={reason}")
            print("No vectors or database records were changed because preflight was not clean.")
            return 2
        if not args.apply:
            print("Dry run only. Review the counts, then rerun with --apply to re-index.")
            return 0

        embedder = create_embedding_service()
        vector_store = ChromaVectorStore()
        chunker = TokenChunker(settings.chunk_size_tokens, settings.chunk_overlap_tokens)
        failures = 0
        for document, content in prepared:
            try:
                chunk_count = reindex_document(
                    document, content, embedder=embedder, vector_store=vector_store, chunker=chunker
                )
                session.commit()
                print(f"indexed_document_id={document.id} chunks={chunk_count}")
            except Exception as exc:
                session.rollback()
                failures += 1
                logger.error(
                    "Document reindex failed (document_id=%s, exception_type=%s)",
                    document.id,
                    type(exc).__name__,
                )
                print(f"failed_document_id={document.id} error={type(exc).__name__}")
        print(f"reindex_complete={failures == 0} failed={failures} previous_collections=preserved")
        return 1 if failures else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
