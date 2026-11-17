from __future__ import annotations
import math
from typing import Any
from evaluation.metrics.retrieval import precision_at_k, recall_at_k, reciprocal_rank

def percentile95(values: list[float]) -> float|None:
    if len(values)<20: return None
    vals=sorted(values); return vals[max(0,math.ceil(.95*len(vals))-1)]

def score_query(ids: list[str], docs: list[str], pages: list[tuple[str,int]], gold: Any, k: int) -> dict[str,Any]:
    top_ids=ids[:k]; top_docs=set(docs[:k]); top_pages=set(pages[:k])
    if gold.answerable:
        hit=bool(set(top_ids)&gold.relevant_passage_ids)
        doc_hit=bool(top_docs&gold.relevant_document_ids)
        page_hit=bool(top_pages&gold.relevant_pages)
        return {"precision_at_k":precision_at_k(top_ids,gold.relevant_passage_ids,k),"recall_at_k":recall_at_k(top_ids,gold.relevant_passage_ids,k),"reciprocal_rank":reciprocal_rank(ids,gold.relevant_passage_ids),"hit_rate":float(hit),"document_hit_rate":float(doc_hit),"page_hit_rate":float(page_hit),"unanswerable_detection":None,"average_retrieved_passages":float(len(ids)),"empty_retrieval_rate":float(not ids)}
    return {"precision_at_k":None,"recall_at_k":None,"reciprocal_rank":None,"hit_rate":None,"document_hit_rate":None,"page_hit_rate":None,"unanswerable_detection":float(not ids),"average_retrieved_passages":float(len(ids)),"empty_retrieval_rate":float(not ids)}

def aggregate(rows: list[dict[str,Any]]) -> dict[str,Any]:
    keys=("precision_at_k","recall_at_k","reciprocal_rank","hit_rate","document_hit_rate","page_hit_rate","unanswerable_detection","average_retrieved_passages","empty_retrieval_rate")
    out={}
    for key in keys:
        values=[r[key] for r in rows if r.get(key) is not None]
        out[key]={"value":sum(values)/len(values) if values else None,"count":len(values)}
    return out
