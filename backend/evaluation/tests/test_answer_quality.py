from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.services.generator import AnswerStatus, EvidenceItem, SourceItem, StructuredAnswer
from app.services.retriever import RetrievalResult, RetrievedPassage
from evaluation.answer_quality.evaluator import evaluate_response, grouped_aggregates
from evaluation.retrieval.ground_truth import QuestionGroundTruth
from evaluation.schemas.dataset import load_dataset

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=load_dataset(ROOT/"datasets/development/raara_synthetic_starter_v0.1.0.jsonl")
Q=QUESTIONS[1]
PID="doc-SYNTH-ACADEMIC-GUIDE-V2-chunk-1"
TEXT="The synthetic workshop minimum attendance requirement is 85 percent."
META={"document_id":"SYNTH-ACADEMIC-GUIDE-V2","document_name":"Synthetic Academic Guide v2","document_type":"synthetic_test_document","page_number":1,"section":"Revised Attendance and Deposits","academic_year":"","version":"2","effective_date":"2026-02-01","source_type":"synthetic_controlled","verification_status":"unverified"}
PASSAGE=RetrievedPassage(PID,TEXT,META,0.1,0.9)
RETRIEVAL=RetrievalResult(Q.question,(PASSAGE,),5,0.35)
GOLD=QuestionGroundTruth(Q.question_id,frozenset({PID}),frozenset({META["document_id"]}),frozenset({(META["document_id"],1)}),{"v2attendance":(PID,)},True)

def make_answer(text=TEXT,*,page=1,passage_id=PID,status=AnswerStatus.SUPPORTED,cite=True):
    evidence=[]
    sources=[]
    if cite:
        evidence=[EvidenceItem(text=TEXT,document=META["document_name"],page=page,section=META["section"],passage_id=passage_id,document_id=META["document_id"],version="2",effective_date=META["effective_date"],academic_year="",verification_status="unverified")]
        sources=[SourceItem(document=META["document_name"],document_id=META["document_id"],document_type=META["document_type"],pages=[page],sections=[META["section"]],academic_year="",version="2",effective_date=META["effective_date"],source_type="synthetic_controlled",verification_status="unverified")]
    return StructuredAnswer(answer=text,evidence=evidence,sources=sources,status=status)

def test_answer_normalization_and_exact_match_metrics():
    row=evaluate_response(Q,GOLD,RETRIEVAL,make_answer("THE synthetic workshop minimum attendance requirement is 85 percent!"))
    assert row["normalized_exact_match"]==0.0  # differs from reference answer wording
    assert row["key_fact_coverage"]["value"]==1.0

def test_correct_answer_with_correct_citation():
    row=evaluate_response(Q,GOLD,RETRIEVAL,make_answer())
    assert row["citations"]["structural_validity_rate"]==1.0
    assert row["citations"]["citation_precision"]==1.0
    assert row["citations"]["citation_recall"]==1.0
    assert row["citations"]["document_accuracy"]==1.0 and row["citations"]["page_accuracy"]==1.0

def test_correct_answer_with_wrong_page_is_not_structurally_valid():
    row=evaluate_response(Q,GOLD,RETRIEVAL,make_answer(page=2))
    assert row["citations"]["structural_validity_rate"]==0.0
    assert row["citations"]["citation_precision"]==0.0
    assert row["citations"]["document_accuracy"]==1.0
    assert row["citations"]["page_accuracy"]==0.0
    assert "PAGE_NUMBER_MISMATCH" in row["citations"]["verification_issues"]

def test_correct_answer_without_citation_has_no_structural_score():
    row=evaluate_response(Q,GOLD,RETRIEVAL,make_answer(cite=False))
    assert row["citations"]["structural_validity_rate"] is None
    assert row["citations"]["citation_precision"]==0.0
    assert row["citations"]["citation_recall"]==0.0

def test_incorrect_numeric_claim_is_contradicted_by_context_and_reference():
    row=evaluate_response(Q,GOLD,RETRIEVAL,make_answer("The synthetic workshop minimum attendance requirement is 100 percent."))
    claim=row["claims"]["items"][0]
    assert claim["support_classification"]=="CONTRADICTED"
    assert claim["reference_corpus_classification"]=="CONTRADICTED"

def test_unsupported_claim_and_empty_retrieval_are_not_faithful():
    empty=RetrievalResult(Q.question,(),5,0.35)
    answer=make_answer("The synthetic dormitory has a midnight curfew.")
    row=evaluate_response(Q,GOLD,empty,answer)
    assert row["claims"]["items"][0]["support_classification"]=="NOT_ENOUGH_EVIDENCE"

def test_structurally_valid_citation_does_not_prove_claim_support():
    row=evaluate_response(Q,GOLD,RETRIEVAL,make_answer("The synthetic hostel has a midnight curfew."))
    assert row["citations"]["structural_validity_rate"]==1.0
    assert row["citations"]["citation_claim_support_precision"]==0.0
    assert row["claims"]["items"][0]["support_classification"]=="NOT_ENOUGH_EVIDENCE"

def test_unanswerable_correct_abstention_and_fabricated_answer_citation():
    uq=QUESTIONS[6]
    ug=QuestionGroundTruth(uq.question_id,frozenset(),frozenset(),frozenset(),{},False)
    empty=RetrievalResult(uq.question,(),5,0.35)
    abstain=StructuredAnswer(answer="No relevant evidence was found.",evidence=[],sources=[],status=AnswerStatus.NOT_FOUND)
    correct=evaluate_response(uq,ug,empty,abstain)
    assert correct["abstention"]["correct_abstention"] and not correct["abstention"]["false_answer"]
    fabricated=evaluate_response(uq,ug,empty,make_answer("The curfew is 10 PM."))
    assert fabricated["abstention"]["false_answer"] and fabricated["abstention"]["fabricated_citation"]
    assert fabricated["citations"]["citation_recall"] is None

def test_fabricated_passage_citation_is_rejected_without_replacement():
    answer=make_answer(passage_id="invented-passage")
    row=evaluate_response(Q,GOLD,RETRIEVAL,answer)
    assert row["citations"]["valid_passage_ids"]==[]
    assert row["citations"]["invalid_citation_count"]==1
    assert row["citations"]["citation_precision"]==0.0
    assert "INVALID_PASSAGE_REFERENCE" in row["citations"]["verification_issues"]

def test_undefined_semantic_and_empty_gold_metrics_stay_unavailable():
    uq=QUESTIONS[6]; ug=QuestionGroundTruth(uq.question_id,frozenset(),frozenset(),frozenset(),{},False)
    empty=RetrievalResult(uq.question,(),5,0.35)
    row=evaluate_response(uq,ug,empty,StructuredAnswer(answer="No evidence.",evidence=[],sources=[],status=AnswerStatus.NOT_FOUND))
    assert row["citations"]["citation_recall"] is None
    assert row["semantic_assessment"]["semantic_faithfulness"] is None

def test_partially_complete_multi_part_answer_has_partial_fact_coverage():
    q=QUESTIONS[3]
    p1=RetrievedPassage("p-deadline","The synthetic assessment registration deadline is 15 March 2026.",{**META,"document_id":"SYNTH-ACADEMIC-GUIDE-V1","document_name":"Synthetic Academic Guide v1","version":"1","section":"Assessment and Attendance"},0.1,0.9)
    p2=RetrievedPassage("p-portal","Students submit the synthetic assessment application through the sample student portal.",{**p1.metadata,"page_number":2,"section":"Applications and Submissions"},0.1,0.9)
    ret=RetrievalResult(q.question,(p1,p2),5,0.35)
    gold=QuestionGroundTruth(q.question_id,frozenset({"p-deadline","p-portal"}),frozenset({"SYNTH-ACADEMIC-GUIDE-V1"}),frozenset({("SYNTH-ACADEMIC-GUIDE-V1",1),("SYNTH-ACADEMIC-GUIDE-V1",2)}),{},True)
    answer=StructuredAnswer(answer="The deadline is 15 March 2026.",evidence=[],sources=[],status=AnswerStatus.SUPPORTED)
    row=evaluate_response(q,gold,ret,answer)
    assert row["key_fact_coverage"]["covered"]==1
    assert row["key_fact_coverage"]["total"]==2
    assert row["key_fact_coverage"]["value"]==0.5

def test_controlled_and_end_to_end_experiment_groups_remain_separate():
    assert grouped_aggregates([evaluate_response(Q,GOLD,RETRIEVAL,make_answer())])["answerable"]["key_fact_coverage"]["value"]==1.0
    controlled={"experiment":"CONTROLLED_EVIDENCE"}; end_to_end={"experiment":"END_TO_END_RAG"}
    assert controlled["experiment"]!=end_to_end["experiment"]

def test_benchmark_runner_keeps_experiment_results_separate(tmp_path):
    from evaluation.answer_quality.runner import run_answer_quality
    dataset=ROOT/"datasets/development/raara_synthetic_starter_v0.1.0.jsonl"
    manifest=ROOT/"datasets/development/manifest.json"
    output=run_answer_quality(dataset,manifest,tmp_path/"answers.json",tmp_path/"answers.md")
    assert set(output["experiments"])=={"CONTROLLED_EVIDENCE","END_TO_END_RAG"}
    controlled=output["experiments"]["CONTROLLED_EVIDENCE"]["questions"]
    e2e=output["experiments"]["END_TO_END_RAG"]["questions"]
    assert len(controlled)==len(e2e)==12
    assert all(row["experiment"]=="CONTROLLED_EVIDENCE" for row in controlled)
    assert all(row["experiment"]=="END_TO_END_RAG" for row in e2e)
    assert output["configuration"]["live_openai_calls"] is False

