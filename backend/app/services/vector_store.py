"""Persistent ChromaDB storage for page-aware, verified-metadata document chunks."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import chromadb

from app.config import settings
from app.services.chunker import TextChunk

logger = logging.getLogger(__name__)
REQUIRED_METADATA = (
    "document_id",
    "document_name",
    "document_type",
    "page_number",
    "section",
    "academic_year",
    "version",
    "effective_date",
    "source_type",
    "verification_status",
    "uploaded_by_user_id",
)


class VectorStoreError(RuntimeError):
    pass


class ChromaVectorStore:
    def __init__(
        self,
        persist_directory: str | Path | None = None,
        *,
        collection_name: str | None = None,
        collection: Any | None = None,
    ) -> None:
        self.persist_directory = str(persist_directory or settings.chroma_persist_dir)
        self.collection_name = collection_name or settings.active_embedding_collection_name
        self._active_embedding_collection = collection is None and collection_name is None
        try:
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            if collection is not None:
                self.collection = collection
                self.client = None
            else:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={
                        "hnsw:space": "cosine",
                        "embedding_provider": settings.embedding_provider.strip().casefold(),
                        "embedding_model": settings.active_embedding_model,
                        "embedding_dimensions": settings.active_embedding_dimensions,
                    },
                )
                if self._active_embedding_collection:
                    self._validate_active_collection()
        except VectorStoreError:
            raise
        except Exception as exc:
            logger.exception("Unable to initialize persistent ChromaDB collection")
            raise VectorStoreError("The document vector store could not be opened.") from exc

    def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception as exc:
            logger.error("ChromaDB collection count failed (exception_type=%s)", type(exc).__name__)
            raise VectorStoreError("The document vector store could not be read.") from exc

    def add_chunks(self, document_id: int | str, chunks: list[TextChunk], embeddings: list[list[float]]) -> list[str]:
        if len(chunks) != len(embeddings):
            raise ValueError("Every chunk must have exactly one embedding.")
        if not chunks:
            return []
        self._validate_embedding_dimensions(embeddings)

        ids = [f"doc-{document_id}-chunk-{chunk.chunk_index}" for chunk in chunks]
        metadatas: list[dict[str, Any]] = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            missing = [key for key in REQUIRED_METADATA if key not in metadata]
            if missing:
                raise ValueError(f"Chunk metadata is missing required fields: {', '.join(missing)}")
            # Chroma accepts scalar values, not None; empty strings preserve absent optional metadata.
            metadatas.append({key: ("" if value is None else value) for key, value in metadata.items()})
        try:
            self.collection.add(
                ids=ids,
                documents=[chunk.text for chunk in chunks],
                embeddings=embeddings,
                metadatas=metadatas,
            )
            return ids
        except Exception as exc:
            logger.exception("Unable to index document %s in ChromaDB", document_id)
            raise VectorStoreError("The document could not be indexed.") from exc

    def replace_document_chunks(
        self,
        document_id: int | str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> list[str]:
        """Upsert local vectors, verify them, then remove stale chunks from this collection only."""
        if len(chunks) != len(embeddings):
            raise ValueError("Every chunk must have exactly one embedding.")
        if not chunks:
            raise ValueError("A reindex operation requires at least one text chunk.")
        self._validate_embedding_dimensions(embeddings)
        ids = [f"doc-{document_id}-chunk-{chunk.chunk_index}" for chunk in chunks]
        metadatas: list[dict[str, Any]] = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            missing = [key for key in REQUIRED_METADATA if key not in metadata]
            if missing:
                raise ValueError(f"Chunk metadata is missing required fields: {', '.join(missing)}")
            metadatas.append({key: ("" if value is None else value) for key, value in metadata.items()})
        try:
            self.collection.upsert(
                ids=ids,
                documents=[chunk.text for chunk in chunks],
                embeddings=embeddings,
                metadatas=metadatas,
            )
            current_ids = self.collection.get(
                where={"document_id": str(document_id)}, include=[]
            ).get("ids", [])
            if not set(ids).issubset(set(current_ids)):
                raise ValueError("The active local collection did not confirm every reindexed chunk.")
            stale_ids = [identifier for identifier in current_ids if identifier not in set(ids)]
            if stale_ids:
                self.collection.delete(ids=stale_ids)
            return ids
        except Exception as exc:
            logger.error(
                "Local collection reindex failed (document_id=%s, exception_type=%s)",
                document_id,
                type(exc).__name__,
            )
            raise VectorStoreError("The document could not be safely synchronized to the local collection.") from None

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        self._validate_embedding_dimensions([query_embedding])
        try:
            response = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            documents = response.get("documents", [[]])[0]
            metadatas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0]
            ids = response.get("ids", [[]])[0]
            return [
                {"id": ids[index], "text": documents[index], "metadata": metadatas[index], "distance": distances[index]}
                for index in range(len(documents))
            ]
        except Exception as exc:
            logger.exception("ChromaDB query failed")
            raise VectorStoreError("The document vector store could not be queried.") from exc

    def get_document_chunks(self, document_id: int | str) -> list[dict[str, Any]]:
        """Read all indexed chunks for one already-authorized document in source order."""
        try:
            response = self.collection.get(
                where={"document_id": str(document_id)},
                include=["documents", "metadatas"],
            )
            ids = response.get("ids", [])
            documents = response.get("documents", [])
            metadatas = response.get("metadatas", [])
            if not (len(ids) == len(documents) == len(metadatas)):
                raise ValueError("Chroma returned incomplete document chunk records.")
            chunks = [
                {"id": identifier, "text": text, "metadata": metadata}
                for identifier, text, metadata in zip(ids, documents, metadatas)
            ]
            chunks.sort(key=_document_chunk_sort_key)
            return chunks
        except Exception as exc:
            logger.error(
                "Unable to load full document chunks (exception_type=%s)",
                type(exc).__name__,
            )
            raise VectorStoreError("The selected document content could not be loaded from the index.") from None

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self.collection.delete(ids=ids)
        except Exception:
            logger.exception("Unable to roll back ChromaDB chunk IDs %s", ids)
    def delete_document(self, document_id: int | str) -> None:
        try:
            matches = self.collection.get(where={"document_id": str(document_id)}, include=[])
            ids = matches.get("ids", [])
            if ids:
                self.collection.delete(ids=ids)
            remaining = self.collection.get(where={"document_id": str(document_id)}, include=[]).get("ids", [])
            if remaining:
                raise ValueError("Some vectors remained after document deletion.")
        except Exception as exc:
            logger.error(
                "Unable to delete ChromaDB vectors for document %s (exception_type=%s)",
                document_id,
                type(exc).__name__,
            )
            raise VectorStoreError("Document vectors could not be deleted safely.") from None

    def update_document_metadata(self, document_id: int | str, updates: dict[str, Any]) -> int:
        """Merge metadata updates into every indexed chunk for a document."""
        try:
            records = self.collection.get(
                where={"document_id": str(document_id)},
                include=["metadatas"],
            )
            ids = records.get("ids", [])
            metadata_rows = records.get("metadatas", [])
            if not ids or len(ids) != len(metadata_rows):
                raise ValueError("No complete indexed chunk metadata was found for the document.")
            merged = []
            for metadata in metadata_rows:
                if not isinstance(metadata, dict) or str(metadata.get("document_id")) != str(document_id):
                    raise ValueError("A document chunk has inconsistent identity metadata.")
                merged.append({**metadata, **updates})
            self.collection.update(ids=ids, metadatas=merged)
            confirmed = self.collection.get(
                where={"document_id": str(document_id)},
                include=["metadatas"],
            )
            confirmed_ids = confirmed.get("ids", [])
            confirmed_metadata = confirmed.get("metadatas", [])
            if len(confirmed_ids) != len(ids) or len(confirmed_metadata) != len(ids):
                raise ValueError("Vector metadata update could not be confirmed for every chunk.")
            if any(any(row.get(key) != value for key, value in updates.items()) for row in confirmed_metadata):
                raise ValueError("Some vector chunks still have stale metadata after the update.")
            return len(ids)
        except Exception as exc:
            logger.error(
                "Unable to synchronize metadata for document %s (exception_type=%s)",
                document_id,
                type(exc).__name__,
            )
            raise VectorStoreError("Document verification metadata could not be synchronized.") from exc

    def _validate_active_collection(self) -> None:
        metadata = self.collection.metadata or {}
        expected = {
            "hnsw:space": "cosine",
            "embedding_provider": "local",
            "embedding_model": settings.active_embedding_model,
            "embedding_dimensions": settings.active_embedding_dimensions,
        }
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise VectorStoreError(
                "The active collection does not match local 384-dimensional cosine vectors. "
                "Existing vectors were left untouched; configure a fresh local collection."
            )

    def _validate_embedding_dimensions(self, embeddings: list[list[float]]) -> None:
        if self._active_embedding_collection and any(
            len(embedding) != settings.active_embedding_dimensions for embedding in embeddings
        ):
            raise ValueError("The active vector collection requires 384-dimensional local embeddings.")


def _document_chunk_sort_key(record: dict[str, Any]) -> tuple[int, int, str]:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    try:
        page = int(metadata.get("page_number", 0))
    except (TypeError, ValueError):
        page = 0
    match = re.search(r"-chunk-(\d+)$", str(record.get("id", "")))
    index = int(match.group(1)) if match else 0
    return page, index, str(record.get("id", ""))
