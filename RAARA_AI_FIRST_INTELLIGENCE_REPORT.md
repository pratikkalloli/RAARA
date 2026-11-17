# RAARA AI-First Conversational Intelligence Report

## Outcome

Chat orchestration now uses the configured generative model to interpret each request before retrieval. The previous application-side phrase and regex routing has been removed. Existing authentication, ownership checks, retrieval, citation verification, prompt A/B/C behavior, and hierarchical document summarization remain in place.

**Implementation:** complete.  
**Mocked verification:** focused tests passed.  
**Full backend regression:** NOT VERIFIED in this Windows environment.  
**Live Gemini verification:** NOT TESTED; no Gemini or OpenAI API calls were made.

## Previous hardcoded logic identified

- `backend/app/services/query_intent.py` classified summaries, page requests, comparisons, extraction, exam preparation, definitions, calculations, explanations, and follow-ups with regular expressions and phrase patterns.
- `backend/app/services/chat.py` returned fixed text for a maintained set of greetings, acknowledgements, introductions, and help requests.
- `backend/app/services/retriever.py` rewrote attendance questions using attendance-specific spelling and keyword rules.
- `backend/app/routes/chat.py` independently classified summary requests and resolved a document by string matching.

Those chat-routing mechanisms have been removed. `query_intent.py` was deleted. Retrieval query cleanup now only trims surrounding whitespace; semantic query rewriting comes from the request interpretation model output.

## Request interpretation architecture

The existing configured answer generator now exposes `interpret_request()` and `generate_conversational()` for both the Gemini adapter and the existing OpenAI generator. This reuses provider configuration, client construction, timeout and retry handling, structured-output validation, and safe provider error translation.

The interpretation call returns a validated JSON object containing:

- intent and whether document evidence is required;
- the model-generated semantic retrieval query;
- a bounded retrieval strategy and result limit;
- the requested output style and optional item count;
- passage-level or whole-document analysis scope;
- optional page number, target document ID, and clarification request.

The `intent` value is an open string field. The application does not maintain a map of example phrases to labels. Bounded strategy and scope fields exist to route the model's decision safely into the existing retrieval or document analysis workflows.

Malformed or unavailable interpretation output raises a safe generation error. Chat requests fail closed through the existing API error handling; the system does not silently return to phrase-based routing.

## API call behavior

1. The configured model interprets the current user message and bounded conversation context.
2. If document evidence is unnecessary, the configured model generates a short conversational response. That response contains no evidence or citations.
3. If evidence is required, RAARA embeds the model-produced retrieval query, applies the interpreted bounded retrieval settings, generates an answer from actual retrieved passages, and runs the existing citation verifier.
4. Whole-document requests use the existing hierarchical summarizer and do not degrade into ordinary top-K retrieval.
5. A clarification decision stops before retrieval or answer generation.

Gemini API configuration uses the existing `GEMINI_CHAT_MODEL`, request timeout, retry settings, and output-token limit. `GEMINI_MAX_RETRIES` is now configurable and defaults to zero retries (one request attempt). The OpenAI provider remains supported through the same interpretation contract when selected by configuration. No permanent learning is performed or claimed.

## Retrieval and document analysis

- Academic retrieval uses the model's semantic `retrieval_query`; the original user question is retained for answer generation and conversation persistence.
- The model may choose focused, broad, page-specific, comparison, document-wide, or no-retrieval handling within schema bounds.
- Document-wide analysis continues to use `DocumentSummarizer` and its hierarchical chunk reduction.
- If a user-selected `document_id` is supplied, the API checks it against documents accessible to the authenticated user before chat orchestration.
- The API supplies only the authenticated user's non-rejected document descriptors to the interpreter, capped at 100 plus an explicitly selected accessible document. The model-selected document ID must match that allow-list before it can be used.
- Model-selected IDs cannot widen server-side document authorization. Non-admin retrieval continues to add the server-controlled owner filter.

## Security and evidence handling

- Gemini credentials remain backend-only. Provider exceptions do not include credential values or raw provider messages in API errors.
- Conversation context is restricted to the configured character limit and recent-message count. It is explicitly treated as untrusted reference context.
- Document names and IDs are serialized as data, not instructions. No PDF text is sent to the interpretation call.
- Retrieved PDF text remains untrusted evidence in the existing answer-generation prompts.
- Citation metadata continues to be constructed from retrieved passages and validated by the existing citation verifier; model-generated metadata is not trusted.
- Unverified documents remain labeled by the existing generator and verification metadata. Model interpretation cannot change a document's verification or approval state.

## Tests and verification

All automated provider calls in the tests use mocks. API keys were blank in test processes.

| Verification | Actual result |
| --- | --- |
| Gemini provider, model interpretation, conversational response, chat orchestration, retrieval, and prompt behavior focused suite | **45 passed** |
| Direct chat-route ownership checks | **2 passed**, 7 TestClient tests deselected |
| Generator and prompt tests plus the same direct route checks | **19 passed**, 7 TestClient tests deselected |
| Python compile check | **Passed** (`compileall` for `app` and `tests`) |
| Full-suite collection | **170 tests collected** |
| Full backend suite execution | **NOT COMPLETE**: one test passed; execution stalled at `tests/test_auth.py::test_register_creates_student_and_never_returns_password` during Windows TestClient startup, then was interrupted. No full-suite pass is claimed. |
| Synthetic-PDF integration test in the Windows environment | **Failed due to missing local tokenizer resource**: `cl100k_base.tiktoken` was not present in the configured cache. One attempt to fetch the resource failed at DNS resolution. No repeat fetch was attempted. |
| Live Gemini/OpenAI API verification | **NOT TESTED**; zero live model calls |
| Frontend build/tests | **NOT RUN**; frontend source was not changed |

Test storage for the full-suite attempt was pointed at a unique temporary directory. The synthetic PDF integration test uses its existing `tmp_path`, temporary SQLite fixture, and temporary Chroma location. No production SQLite, ChromaDB, uploads, official evidence registries, or Phase 9A assets were targeted.

The existing WSL test environment could not be launched from this execution environment (`Wsl/E_ACCESSDENIED`), so it could not be used to complete the regression run.

### Commands used

Run from `C:\prompt_mini_proj\backend` in PowerShell:

```powershell
$env:GEMINI_API_KEY = ''
$env:OPENAI_API_KEY = ''
$env:TIKTOKEN_CACHE_DIR = Join-Path $env:LOCALAPPDATA 'RAARA\tiktoken-cache'
.\.venv311\Scripts\python.exe -m pytest tests/test_gemini_provider.py tests/test_chat_behaviors.py tests/test_query_intent_and_strategy.py tests/test_phase5_chat.py tests/test_retriever.py -q
```

Direct route ownership tests:

```powershell
.\.venv311\Scripts\python.exe -m pytest tests/test_chat_api.py -k 'chat_route_' -q
```

Generator, prompt, and direct route checks (the seven HTTP `TestClient` cases were deselected because this Windows environment stalls during TestClient startup):

```powershell
.\.venv311\Scripts\python.exe -m pytest tests/test_generator.py tests/test_prompting.py tests/test_chat_api.py -k 'not chat_api_returns_structured_answer and not chat_api_rejects_blank_question and not chat_api_defaults_to_prompt_c and not chat_api_rejects_invalid_prompt_type and not summary_request and not chat_api_requires_authentication' -q
```

This command completed with **19 passed, 7 deselected**.

Tokenizer-dependent integration test attempt:

```powershell
.\.venv311\Scripts\python.exe -m pytest tests/test_full_audit_regressions.py -k synthetic_pdf_ingestion -vv
```

This test failed because the local `cl100k_base.tiktoken` resource was missing and the single download attempt could not resolve its host.

Full-suite collection and execution attempted:

```powershell
.\.venv311\Scripts\python.exe -m pytest tests --collect-only -q
.\.venv311\Scripts\python.exe -m pytest tests -v
```

Compile check:

```powershell
.\.venv311\Scripts\python.exe -m compileall -q app tests
```

The execution command was preceded by this isolation setup (with a newly generated suffix for that run):

```powershell
$env:GEMINI_API_KEY = ''
$env:OPENAI_API_KEY = ''
$isolation = Join-Path $env:TEMP ('raara-ai-first-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $isolation | Out-Null
$forward = $isolation.Replace('\','/')
$env:DATABASE_URL = "sqlite:///$forward/backend-test.db"
$env:CHROMA_PERSIST_DIR = "$forward/chroma"
$env:UPLOAD_DIR = "$forward/uploads"
$env:TIKTOKEN_CACHE_DIR = Join-Path $env:LOCALAPPDATA 'RAARA\tiktoken-cache'
```

The full execution did not complete for the reasons recorded in the table.

## Changed files

Created:

- `backend/app/services/request_interpreter.py`
- `RAARA_AI_FIRST_INTELLIGENCE_REPORT.md`

Modified:

- `backend/app/config.py`
- `backend/app/prompting/prompt_templates.py`
- `backend/app/routes/chat.py`
- `backend/app/services/chat.py`
- `backend/app/services/generator.py`
- `backend/app/services/retriever.py`
- `backend/tests/test_chat_api.py`
- `backend/tests/test_chat_behaviors.py`
- `backend/tests/test_conversations.py`
- `backend/tests/test_full_audit_regressions.py`
- `backend/tests/test_gemini_provider.py`
- `backend/tests/test_phase5_chat.py`
- `backend/tests/test_query_intent_and_strategy.py`
- `backend/tests/test_retriever.py`

Deleted:

- `backend/app/services/query_intent.py`

## Remaining limitations

- The live Gemini interpretation and response calls have not been exercised. Mock tests verify schema wiring and orchestration, not model behavior or availability of the configured model for this account.
- The complete backend regression result remains unverified until the Windows TestClient startup stall is resolved or the project’s WSL environment can be run.
- PDF ingestion tests that need `cl100k_base` require restoring that tokenizer resource to `%LOCALAPPDATA%\RAARA\tiktoken-cache` from an already approved local or package source. Production tokenization was not changed.
- Model-generated intent and retrieval queries can still be mistaken. Structured validation, owner-scoped document allow-listing, bounded retrieval, evidence-grounded generation, and citation verification remain the enforcement boundaries.
- No claim is made that model inference permanently learns from a user's requests.
