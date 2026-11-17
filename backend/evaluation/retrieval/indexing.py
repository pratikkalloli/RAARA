from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from app.services.chunker import TextChunk, TokenChunker
from app.services.document_processor import extract_pdf_pages
from evaluation.retrieval.embeddings import DeterministicTfidfHashEmbedding

@dataclass(frozen=True)
class IndexedCorpus:
    chunks_by_document: dict[str,list[TextChunk]]
    added_chunks: int
    reused_chunks: int

class EvaluationIndexer:
    def __init__(self, vector_store: Any, embedder: Any, *, chunk_size: int|None=None, overlap: int|None=None):
        self.vector_store, self.embedder = vector_store, embedder
        if not chunk_size or overlap is None:
            from app.config import settings
        else:
            settings = None
        resolved_chunk_size = chunk_size or settings.chunk_size_tokens
        resolved_overlap = settings.chunk_overlap_tokens if overlap is None else overlap
        self.chunker=TokenChunker(resolved_chunk_size, resolved_overlap)
    def index(self, manifest_path: str|Path, manifest: dict[str,Any]) -> IndexedCorpus:
        base=Path(manifest_path).resolve().parent; chunks_by_document={}
        for doc in manifest["documents"]:
            path=(base/doc["path"]).resolve(); path.relative_to(base)
            pages=extract_pdf_pages(path.read_bytes())
            if len(pages)!=doc["page_count"]: raise ValueError(f"Page count mismatch for {doc['document_id']}")
            doc_id=doc["document_id"]
            metadata={"document_id":doc_id,"document_name":doc["document_name"],"document_type":"synthetic_test_document","academic_year":doc.get("academic_year", ""),"version":doc.get("version",""),"effective_date":doc.get("effective_date",""),"source_type":doc.get("source_type", "synthetic_controlled"),"verification_status":"unverified","uploaded_by_user_id":""}
            for key in ("dataset_type", "is_official_university_policy", "dataset_version", "applicable_programme", "applicable_campus", "applicable_admission_batches"):
                if key in doc:
                    metadata[key] = doc[key]
            chunks_by_document[doc_id]=self.chunker.chunk_pages(pages,metadata)
        all_chunks=[c for rows in chunks_by_document.values() for c in rows]
        if not all_chunks: return IndexedCorpus(chunks_by_document,0,0)
        texts=[c.text for c in all_chunks]; fit=getattr(self.embedder,"fit_documents",None)
        if callable(fit): fit(texts)
        vectors=self.embedder.embed_texts(texts)
        if len(vectors)!=len(all_chunks): raise ValueError("Embedding count does not match evaluation chunks")
        ids=[f"doc-{c.metadata['document_id']}-chunk-{c.chunk_index}" for c in all_chunks]
        existing=self.vector_store.collection.get(ids=ids,include=["documents","metadatas"])
        rows={pid:(doc,meta) for pid,doc,meta in zip(existing.get("ids",[]),existing.get("documents",[]),existing.get("metadatas",[]))}
        for pid,chunk in zip(ids,all_chunks):
            if pid in rows:
                old_text,old_meta=rows[pid]; expected={k:("" if v is None else v) for k,v in chunk.metadata.items()}
                if old_text!=chunk.text or any(old_meta.get(k)!=v for k,v in expected.items()): raise ValueError(f"Evaluation fixture differs for existing chunk {pid}")
        added=0; vector_by_chunk={id(c):v for c,v in zip(all_chunks,vectors)}
        for doc_id,chunks in chunks_by_document.items():
            missing=[c for c in chunks if f"doc-{doc_id}-chunk-{c.chunk_index}" not in rows]
            if missing: self.vector_store.add_chunks(doc_id,missing,[vector_by_chunk[id(c)] for c in missing]); added+=len(missing)
        return IndexedCorpus(chunks_by_document,added,len(all_chunks)-added)
