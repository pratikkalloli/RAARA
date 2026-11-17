# RAARA Document Intelligence Report

## Result

**PASS — automated implementation and regression checks.** The document-wide summary path, intent-aware retrieval, citation preservation, and UI formatting are implemented and covered by offline tests.

**NOT TESTED — live Gemini acceptance.** No live provider calls were made. Automated tests use deterministic mocked generation and blank API-key environment variables.

## Root causes

1. Every non-conversational chat question used the same retrieval path. The retriever defaulted to five passages, and the generator only saw those passages. A request to summarize a PDF therefore behaved like a focused top-five answer rather than document-wide analysis.
2. The vector query requested only the final top-K results. It did not oversample, remove duplicate text, or select for page and section diversity. Token chunks also overlap, so neighboring chunks could repeat the same passages.
3. There was no deterministic question-intent routing for document summaries, page questions, comparisons, broad extraction, or other common academic tasks.
4. The existing generator and citation verifier already construct citations from retrieved chunk metadata. The new summary path reuses those interfaces and maps hierarchical summaries back to original Chroma chunk IDs before final verification.

The fictional attendance value remains test-only data. Unverified content continues to be labeled as unverified; no document review or official-policy state was changed.

## Implemented functionality

### Document-wide summaries

- Detects summary requests and follow-ups to an earlier summary request.
- Resolves the target from the selected document, an exact document-name/filename mention in the conversation, or the sole document in the user's library. If multiple documents remain possible, it asks the user to choose.
- The API verifies document ownership and requires the selected document to be indexed and synchronized before analysis.
- Reads all indexed chunks for that document in page/chunk order from the existing Chroma collection. It does not re-embed or rebuild the collection.
- Summarizes documents with at most 12 chunks in one generation. Larger inputs are summarized in batches of six and recursively reduced using the configured existing prompt and generator.
- Caps a single summary run at a spread sample of 120 chunks. When the cap applies, the structured answer and UI show an explicit coverage note.
- Honors requested point counts up to 20. It removes exact and very high lexical-overlap duplicate bullets, returns fewer points when fewer are distinct, and reports the limitation rather than padding with repeats.
- Rebuilds final evidence and source metadata from the original chunks, then runs the existing deterministic citation verifier. Unverified and administrator-reviewed caveats are preserved.
- Distinguishes an empty/missing vector index from a failed or incomplete extraction/indexing state; neither is presented as proof that information is absent from the PDF.

### Retrieval and intent routing

- Requests up to four times the output K from Chroma, capped at 50 candidates.
- Suppresses normalized exact duplicates and highly overlapping candidate text, then applies a bounded greedy relevance/diversity selection that rewards new pages and sections.
- Uses lexical overlap as a dependency-free MMR approximation because the existing Chroma query response contains distances, not candidate vectors. Cosine relevance thresholds remain enforced.
- Normal chat is restricted to one document by default; multiple documents are allowed when the question explicitly asks for comparison.
- Uses bounded intent strategies: focused/definition/calculation/follow-up (K=5), detailed explanation/page-specific (K=8), comparison (K=10), exam preparation (K=12), and broad extraction (K=20). Page-specific questions also add the requested page metadata filter.
- Preserves the original user question for generation and keeps prior conversation text as retrieval context, not evidence.

### Frontend

- Added an optional indexed-document selector to the existing assistant view.
- Renders numbered and bulleted responses as semantic HTML lists and markdown headings as headings.
- Displays structured coverage notes separately from the answer and citations.
- Kept the rest of the frontend layout unchanged.

## Files created

- `backend/app/services/document_summarizer.py`
- `backend/app/services/query_intent.py`
- `backend/tests/test_document_summarizer.py`
- `backend/tests/test_query_intent_and_strategy.py`
- `RAARA_DOCUMENT_INTELLIGENCE_REPORT.md`

## Files modified

- `backend/app/routes/chat.py`
- `backend/app/services/chat.py`
- `backend/app/services/generator.py`
- `backend/app/services/retriever.py`
- `backend/app/services/vector_store.py`
- `backend/tests/test_chat_api.py`
- `backend/tests/test_full_audit_regressions.py`
- `backend/tests/test_retriever.py`
- `backend/tests/test_vector_store.py`
- `frontend/src/App.jsx`
- `frontend/src/App.css`
- `frontend/e2e/ui.acceptance.cjs`

No database schema or production storage configuration was changed.

## Tests and verification

- Backend full suite: **201 passed, 0 failed** in 37.01 seconds.
- Frontend unit suite: **8 passed, 0 failed**.
- Playwright acceptance: **8 passed, 0 failed**. Includes markdown/list/coverage rendering, outgoing document selection, existing authentication/chat/history behaviors, and responsive Overview checks.
- Frontend production build: **passed** (26 modules transformed).
- Python compile check: **passed**.
- Synthetic summary tests cover a 10-page document and 10 distinct points, page citations, sparse one-page input, duplicate chunks, empty indexes, and large-document sampling.
- Intent/retrieval tests cover page-specific questions, comparisons, information extraction, exam preparation, follow-ups, duplicate suppression, page diversity, and single-document default behavior.
- Chat API tests cover explicit document selection and preventing access to another student's selected document.
- Gemini and OpenAI credentials were blank in backend test processes. Tests used isolated temporary SQLite, ChromaDB, and upload paths. Production SQLite, ChromaDB, uploads, official evidence approvals, and Phase 9A assets were not targeted.

The Windows `.venv311` focused run could not load `cl100k_base.tiktoken` because the local cache was missing and network name resolution was unavailable. The complete successful backend run used the existing WSL Python 3.11 environment and its restored tokenizer cache; application tokenization was not replaced or altered.

### Exact successful backend command

```powershell
wsl.exe -e bash -lc 'cd /mnt/c/prompt_mini_proj/backend && root=/tmp/raara-intelligence-full-20261114b && mkdir -p "$root/chroma" "$root/uploads" && env DATABASE_URL="sqlite:////tmp/raara-intelligence-full-20261114b/test.db" CHROMA_PERSIST_DIR="$root/chroma" UPLOAD_DIR="$root/uploads" AI_PROVIDER=gemini GEMINI_API_KEY= OPENAI_API_KEY= JWT_SECRET_KEY="raara-intelligence-full-suite-secret-2026b" TIKTOKEN_CACHE_DIR="/mnt/c/Users/Pratik Kalloli/AppData/Local/RAARA/tiktoken-cache" .venv-wsl311/bin/python -m pytest tests -q'
```

### Frontend verification commands

```powershell
Set-Location C:\prompt_mini_proj\frontend
npm test
npm run build
```

For Playwright, start Vite in one terminal:

```powershell
Set-Location C:\prompt_mini_proj\frontend
npm run dev -- --host 127.0.0.1 --port 5180
```

Then run in another terminal:

```powershell
Set-Location C:\prompt_mini_proj\frontend
$env:RAARA_E2E_BASE_URL = 'http://127.0.0.1:5180/'
npm run test:e2e
```

The acceptance runner intercepts `/api` with synthetic fixtures; it does not make live provider calls.

## Known limitations

- Live Gemini behavior and paid generation latency/cost were not tested. The automated generator outputs are deterministic mocks.
- Prompt intent detection is deterministic pattern matching; uncommon paraphrases can use the focused retrieval path.
- Broad information extraction retrieves a bounded, diverse set of 20 chunks; it is not exhaustive full-document extraction. Full-document processing is currently dedicated to summaries.
- Very large summaries sample at most 120 indexed chunks and show that limitation. Hierarchical generation can make multiple provider requests for a large document.
- Lexical overlap is an approximation to vector-based MMR. It reduces duplicated evidence but is not a semantic duplicate detector.
- Citation verification confirms source identity and page metadata, not semantic entailment. The application continues to mark semantic faithfulness as unverified.
- Scanned PDFs without extractable text remain unsupported by the existing ingestion pipeline.
