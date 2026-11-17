# RAARA Phase 8E — Targeted Repair Report

**Date:** 2026-11-15  
**Scope:** Conversation context after abstentions, selected-document summary routing, and provenance-aware abstention explanations.

## Outcome

Phase 8E targeted repairs are implemented. Focused regression tests passed (113 passed). The complete backend suite then completed with exit code 0; it collected 204 tests and passed all 204. No live Gemini or OpenAI calls were made. This report does not claim live acceptance.

## Root causes

1. **Conversational follow-ups after `NOT_FOUND`:** Conversation history retained only role and answer text. It omitted the persisted structured answer status and evidence count. The request interpreter therefore could not tell that the preceding assistant message was an evidence abstention, and could classify a conversational follow-up as a new evidence-seeking academic question.
2. **Selected-document summary returned HTTP 422 / clarification:** The API correctly authorized the selected document, but the service did not pass that explicit selection to request interpretation. When interpretation requested clarification about scope, orchestration returned early before the existing whole-document summarizer could use the authorized selection. The frontend already sent `document_id`; no frontend contract change was needed.
3. **Abstention explanation lost provenance detail:** Citation verification replaced valid model-generated `NOT_FOUND` responses without citations with a generic abstention message. This discarded distinctions already available from retrieval and document metadata, such as no accessible documents, no relevant passages, or relevant unverified material.

## Changes made

### Application files

- `backend/app/services/conversations.py` — carries the prior assistant answer status and evidence count into bounded interpretation context without adding source text.
- `backend/app/services/request_interpreter.py` — includes explicit selected-document scope in the model input; preserves safe assistant status metadata; clarifies that a prior `NOT_FOUND` response is conversational context rather than evidence.
- `backend/app/services/generator.py` — supplies retrieval and provenance states to abstention generation and clarifies how to explain evidence limitations without inferring document authority from names.
- `backend/app/services/chat.py` — validates explicit selections against the authorized document list before interpretation; passes selection into interpretation; allows a model-identified whole-document request to reach the existing summarizer; prevents scope widening.
- `backend/app/services/citation_verifier.py` — preserves a valid no-citation `NOT_FOUND` explanation and its citation-not-applicable state rather than replacing it with a generic message.

### Test files

- `backend/tests/test_chat_behaviors.py`
- `backend/tests/test_conversations.py`
- `backend/tests/test_gemini_provider.py`
- `backend/tests/test_citation_verifier.py`
- `backend/tests/test_full_audit_regressions.py` — the direct service integration fixture now supplies the authorized-document metadata that the production route supplies.

No frontend files, model configuration, production retrieval settings, or numerical citation verification rules were changed.

## Safety and behavior

- Intent remains model-driven; no greeting list, regex routing, keyword routing, or phrase-based query expansion was added.
- An explicit selected document is checked against the caller's authorized document set before model interpretation. An unavailable selection is rejected safely, and a model target cannot widen the requested scope.
- Conversation context carries only status and evidence count in addition to the existing role/content fields; it does not expose hidden prompts, credentials, or saved evidence text to this added metadata path.
- Existing hierarchical document summarization remains in use.
- Evidence abstentions can distinguish retrieval state and verification/provenance state using document metadata. This does not establish semantic faithfulness or document authority.

## Test results

- Focused tests: **113 passed in 24.37 seconds**.
- Complete backend suite: **204 collected, 204 passed, 0 failed, exit code 0**.
- During regression, the first full run after the changes had 203 passed and one integration test failure because its direct service fixture omitted the authorized-document list. The fixture was corrected to match the production route contract; the test passed on targeted rerun, and the complete suite then finished successfully.
- The subsequent quiet rerun could not start because WSL returned `Wsl/E_ACCESSDENIED`. It was not counted as a test run and does not alter the completed verbose run result.
- Automated tests used isolated temporary SQLite, ChromaDB, and upload directories with external API keys blank. Provider calls were mocked.

## Limitations

- Live Gemini behavior has not been revalidated after these changes. The passing tests establish orchestration and contract behavior with mocked provider responses only.
- The service-level provenance categories rely on the metadata currently present on accessible documents; they do not independently verify issuing authority.
- The selected-document HTTP 422 root cause was addressed through orchestration and authorized scope propagation. Invalid or inaccessible document IDs remain subject to the existing route authorization response.
- Whole-document summaries and requested-point recovery rely on the existing summarizer and its current extraction/context limits.

## Data protection confirmation

The regression run used a newly created temporary test directory under `/tmp` for SQLite, ChromaDB, and uploads. No production SQLite database, production ChromaDB collection, uploaded PDF, evidence approval, or Phase 9A asset was modified. No live API request was made. Human review and document approval state remain unchanged.

## Verification command

The completed full-suite run used WSL Python 3.11 with isolated paths and blank API keys:

```powershell
wsl.exe -e bash -lc 'set -e; cd /mnt/c/prompt_mini_proj/backend; ISOLATION=$(mktemp -d /tmp/raara-phase8e-final-XXXXXX); export GEMINI_API_KEY= OPENAI_API_KEY=; export DATABASE_URL="sqlite:///$ISOLATION/backend.db" CHROMA_PERSIST_DIR="$ISOLATION/chroma" UPLOAD_DIR="$ISOLATION/uploads" TIKTOKEN_CACHE_DIR="$HOME/.cache/tiktoken" JWT_SECRET_KEY="phase8e-final-secret-<random>"; mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"; ./.venv-wsl311/bin/python -m pytest tests -v'
```

Focused test command:

```powershell
wsl.exe -e bash -lc 'cd /mnt/c/prompt_mini_proj/backend && ./.venv-wsl311/bin/python -m pytest tests/test_chat_behaviors.py tests/test_conversations.py tests/test_gemini_provider.py tests/test_citation_verifier.py tests/test_chat_api.py tests/test_document_summarizer.py tests/test_query_intent_and_strategy.py tests/test_generator.py -v'
```

**Phase 8E implementation and regression work is complete. No Phase 8F or live acceptance was started.**
