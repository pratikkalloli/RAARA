# Isolated Generic Academic Policy RAG Demonstration

## Purpose and data provenance

This module demonstrates a local retrieval-and-answer flow over the separate Stage 3 dataset at `evaluation/datasets/project_authored_academic_policy/generic_academic_policy_dataset.json`. It loads 28 project-authored policy records and 30 labeled demonstration questions. Every record must validate as `PROJECT_AUTHORED`, `GENERIC_PROJECT_POLICY`, `NOT_OFFICIAL`, and `is_official_university_policy: false`. The runtime context label is `PROJECT_AUTHORED_GENERIC_POLICY`.

The records are project assumptions, not PES University rules, not universal academic requirements, and not specific to a real course, campus, or admission batch. See `GENERIC_POLICY_ASSUMPTIONS.md` for numeric rationale. The Phase 8A official registry, Phase 9A corpus, and production data are separate and never searched by this demo.

## Architecture

- **Dataset loader:** uses Stage 3's strict Pydantic schema and arithmetic validator.
- **Retriever:** builds a process-local in-memory index with the existing deterministic `DeterministicTfidfHashEmbedding` evaluation embedder. It uses cosine similarity, deterministic tie ordering, duplicate evidence-ID suppression, configurable local `top_k` (default 5), and configurable relevance threshold (default 0.12). Thresholds apply only to this demo. Scores are lexical retrieval hints, not authority or truth scores.
- **Provenance gate:** revalidates all retrieved records and rejects any mismatch, official/verified label, or known instruction-like override content. It preserves policy/evidence IDs, title, category, version, exact text, and labels.
- **Answerer:** deterministic templates and arithmetic functions; it is **not an LLM**. It only creates citations from records actually retrieved. Citations contain exact policy/evidence IDs, title, category, version, and provenance labels. It does not invent document pages or URLs.
- **Pipeline:** checks citations against retrieved metadata and abstains if any citation does not match. No persistent vector index is created; no ChromaDB or SQLite is used by this path.
- **CLI:** one-shot or interactive local demonstration. No network calls, API keys, paid service, or additional dependency is needed.

## Answer and abstention behavior

Answers carry status, citations, and a disclaimer. Retrieved source excerpts and citations show `PROJECT_AUTHORED`, `GENERIC_PROJECT_POLICY`, `NOT_OFFICIAL`, `is_official_university_policy: false`, and `PROJECT_AUTHORED_GENERIC_POLICY`.

Official PES/university questions and real admission-batch applicability questions return `NOT_FOUND` without generic citations. Questions requiring unspecified rules (such as medical exemptions, attempt limits, dates, deadlines, or institution-specific thresholds) abstain, optionally citing the exact generic record that states the detail is unspecified. Questions with no score above the relevance threshold return `NOT_FOUND`; underspecified prompts such as “Is it enough?” return `NEEDS_CLARIFICATION`. Version comparison returns `CONFLICTING_SOURCES` only when both explicitly project-authored attendance versions were retrieved.

A deterministic query guard recognizes common institutional phrasing. It is intentionally conservative/simple and is not a production safety boundary. No live generation model is involved.

## Calculations

Calculation assumptions are read from the validated dataset at runtime. Supported operations:

- Attendance percentage from attended and held class counts.
- Weighted course total using the dataset's internal/end-semester weights.
- Credit-weighted SGPA and CGPA using the dataset's grade-point scale.
- Overall illustrative pass-threshold comparison.

Inputs are checked for invalid counts, out-of-range component scores, zero/negative credits, empty course lists, and grade points outside the project scale. Division by zero is rejected. Results are rounded to two decimals and include arithmetic steps and citations to retrieved generic formula evidence. Every calculation remains labeled illustrative.

## Run the CLI

From `backend` in `.venv311`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "What is the illustrative minimum attendance?"
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "What is the official PES University attendance requirement?"
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "Calculate SGPA using 4 credits at 9 grade points, 3 credits at 8 grade points."
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "When is the next cricket match?" --min-relevance 0.12 --top-k 5
```

Interactive mode prints JSON with retrieved records, scores, answer status, exact citations, validation result, and disclaimer; enter `exit` or `quit` to finish. One-shot mode prints one JSON result and exits. A typical attendance answer cites `GAP-E-ATT-001` and states the illustrative 75% value; an official PES question returns an abstention and no generic citation.

## Tests

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_project_authored_policies
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_generic_policy_demo.py
```

Tests cover deterministic retrieval, relevance thresholds, answerable/abstention/clarification/conflict scenarios, numerical arithmetic and invalid inputs, exact citations, provenance, prompt-injection rejection, and official-gate/registry isolation.

## Limitations and production separation

The local embedder is a deterministic lexical hash baseline; retrieval quality is limited and scores are not calibrated for general academic-policy use. Query expansion and official-policy phrase detection are rule-based. The deterministic answerer is a collection of templates/calculations, not generative AI. There is no PDF page citation because these policy records are authored JSON entries, not sourced PDF pages. This module is not connected to `/api/chat`, production retrieval, prompts A/B/C, production settings, production SQLite, or production ChromaDB.

If later added to a demonstration UI, preserve the disclaimer and use only this separate dataset and a dedicated evaluation-only index. For actual university rules, acquire authorized documents and complete applicability/provenance/human-review steps; never promote generic records into the official registry or reuse them as official evidence.
