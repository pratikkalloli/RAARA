# RAARA Gemini Integration Report

Date: 2026-11-14  
Project: `C:\prompt_mini_proj`

## Summary

The backend now selects Gemini by default for chat and embeddings through provider factories. It keeps OpenAI as an optional provider and stores Gemini embeddings in a separate, model and dimension-specific Chroma collection. Existing retrieval, prompt selection, answer schema, citation reconstruction, verification, authentication, upload and conversation flows are retained.

No live Gemini or OpenAI API calls were made. No credentials were read, added to files, logged, or exposed. Frontend source was not changed.

**Implementation status:** Integration code and mocked provider checks are present.  
**Offline SDK status:** `google-genai` is declared, but is not installed in the active environment because package-index DNS resolution failed. Live/local SDK execution is therefore not yet runnable in this environment.  
**Backend regression status:** Incomplete; see Test results.

## Prior OpenAI implementation audit

Before this change, chat and document upload routes instantiated `OpenAIAnswerGenerator` and `OpenAIEmbeddingService` directly. Ingestion also defaulted to OpenAI embeddings; Chroma used one collection name for all vectors. The OpenAI Responses API path already owned structured answer validation and citation construction from retrieved passage metadata.

The OpenAI services remain available behind `AI_PROVIDER=openai`. Gemini uses the official Google Gen AI SDK adapter while reusing the existing structured answer validation and canonical citation construction path. Existing evaluation modules that explicitly exercise OpenAI remain unchanged and are not used by the default application provider.

## Files changed

- `backend/app/config.py` — Gemini provider/model/key settings, active provider properties, and model/dimension-specific Gemini collection naming; OpenAI collection naming remains unchanged.
- `backend/app/services/embeddings.py` — Gemini batched embeddings, document/query task types, dimension checks and normalization; provider factory; configurable OpenAI embedding dimension retained for the optional provider.
- `backend/app/services/generator.py` — Gemini generation adapter using `google-genai` structured JSON output and safe provider errors; reuses the current answer schema, evidence validation, and metadata-derived citations.
- `backend/app/services/vector_store.py` — provider-aware default Chroma collection with cosine space and embedding provider/model/dimension metadata.
- `backend/app/services/retriever.py` — use the Gemini query embedding task when the provider exposes it; preserve legacy embedding interface.
- `backend/app/services/ingestion.py` — provider factory used for default document embedding.
- `backend/app/services/chat.py` — accept either configured generator implementation.
- `backend/app/routes/chat.py` — provider factories wired into the existing chat route.
- `backend/app/routes/documents.py` — provider factory wired into existing upload ingestion.
- `backend/app/main.py` — startup warning names the active provider without exposing credential contents.
- `backend/requirements.txt` — declare `google-genai`.
- `backend/.env.example` — add Gemini settings and keep blank optional OpenAI credentials.
- `backend/tests/test_embeddings.py` — mock OpenAI dimensions explicitly after making dimensions configurable.
- `backend/tests/test_gemini_provider.py` — mocked Gemini provider, structured generation, isolated collection and synthetic PDF indexing checks.
- `RAARA_GEMINI_INTEGRATION_REPORT.md` — this report.

## Provider, models and configuration

Default settings:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_CHAT_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=768
```

`gemini-2.5-flash-lite` is listed by Google for the Gemini Developer API and currently has a Free Tier entry; the pricing page also lists a free tier for Gemini embeddings. Eligibility, quotas, model availability, and account limits can vary. `gemini-embedding-001` is Google's stable text embedding model. Google documents supported reduced output dimensions, recommends 768, 1536 or 3072 dimensions, and states that reduced-dimensionality embeddings should be normalized. The implementation requests 768 dimensions and L2-normalizes returned vectors.

Sources: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing/), [Gemini embedding documentation](https://ai.google.dev/gemini-api/docs/embeddings), [Google Gen AI SDK quickstart](https://ai.google.dev/gemini-api/docs/get-started), and [structured output documentation](https://ai.google.dev/gemini-api/docs/structured-output). Free-tier service is subject to Google's current project/account eligibility and limits; this report does not assert that a particular account has access.

Set the API key only in the backend's local environment (for example, `backend/.env`). Do not place it in frontend variables. The checked-in example leaves it blank. Optional OpenAI configuration remains available by setting `AI_PROVIDER=openai` and the existing OpenAI environment variables.

## Embedding and Chroma isolation

For Gemini, the default collection name incorporates the configured embedding model and dimension, for example:

```text
raara_documents_gemini_gemini-embedding-001_768d
```

The existing OpenAI collection remains `raara_documents`. No migration, deletion, or overwrite was performed. Existing OpenAI vectors cannot be queried with Gemini embeddings; documents must be re-embedded into the Gemini collection through the normal upload/indexing workflow. Embedding model changes likewise require a separate collection/re-indexing strategy. The synthetic PDF test uses mocked 768-dimensional embeddings and a temporary Chroma directory; it does not represent a live Gemini embedding result.

## Test results

| Check | Actual result |
|---|---|
| Focused backend provider and regression selection (`test_gemini_provider.py`, embeddings, generator, retriever, vector store) | **32 passed** |
| Frontend tests (`npm test`) | **8 passed, 0 failed** |
| Frontend production build (`npm run build`) | **Passed** |
| Full backend suite | **NOT COMPLETE** — 282 tests collected. The run encountered tokenizer-related failures and stalled in the authentication registration test; it was interrupted without a final suite summary. Do not treat as a full pass. |
| Five individually re-run evaluation tests from the full run | **5 failed** because the required `cl100k_base.tiktoken` cache was absent and network DNS could not reach `openaipublic.blob.core.windows.net`. |
| `google-genai` installation | **Blocked** — `pip install google-genai` could not resolve `pypi.org` in this network environment. |
| Live Gemini / OpenAI calls | **Not run**, as required. |

The active Python environment reports `tiktoken 0.14.0`. Its expected cache directory, `%USERPROFILE%\.cache\tiktoken`, is absent. Tokenization logic and production chunk settings were not changed, and no tests were skipped or weakened. The full regression outcome remains unverified until the suite finishes in an environment with the tokenizer resource available. The isolated provider selection avoids the five tokenizer-dependent paths, but does not replace a full-suite result.

Test storage paths used for the full backend attempt were under `%TEMP%`; Gemini Chroma tests use pytest temporary directories. No production SQLite or Chroma data was intentionally targeted. No frontend files were modified.

## Limitations and next steps

1. Restore package-index/network access or install `google-genai` from an approved local package source, then install the backend requirements.
2. Restore `cl100k_base.tiktoken` via the approved offline tokenizer-cache procedure (or use a network-enabled environment). Do not substitute a different tokenizer for production chunking.
3. Re-run the complete backend suite and capture the final summary.
4. Configure a backend-only `GEMINI_API_KEY` locally and verify the configured model with a separately approved live acceptance run. No live check was done here.
5. Re-embed the synthetic acceptance PDF with actual Gemini embeddings only during authorized live acceptance; the current isolated indexing test uses deterministic mocks.
6. After switching a deployment to Gemini, re-index its authorized documents into the Gemini collection. Do not mix or copy OpenAI vector data.

## PowerShell verification commands

From the project root, with an approved package source available:

```powershell
cd C:\prompt_mini_proj\backend
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
```

Run mocked provider/regression tests with blank credentials and temporary storage:

```powershell
cd C:\prompt_mini_proj\backend
$env:AI_PROVIDER = 'gemini'
$env:GEMINI_API_KEY = ''
$env:OPENAI_API_KEY = ''
$env:DATABASE_URL = 'sqlite:///./raara_gemini_test_only.db'
$env:CHROMA_PERSIST_DIR = (Join-Path $env:TEMP 'raara_gemini_test_only_chroma')
.\.venv311\Scripts\python.exe -m pytest tests/test_gemini_provider.py tests/test_embeddings.py tests/test_generator.py tests/test_retriever.py tests/test_vector_store.py -v
```

After installing the tokenizer resource through the approved procedure, rerun the full backend suite:

```powershell
cd C:\prompt_mini_proj\backend
$env:AI_PROVIDER = 'gemini'
$env:GEMINI_API_KEY = ''
$env:OPENAI_API_KEY = ''
$env:DATABASE_URL = ('sqlite:///' + (Join-Path $env:TEMP 'raara_gemini_full_test_only.db').Replace('\', '/'))
$env:CHROMA_PERSIST_DIR = (Join-Path $env:TEMP 'raara_gemini_full_test_only_chroma')
.\.venv311\Scripts\python.exe -m pytest -v
```

Frontend verification:

```powershell
cd C:\prompt_mini_proj\frontend
npm test
npm run build
```
