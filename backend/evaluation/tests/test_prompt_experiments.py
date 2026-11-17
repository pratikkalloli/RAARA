from __future__ import annotations
from pathlib import Path
import pytest
from app.prompting.system_prompt import PromptType, get_prompt_configuration
from app.services.retriever import RetrievalResult, RetrievedPassage
from evaluation.prompt_experiments.runner import PromptDiagnosticGenerator, run_prompt_comparison

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"datasets/development/raara_synthetic_starter_v0.1.0.jsonl"
MANIFEST=ROOT/"datasets/development/manifest.json"

def test_all_prompts_receive_identical_retrieval_and_payload():
    metadata={"document_id":"d1","document_name":"Synthetic source","document_type":"synthetic","page_number":1,"section":"Section 1","academic_year":"","version":"1","effective_date":"2025-01-01","source_type":"synthetic_controlled","verification_status":"unverified"}
    passage=RetrievedPassage("p1","A synthetic policy passage.",metadata,0.1,0.9)
    retrieval=RetrievalResult("What does the synthetic policy say?",(passage,),5,0.35)
    generator=PromptDiagnosticGenerator()
    outputs=[generator.generate_with_usage(retrieval,prompt_type=ptype) for ptype in PromptType]
    assert [row.prompt_type.value for row in outputs]==["A","B","C"]
    assert all(row.answer.model_dump()==outputs[0].answer.model_dump() for row in outputs)
    calls=generator.calls
    assert len({c["retrieval_fingerprint"] for c in calls})==1
    assert len({c["user_payload_sha256"] for c in calls})==1
    assert len({c["output_schema_sha256"] for c in calls})==1
    assert len({c["system_prompt_sha256"] for c in calls})==3
    assert len({c["combined_prompt_sha256"] for c in calls})==3

def test_prompt_hashes_are_content_addressed_and_stable():
    first={p.value:get_prompt_configuration(p).system_instructions for p in PromptType}
    second={p.value:get_prompt_configuration(p).system_instructions for p in PromptType}
    assert first==second
    assert len(set(first.values()))==3
    assert all(len(value)>100 for value in first.values())
    metadata={"document_id":"d1","document_name":"Synthetic source","document_type":"synthetic","page_number":1,"section":"Section 1","academic_year":"","version":"1","effective_date":"2025-01-01","source_type":"synthetic_controlled","verification_status":"unverified"}
    retrieval=RetrievalResult("Question?",(RetrievedPassage("p1","Answer evidence sentence.",metadata,0.1,0.9),),5,0.35)
    generator=PromptDiagnosticGenerator()
    one=generator.generate_with_usage(retrieval,prompt_type="B")
    two=generator.generate_with_usage(retrieval,prompt_type="B")
    assert one.answer.model_dump()==two.answer.model_dump()
    assert generator.calls[0]["combined_prompt_sha256"]==generator.calls[1]["combined_prompt_sha256"]

def test_mock_usage_and_cost_are_unavailable_not_zero():
    metadata={"document_id":"d1","document_name":"Synthetic source","document_type":"synthetic","page_number":1,"section":"Section 1","academic_year":"","version":"1","effective_date":"2025-01-01","source_type":"synthetic_controlled","verification_status":"unverified"}
    retrieval=RetrievalResult("Question?",(RetrievedPassage("p1","Answer evidence sentence.",metadata,0.1,0.9),),5,0.35)
    result=PromptDiagnosticGenerator().generate_with_usage(retrieval,prompt_type="B")
    assert result.input_tokens is None and result.output_tokens is None
    from evaluation.prompt_experiments.runner import _usage_summary
    usage=_usage_summary([{"input_tokens":None,"output_tokens":None,"generation_latency_ms":0.1}])
    assert usage["total_tokens"] is None
    assert usage["estimated_api_cost_usd"] is None

def test_runner_separates_experiments_and_reuses_one_retrieval(tmp_path):
    result=run_prompt_comparison(DATA,MANIFEST,tmp_path/"prompt.json",tmp_path/"prompt.md")
    assert result["consistency"]["CONTROLLED_EVIDENCE"]["retrieval_operations"]==0
    assert result["consistency"]["END_TO_END_RAG"]["retrieval_operations"]==12
    for experiment in ("CONTROLLED_EVIDENCE","END_TO_END_RAG"):
        consistency=result["consistency"][experiment]
        assert consistency["prompt_generations"]==36
        assert consistency["same_evidence_passed_to_all_prompts"]
        assert consistency["same_passage_ids_passed_to_all_prompts"]
        assert all(x["outputs_identical_under_mock"] for x in consistency["per_question"].values())
        by_prompt=result["experiments"][experiment]["prompt_types"]
        assert by_prompt["A"]["metrics"]==by_prompt["B"]["metrics"]==by_prompt["C"]["metrics"]
        assert all(by_prompt[p]["usage"]["input_tokens"] is None for p in ("A","B","C"))
        assert all(by_prompt[p]["usage"]["estimated_api_cost_usd"] is None for p in ("A","B","C"))
    assert result["experiments"]["CONTROLLED_EVIDENCE"]["prompt_types"]["A"]["metrics"]["answerable"]["key_fact_coverage"]["value"]==pytest.approx(0.6166666666666667)
    assert result["experiments"]["END_TO_END_RAG"]["prompt_types"]["A"]["metrics"]["answerable"]["key_fact_coverage"]["value"]==pytest.approx(0.1)
    # The two NOT_FOUND fixtures remain abstentions in all three prompt runs.
    for prompt in ("A","B","C"):
        rows=result["experiments"]["CONTROLLED_EVIDENCE"]["prompt_types"][prompt]["questions"]
        unanswerable=[r for r in rows if not r["answerable"]]
        assert len(unanswerable)==2
        assert all(r["abstention"]["correct_abstention"] for r in unanswerable)
