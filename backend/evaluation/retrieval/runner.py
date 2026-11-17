from __future__ import annotations
import hashlib, json, statistics, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.config import settings
from app.services.retriever import Retriever
from app.services.vector_store import ChromaVectorStore
from evaluation.retrieval.ground_truth import build_ground_truth
from evaluation.retrieval.indexing import DeterministicTfidfHashEmbedding, EvaluationIndexer
from evaluation.retrieval.metrics import aggregate, percentile95, score_query
from evaluation.schemas.dataset import validate_dataset

class TimedEmbedder:
    def __init__(self, wrapped): self.wrapped=wrapped; self.latencies=[]
    def embed_texts(self,texts):
        start=time.perf_counter_ns(); result=self.wrapped.embed_texts(texts); self.latencies.append((time.perf_counter_ns()-start)/1e6); return result

class TimedVectorStore:
    def __init__(self, wrapped): self.wrapped=wrapped; self.latencies=[]
    def count(self): return self.wrapped.count()
    def query(self, query_embedding, *, top_k=5, where=None):
        start=time.perf_counter_ns(); result=self.wrapped.query(query_embedding,top_k=top_k,where=where); self.latencies.append((time.perf_counter_ns()-start)/1e6); return result

def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def run_benchmark(dataset_path: str|Path, manifest_path: str|Path, output_json: str|Path, output_markdown: str|Path, *, repetitions: int=3, collection_name: str="raara_eval_7b") -> dict[str,Any]:
    if repetitions<1: raise ValueError("repetitions must be positive")
    dataset_path,manifest_path=Path(dataset_path),Path(manifest_path)
    validated=validate_dataset(dataset_path,manifest_path); manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    embed=DeterministicTfidfHashEmbedding(); store=ChromaVectorStore(settings.chroma_persist_dir,collection_name=collection_name)
    indexed=EvaluationIndexer(store,embed).index(manifest_path,manifest)
    gold=build_ground_truth(validated.questions,indexed.chunks_by_document)
    timed=TimedEmbedder(embed); timed_store=TimedVectorStore(store)
    retriever=Retriever(timed,timed_store,top_k=5,relevance_threshold=settings.retrieval_min_relevance)
    # Warm-up is kept outside measured repetitions.
    if validated.questions: retriever.retrieve(validated.questions[0].question,top_k=5)
    rows_by_k={k:[] for k in (1,3,5)}; latencies_by_k={k:[] for k in (1,3,5)}; query_records=[]
    categories=defaultdict(lambda:defaultdict(list))
    for q in validated.questions:
        k_records={}
        for k in rows_by_k:
            q_runs=[]
            for _ in range(repetitions):
                emb_before=len(timed.latencies); vec_before=len(timed_store.latencies); start=time.perf_counter_ns()
                result=retriever.retrieve(q.question,top_k=k)
                elapsed=(time.perf_counter_ns()-start)/1e6
                embedding_ms=timed.latencies[emb_before] if len(timed.latencies)>emb_before else 0.0
                vector_ms=timed_store.latencies[vec_before] if len(timed_store.latencies)>vec_before else 0.0
                q_runs.append((result,elapsed,embedding_ms,vector_ms))
            ranking=lambda r:[p.id for p in r.passages]
            if any(ranking(run[0])!=ranking(q_runs[0][0]) for run in q_runs[1:]): raise RuntimeError("Deterministic retrieval ranking changed between repetitions")
            passages=q_runs[0][0].passages; passage_ids=[p.id for p in passages]
            doc_ids=[str(p.metadata["document_id"]) for p in passages]
            pages=[(str(p.metadata["document_id"]),int(p.metadata["page_number"])) for p in passages]
            row=score_query(passage_ids,doc_ids,pages,gold[q.question_id],k)
            rows_by_k[k].append(row); categories[q.category][k].append(row); latencies_by_k[k].extend(run[1] for run in q_runs)
            k_records[str(k)]={"retrieved":[{"passage_id":p.id,"document_id":p.metadata.get("document_id"),"document":p.metadata.get("document_name"),"page":p.metadata.get("page_number"),"section":p.metadata.get("section"),"cosine_distance":p.cosine_distance,"relevance_score":p.relevance_score,"verification_status":p.metadata.get("verification_status"),"is_relevant":p.id in gold[q.question_id].relevant_passage_ids} for p in passages],"metrics":row,"retrieval_latency_ms":{"mean":statistics.mean(r[1] for r in q_runs),"median":statistics.median(r[1] for r in q_runs),"p95":percentile95([r[1] for r in q_runs])},"query_embedding_latency_ms":{"mean":statistics.mean(r[2] for r in q_runs),"median":statistics.median(r[2] for r in q_runs)},"vector_query_latency_ms":{"mean":statistics.mean(r[3] for r in q_runs),"median":statistics.median(r[3] for r in q_runs)},"empty_retrieval":not passages,"retrieved_count":len(passages)}
        query_records.append({"question_id":q.question_id,"category":q.category,"expected_status":q.expected_status,"relevant_passage_ids":sorted(gold[q.question_id].relevant_passage_ids),"relevant_document_ids":sorted(gold[q.question_id].relevant_document_ids),"relevant_pages":[{"document_id":d,"page":p} for d,p in sorted(gold[q.question_id].relevant_pages)],"by_k":k_records,"repetitions":repetitions})
    metrics={str(k):aggregate(rows) for k,rows in rows_by_k.items()}
    category_metrics={cat:{str(k):aggregate(vals) for k,vals in by_k.items()} for cat,by_k in categories.items()}
    latency_stats={str(k):{"sample_count":len(vals),"mean":statistics.mean(vals) if vals else None,"median":statistics.median(vals) if vals else None,"p95":percentile95(vals)} for k,vals in latencies_by_k.items()}
    report={"benchmark":"RAARA Phase 7B retrieval benchmark","created_at_utc":datetime.now(timezone.utc).isoformat(),"dataset_version":validated.dataset_version,"dataset_sha256":_sha(dataset_path),"manifest_sha256":_sha(manifest_path),"question_count":len(validated.questions),"repetitions":repetitions,"index":{"added_chunks":indexed.added_chunks,"reused_chunks":indexed.reused_chunks,"chunk_count":sum(map(len,indexed.chunks_by_document.values()))},"configuration":{"distance_metric":"cosine","cosine_similarity":"1 - cosine_distance","relevance_threshold":retriever.relevance_threshold,"top_k_values":[1,3,5],"chunk_size_tokens":settings.chunk_size_tokens,"chunk_overlap_tokens":settings.chunk_overlap_tokens,"production_embedding_model_configured":settings.openai_embedding_model,"embedding_model_used":embed.model_name,"generation":"not run","storage":"isolated evaluation collection","verification_status":"unverified synthetic test documents"},"latency_scope":"Retrieval duration includes query embedding and Chroma vector query; separate timings are recorded for both. Excludes PDF extraction, chunking, indexing, and answer generation.","latency_ms_by_k":latency_stats,"metrics":metrics,"by_category":category_metrics,"questions":query_records,"limitations":["Synthetic development corpus only; not real academic policy.","Deterministic lexical hashing substitute was used; scores do not measure OpenAI embedding performance.","Unanswerable detection here means no results passed the production threshold; it does not measure answer abstention.","Scores measure retrieval matching only, not semantic answer correctness or faithfulness."]}
    out=Path(output_json); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    md=["# RAARA Phase 7B Retrieval Benchmark","",f"- Dataset: `{validated.dataset_version}` ({report['question_count']} questions)",f"- Embedding used: `{embed.model_name}` (offline lexical substitute)",f"- Chunks indexed: {report['index']['chunk_count']} ({report['index']['added_chunks']} added, {report['index']['reused_chunks']} reused)",f"- Threshold: {retriever.relevance_threshold}; cosine distance metric","", "| K | Precision | Recall | MRR | Hit rate | Document hit | Page hit |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for k,vals in metrics.items():
        get=lambda key: vals[key]["value"]
        fmt=lambda v: "N/A" if v is None else f"{v:.3f}"
        md.append(f"| {k} | {fmt(get('precision_at_k'))} | {fmt(get('recall_at_k'))} | {fmt(get('reciprocal_rank'))} | {fmt(get('hit_rate'))} | {fmt(get('document_hit_rate'))} | {fmt(get('page_hit_rate'))} |")
    md += ["", "## Latency by K", "", "| K | Samples | Mean ms | Median ms | P95 ms |", "|---:|---:|---:|---:|---:|"]
    for k, stat in latency_stats.items():
        md.append(f"| {k} | {stat['sample_count']} | {stat['mean']:.3f} | {stat['median']:.3f} | {stat['p95'] if stat['p95'] is not None else 'N/A (<20 samples)'} |")
    md += ["", "Average retrieved count and empty retrieval rate are also included in JSON per K and category.", "", "## Limitations",*['- '+x for x in report["limitations"]],""]
    Path(output_markdown).parent.mkdir(parents=True,exist_ok=True); Path(output_markdown).write_text("\n".join(md),encoding="utf-8")
    client = getattr(store, "client", None)
    if client is not None and callable(getattr(client, "close", None)):
        client.close()
    return report
