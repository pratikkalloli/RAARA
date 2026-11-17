# RAARA — Academic Policy Assistant (local demonstration)

This standalone interface presents the isolated Phase 8C Stage 4 generic-policy pipeline. It is a project demonstration, **not** a production assistant or official PES University policy service.

## Requirements and start

No UI framework or additional package is required. The server uses Python's standard library and the existing backend `.venv311` dependencies. It runs offline, needs no OpenAI key, and binds only to loopback.

From PowerShell, in `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.raara_demo_ui.server
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Stop the server with **Ctrl+C** in that terminal. To choose another local port:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.raara_demo_ui.server --port 8766
```

The `--host` option accepts loopback addresses only. The interface is served by the local Python process; no cloud deployment, external assets, tracking, database, ChromaDB, or persistent index is used.

## Interface

- **Ask RAARA:** submit a question to the existing `GenericPolicyDemo` pipeline. The page shows the answer status, answer citations, retrieved passages, exact IDs/text, version, provenance, authority status, and disclaimer.
- **Example questions:** selectable questions are grouped from the existing 30-question dataset. Text and IDs are loaded from the dataset; the UI does not author replacement examples.
- **Five-minute walkthrough:** runs the five requested scenarios and shows expected and actual status, evidence IDs, retrieved passages, and whether pipeline citation metadata validation passed.
- **Calculations:** attendance, weighted course score, SGPA, and CGPA use the existing calculation functions and validated dataset assumptions. Inputs, formula, arithmetic steps, result, and supporting dataset evidence are shown.
- **Evaluation dashboard:** runs all 30 existing questions in their dataset order and shows actual status matches, evidence retrieval, citation metadata checks, abstention correctness, numerical question status matches, and per-question pass/fail. A diagnostic pass requires expected status, valid citation metadata, and retrieval of all expected evidence for answerable questions. It is not a semantic faithfulness score or official-policy accuracy metric.
- **Architecture and limitations:** explains local cosine similarity, deterministic answer templates, and nonofficial corpus status.

The dashboard displays the recorded full-suite result from `test_run_result.json` only when that file contains a completed passing run with consistent counts. This record comes from the actual isolated Phase 8C Stage 5 suite execution. If no valid result record is present, the UI displays “Not measured.” Update the record only after a completed test run; it is not inferred from source code.

## Run the reproducible evaluator

From `backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.raara_demo_ui.evaluate
```

It prints JSON for all dataset questions, including question ID, expected and actual status, retrieved and cited evidence IDs, citation validity, expected-evidence retrieval, abstention correctness, and pass/fail. It makes no API calls and does not modify the dataset or write result files.

## Architecture and safety

Browser requests are handled by `server.py`, which creates one `GenericPolicyDemo` instance per process. It delegates question answering to the Stage 4 pipeline and calculation work to Stage 4's existing deterministic functions. There is no duplicate retriever or answerer. The UI has no document approval or official-registry write endpoint.

The demo corpus contains 28 `PROJECT_AUTHORED` / `GENERIC_PROJECT_POLICY` / `NOT_OFFICIAL` records. The retrieval engine uses local cosine similarity; scores are not probabilities. Answer generation is deterministic templates and calculations, **not an LLM**. No live OpenAI API is used. Citation validation confirms references match retrieved corpus metadata; that check does not prove that prose is semantically faithful. Current official PES University B.Tech AIML regulations are not verified in the corpus.

Questions are length-limited, request bodies are size-limited, static assets are allowlisted, the server binds to loopback, and browser output is rendered as text. Request logs omit question content. No API key or application production settings are loaded by the UI.

## Tests

From `backend`:

```powershell
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_raara_demo_ui.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_generic_policy_demo.py
```

The UI tests cover the five scenarios, dataset-order reproducibility, exact examples, all four calculations, provenance and citation visibility, official-policy abstention, local HTTP smoke behavior, invalid inputs, and production configuration/registry isolation.

## Known limitations

- Retrieval is the Stage 4 deterministic lexical hash embedder over a small synthetic project-authored corpus; its ranking is not a general semantic guarantee.
- The answerer is a deterministic rule/template system and can miss paraphrases or have status/evidence mismatches. The evaluation table exposes these rather than adjusting expected outcomes.
- Citation metadata validation does not establish semantic claim support.
- No verified university policy, PDF page citation, live LLM, authentication, deployment, or persistence is part of this local demonstration.
