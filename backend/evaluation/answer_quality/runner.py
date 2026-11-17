from __future__ import annotations
import hashlib, json, statistics, tempfile, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.config import settings
from app.services.citation_verifier import CitationVerifier
from app.services.retriever import RetrievalResult, RetrievedPassage, Retriever
from app.services.vector_store import ChromaVectorStore
from evaluation.answer_quality.adapters import DeterministicMockGenerator
from evaluation.answer_quality.evaluator import evaluate_response, grouped_aggregates
from evaluation.retrieval.ground_truth import build_ground_truth, evaluation_passage_id
from evaluation.retrieval.indexing import DeterministicTfidfHashEmbedding, EvaluationIndexer
from evaluation.schemas.dataset import validate_dataset

def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def _controlled_retrieval(question: Any, gold: Any, chunks_by_doc: dict[str,list[Any]]) -> RetrievalResult:
    passages=[]
    wanted=gold.relevant_passage_ids
    for document_id,chunks in chunks_by_doc.items():
        for chunk in chunks:
            passage_id=evaluation_passage_id(document_id,chunk.chunk_index)
            if passage_id in wanted:
                passages.append(RetrievedPassage(passage_id,chunk.text,chunk.metadata,0.0,1.0))
    return RetrievalResult(question.question,tuple(passages),max(1,len(passages)),0.0)

def run_answer_quality(dataset_path: str|Path,manifest_path: str|Path,output_json: str|Path,output_markdown: str|Path) -> dict[str,Any]:
    dataset_path,manifest_path=Path(dataset_path),Path(manifest_path)
    dataset=validate_dataset(dataset_path,manifest_path); manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    embed=DeterministicTfidfHashEmbedding(); generator=DeterministicMockGenerator(); verifier=CitationVerifier()
    # The controlled experiment uses only gold-aligned passage chunks and bypasses retrieval.
    chunks_by_doc={}
    with tempfile.TemporaryDirectory(prefix="raara-7c-controlled-") as temp:
        # An evaluation indexer provides production extraction/chunking without persistent DB use.
        local_store=ChromaVectorStore(temp,collection_name="controlled_fixture_index")
        indexed=EvaluationIndexer(local_store,embed).index(manifest_path,manifest)
        local_store.client.close()
        chunks_by_doc=indexed.chunks_by_document
    ground_truth=build_ground_truth(dataset.questions,chunks_by_doc)
    controlled=[]; e2e=[]
    for question in dataset.questions:
        retrieval=_controlled_retrieval(question,ground_truth[question.question_id],chunks_by_doc)
        generated=generator.generate_with_usage(retrieval)
        row=evaluate_response(question,ground_truth[question.question_id],retrieval,generated.answer,verifier=verifier)
        row["experiment"]="CONTROLLED_EVIDENCE"; row["generation_model"]=generated.model; row["generation_adapter"]=generator.model
        row["retrieval_mode"]="bypassed; ground-truth evidence chunks supplied"
        controlled.append(row)

    # End-to-end experiment builds an isolated temporary Chroma corpus and invokes production Retriever once/query.
    with tempfile.TemporaryDirectory(prefix="raara-7c-rag-") as temp:
        store=ChromaVectorStore(temp,collection_name="end_to_end_eval")
        index_embed=DeterministicTfidfHashEmbedding()
        indexed=EvaluationIndexer(store,index_embed).index(manifest_path,manifest)
        ground_truth=build_ground_truth(dataset.questions,indexed.chunks_by_document)
        class TimedEmbedder:
            def __init__(self,wrapped): self.wrapped=wrapped
            def embed_texts(self,texts): return self.wrapped.embed_texts(texts)
        retriever=Retriever(TimedEmbedder(index_embed),store,top_k=settings.retrieval_top_k,relevance_threshold=settings.retrieval_min_relevance)
        for question in dataset.questions:
            start=time.perf_counter_ns(); retrieval=retriever.retrieve(question.question); retrieval_ms=(time.perf_counter_ns()-start)/1e6
            start=time.perf_counter_ns(); generated=generator.generate_with_usage(retrieval); generation_ms=(time.perf_counter_ns()-start)/1e6
            row=evaluate_response(question,ground_truth[question.question_id],retrieval,generated.answer,verifier=verifier)
            row["experiment"]="END_TO_END_RAG"; row["generation_model"]=generated.model; row["generation_adapter"]=generator.model
            row["retrieval_mode"]="production Retriever over isolated evaluation Chroma collection"
            row["timing_ms"]={"retrieval_including_local_query_embedding":retrieval_ms,"mock_generation":generation_ms}
            e2e.append(row)
        store.client.close()

    all_rows=[*controlled,*e2e]
    report={"benchmark":"RAARA Phase 7C Answer Quality and Citation Evaluation","created_at_utc":datetime.now(timezone.utc).isoformat(),"dataset_version":dataset.dataset_version,"dataset_sha256":_sha(dataset_path),"manifest_sha256":_sha(manifest_path),"question_count":len(dataset.questions),"experiments":{"CONTROLLED_EVIDENCE":{"purpose":"Generator/evaluator check with gold-aligned evidence; retrieval intentionally bypassed.","metrics":grouped_aggregates(controlled),"questions":controlled},"END_TO_END_RAG":{"purpose":"Production Retriever over the isolated Phase 7B synthetic corpus followed by the same injected mock generator.","metrics":grouped_aggregates(e2e),"questions":e2e}},"configuration":{"embedding_model_used":embed.model_name,"production_embedding_model_configured":settings.openai_embedding_model,"generator_model":"deterministic-extractive-mock-v1","generation":"offline deterministic extractive adapter; not OpenAI or production generation","prompt_configuration_reference":"No prompt executed; generation adapter's default Prompt C interface marker only. Production prompt text was not modified.","retrieval_top_k":settings.retrieval_top_k,"retrieval_threshold":settings.retrieval_min_relevance,"chunk_size_tokens":settings.chunk_size_tokens,"chunk_overlap_tokens":settings.chunk_overlap_tokens,"distance_metric":"cosine","citation_verifier":"app.services.citation_verifier.CitationVerifier","evaluator_version":"answer-quality-heuristics-v1","semantic_judge":"not run","storage":"temporary isolated Chroma; no production SQLite/Chroma writes","live_openai_calls":False},"interpretation":"Deterministic lexical heuristics and a local mock/extractive generator are instrumentation checks, not semantic ground truth. Controlled and end-to-end metrics are separate and must not be collapsed into a single score.","limitations":["All 12 items and both PDFs are synthetic development fixtures, not official policy.","The offline embedding substitute is not text-embedding-3-small; real production embedding performance is unverified.","The mock generator is not the configured OpenAI generator; production generation quality is untested.","Claim support and correctness use explicit lexical heuristics and are not semantic entailment judgments.","No human evaluator or LLM-as-judge was used; semantic correctness and faithfulness remain unverified.","The dataset is small and has no populated held-out split."]}
    out=Path(output_json); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    md=["# RAARA Phase 7C Answer Quality and Citation Evaluation","",f"- Dataset: `{dataset.dataset_version}` ({len(dataset.questions)} synthetic development questions)",f"- Embedding used: `{embed.model_name}` (offline substitute)",f"- Generation used: `{generator.model}` (deterministic mock/extractive adapter)","- No live OpenAI calls; production SQLite/Chroma untouched.","", "Controlled evidence and end-to-end RAG are separate experiments. Metrics below are not combined."]
    for name,rows in (("CONTROLLED_EVIDENCE",controlled),("END_TO_END_RAG",e2e)):
        metrics=grouped_aggregates(rows)
        md += ["",f"## {name}","", "| Metric | Answerable | Unanswerable | Denominator note |", "|---|---:|---:|---|"]
        for metric in ("normalized_exact_match","key_fact_coverage","claim_support_rate","claim_contradiction_rate","claim_not_enough_evidence_rate","reference_correct_claim_rate","reference_claim_contradiction_rate","reference_claim_not_evaluated_rate","answer_relevance","off_topic_rate","citation_precision","citation_claim_support_precision","citation_recall","document_accuracy","page_accuracy","structural_validity_rate","correct_abstention_rate","false_answer_rate","fabricated_citation_rate","unsupported_claim_rate"):
            aa=metrics["answerable"][metric]["value"]; uu=metrics["unanswerable"][metric]["value"]
            fmt=lambda x:"N/A" if x is None else f"{x:.3f}"
            md.append(f"| {metric} | {fmt(aa)} | {fmt(uu)} | counts in JSON |")
        md += ["", "Per-category and per-question details are recorded in JSON. These deterministic heuristics do not establish semantic faithfulness."]
    md += ["", "## Limitations", *["- "+item for item in report["limitations"]],""]
    Path(output_markdown).parent.mkdir(parents=True,exist_ok=True); Path(output_markdown).write_text("\n".join(md),encoding="utf-8")
    return report
