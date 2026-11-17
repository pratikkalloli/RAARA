# RAARA Phase 8D — Semantic Accuracy, Context Reliability and Document Intelligence

## Outcome

**Implementation: COMPLETE. Regression tests: PASS. Live Gemini acceptance: NOT RUN.**

This work addresses conversational follow-up handling, whole-document summary coverage, numerical claim reliability, and evidence-aware abstention. It does not establish general semantic faithfulness: citation verification confirms that citations identify actual retrieved passages, while semantic checking remains a separate, model-assisted process with limitations described below.

## Root causes

### Conversational follow-up and history

The chat route already retrieved only the authenticated user's owned history, ordered messages chronologically, and supplied that history to both request interpretation and conversational generation. No history-loading, ownership, or conversation-persistence defect was found. The weakness was in the interpreter and conversational generation instructions: they did not explicitly direct the configured model to resolve references such as “that” from the recent exchange and to explain the assistant's prior response or offer when the referent was clear. The Phase 8C example also followed a generic greeting/offer, which did not itself establish an academic referent. The prompts now handle a clear antecedent when available and retain clarification behavior when context is genuinely ambiguous or absent. No greeting list, phrase routing, or deterministic conversational response was added.

### Underfilled whole-document summaries

The summarizer already used hierarchical batches and preserved citations, but its final generation prompt did not sufficiently emphasize distinct facts, conditions, exceptions, dates, and quantities across all supplied passages. The model could therefore return fewer points than requested. The summarizer now makes one bounded retry when enough distinct source passages exist but the first summary underfills the requested count. It adopts the retry only when it improves the number of distinct points. It does not pad, duplicate, or invent points, and the existing coverage disclosure remains in effect when the source cannot support the requested count.

### Incorrect numerical selection

Citation verification validated passage identity and source metadata, not whether a cited number answered the question or belonged to the correct subject, condition, or assessment component. Thus a citation could be real while a number selected from nearby text (for example, a score value instead of the requested allocation) was semantically wrong. A separate numerical consistency verifier now asks the configured model to map every numeric claim to actual cited passage IDs and check the subject, units, conditions, dates, and question relevance. The application validates the response schema, requires complete numeric coverage and actual cited IDs, and withholds numeric claims on unsupported, ambiguous, incomplete, or failed review. It does not substitute a different number.

### Generic abstention explanation

When retrieval returned no relevant passages, the default explanation did not account for whether the index was empty, retrieval found no candidates, a selected document had no matching passages, or accessible documents were unverified. Retrieval now exposes a bounded retrieval-state value, and the configured generator can explain the evidence gap from that state and the authenticated user's available document metadata. It continues to label unverified sources explicitly and does not claim an unsupported policy fact. Safe generic abstention remains available if that model explanation method is absent in an injected/legacy service.

## Changes made

### Application files

- `backend/app/services/request_interpreter.py` — stronger model instructions for resolving clear follow-up references through recent conversation history.
- `backend/app/services/generator.py` — context-aware conversational generation, structured evidence-gap explanations, and structured numerical-claim review using the configured provider/model.
- `backend/app/services/retriever.py` — explicit retrieval outcome state for empty index, no candidates, and no relevant passages.
- `backend/app/services/factual_verifier.py` — new fail-closed numerical consistency layer; checks claims against actual cited retrieved passage IDs and preserves valid citation metadata without inventing replacements.
- `backend/app/services/chat.py` — invokes the evidence-gap explanation for empty/insufficient results, preserves citation verification, then applies numerical consistency review.
- `backend/app/services/document_summarizer.py` — one conditional bounded retry for underfilled summaries when enough distinct source material exists; applies the numerical consistency check after canonical citation handling.
- `backend/app/routes/chat.py` — injects the shared configured generator's numerical checker and supplies authenticated, owner-scoped document verification/source metadata to interpretation and abstention.

### Test files

- `backend/tests/test_factual_verifier.py` — new numeric relevance, conflict, unsupported, incomplete, invalid-ID, unavailable-review and nonnumeric cases.
- `backend/tests/test_chat_behaviors.py` — follow-up context, no-evidence explanation, citation-to-numerical-check order, and authorization-related orchestration behavior.
- `backend/tests/test_conversations.py` — chronological multi-turn context coverage.
- `backend/tests/test_gemini_provider.py` — mocked Gemini prompt/context, abstention metadata and numerical-review request coverage.
- `backend/tests/test_document_summarizer.py` — bounded recovery of distinct points while preserving conditions and source references.
- `backend/tests/test_retriever.py` — retrieval state coverage.
- `backend/tests/test_phase5_chat.py` — mocked evidence-gap generation and abstention flow.
- `backend/tests/test_query_intent_and_strategy.py` — corrected the test double to provide citation-ready synthetic evidence for tests that assert answer generation. Empty-result cases remain covered by abstention tests.

No frontend files, provider selection, model names, embedding configuration, production chunking parameters, retrieval thresholds, official evidence approvals, or Phase 9A assets were changed.

## Verification

All tests used WSL Python 3.11 (`backend/.venv-wsl311`), blank `GEMINI_API_KEY` and `OPENAI_API_KEY`, a temporary SQLite database, temporary ChromaDB directory, temporary upload directory, and the existing tokenizer cache at `/tmp/data-gym-cache`. No live Gemini or OpenAI calls were made.

Focused repair tests:

```text
19 passed in 87.07s
```

Query strategy tests after the test-double correction:

```text
5 passed in 73.90s
```

Complete backend suite:

```text
189 passed in 125.18s
```

The final full-suite command was run from the backend directory with temporary paths and blank keys:

```bash
ISOLATION=$(mktemp -d /tmp/raara-phase8d-final-XXXXXX)
export GEMINI_API_KEY= OPENAI_API_KEY=
export DATABASE_URL="sqlite:///$ISOLATION/backend.db"
export CHROMA_PERSIST_DIR="$ISOLATION/chroma"
export UPLOAD_DIR="$ISOLATION/uploads"
export TIKTOKEN_CACHE_DIR=/tmp/data-gym-cache
mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"
./.venv-wsl311/bin/python -m pytest tests -v
```

## Remaining limitations

- Numerical consistency is model-assisted, not a deterministic proof of semantic correctness. The deterministic safeguards enforce schema validity, complete numeric coverage, and that cited evidence IDs are from actual retrieved/cited passages; they cannot guarantee that the model's subject/condition interpretation is correct. Any review failure or ambiguity withholds the numeric answer.
- Non-numerical semantic claims still are not comprehensively checked claim by claim. Valid citations alone do not prove answer faithfulness.
- Summary retry is bounded to one retry and only attempts recovery when enough distinct source passages exist. Concision, model output limits, source extraction quality, or genuinely insufficient evidence can still result in fewer points; coverage is not fabricated.
- The improved prompts and abstention explanations were covered with mocked provider calls. Their live behavior with Gemini has not been tested in this phase.
- Frontend tests/build were not rerun because no frontend files or contracts changed.

## Data and safety

The test command used isolated temporary storage and blank provider credentials. Production SQLite, ChromaDB collections, uploaded PDFs, official evidence approvals, and Phase 9A assets were not targeted or modified. No secrets or private document text were written to the report.
