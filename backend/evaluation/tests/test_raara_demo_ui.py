from __future__ import annotations

import json
from io import BytesIO

import pytest

from evaluation.generic_policy_demo.pipeline import GenericPolicyDemo
from evaluation.generic_policy_demo.retriever import DEFAULT_DATASET_PATH
from evaluation.project_authored_policies import load_project_policy_dataset
from evaluation.raara_demo_ui.runner import grouped_questions, run_dataset_evaluation, run_five_case_demo
from evaluation.raara_demo_ui.server import DemoApplication, calculate_demo, make_handler


@pytest.fixture(scope="module")
def demo() -> GenericPolicyDemo:
    return GenericPolicyDemo(dataset_path=DEFAULT_DATASET_PATH)


def dispatch(app: DemoApplication, method: str, path: str, payload: dict | None = None):
    handler_type = make_handler(app)
    handler = object.__new__(handler_type)
    handler.path = path
    handler.command = method
    captured = {}
    handler.send_response = lambda status: captured.update(status=status)
    handler.send_header = lambda name, value: captured.setdefault("headers", {}).update({name: value})
    handler.end_headers = lambda: None
    handler.wfile = BytesIO()
    if method == "POST":
        body = json.dumps(payload or {}).encode("utf-8")
        handler.rfile = BytesIO(body)
        handler.headers = {"Content-Length": str(len(body))}
    if method == "GET":
        handler.do_GET()
    else:
        handler.do_POST()
    captured["body"] = handler.wfile.getvalue()
    if captured.get("headers", {}).get("Content-Type", "").startswith("application/json"):
        captured["payload"] = json.loads(captured["body"])
    return captured


def test_runner_uses_original_30_questions_in_dataset_order_and_is_reproducible(demo: GenericPolicyDemo):
    first = run_dataset_evaluation(demo)
    second = run_dataset_evaluation(demo)
    assert first == second
    assert first["policy_count"] == 28
    assert first["question_count"] == 30
    expected = load_project_policy_dataset(DEFAULT_DATASET_PATH)
    assert [row["question_id"] for row in first["results"]] == [row.question_id for row in expected.questions]
    assert [row["question"] for row in first["results"]] == [row.question for row in expected.questions]
    assert first["summary"]["numerical_calculation_questions"] == 6


def test_evaluation_records_actual_status_evidence_citations_and_abstentions(demo: GenericPolicyDemo):
    report = run_dataset_evaluation(demo)
    assert all(set(row["cited_evidence_ids"]).issubset(row["retrieved_evidence_ids"]) for row in report["results"])
    assert all(row["citation_validity"] for row in report["results"])
    assert all(row["passed"] == (row["actual_status"] == row["expected_answerability"] and row["expected_evidence_retrieved"] is not False) for row in report["results"])
    assert report["summary"]["abstentions_expected"] > 0
    # The runner reports the existing pipeline's misses instead of rewriting expectations.
    assert report["summary"]["failed_questions"] > 0


def test_five_case_walkthrough_preserves_expected_and_actual_outcomes(demo: GenericPolicyDemo):
    cases = run_five_case_demo(demo)
    assert len(cases) == 5
    assert [case["case_id"] for case in cases] == ["1", "2", "3", "4", "5"]
    assert cases[0]["actual_status"] == "SUPPORTED"
    assert "GAP-E-ATT-001" in [citation["evidence_id"] for citation in cases[0]["citations"]]
    assert cases[1]["actual_status"] == "SUPPORTED"
    assert cases[2]["actual_status"] == "SUPPORTED"
    assert len(cases[2]["citations"]) >= 2
    assert cases[3]["actual_status"] == "NOT_FOUND" and not cases[3]["citations"]
    assert cases[4]["actual_status"] == "NOT_FOUND"
    assert all(case["citations_validated"] for case in cases)


def test_examples_are_exact_dataset_question_text_grouped_without_invention(demo: GenericPolicyDemo):
    grouped = grouped_questions(demo)
    flattened = [item for questions in grouped.values() for item in questions]
    dataset = load_project_policy_dataset(DEFAULT_DATASET_PATH)
    assert len(flattened) == 30
    assert {item["question_id"] for item in flattened} == {item.question_id for item in dataset.questions}
    assert {item["question"] for item in flattened} == {item.question for item in dataset.questions}
    assert grouped["Official-policy questions"]
    assert grouped["Unanswerable questions"]


@pytest.mark.parametrize(
    ("payload", "result", "formula_piece", "evidence_id"),
    [
        ({"calculation": "attendance", "attended": 72, "held": 90}, "80.00%", "(72 / 90) x 100", "GAP-E-ATT-002"),
        ({"calculation": "course_total", "internal_score": 34, "exam_score": 52}, "44.80/100", "0.4", "GAP-E-ASSESS-001"),
        ({"calculation": "sgpa", "courses": [{"credits": 4, "grade_point": 9}, {"credits": 3, "grade_point": 8}, {"credits": 3, "grade_point": 7}]}, "8.10", "credits", "GAP-E-SGPA-001"),
        ({"calculation": "cgpa", "courses": [{"credits": 10, "grade_point": 8.1}, {"credits": 20, "grade_point": 7.5}]}, "7.70", "credits", "GAP-E-CGPA-001"),
    ],
)
def test_calculators_use_pipeline_functions_and_dataset_evidence(demo, payload, result, formula_piece, evidence_id):
    output = calculate_demo(payload, demo)
    assert output["result"] == result
    assert formula_piece in output["formula"] or formula_piece in output["steps"]
    assert output["evidence"]["evidence_id"] == evidence_id
    assert output["evidence"]["authority_status"] == "NOT_OFFICIAL"
    assert "Illustrative" in output["label"]


@pytest.mark.parametrize(
    "payload",
    [
        {"calculation": "attendance", "attended": "72", "held": 90},
        {"calculation": "attendance", "attended": 91, "held": 90},
        {"calculation": "course_total", "internal_score": 101, "exam_score": 40},
        {"calculation": "sgpa", "courses": [{"credits": 0, "grade_point": 9}]},
        {"calculation": "cgpa", "courses": [{"credits": 2, "grade_point": 11}]},
        {"calculation": "unknown"},
    ],
)
def test_invalid_calculation_inputs_are_rejected(demo, payload):
    with pytest.raises(ValueError):
        calculate_demo(payload, demo)


def test_web_smoke_serves_ui_dashboard_examples_and_question_answers(demo):
    app = DemoApplication(demo)
    health = dispatch(app, "GET", "/api/health")
    assert health["status"] == 200 and health["payload"]["mode"] == "offline_project_demo"
    page = dispatch(app, "GET", "/")
    html = page["body"].decode()
    assert page["status"] == 200 and "Academic Policy Assistant" in html
    assert "not an official PES University policy service" in html
    assert "Content-Security-Policy" in page["headers"]
    dashboard_response = dispatch(app, "GET", "/api/dashboard")
    dashboard = dashboard_response["payload"]
    assert dashboard_response["status"] == 200
    assert dashboard["policy_count"] == 28 and dashboard["question_count"] == 30
    assert dashboard["test_suite_result"]["passed"] == dashboard["test_suite_result"]["collected"] == 265
    assert dashboard["test_suite_result"]["failed"] == 0
    assert dashboard["test_suite_result"]["storage_isolated"] is True
    assert dashboard["test_suite_display"] == "Recorded full backend suite: 265 passed, 0 failed (2026-11-14)"
    groups = dispatch(app, "GET", "/api/examples")["payload"]
    assert sum(len(rows) for rows in groups.values()) == 30
    answer_response = dispatch(app, "POST", "/api/ask", {"question": "What is the illustrative minimum attendance?"})
    status, answer = answer_response["status"], answer_response["payload"]
    assert status == 200 and answer["answer"]["status"] == "SUPPORTED"
    assert answer["answer"]["citations"][0]["evidence_id"] == "GAP-E-ATT-001"
    assert answer["citations_validated"] is True


def test_web_smoke_official_question_abstains_without_generic_citation(demo):
    app = DemoApplication(demo)
    response = dispatch(app, "POST", "/api/ask", {"question": "What is the official PES University attendance requirement?"})
    status, answer = response["status"], response["payload"]
    assert status == 200
    assert answer["answer"]["status"] == "NOT_FOUND"
    assert answer["answer"]["citations"] == []
    assert "cannot establish an official" in answer["answer"]["answer"]


def test_web_request_validation_and_calculation_endpoints(demo):
    app = DemoApplication(demo)
    invalid = dispatch(app, "POST", "/api/ask", {"question": "   "})
    assert invalid["status"] == 400
    calculation_response = dispatch(app, "POST", "/api/calculate", {"calculation": "attendance", "attended": 72, "held": 90})
    status, calculation = calculation_response["status"], calculation_response["payload"]
    assert status == 200 and calculation["result"] == "80.00%"
    assert calculation["evidence"]["evidence_id"] == "GAP-E-ATT-002"
    tour_response = dispatch(app, "GET", "/api/demo-sequence")
    status, tour = tour_response["status"], tour_response["payload"]
    assert status == 200 and len(tour) == 5


def test_ui_does_not_import_production_config_or_change_official_registry():
    import subprocess
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[2]
    code = "import sys; from evaluation.raara_demo_ui.server import DemoApplication; DemoApplication(); print('app.config' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], cwd=backend, text=True, capture_output=True, check=True)
    assert result.stdout.strip() == "False"
    registry = json.loads((backend / "evaluation/datasets/held_out/documents.json").read_text(encoding="utf-8"))
    assert registry["documents"] == []
