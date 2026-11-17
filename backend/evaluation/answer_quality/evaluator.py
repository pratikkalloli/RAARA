from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from app.services.citation_verifier import CitationVerifier
from app.services.generator import AnswerStatus, StructuredAnswer
from app.services.retriever import RetrievalResult
from evaluation.metrics.answer import normalize_answer, normalized_exact_match
from evaluation.metrics.citations import (
    citation_precision, citation_recall, document_identification_accuracy, page_accuracy,
)
from evaluation.retrieval.ground_truth import QuestionGroundTruth
from evaluation.schemas.dataset import EvaluationQuestion

_STOP = set("a an and are as at be by for from has have how in is it of on or the to was were what when where which who with does do did according this that states state synthetic version".split())
_NUM_WORDS = {"zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10","eighty":"80","ninety":"90"}

def _tokens(value: str) -> list[str]:
    raw = re.findall(r"[a-z]+|\d+(?:\.\d+)?", normalize_answer(value))
    normalized=[]
    for token in raw:
        if token in _NUM_WORDS:
            normalized.append(_NUM_WORDS[token])
        else:
            normalized.append(token)
    # Collapse common number phrases, e.g. eighty five -> 85.
    out=[]; i=0
    while i<len(normalized):
        if normalized[i]=="80" and i+1<len(normalized) and normalized[i+1]=="5": out.append("85"); i+=2
        elif normalized[i]=="90" and i+1<len(normalized) and normalized[i+1]=="5": out.append("95"); i+=2
        else: out.append(normalized[i]); i+=1
    return out

def _content(value: str) -> set[str]:
    value=re.sub(r"\bversion\s+\d+(?:\.\d+)*\b", " ", normalize_answer(value))
    tokens=_tokens(value)
    return {token for token in tokens if token not in _STOP and (len(token)>1 or token.isdigit())}

def _claim_segments(answer: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|;\s+", answer) if part.strip()]

def _fact_covered(fact: str, answer: str) -> bool:
    required=_content(fact); given=_content(answer)
    return bool(required) and required.issubset(given)

def _classify_claim(claim: str, retrieval: RetrievalResult, expected_claims: list[str]) -> dict[str, Any]:
    claim_norm=normalize_answer(claim)
    claim_tokens=_content(claim)
    supporting=[]; contradicted=[]
    for passage in retrieval.passages:
        context=normalize_answer(passage.text); context_tokens=_content(context)
        if claim_norm and claim_norm in context:
            supporting.append(passage.id); continue
        numbers={t for t in _tokens(claim) if t.isdigit()}
        context_numbers={t for t in _tokens(context) if t.isdigit()}
        shared=claim_tokens & context_tokens
        if numbers and context_numbers and numbers.isdisjoint(context_numbers) and len(shared)>=max(2, int(len(claim_tokens)*0.65)):
            contradicted.append(passage.id)
        elif claim_tokens and claim_tokens.issubset(context_tokens):
            supporting.append(passage.id)
    if supporting:
        support="SUPPORTED"; support_ids=supporting; explanation="Claim text is present in, or its content terms are contained by, retrieved evidence."
    elif contradicted:
        support="CONTRADICTED"; support_ids=contradicted; explanation="Retrieved context contains overlapping subject terms with conflicting numeric/date values."
    elif retrieval.passages:
        support="NOT_ENOUGH_EVIDENCE"; support_ids=[]; explanation="No retrieved passage matched the claim under the deterministic lexical rule."
    else:
        support="NOT_ENOUGH_EVIDENCE"; support_ids=[]; explanation="No retrieved context was available to support the claim."

    correct="NOT_EVALUATED"; correct_explanation="Claim correctness is not inferred from lexical similarity alone."
    for expected in expected_claims:
        expected_terms=_content(expected); overlap=claim_tokens & expected_terms
        if _fact_covered(expected, claim):
            correct="SUPPORTED"; correct_explanation="Expected key fact terms and values are all present in the claim."; break
        expected_nums={t for t in _tokens(expected) if t.isdigit()}; claim_nums={t for t in _tokens(claim) if t.isdigit()}
        if expected_nums and claim_nums and expected_nums.isdisjoint(claim_nums) and len(overlap)>=max(2,int(len(expected_terms)*0.55)):
            correct="CONTRADICTED"; correct_explanation="Claim overlaps an expected key fact but gives a different numeric/date value."; break
    return {"claim":claim,"support_classification":support,"supporting_evidence_ids":support_ids,"support_explanation":explanation,"reference_corpus_classification":correct,"reference_explanation":correct_explanation}

def evaluate_response(
    question: EvaluationQuestion,
    gold: QuestionGroundTruth,
    retrieval: RetrievalResult,
    answer: StructuredAnswer,
    *,
    verifier: CitationVerifier | None = None,
) -> dict[str, Any]:
    verification=(verifier or CitationVerifier()).verify(answer,retrieval)
    final=verification.answer
    claim_records=[_classify_claim(claim,retrieval,question.expected_claims) for claim in _claim_segments(answer.answer) if answer.status != AnswerStatus.NOT_FOUND]
    claims_n=len(claim_records)
    support_counts={name:sum(record["support_classification"]==name for record in claim_records) for name in ("SUPPORTED","CONTRADICTED","NOT_ENOUGH_EVIDENCE")}
    reference_counts={name:sum(record["reference_corpus_classification"]==name for record in claim_records) for name in ("SUPPORTED","CONTRADICTED","NOT_EVALUATED")}
    key_matches=[fact for fact in question.expected_claims if _fact_covered(fact,answer.answer)]
    question_terms=_content(question.question)
    answer_terms=_content(answer.answer)
    relevance=(len(question_terms & answer_terms)/len(question_terms)) if question_terms else None

    citations=list(answer.evidence)
    predicted_ids=list(dict.fromkeys(c.passage_id for c in citations if c.passage_id))
    retrieved={p.id:p for p in retrieval.passages}
    structurally_valid=[c for c in citations if c.passage_id in verification.valid_passage_ids and c.passage_id in retrieved]
    structurally_valid_ids=list(dict.fromkeys(c.passage_id for c in structurally_valid))
    relevant_citations=[pid for pid in predicted_ids if pid in gold.relevant_passage_ids]
    # Citation-to-claim lexical support is a separate heuristic from structural validity.
    claim_support_ids={passage_id for claim in claim_records for passage_id in claim["supporting_evidence_ids"]}
    supported_citations=[pid for pid in structurally_valid_ids if pid in claim_support_ids]

    is_unanswerable=not gold.answerable
    has_answer=answer.status != AnswerStatus.NOT_FOUND and bool(answer.answer.strip())
    cited_documents={str(c.document_id) for c in citations if c.passage_id in retrieved and str(c.document_id)==str(retrieved[c.passage_id].metadata.get("document_id",""))}
    cited_pages={(str(c.document_id),int(c.page)) for c in citations if c.passage_id in retrieved and str(c.document_id)==str(retrieved[c.passage_id].metadata.get("document_id",""))}
    return {
        "experiment":None,
        "question_id":question.question_id,
        "category":question.category,
        "expected_status":question.expected_status,
        "answerable":gold.answerable,
        "question":question.question,
        "reference_answer":question.reference_answer,
        "expected_claims":question.expected_claims,
        "generated_answer":answer.answer,
        "verified_answer":final.answer,
        "generated_status":answer.status.value,
        "verified_status":final.status.value,
        "normalized_exact_match":normalized_exact_match(answer.answer,question.reference_answer) if question.reference_answer else None,
        "key_fact_coverage":{"covered":len(key_matches),"total":len(question.expected_claims),"value":len(key_matches)/len(question.expected_claims) if question.expected_claims else None,"matched_facts":key_matches,"correct_claims":key_matches,"missing_facts":[fact for fact in question.expected_claims if fact not in key_matches],"missing_claims":[fact for fact in question.expected_claims if fact not in key_matches],"incorrect_claims":[c["claim"] for c in claim_records if c["reference_corpus_classification"]=="CONTRADICTED"]},
        "claims":{"items":claim_records,"support_rate":support_counts["SUPPORTED"]/claims_n if claims_n else None,"contradiction_rate":support_counts["CONTRADICTED"]/claims_n if claims_n else None,"not_enough_evidence_rate":support_counts["NOT_ENOUGH_EVIDENCE"]/claims_n if claims_n else None,"reference_correct_claims":reference_counts["SUPPORTED"],"reference_contradicted_claims":reference_counts["CONTRADICTED"],"reference_not_evaluated_claims":reference_counts["NOT_EVALUATED"],"reference_correct_rate":reference_counts["SUPPORTED"]/(claims_n-reference_counts["NOT_EVALUATED"]) if claims_n>reference_counts["NOT_EVALUATED"] else None,"reference_contradiction_rate":reference_counts["CONTRADICTED"]/(claims_n-reference_counts["NOT_EVALUATED"]) if claims_n>reference_counts["NOT_EVALUATED"] else None,"reference_not_evaluated_rate":reference_counts["NOT_EVALUATED"]/claims_n if claims_n else None,"denominator":claims_n},
        "answer_relevance":{"question_content_coverage":relevance,"expected_fact_coverage":len(key_matches)/len(question.expected_claims) if question.expected_claims else None,"off_topic_flag":bool(answer.status!=AnswerStatus.NOT_FOUND and relevance is not None and relevance<0.2)},
        "citations":{"predicted_passage_ids":predicted_ids,"valid_passage_ids":structurally_valid_ids,"invalid_citation_count":len(citations)-len(structurally_valid),"structural_validity_rate":len(structurally_valid)/len(citations) if citations else None,"citation_precision":(len(set(structurally_valid_ids)&gold.relevant_passage_ids)/len(set(predicted_ids))) if predicted_ids else 0.0,"citation_claim_support_precision":len(set(supported_citations))/len(set(structurally_valid_ids)) if structurally_valid_ids else None,"citation_recall":citation_recall(structurally_valid_ids,gold.relevant_passage_ids),"document_accuracy":document_identification_accuracy(cited_documents,gold.relevant_document_ids),"page_accuracy":page_accuracy(cited_pages,gold.relevant_pages),"verification_issues":list(verification.issues)},
        "abstention":{"correct_abstention":bool(is_unanswerable and final.status==AnswerStatus.NOT_FOUND),"false_answer":bool(is_unanswerable and has_answer),"fabricated_citation":bool(is_unanswerable and any(c.passage_id not in retrieved for c in citations)),"unsupported_claim_count":support_counts["NOT_ENOUGH_EVIDENCE"]+support_counts["CONTRADICTED"],"unsupported_claim_rate":(support_counts["NOT_ENOUGH_EVIDENCE"]+support_counts["CONTRADICTED"])/claims_n if claims_n else None},
        "retrieval":{"passage_ids":[p.id for p in retrieval.passages],"passages":[{"passage_id":p.id,"document_id":p.metadata.get("document_id"),"document":p.metadata.get("document_name"),"page":p.metadata.get("page_number"),"section":p.metadata.get("section"),"verification_status":p.metadata.get("verification_status"),"relevance_score":p.relevance_score} for p in retrieval.passages]},
        "semantic_assessment":{"assessor":"not_assessed","semantic_correctness":None,"semantic_faithfulness":None,"answer_relevance":None,"note":"Deterministic lexical heuristics are not semantic ground truth; no human or LLM judge was run."},
    }

def _mean(values: list[float]) -> dict[str, Any]:
    return {"value":sum(values)/len(values) if values else None,"count":len(values)}

def aggregate_records(records: list[dict[str,Any]]) -> dict[str,Any]:
    metrics={"normalized_exact_match":[],"key_fact_coverage":[],"claim_support_rate":[],"claim_contradiction_rate":[],"claim_not_enough_evidence_rate":[],"reference_correct_claim_rate":[],"reference_claim_contradiction_rate":[],"reference_claim_not_evaluated_rate":[],"answer_relevance":[],"off_topic_rate":[],"citation_precision":[],"citation_claim_support_precision":[],"citation_recall":[],"document_accuracy":[],"page_accuracy":[],"structural_validity_rate":[],"correct_abstention_rate":[],"false_answer_rate":[],"fabricated_citation_rate":[],"unsupported_claim_rate":[]}
    for row in records:
        m=row["citations"]; c=row["claims"]; a=row["abstention"]
        if row["answerable"]:
            if row["normalized_exact_match"] is not None: metrics["normalized_exact_match"].append(row["normalized_exact_match"])
            if row["key_fact_coverage"]["value"] is not None: metrics["key_fact_coverage"].append(row["key_fact_coverage"]["value"])
            if c["support_rate"] is not None: metrics["claim_support_rate"].append(c["support_rate"])
            if c["contradiction_rate"] is not None: metrics["claim_contradiction_rate"].append(c["contradiction_rate"])
            if c["not_enough_evidence_rate"] is not None: metrics["claim_not_enough_evidence_rate"].append(c["not_enough_evidence_rate"])
            if c["reference_correct_rate"] is not None: metrics["reference_correct_claim_rate"].append(c["reference_correct_rate"])
            if c["reference_contradiction_rate"] is not None: metrics["reference_claim_contradiction_rate"].append(c["reference_contradiction_rate"])
            if c["reference_not_evaluated_rate"] is not None: metrics["reference_claim_not_evaluated_rate"].append(c["reference_not_evaluated_rate"])
            if row["answer_relevance"]["question_content_coverage"] is not None: metrics["answer_relevance"].append(row["answer_relevance"]["question_content_coverage"])
            metrics["off_topic_rate"].append(float(row["answer_relevance"]["off_topic_flag"]))
            metrics["citation_precision"].append(m["citation_precision"])
            if m["citation_claim_support_precision"] is not None: metrics["citation_claim_support_precision"].append(m["citation_claim_support_precision"])
            if m["citation_recall"] is not None: metrics["citation_recall"].append(m["citation_recall"])
            metrics["document_accuracy"].append(m["document_accuracy"]); metrics["page_accuracy"].append(m["page_accuracy"])
            if m["structural_validity_rate"] is not None: metrics["structural_validity_rate"].append(m["structural_validity_rate"])
            if a["unsupported_claim_rate"] is not None: metrics["unsupported_claim_rate"].append(a["unsupported_claim_rate"])
        else:
            if c["reference_correct_rate"] is not None: metrics["reference_correct_claim_rate"].append(c["reference_correct_rate"])
            if c["reference_contradiction_rate"] is not None: metrics["reference_claim_contradiction_rate"].append(c["reference_contradiction_rate"])
            if c["reference_not_evaluated_rate"] is not None: metrics["reference_claim_not_evaluated_rate"].append(c["reference_not_evaluated_rate"])
            metrics["correct_abstention_rate"].append(float(a["correct_abstention"]))
            metrics["false_answer_rate"].append(float(a["false_answer"]))
            metrics["fabricated_citation_rate"].append(float(a["fabricated_citation"]))
            if a["unsupported_claim_rate"] is not None: metrics["unsupported_claim_rate"].append(a["unsupported_claim_rate"])
    return {name:_mean(values) for name,values in metrics.items()}

def grouped_aggregates(records: list[dict[str,Any]]) -> dict[str,Any]:
    groups={"all":records,"answerable":[r for r in records if r["answerable"]],"unanswerable":[r for r in records if not r["answerable"]],"by_category":{}}
    for row in records: groups["by_category"].setdefault(row["category"],[]).append(row)
    return {"all":aggregate_records(groups["all"]),"answerable":aggregate_records(groups["answerable"]),"unanswerable":aggregate_records(groups["unanswerable"]),"by_category":{cat:aggregate_records(rows) for cat,rows in groups["by_category"].items()},"denominators":{"all_questions":len(records),"answerable_questions":sum(r["answerable"] for r in records),"unanswerable_questions":sum(not r["answerable"] for r in records),"metric_counts_are_reported_per_metric":True}}
