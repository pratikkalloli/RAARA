from __future__ import annotations
import json
from pathlib import Path
import pytest
from app.services.chunker import TextChunk
from evaluation.retrieval.ground_truth import GroundTruthMappingError, build_ground_truth
from evaluation.retrieval.metrics import aggregate, percentile95, score_query
from evaluation.retrieval.indexing import DeterministicTfidfHashEmbedding
from evaluation.schemas.dataset import load_dataset, validate_dataset

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"datasets/development/raara_synthetic_starter_v0.1.0.jsonl"
MANIFEST=ROOT/"datasets/development/manifest.json"

def test_ground_truth_requires_full_span_and_same_page_section():
    class E:
        def __init__(self,document_id,page_number,section,evidence_id,text): self.document_id=document_id; self.page_number=page_number; self.section=section; self.evidence_id=evidence_id; self.text=text
    class Q:
        question_id="q"; relevant_evidence=[E("doc",1,"Policy","ev","attendance must be 80 percent")]; relevant_pages=[]; relevant_document_ids=["doc"]; expected_status="SUPPORTED"
    chunk=TextChunk("attendance must be 80 percent",1,"Policy",0,5,{})
    mapped=build_ground_truth([Q() ],{"doc":[chunk]})["q"]
    assert mapped.relevant_passage_ids==frozenset({"doc-doc-chunk-0"})
    wrong=TextChunk("attendance must be 80",1,"Policy",0,4,{})
    with pytest.raises(GroundTruthMappingError): build_ground_truth([Q()],{"doc":[wrong]})

def test_metrics_exclude_unanswerable_from_recall_and_p95_requires_samples():
    from types import SimpleNamespace
    gold=SimpleNamespace(answerable=False,relevant_passage_ids=frozenset(),relevant_document_ids=frozenset(),relevant_pages=frozenset())
    row=score_query([],[],[],gold,3)
    assert row["unanswerable_detection"]==1 and row["recall_at_k"] is None
    assert aggregate([row])["recall_at_k"]["count"]==0
    assert percentile95(list(range(19))) is None
    assert percentile95(list(range(20)))==18

def test_tfidf_hash_embeddings_are_deterministic_and_normalized():
    embed=DeterministicTfidfHashEmbedding(); texts=["attendance minimum is eighty percent","deadline for appeal"]
    embed.fit_documents(texts); a=embed.embed_texts(texts); b=embed.embed_texts(texts)
    assert a==b and all(abs(sum(v*v for v in vector)-1)<1e-9 for vector in a)

def test_precision_recall_and_mrr_with_irrelevant_duplicates_and_multiple_gold():
    from types import SimpleNamespace
    gold=SimpleNamespace(answerable=True,relevant_passage_ids=frozenset({"a","c"}),relevant_document_ids=frozenset({"d1","d2"}),relevant_pages=frozenset({("d1",1),("d2",3)}))
    row=score_query(["x","a","a","c"],["bad","d1","d1","d2"],[("bad",9),("d1",1),("d1",1),("d2",3)],gold,3)
    assert row["precision_at_k"]==pytest.approx(1/3)
    assert row["recall_at_k"]==pytest.approx(1/2)
    assert row["reciprocal_rank"]==pytest.approx(1/2)
    assert row["hit_rate"]==1 and row["document_hit_rate"]==1 and row["page_hit_rate"]==1

def test_evaluation_indexing_is_repeatable_and_isolated(tmp_path):
    import json
    from app.services.vector_store import ChromaVectorStore
    from evaluation.retrieval.indexing import EvaluationIndexer
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    store=ChromaVectorStore(tmp_path/"only-evaluation",collection_name="test_phase7b")
    embed=DeterministicTfidfHashEmbedding()
    indexer=EvaluationIndexer(store,embed)
    first=indexer.index(MANIFEST,manifest); second=indexer.index(MANIFEST,manifest)
    assert first.added_chunks==12 and first.reused_chunks==0
    assert second.added_chunks==0 and second.reused_chunks==12
    assert store.count()==12
    assert store.persist_directory==str(tmp_path/"only-evaluation")
    store.client.close()

def test_dataset_exact_evidence_span_mapping_audit():
    # Production extractor and chunker are reused, while no persistent store is opened here.
    import json
    from evaluation.retrieval.indexing import EvaluationIndexer, DeterministicTfidfHashEmbedding
    from app.services.chunker import TokenChunker
    from app.services.document_processor import extract_pdf_pages
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8")); chunks={}
    for doc in manifest["documents"]:
        pages=extract_pdf_pages((MANIFEST.parent/doc["path"]).read_bytes())
        meta={"document_id":doc["document_id"],"document_name":doc["document_name"],"document_type":"synthetic_test_document","academic_year":"","version":doc["version"],"effective_date":doc["effective_date"],"source_type":"synthetic_controlled","verification_status":"unverified","uploaded_by_user_id":""}
        chunks[doc["document_id"]]=TokenChunker(700,100).chunk_pages(pages,meta)
    q=load_dataset(DATA); mapped=build_ground_truth(q,chunks)
    assert sum(len(item.evidence_to_passage_ids) for item in mapped.values())==15
    assert all(len(passage_ids)==1 for item in mapped.values() for passage_ids in item.evidence_to_passage_ids.values())
    assert sum(not item.answerable for item in mapped.values())==2
