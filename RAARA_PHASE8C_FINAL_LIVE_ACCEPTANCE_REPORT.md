# RAARA Phase 8C — Final Controlled Live Gemini Acceptance

## Overall result

**PARTIALLY ACCEPTED.** Live Gemini and the application completed the greeting, selected-document retrieval, summary, examination, unsupported-policy, and cross-user requests without an HTTP 422. Several expectations were met, but conversational follow-up was not context-aware, the whole-document summary returned only one distinct point, and the examination answer selected the wrong fictional marks from the synthetic example. The unsupported-policy request abstained but did not explicitly explain why the synthetic corpus cannot establish an official requirement.

## Environment and safety

- Application: current RAARA backend source in `backend`, using WSL Python 3.11.18 from `.venv-wsl311`.
- Provider: Gemini.
- Chat model: `gemini-3.5-flash-lite`.
- Embedding model: `gemini-embedding-001` (768-dimensional Gemini collection).
- Gemini credential: configured in the existing backend environment; its value was not read, displayed, logged, or copied.
- Backend: temporary Uvicorn server on port 8000. The earlier isolated server was stopped after verifying its test-only storage path. The acceptance server was stopped after the run.
- Storage: fresh isolated directory `/tmp/raara-phase8c-final-live-YPSIOU/` containing `acceptance.db`, `chroma/`, and `uploads/`. The configured production paths were not used.
- JWT: generated as a random process-only secret for disposable accounts. `backend/.env` was not changed.
- Test accounts: two disposable students, credentials held only in process memory and never printed.
- PDFs: all three were generated for this test and visibly labelled **SYNTHETIC TEST ONLY — NOT OFFICIAL UNIVERSITY POLICY**. No official or private PDFs were used.
- Automated backend regression: the latest recorded full run remains **174 passed in 95.92s** (WSL Python 3.11, blank provider keys, temporary storage), as recorded in `RAARA_PHASE8C_INTENT_AND_DOCUMENT_FIX_REPORT.md`. No automated tests made live calls. A collection-only preflight attempted during this acceptance stalled on WSL mounted-filesystem I/O and was stopped; this acceptance did not rerun the full suite.

## Synthetic uploads

All upload requests returned HTTP 201. Each document was indexed and remained `unverified`:

| Fixture | Owner | Pages | Indexed chunks | Review status |
|---|---|---:|---:|---|
| Fictional Attendance Workbook | Student A | 13 | 40 | unverified |
| Synthetic Examination Example | Student A | 1 | 3 | unverified |
| Synthetic Second Student Example | Student B | 1 | 3 | unverified |

The 40-chunk first document exceeds the summarizer's 12-chunk direct-processing limit and exercises its hierarchical reduction path. The acceptance data remains in the isolated temporary directory for review.

## Live cases

| Case | HTTP and observed result | Assessment |
|---|---|---|
| A — Greeting | HTTP 200; Gemini returned a nonempty natural response with status `CONVERSATIONAL`, no evidence, and no sources. | **PASS.** The repaired conversation route was used. The application branches to conversational generation before retrieval. |
| B — Conversational follow-up | HTTP 200; status `CONVERSATIONAL`, no evidence or sources. The response asked the user to specify what to explain, despite the preceding greeting in the same conversation. | **FAIL — context use.** No `NOT_FOUND` or document citations were produced, but the response did not resolve the conversational follow-up from context. |
| C — Selected attendance document | HTTP 200; response included the expected fictional 90% value. All three evidence records named only the selected document and cited page 1. Citation validation was `VERIFIED`; source verification remained `unverified`; answer status was `PARTIALLY_SUPPORTED`. | **PASS for selection, retrieval and citation identity.** The administrator review state was not elevated. Semantic entailment of every additional answer detail was not independently adjudicated. |
| D — Whole-document summary | HTTP 200; the 40-chunk document returned a summary with 12 evidence records citing actual pages 1–9. All persisted citation records matched Chroma passage ID, document name and page. Coverage disclosed: “The indexed content supports 1 distinct summary points, fewer than the 5 requested; facts were not repeated to fill the list.” Status was `PARTIALLY_SUPPORTED`. | **PARTIAL.** Hierarchical processing and citation validation were exercised, and the coverage limitation was disclosed. The requested five distinct points were not produced. |
| E — Examination document | HTTP 200; evidence was limited to the selected examination document, page 1. Citation validation was `VERIFIED`, and the source remained `unverified`. The answer discussed the synthetic example scores of 32 ISA and 45 ESA marks; it did not provide the requested fictional distribution of 40 ISA and 60 ESA marks. | **FAIL — answer accuracy.** The source selection and citation were correct, but the answer chose the wrong figures from the document. |
| F — Unsupported official-policy question | HTTP 200; status `NOT_FOUND`, with no evidence or sources and no official requirement asserted. | **PARTIAL.** The system abstained, but the response did not explicitly explain that the uploaded synthetic documents cannot establish an official university rule. |
| G — Cross-user document selection | HTTP 404 before chat orchestration. The response did not contain the other user's synthetic marker or document name. | **PASS.** Ownership enforcement denied access. |

### HTTP 422 diagnostics

No selected-document request returned HTTP 422 in this run. The selected attendance question, whole-document summary, and examination question all returned HTTP 200. No request-schema change was made during acceptance. This establishes that the earlier 422 was not reproduced under the repaired request contract; it does not retroactively identify the uncaptured cause of the earlier response.

### Citation and persistence verification

The isolated Chroma index was read after the live requests. Every citation persisted for cases C, D, and E matched a real indexed passage by passage ID, document ID, document name, and page number. No replacement citations were synthesized during this check. Citation validity confirms reference identity; it does not prove semantic faithfulness of every answer claim.

The main conversation contained **10 persisted messages: five user/assistant pairs** for cases A–E. The unsupported-policy case was sent without a conversation ID; the denied cross-user request did not enter orchestration. No empty conversation remained.

## Acceptance criteria summary

- Greeting: **PASS**.
- Context-aware conversational follow-up: **FAIL**.
- Selected-document retrieval and page citation: **PASS**, with source explicitly unverified and answer status partial.
- Whole-document hierarchical summary path: **PARTIAL**; one distinct point returned instead of five, with an accurate limitation notice and valid source references.
- Cross-document selection isolation for PDF B: **PASS** for selected-source identity; **FAIL** for returning the requested 40/60 distribution.
- Unsupported official-policy question: **PARTIAL**; it abstained without inventing an official answer, but its explanation was generic.
- Cross-user access denial: **PASS**.
- Conversation persistence: **PASS** for five successful in-conversation exchanges.
- Selected-document HTTP 422: **not reproduced**.

## Remaining limitations

- Gemini sometimes treats a context-dependent conversational follow-up as ambiguous, even though it avoids retrieval.
- The exam response demonstrates a factual selection error between two nearby figures in the same synthetic source. Citation verification correctly validated the source but does not catch that semantic mismatch.
- The summarizer reported its limited coverage accurately, but did not meet the requested five-point output.
- The unsupported-policy answer abstained but needs a clearer user-facing explanation when available documents are synthetic or unverified.
- No browser/visual frontend acceptance was performed. Frontend source was not changed.
- No claim of permanent Gemini learning is made. Each response used the configured model and the current request/context.

## Data and file changes

- No frontend source or production application source was changed during this acceptance.
- No production SQLite database, production Chroma collection, existing uploads, evidence approvals, or Phase 9A assets were modified.
- The fresh isolated SQLite/Chroma/upload artifacts were retained at `/tmp/raara-phase8c-final-live-YPSIOU/` for review; they contain only disposable accounts and synthetic documents.
- Temporary acceptance runner scripts were removed after use.

**Final classification: PARTIALLY ACCEPTED.**
