# RAARA Phase 8C — Intent and Selected-Document Fix Report

## Result

- **Conversational routing repair:** implemented and verified with mocked provider tests.
- **Selected-document request contract:** reproduced with the frontend's request fields and types; the accessible-document API request succeeds in the isolated test. The original live HTTP 422 remains **unattributed** because its response body was not captured. No live retry was made, and no unrelated backend behavior was changed to guess at its cause.
- **Backend regression:** **174 passed, 0 failed**.
- **Live Gemini acceptance:** not performed in this task.

## Root cause analysis

### Conversational requests

The interpretation schema had a free-form `intent` and overlapping routing fields, including `requires_document_evidence` and `clarification_needed`, but no single, constrained route value. The instructions described the intended behavior, but the orchestration ignored `intent` and branched only on `requires_document_evidence`. Thus a structured response could validly classify the message inconsistently and send ordinary conversation to retrieval. The previous acceptance report retained the empty-evidence `NOT_FOUND` answers, but not Gemini's raw interpretation JSON; therefore the exact boolean returned for those two turns cannot be established after the fact.

### Selected-document HTTP 422

The accepted request schema is `question` (trimmed nonblank string, max 4,000 characters), optional `document_id` (positive integer), optional `conversation_id` (positive integer), optional UUID `idempotency_key`, and `prompt_type` A/B/C. The frontend sends those identifiers as numbers and the idempotency key as a UUID. A new isolated API test using this exact field/type contract and an accessible synthetic document receives HTTP 200. Existing tests continue to confirm an inaccessible document is rejected before the chat service runs.

The existing live report explicitly states that the HTTP 422 response body was not captured. Since route-level validation succeeds for the actual frontend contract and the report contains no sanitized downstream error, the specific cause of that historical 422 is **not determinable from available evidence**. It would be unsafe to claim a root cause or add a speculative fix. No frontend change was justified.

## Repairs

- Added a discriminated `request_mode`: `conversation`, `document_evidence`, or `clarification`.
- Added structured-schema descriptions and explicit instructions for mutually consistent route selection, including conversational follow-ups.
- Added model validation that rejects inconsistent routing fields. Existing generator handling converts malformed interpretation output into a safe `GenerationError`, rather than falling back to another routing mechanism.
- Updated chat orchestration to route from the validated `request_mode`. Conversation requests invoke model-generated conversational output without retrieval; evidence requests continue through the existing semantic query, document ownership check, retrieval, citation verification, and persistence flow. Clarification requests stop before retrieval.
- Added mocked Gemini interpretation cases for a conversational request and a conversational follow-up, plus a malformed/inconsistent output case.
- Added an isolated API regression for selected accessible-document requests using frontend-compatible numeric IDs and UUID idempotency key.

No greeting lists, keyword routing, regex intent classification, deterministic conversational responses, model changes, or frontend changes were introduced.

## Files changed

Application code:

- `backend/app/services/request_interpreter.py`
- `backend/app/services/chat.py`

Tests updated or added:

- `backend/tests/test_chat_behaviors.py`
- `backend/tests/test_chat_api.py`
- `backend/tests/test_gemini_provider.py`
- `backend/tests/test_conversations.py`
- `backend/tests/test_query_intent_and_strategy.py`
- `backend/tests/test_phase5_chat.py`
- `backend/tests/test_full_audit_regressions.py`

Report:

- `RAARA_PHASE8C_INTENT_AND_DOCUMENT_FIX_REPORT.md`

## Test results

Focused command (WSL Python 3.11), executed with empty Gemini/OpenAI keys and temporary SQLite, ChromaDB, and upload paths:

```bash
cd /mnt/c/prompt_mini_proj/backend
ISOLATION=$(mktemp -d /tmp/raara-phase8c-focused-XXXXXX)
export GEMINI_API_KEY= OPENAI_API_KEY=
export DATABASE_URL="sqlite:///$ISOLATION/backend.db"
export CHROMA_PERSIST_DIR="$ISOLATION/chroma" UPLOAD_DIR="$ISOLATION/uploads"
export TIKTOKEN_CACHE_DIR=/tmp/data-gym-cache
mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"
./.venv-wsl311/bin/python -m pytest tests/test_chat_behaviors.py tests/test_chat_api.py tests/test_gemini_provider.py tests/test_conversations.py tests/test_phase5_chat.py tests/test_query_intent_and_strategy.py tests/test_full_audit_regressions.py -q
```

Result: **70 passed**.

Full backend suite command, with a separate temporary storage directory and blank keys:

```bash
cd /mnt/c/prompt_mini_proj/backend
ISOLATION=$(mktemp -d /tmp/raara-phase8c-final-XXXXXX)
export GEMINI_API_KEY= OPENAI_API_KEY=
export DATABASE_URL="sqlite:///$ISOLATION/backend.db"
export CHROMA_PERSIST_DIR="$ISOLATION/chroma" UPLOAD_DIR="$ISOLATION/uploads"
export TIKTOKEN_CACHE_DIR=/tmp/data-gym-cache
mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"
./.venv-wsl311/bin/python -m pytest tests -v
```

Result: **174 passed in 95.92s**. No tests failed, skipped, or errored. The complete suite includes citation verifier, ownership, summary routing, retrieval, prompt injection, and conversation persistence tests. Provider calls in automated tests are mocked; no live API calls were made.

The selected-document regression validates API request parsing, accessible document resolution, and response handling using a mocked chat service. It does not reproduce the original real Gemini/retrieval request and therefore does not establish what produced the missing historical 422.

## Remaining limitations

- A live greeting/follow-up has not been rerun after adding the explicit route field. Mocked tests verify the schema and orchestration only; they do not claim live Gemini acceptance.
- The original selected-document 422 remains unexplained. To identify its exact cause, a future authorized isolated acceptance run must capture only the sanitized status and validation detail (never credentials or private document text). No live calls were made here, per task constraints.
- Semantic faithfulness remains outside what these routing and API contract tests prove. Citation verification continues to validate references against retrieved passages and does not prove claim entailment.

## Data safety

The complete suite used a unique temporary directory for SQLite, ChromaDB, and uploads, with `GEMINI_API_KEY` and `OPENAI_API_KEY` blank. No production database, Chroma collection, uploaded PDF, evidence approval, or Phase 9A asset was accessed for writes or modified. Frontend files and provider/model configuration were not changed.
