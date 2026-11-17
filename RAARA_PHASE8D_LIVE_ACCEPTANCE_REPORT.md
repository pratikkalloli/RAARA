# RAARA Phase 8D — Controlled Live Gemini Acceptance

## Overall result

**PARTIALLY ACCEPTED.** Live Gemini requests, uploads, retrieval, and authentication completed successfully in an isolated acceptance environment. The numerical distinction scenario passed. Conversation-context behavior, whole-document summary routing, and the required specificity of the evidence-aware abstention did not satisfy the acceptance criteria. No application changes or retries were made.

## Environment and preflight

- WSL Python: **3.11.18**, `/mnt/c/prompt_mini_proj/backend/.venv-wsl311/bin/python`.
- Persistent tokenizer cache: `/home/pratik_kalloli/.cache/tiktoken`.
- `TIKTOKEN_CACHE_DIR` was exported in the WSL shell. A fresh network-isolated Python process loaded `cl100k_base` and passed an encode/decode round trip.
- Provider: `gemini`.
- Chat model: `gemini-3.5-flash-lite`.
- Embedding model: `gemini-embedding-001`.
- Embedding dimensions: **768**.
- Configured provider credential: present; its value was never printed or logged.
- The prior backend regression result remains **189 passed** per the Phase 8D implementation report. It was not rerun, as directed.

The actual FastAPI application and endpoints were exercised through an in-process `TestClient`; model and embedding requests were live Gemini calls. No frontend or application source was modified.

## Isolated storage and synthetic documents

All acceptance storage was created under this fresh temporary root:

- SQLite: `/tmp/raara-phase8d-live-zpvql928/acceptance.db`
- ChromaDB: `/tmp/raara-phase8d-live-zpvql928/chroma`
- Uploads: `/tmp/raara-phase8d-live-zpvql928/uploads`

A disposable student account and conversation were used. Password and bearer token were kept in process memory and not recorded. No second account was created, so the optional cross-user selection test was not performed.

| Synthetic PDF | Pages | Indexed chunks | Status | SHA-256 |
|---|---:|---:|---|---|
| `SYNTHETIC TEST ONLY - NOT OFFICIAL UNIVERSITY POLICY - Exam Pattern` | 2 | 4 | Indexed, unverified, synced | `b97443c56db4b9fb34befbe89b8b89520e3879ddf9b4037b4f65a7b075e2eff9` |
| `SYNTHETIC TEST ONLY - NOT OFFICIAL UNIVERSITY POLICY - Attendance Workbook` | 13 | 27 | Indexed, unverified, synced | `169b5af84c22cf80ade789fbc3a5ac6b8c4c284068208ac59b963d0bd2a9b1d4` |

Every PDF page was labeled `SYNTHETIC TEST ONLY — NOT OFFICIAL UNIVERSITY POLICY`. The isolated document registry continued to show both documents as `unverified`; neither entered an official evidence registry.

## HTTP results

Every request completed with the listed status; there were no HTTP errors or provider exceptions.

| Request | Status |
|---|---:|
| `GET /api/health` | 200 |
| `GET /api/health/ai` | 200 |
| Disposable student registration | 201 |
| Disposable student login | 200 |
| Conversation creation | 201 |
| Conversation first turn | 200 |
| Conversation follow-up | 200 |
| Persisted conversation read | 200 |
| Synthetic exam PDF upload | 201 |
| ISA/ESA allocation question | 200 |
| Individual score question | 200 |
| Synthetic attendance PDF upload | 201 |
| Whole-document summary request | 200 |
| Official attendance requirement question | 200 |
| Isolated document list | 200 |

## Scenario A — Conversation context

Prompts used:

1. `What does the term ISA mean in this discussion?`
2. `Can you explain that further?`

**Result: FAILED acceptance criterion.**

The first answer was `NOT_FOUND`: “I couldn't provide a sufficiently supported answer from the available retrieved documents.” Diagnostics show the first turn was sent through retrieval, which returned `empty_index` with zero passages. The second answer was: “Could you please specify what 'that' refers to so I can provide more details?” It did not provide the requested explanation.

Sanitized history diagnostics confirm that the second-turn interpreter received two chronological messages with roles `user`, `assistant`; both the preceding user question and the preceding assistant answer were present. The second turn made no retrieval call. The model was given history, but the first turn had not established a substantive ISA explanation, and the follow-up still requested clarification.

Persistence passed: the same conversation contained four messages in order (`user`, `assistant`, `user`, `assistant`), with both questions and both answers saved.

## Scenario B — Numerical factual accuracy

### Mark allocations

Prompt:

`According to this document, what are the ISA and ESA mark allocations? Do not confuse allocations with the individual student's scores.`

**Result: PASS.** Response status was `PARTIALLY_SUPPORTED`, appropriately reflecting unverified source material. The answer distinguished the allocations as **ISA 40 marks** and **ESA 60 marks** and said the source was unverified and not confirmed as official policy. Numerical review returned two `SUPPORTED` checks, and the returned evidence IDs matched the actual retrieved passage IDs. Both citations resolved to Chroma metadata with matching document identity, name, section, page, and unverified status; cited pages were 1 and 2.

### Individual scores

Prompt:

`What are the individual student's ISA and ESA scores?`

**Result: PASS.** Response status was `PARTIALLY_SUPPORTED`. The answer identified **ISA 32 marks** and **ESA 45 marks** as the individual learner's scores and kept them distinct from the maximum allocations. Numerical review returned two `SUPPORTED` checks with evidence IDs present in the cited context. The citation resolved to the actual synthetic exam document on page 2, in the `Separate individual learner score record` section, and remained labeled unverified.

The two tests therefore distinguished the allocated maxima from the separate learner scores. Citation identity and page checks passed for all returned evidence in both answers. `semantic_faithfulness` remains `NOT_VERIFIED`; the numerical checker is model-assisted and is not a general proof of answer correctness.

## Scenario C — Whole-document summary

Prompt:

`Summarize the entire document in exactly 5 distinct bullet points.`

**Result: FAILED acceptance criterion.** The endpoint returned HTTP 200 but answered: “Which of the available documents would you like me to summarize?” It returned `NOT_FOUND`, zero bullets, zero citations, and no coverage statement.

The selected accessible document had 13 pages and **27 indexed chunks**, exceeding the direct summarization limit of 12. However, diagnostics recorded no full-document chunk read and no summarization generation stages. Thus the request stopped before hierarchical summarization; full-document inclusion, distinctness, numerical accuracy, citations, and coverage could not be evaluated. The sanitized harness did not retain the model's raw structured interpretation, so the precise interpretation field that led to clarification is unknown. The API did not produce an incorrect summary, but it did not perform the requested one.

## Scenario D — Evidence-aware abstention

Prompt:

`What is the official university requirement for attendance eligibility in examinations?`

**Result: PARTIAL.** The response had status `NOT_FOUND` and made no official attendance claim. It returned no evidence or citations, so it did not fabricate source metadata. Its answer was only: “I couldn't provide a sufficiently supported answer from the available retrieved documents.” It did **not** explain that the available attendance material was synthetic and unverified, as required.

Retrieval did return five passages from the unverified synthetic attendance workbook (pages 2, 4, 8, 9, and 13). The final response had citation status `FAILED` and issue `INSUFFICIENT_RETRIEVED_EVIDENCE`, with no evidence items. The insufficiency status was safe, but the explanation did not distinguish synthetic evidence from official university authority.

## Automated tests versus live requests

- **Prior automated mocked backend suite:** 189 passed, as recorded in the Phase 8D implementation report; not rerun for this acceptance.
- **Live Gemini generation/embedding:** used for the requests above. No live provider error occurred.
- **Live API scenarios:** actual statuses and outcomes are recorded by scenario above.
- **Browser acceptance:** not performed; this task exercised FastAPI routes through `TestClient` and did not include browser criteria.

## Limitations and data safety

- Overall acceptance is partial because the conversation follow-up failed to resolve, the summary request did not enter the full-document pipeline, and the abstention explanation omitted the synthetic/unverified limitation.
- The optional cross-user ownership test was not run. Ownership enforcement was not weakened or bypassed.
- Numerical checking is model-assisted. Citation identity being valid does not establish semantic faithfulness for all claims.
- No speculative retries or code patches were made after observing failures.
- Production SQLite, production ChromaDB, production uploads, official evidence approvals, and Phase 9A assets were not used or modified. All created database, vector, and upload data belongs to the isolated `/tmp/raara-phase8d-live-zpvql928` acceptance root.
- No OpenAI calls were made. No API credential, disposable password, bearer token, or private document content was placed in diagnostics or this report.
