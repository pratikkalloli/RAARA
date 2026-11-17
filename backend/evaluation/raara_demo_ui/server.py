"""Dependency-free loopback web server for the isolated Stage 4 pipeline."""
from __future__ import annotations

import json
import logging
import math
import mimetypes
from dataclasses import asdict
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from evaluation.generic_policy_demo.answerer import (
    calculate_attendance,
    calculate_cgpa,
    calculate_course_total,
    calculate_sgpa,
)
from evaluation.generic_policy_demo.pipeline import GenericPolicyDemo
from evaluation.generic_policy_demo.retriever import DEFAULT_DATASET_PATH
from evaluation.raara_demo_ui.runner import calculation_evidence, grouped_questions, run_dataset_evaluation, run_five_case_demo


LOGGER = logging.getLogger("raara_demo_ui")
UI_DIR = Path(__file__).resolve().parent
MAX_REQUEST_BYTES = 64 * 1024


@lru_cache(maxsize=1)
def get_demo() -> GenericPolicyDemo:
    """Load and index the local dataset once for this process."""
    return GenericPolicyDemo(dataset_path=DEFAULT_DATASET_PATH)


def get_recorded_test_result() -> dict[str, Any] | None:
    """Read only the actual regression result recorded for this demo release."""
    try:
        result = json.loads((UI_DIR / "test_run_result.json").read_text(encoding="utf-8"))
        if (
            result.get("status") != "PASS"
            or result.get("passed") != result.get("collected")
            or result.get("failed") != 0
        ):
            return None
        return result
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a number.")
    return float(value)


def calculate_demo(payload: dict[str, Any], demo: GenericPolicyDemo | None = None) -> dict[str, Any]:
    active_demo = demo or get_demo()
    calculation = payload.get("calculation")
    if not isinstance(calculation, str):
        raise ValueError("Choose a calculation type.")

    if calculation == "attendance":
        attended, held = payload.get("attended"), payload.get("held")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (attended, held)):
            raise ValueError("Class counts must be whole numbers.")
        value, steps = calculate_attendance(attended, held)
        formula = "(attended classes / classes held) x 100"
        evidence = calculation_evidence(active_demo, "GAP-E-ATT-002")
        result = f"{value:.2f}%"
        inputs = {"attended": attended, "held": held}
    elif calculation == "course_total":
        internal = _number(payload.get("internal_score"), "Internal score")
        exam = _number(payload.get("exam_score"), "End-semester score")
        value, steps, _ = calculate_course_total(internal, exam, active_demo.dataset)
        record = next(row for row in active_demo.dataset.policies if row.policy_id == "GAP-ASSESS-001")
        details = record.calculation_details or {}
        formula = f"(internal score x {float(details['internal_weight_percent']) / 100:g}) + (end-semester score x {float(details['end_semester_weight_percent']) / 100:g})"
        evidence = calculation_evidence(active_demo, record.evidence_id)
        result = f"{value:.2f}/100"
        inputs = {"internal_score": internal, "exam_score": exam}
    elif calculation in {"sgpa", "cgpa"}:
        courses = payload.get("courses")
        if not isinstance(courses, list):
            raise ValueError("Provide at least one course or term entry.")
        parsed = []
        for item in courses:
            if not isinstance(item, dict):
                raise ValueError("Each entry needs credits and grade_point values.")
            parsed.append((_number(item.get("credits"), "Credits"), _number(item.get("grade_point"), "Grade points")))
        if calculation == "sgpa":
            value, steps, evidence_id = calculate_sgpa(parsed, active_demo.dataset)
            formula = "sum(credits x grade points) / sum(credits)"
        else:
            value, steps, evidence_id = calculate_cgpa(parsed, active_demo.dataset)
            formula = "sum(credits x term grade points) / sum(credits)"
        evidence = calculation_evidence(active_demo, evidence_id)
        result = f"{value:.2f}"
        inputs = {"courses": [{"credits": credits, "grade_point": grade} for credits, grade in parsed]}
    else:
        raise ValueError("Unknown calculation type.")

    return {
        "calculation": calculation,
        "label": "Illustrative project calculation only; not an official university result.",
        "inputs": inputs,
        "formula": formula,
        "steps": steps,
        "result": result,
        "evidence": evidence,
    }


class DemoApplication:
    def __init__(self, demo: GenericPolicyDemo | None = None) -> None:
        self.demo = demo or get_demo()

    def dashboard(self) -> dict[str, Any]:
        evaluation = run_dataset_evaluation(self.demo)
        test_result = get_recorded_test_result()
        test_display = (
            f"Recorded full backend suite: {test_result['passed']} passed, {test_result['failed']} failed ({test_result['observed_date']})"
            if test_result
            else "Not measured"
        )
        return {
            "dataset_id": self.demo.dataset.dataset_id,
            "dataset_version": self.demo.dataset.dataset_version,
            "policy_count": len(self.demo.dataset.policies),
            "question_count": len(self.demo.dataset.questions),
            "retrieval_test_count": evaluation["question_count"],
            "summary": evaluation["summary"],
            "evaluation": evaluation,
            "test_suite_result": test_result,
            "test_suite_display": test_display,
            "evaluation_note": evaluation["method_note"],
            "framework": "Python standard library HTTP server + HTML/CSS/JavaScript",
        }

    def ask(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Enter a question before submitting.")
        if len(question) > 2000:
            raise ValueError("Questions must be 2,000 characters or fewer.")
        run = self.demo.ask(question)
        return {
            "question": run.question,
            "answer": asdict(run.answer),
            "citations_validated": run.citations_validated,
            "retrieved_evidence": [asdict(row) for row in run.retrieved],
        }


class DemoRequestHandler(BaseHTTPRequestHandler):
    server_version = "RAARA-Local-Demo"
    application: DemoApplication

    def log_message(self, format: str, *args: Any) -> None:
        # Avoid logging user questions or request bodies.
        LOGGER.info("%s %s", self.command, self.path.split("?", 1)[0])

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._write(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self._static("index.html")
        if path in {"/styles.css", "/app.js"}:
            return self._static(path.lstrip("/"))
        if path == "/api/health":
            return self._json(200, {"status": "ok", "dataset_loaded": True, "mode": "offline_project_demo"})
        if path == "/api/dashboard":
            return self._json(200, self.application.dashboard())
        if path == "/api/examples":
            return self._json(200, grouped_questions(self.application.demo))
        if path == "/api/evaluation":
            return self._json(200, run_dataset_evaluation(self.application.demo))
        if path == "/api/demo-sequence":
            return self._json(200, run_five_case_demo(self.application.demo))
        self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        path = self.path.split("?", 1)[0]
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json(400, {"error": "Invalid request length."})
        if length <= 0 or length > MAX_REQUEST_BYTES:
            return self._json(413, {"error": "Request body is empty or too large."})
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._json(400, {"error": "Request body must be valid JSON."})
        if not isinstance(payload, dict):
            return self._json(400, {"error": "Request body must be a JSON object."})

        try:
            if path == "/api/ask":
                return self._json(200, self.application.ask(payload))
            if path == "/api/calculate":
                return self._json(200, calculate_demo(payload, self.application.demo))
            self._json(404, {"error": "Not found."})
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
        except Exception:
            LOGGER.exception("Local demonstration request failed at %s", path)
            self._json(500, {"error": "The local demonstration could not complete this request. Please retry or restart it."})

    def _static(self, name: str) -> None:
        allowed = {"index.html", "styles.css", "app.js"}
        if name not in allowed:
            return self._json(404, {"error": "Not found."})
        try:
            body = (UI_DIR / name).read_bytes()
        except OSError:
            LOGGER.exception("Demo UI asset is unavailable: %s", name)
            return self._json(503, {"error": "A demonstration interface file is missing."})
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        if name.endswith(".js"):
            content_type = "text/javascript"
        self._write(200, body, f"{content_type}; charset=utf-8")


def make_handler(application: DemoApplication) -> type[DemoRequestHandler]:
    class BoundDemoRequestHandler(DemoRequestHandler):
        pass

    BoundDemoRequestHandler.application = application
    return BoundDemoRequestHandler


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the isolated offline RAARA academic-policy demonstration UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host to bind; default 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("This demonstration may only bind to loopback.")
    application = DemoApplication()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(application))
    LOGGER.info("RAARA offline demo ready at http://%s:%s", args.host, args.port)
    print(f"RAARA local demo: http://{args.host}:{args.port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping RAARA local demo.", flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
