# RAARA Phase 8E — Isolated Live Re-Acceptance Report

**Date:** 2026-11-15  
**Classification:** NOT RUN — required WSL preflight blocked  
**Overall result:** Not accepted; no live scenario was executed.

## Preflight outcome

The user-provided environment note says the WSL preflight passed. I independently attempted the required WSL checks in this execution context before setting up any acceptance resources. `wsl.exe` failed before starting a shell or Python process:

```text
Access is denied.
Error code: Wsl/E_ACCESSDENIED
```

As a result, this run could not verify Python 3.11.18, load `cl100k_base`, inspect runtime-loaded Gemini settings, or inspect/reuse a WSL acceptance script. The command was:

```powershell
wsl.exe -e bash -lc 'set -e; cd /mnt/c/prompt_mini_proj/backend; export TIKTOKEN_CACHE_DIR="$HOME/.cache/tiktoken"; printf "PYTHON="; ./.venv-wsl311/bin/python -V; ./.venv-wsl311/bin/python - <<"PY"
import os,tiktoken
enc=tiktoken.get_encoding("cl100k_base")
print("TOKENIZER_OK",len(enc.encode("RAARA isolated acceptance")),"CACHE_SET",os.environ.get("TIKTOKEN_CACHE_DIR"))
from app.core.config import settings
print("PROVIDER",settings.ai_provider)
print("CHAT_MODEL",settings.openai_chat_model if settings.ai_provider=="openai" else settings.gemini_chat_model)
print("EMBED_MODEL",settings.openai_embedding_model if settings.ai_provider=="openai" else settings.gemini_embedding_model)
print("EMBED_DIM",settings.gemini_embedding_dimensions)
print("GEMINI_CREDENTIAL_PRESENT",bool(settings.gemini_api_key))
PY'
```

Exit code: **1**. The failure is at `wsl.exe` startup; none of the Python statements ran. The existing Phase 8E implementation and prior acceptance reports were read. The targeted repair report records the original implementation status and tests. The prior live acceptance report is still a blocked/not-run report. No source files were modified.

The Phase 8D/8E live-acceptance script and WSL test fixtures were not executed or inspected further because the mandatory runtime preflight failed. No substitute Windows Python or new harness was used.

## Scenario results

All scenarios are **NOT RUN** because the required WSL/runtime preflight failed. No Gemini calls, API calls, test-account registration, synthetic PDF creation, or isolated acceptance storage setup occurred.

| Scenario | Setup and question | HTTP / answer status | Gemini called | Evidence, citation, and verifier outcome | Result |
|---|---|---|---|---|---|
| A — Follow-up after `NOT_FOUND` | Empty isolated index; `What is the official university definition of ISA?` followed in the same conversation by `Can you explain that further?` | None | No | No context, retrieval, or persistence diagnostics available | NOT RUN |
| B — General conversational context | `Explain the general difference between formative and summative assessment, without claiming a university-specific rule.` followed by `Can you give me an example of the first one?` | None | No | No interpreter, retrieval, or conversation diagnostics available | NOT RUN |
| C — Selected-document summary | Synthetic 13-page unverified PDF with >12 indexed chunks; explicitly selected; request: `Summarize the entire selected document in exactly 5 distinct bullet points.` | None | No | No authorization, chunk counts, hierarchical stages, coverage, citation identity, or page checks available | NOT RUN |
| C — Invalid/inaccessible selection | Invalid or unauthorized selected document ID | None | No | Authorization/scope-widening behavior not exercised | NOT RUN |
| D — Provenance-aware abstention | Synthetic/unverified attendance evidence; ask for the official university attendance eligibility requirement | None | No | No retrieval/provenance state, abstention, or citation diagnostics available | NOT RUN |
| E — Numerical regression: allocations | Synthetic examination source with ISA/ESA allocation 40/60; ask `According to this document, what are the ISA and ESA mark allocations?` | None | No | No evidence IDs/pages or numerical verifier result available | NOT RUN |
| E — Numerical regression: scores | Same synthetic source with individual scores 32/45; ask `What are the individual student's ISA and ESA scores?` | None | No | No evidence IDs/pages or numerical verifier result available | NOT RUN |

No HTTP status, prompt classification, response classification, selected document ID, ownership decision, indexed/processed chunk count, citation identity, or numerical verifier result exists for this attempt.

## Interpretation and limitations

- This report does not treat the user's prior statement that preflight passed as evidence that WSL is available to this execution. The command executed here returned `Wsl/E_ACCESSDENIED` before Python launched.
- No Gemini response was generated, so no conclusion can be drawn about conversational context, summary routing, provenance-aware abstention, citation correctness, or numerical checking after Phase 8E.
- Citation identity validation and semantic faithfulness were not tested. No semantic correctness claim is made.
- No retries were attempted. No application workaround or alternate runtime was used.

## Data and source protection

No SQLite, ChromaDB, upload, or disposable account was created for this run. Production SQLite, ChromaDB collections, uploads, user data, official evidence approvals, and Phase 9A assets were not accessed or modified. Application source and frontend files were not modified. The persistent tokenizer cache was not changed. No Gemini or OpenAI API calls were made; no API key was displayed or logged. The 204-test backend suite was not rerun.

## Next action

Run the same preflight in a WSL session where the existing Ubuntu distribution is accessible. If the WSL launch and tokenizer check pass in the execution environment used for acceptance, then the live scenarios may be run against newly isolated storage. This report does not claim acceptance.

## Repair follow-up — 2026-11-15

The later Phase 8E live acceptance results supplied for repair reported: general conversation and follow-up passed; synthetic PDF upload/indexing and cross-user rejection passed; whole-document summary failed with `NUMERICAL_REVIEW_INCOMPLETE` and citations from only the first six pages; official-policy abstention returned a generic intermediate-summary failure; ISA/ESA allocation returned HTTP 503 with invalid request interpretation; and the separate score answer was withheld by numerical verification.

This follow-up is implementation work only. The immediately preceding environment check returned `Wsl/E_ACCESSDENIED`; no additional WSL invocation was made during repair, in keeping with the no-repeat instruction. The required Python 3.11 regression and live Gemini acceptance were not run. No new HTTP outcomes are available. The historical results above remain unchanged and are not represented as rerun results.

Backend changes in this repair attempt are listed in `RAARA_PHASE8E_REPAIR_REPORT.md`. Newly added tests are not yet executed. The runtime acceptance status remains **NOT RUN**.

## Final live acceptance attempt — 2026-11-15

**Classification:** **BLOCKED — no live Gemini scenarios executed**  
**Phase 8E acceptance:** **PENDING**

### Infrastructure inspection

Searched the backend tree for Phase 8E/live acceptance scripts. No dedicated Phase 8E acceptance runner or existing harness covering these six scenarios was found. Existing files named for evaluation are offline benchmark/readiness tools, not the requested application API live acceptance runner. Reviewed this report, `RAARA_PHASE8E_REPAIR_REPORT.md`, and the route contracts for registration, conversation creation, PDF upload, and chat.

The current execution context has repeatedly failed to launch WSL with `Wsl/E_ACCESSDENIED`. In accordance with the instruction not to switch to another Python environment, no server, account, PDF, isolated store, or live API request was created here. No API key was read or exposed. No second acceptance framework was added.

### Current scenario results

These are outcomes for the requested final acceptance attempt, distinct from the historical repair outcomes summarized above.

| Scenario | Test input/setup | HTTP / application result | Provider | Storage isolation | Result |
|---|---|---|---|---|---|
| 1. Conversation and follow-up | General conversational question followed by a context-dependent follow-up in one conversation | No request made; no response/status available | Not called | No stores created | **NOT RUN** |
| 2. Whole-document summary | Synthetic PDF, exactly five distinct summary points | No upload or chat request made; coverage and citations unavailable | Not called | No stores created | **NOT RUN** |
| 3. ISA/ESA allocation | Synthetic PDF states fictional ISA 40% / ESA 60% allocation | No request made; no answer or citation available | Not called | No stores created | **NOT RUN** |
| 4. Separate scores | Same synthetic PDF states a separate individual score of 32/45 | No request made; no answer or citation available | Not called | No stores created | **NOT RUN** |
| 5. Unsupported official attendance rule | Ask for official attendance policy absent from the synthetic evidence | No request made; abstention not observed | Not called | No stores created | **NOT RUN** |
| 6. Cross-user selected-document access | Second disposable user selects first user’s uploaded document | No request made; expected access rejection not observed | Not called | No stores created | **NOT RUN** |

The user supplied the latest automated results: focused tests **75 passed**; full backend suite **374 passed, 1 failed**, with the sole failure `test_phase9a_assets_remain_byte_for_byte_unchanged` due to the known Phase 9A aggregate fingerprint mismatch. These are automated tests, not live acceptance. The Phase 9A test/assets/hash were not modified.

These test counts were supplied by the user and were not rerun in this execution. They are recorded as automated regression results, not evidence of live Gemini behavior.

### Exact Ubuntu procedure for manual live acceptance

The following procedure is source-audited below and supersedes earlier command assumptions in this report. It has **NOT been executed**. Run from Ubuntu WSL only after the distribution is available. It starts the actual FastAPI application with temporary SQLite, Chroma, and upload locations. The backend is launched with its working directory set to `backend`, which is how `SettingsConfigDict(env_file=".env")` locates the existing backend `.env`. The procedure removes inherited provider/key variables so the configured `AI_PROVIDER` and `GEMINI_API_KEY` come from that `.env`; it does not print the credential. Do not proceed if preflight fails or reports a provider/model/dimension different from the expected existing Gemini configuration.

### Source-verified API and configuration contracts

| Area | Verified contract |
|---|---|
| Settings | Module is `app.config`; import is `from app.config import settings`. The names `active_chat_model`, `active_embedding_model`, and `active_embedding_dimensions` are actual properties. `SettingsConfigDict(env_file=".env")` loads `.env` relative to the process working directory. |
| Environment variables | Pydantic settings fields map to `AI_PROVIDER`, `DATABASE_URL`, `CHROMA_PERSIST_DIR`, `UPLOAD_DIR`, `JWT_SECRET_KEY`, and `GEMINI_API_KEY`. `AI_PROVIDER=gemini` selects the Gemini implementation; the corrected procedure instead reads the existing `.env` setting and asserts it is Gemini. It does not override model names or dimensions. |
| Registration | `POST /api/auth/register`; JSON `{ "username": ..., "email": ..., "password": ... }`; password length 12–128. Creates and commits an active student immediately (no email or admin step). Returns a profile, not a token. |
| Login | `POST /api/auth/login`; JSON `{ "identifier": ..., "password": ... }`. `LoginResponse.access_token` is the bearer token. Commands store it only in shell variables and do not print it. |
| Conversation | `POST /api/conversations` accepts `{}` (all fields are optional; `title` defaults to null) and returns an integer `id`. Conversations are **not** automatically created by chat. Both chat calls must send the same numeric `conversation_id` to retain/persist history. |
| Chat | `POST /api/chat`; `question` required; optional `conversation_id` and `document_id` are positive integers (not UUIDs). Passing an owned `conversation_id` loads prior context and persists the exchange. The selected document field is `document_id`. |
| Upload | `POST /api/documents/upload`, multipart `file` required; accepted optional form fields include `document_name`, `document_type`, and `source_type` (also academic year/version/effective date). Upload and indexing are synchronous in `ingest_pdf`: it extracts, embeds, writes Chroma and commits before returning. Response includes both integer `id` and string numeric `document_id`, plus `page_count`, `chunk_count`, `processing_status`, and `verification_status`. `GET /api/documents` returns `vector_sync_status` and those counts/statuses. No sleep or polling is needed; inspect the post-upload document row and stop if it is not indexed/synced. |
| Cross-user selection | The chat route queries a selected document within the authenticated user’s accessible-document query. An inaccessible/missing selected `document_id` raises HTTP 404 with `The selected document was not found in your document library.` before chat service execution; chat does not drop the selection and broaden retrieval. |

The questioned old assumptions were source-checked: the settings import and property names are valid; `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` are valid environment names; an empty conversation object is accepted; `identifier` is the login field; the three listed upload fields are accepted; upload returns `document_id`; and chat accepts `question`, `conversation_id`, and `document_id`. The corrections are to validate all three storage paths before server startup, verify synchronous indexed/synced state through `GET /api/documents`, validate the 13-page fixture itself, and stop unless actual `chunk_count > 12`. No API route requires an arbitrary processing delay.

Terminal 1 — isolated server and synthetic fixture:

```bash
cd /mnt/c/prompt_mini_proj/backend
set -e
export TIKTOKEN_CACHE_DIR="$HOME/.cache/tiktoken"
# Force configuration to come from this backend's existing .env file.
unset AI_PROVIDER GEMINI_API_KEY OPENAI_API_KEY
RUN_DIR="$(mktemp -d /tmp/raara-phase8e-live-XXXXXX)"
printf 'Isolated run directory: %s\n' "$RUN_DIR"
export RAARA_RUN_DIR="$RUN_DIR"
export DATABASE_URL="sqlite:///$RUN_DIR/acceptance.db"
export CHROMA_PERSIST_DIR="$RUN_DIR/chroma"
export UPLOAD_DIR="$RUN_DIR/uploads"
export JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"

# Fail-closed preflight. It prints paths and non-secret model settings only.
./.venv-wsl311/bin/python - <<'PY'
import os
from pathlib import Path
import tiktoken
from sqlalchemy.engine import make_url
from app.config import settings
root = Path(os.environ["RAARA_RUN_DIR"]).resolve()
assert root.parent == Path("/tmp").resolve()
assert root.name.startswith("raara-phase8e-live-")
url = make_url(settings.database_url)
assert url.get_backend_name() == "sqlite", "Acceptance DB must be SQLite"
db_path = Path(url.database or "").resolve()
chroma_path = Path(settings.chroma_persist_dir).resolve()
upload_path = Path(settings.upload_dir).resolve()
for label, path in (("SQLite", db_path), ("Chroma", chroma_path), ("uploads", upload_path)):
    assert path != root and path.is_relative_to(root), f"{label} path escaped isolated RUN_DIR"
assert db_path == root / "acceptance.db"
assert chroma_path == root / "chroma"
assert upload_path == root / "uploads"
assert len({db_path, chroma_path, upload_path}) == 3, "Storage paths must be separate"
assert settings.ai_provider.strip().casefold() == "gemini", "Configured provider is not Gemini; stop"
assert settings.gemini_api_key, "Gemini credential is not configured in backend .env; stop"
cache = Path(os.environ["TIKTOKEN_CACHE_DIR"]).resolve()
assert cache.is_dir(), "Persistent tiktoken cache is unavailable"
encoding = tiktoken.get_encoding("cl100k_base")
assert encoding.decode(encoding.encode("RAARA offline tokenizer check")) == "RAARA offline tokenizer check"
print("provider:", settings.ai_provider)
print("chat model:", settings.active_chat_model)
print("embedding model:", settings.active_embedding_model)
print("embedding dimensions:", settings.active_embedding_dimensions)
print("Gemini credential configured:", bool(settings.gemini_api_key))
print("SQLite:", db_path)
print("Chroma:", chroma_path)
print("uploads:", upload_path)
print("tokenizer cache:", cache)
print("cl100k_base:", "PASS")
PY

# Create a clearly synthetic, non-authoritative 13-page PDF in the isolated run directory.
./.venv-wsl311/bin/python - "$RUN_DIR/RAARA_SYNTHETIC_NOT_OFFICIAL.pdf" <<'PY'
import sys
import pymupdf

path = sys.argv[1]
doc = pymupdf.open()
topics = [
    "Planning: a fictional learner reviews the term calendar before choosing activities.",
    "Formative assessment: a practice exercise gives feedback before a final evaluation.",
    "Assessment allocation: the fictional ISA share is 40% and ESA share is 60%.",
    "Individual result: Mira scored 32 out of 45 on one ISA examination; this is not an allocation.",
    "Progression: a learner reviews completed work and plans the next fictional module.",
    "Registration: the example records a learner's selected fictional study activities.",
    "Feedback: the learner uses comments to identify one improvement for the next exercise.",
    "Review: the learner checks completed tasks against a personal study plan.",
    "Support: the fictional example describes asking a tutor to clarify course material.",
    "Practice: the learner completes a short exercise and records what remains unclear.",
    "Reflection: the learner notes which study approach helped with the fictional topic.",
    "Preparation: the learner sets aside time to review material before an assessment.",
    "Summary: the learner records progress and a next step for the following term.",
]
for page_no in range(1, 14):
    page = doc.new_page()
    lines = [
        "SYNTHETIC TEST DOCUMENT — NOT OFFICIAL UNIVERSITY POLICY",
        f"Fictional section {page_no}: academic process demonstration.",
        topics[page_no - 1],
        "These examples are invented solely for testing RAARA and have no institutional authority.",
    ]
    # Repeat synthetic explanatory prose to ensure multi-chunk indexing while retaining page labels.
    lines += [f"Fictional detail {i}: section {page_no} supports planning, review, and feedback in this invented example." for i in range(1, 66)]
    remaining_height = page.insert_textbox(pymupdf.Rect(45, 40, 550, 790), "\n".join(lines), fontsize=8)
    assert remaining_height >= 0, f"Synthetic page {page_no} text overflowed; adjust only the fixture layout."
assert doc.page_count == 13, f"Expected 13 pages; got {doc.page_count}"
doc.save(path)
print("Synthetic fixture created:", path)
PY

./.venv-wsl311/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — disposable users and API scenarios. Requires Bash, `curl`, and `python3`. Paste the printed `RUN_DIR` when prompted. The helper below sends passwords and bearer tokens through stdin/config pipes, not curl's process arguments, output, or files.

```bash
cd /mnt/c/prompt_mini_proj/backend
set -e
read -r -p 'Paste the isolated RUN_DIR printed by Terminal 1: ' RUN_DIR
case "$RUN_DIR" in /tmp/raara-phase8e-live-*) ;; *) echo 'Unsafe RUN_DIR path; stop.' >&2; exit 2 ;; esac
test -d "$RUN_DIR" || { echo 'RUN_DIR does not exist; stop.' >&2; exit 2; }
BASE=http://127.0.0.1:8000
PDF="$RUN_DIR/RAARA_SYNTHETIC_NOT_OFFICIAL.pdf"
RUN_TAG="$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
U1="raara_live_${RUN_TAG}_a"
U2="raara_live_${RUN_TAG}_b"
MAIL1="$U1@example.invalid"
MAIL2="$U2@example.invalid"
PASS1="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
PASS2="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"

api_json() {
  local method="$1" url="$2" token="$3" payload="$4" config response
  config="$(printf 'url = "%s"\nrequest = "%s"\n' "$url" "$method")"
  if [ -n "$token" ]; then config+=$'\n'; config+="$(printf 'header = "Authorization: Bearer %s"\n' "$token")"; fi
  config+=$'\nheader = "Content-Type: application/json"\n'
  if [ -n "$payload" ]; then config+=$'data = "@-"\n'; fi
  if [ -n "$payload" ]; then
    response="$(printf '%s' "$payload" | curl --disable --silent --show-error --config <(printf '%s' "$config") --write-out $'\n%{http_code}')"
  else
    response="$(curl --disable --silent --show-error --config <(printf '%s' "$config") --write-out $'\n%{http_code}')"
  fi
  HTTP_STATUS="${response##*$'\n'}"
  HTTP_BODY="${response%$'\n'*}"
}

api_json GET "$BASE/api/health" "" ""; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
api_json GET "$BASE/api/health/ai" "" ""; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
printf -v BODY1 '{"username":"%s","email":"%s","password":"%s"}' "$U1" "$MAIL1" "$PASS1"
api_json POST "$BASE/api/auth/register" "" "$BODY1"; test "$HTTP_STATUS" = 201; printf 'user 1 registration HTTP %s\n' "$HTTP_STATUS"
printf -v BODY2 '{"username":"%s","email":"%s","password":"%s"}' "$U2" "$MAIL2" "$PASS2"
api_json POST "$BASE/api/auth/register" "" "$BODY2"; test "$HTTP_STATUS" = 201; printf 'user 2 registration HTTP %s\n' "$HTTP_STATUS"
printf -v BODY1 '{"identifier":"%s","password":"%s"}' "$U1" "$PASS1"
api_json POST "$BASE/api/auth/login" "" "$BODY1"; test "$HTTP_STATUS" = 200
TOKEN1="$(printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
printf -v BODY2 '{"identifier":"%s","password":"%s"}' "$U2" "$PASS2"
api_json POST "$BASE/api/auth/login" "" "$BODY2"; test "$HTTP_STATUS" = 200
TOKEN2="$(printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
unset BODY1 BODY2 PASS1 PASS2 HTTP_BODY

# Multipart upload config carries the token via process substitution, not argv.
UPLOAD_CONFIG="$(printf 'url = "%s/api/documents/upload"\nheader = "Authorization: Bearer %s"\nform = "file=@%s;type=application/pdf"\nform = "document_name=RAARA synthetic test only — not official policy"\nform = "document_type=synthetic_test"\nform = "source_type=synthetic_test"\n' "$BASE" "$TOKEN1" "$PDF")"
UPLOAD_RESPONSE="$(curl --disable --silent --show-error --config <(printf '%s' "$UPLOAD_CONFIG") --write-out $'\n%{http_code}')"
HTTP_STATUS="${UPLOAD_RESPONSE##*$'\n'}"; HTTP_BODY="${UPLOAD_RESPONSE%$'\n'*}"
test "$HTTP_STATUS" = 201; printf 'synthetic PDF upload HTTP %s\n' "$HTTP_STATUS"
DOC_ID="$(printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["document_id"])')"
printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:d.get(k) for k in ("document_id","verification_status","processing_status","page_count","chunk_count")})'
unset UPLOAD_CONFIG UPLOAD_RESPONSE HTTP_BODY

# Upload/indexing is synchronous; verify the final row instead of sleeping or polling.
api_json GET "$BASE/api/documents" "$TOKEN1" ""; test "$HTTP_STATUS" = 200
DOC_SUMMARY="$(printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; rows=json.load(sys.stdin); wanted=sys.argv[1]; d=next((r for r in rows if str(r["document_id"])==wanted), None); assert d is not None; print(json.dumps(d))' "$DOC_ID")"
printf '%s' "$DOC_SUMMARY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:d.get(k) for k in ("document_id","verification_status","processing_status","vector_sync_status","page_count","chunk_count")}); assert d["processing_status"]=="indexed" and d["vector_sync_status"]=="synced"; assert d["page_count"]==13; assert int(d["chunk_count"] or 0)>12, "STOP: add fictional PDF content and re-upload; do not change chunk settings"'
unset HTTP_BODY DOC_SUMMARY

api_json POST "$BASE/api/conversations" "$TOKEN1" '{}' ; test "$HTTP_STATUS" = 201
CONV_ID="$(printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
unset HTTP_BODY

# 1. Conversation and context-dependent follow-up in the same persisted conversation.
printf -v BODY1 '{"question":"Explain the general difference between formative and summative assessment without claiming a university-specific rule.","conversation_id":%s}' "$CONV_ID"
api_json POST "$BASE/api/chat" "$TOKEN1" "$BODY1"; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
printf -v BODY1 '{"question":"Can you give me an example of the first one?","conversation_id":%s}' "$CONV_ID"
api_json POST "$BASE/api/chat" "$TOKEN1" "$BODY1"; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
api_json GET "$BASE/api/conversations/$CONV_ID" "$TOKEN1" ""; test "$HTTP_STATUS" = 200
printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("persisted messages:",len(d["messages"]))'
unset BODY1 HTTP_BODY

# 2. Whole-document summary; manually count five distinct numbered points and inspect coverage/pages.
printf -v BODY1 '{"question":"Summarize the entire selected synthetic document in exactly five distinct points.","document_id":%s}' "$DOC_ID"
api_json POST "$BASE/api/chat" "$TOKEN1" "$BODY1"; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
unset BODY1 HTTP_BODY

# 3. Allocation and 4. Separate individual score.
printf -v BODY1 '{"question":"According to this synthetic document, what are the ISA and ESA allocation percentages? Distinguish allocations from an individual score.","document_id":%s}' "$DOC_ID"
api_json POST "$BASE/api/chat" "$TOKEN1" "$BODY1"; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
printf -v BODY1 '{"question":"What separate individual ISA examination score is stated, and what is its denominator? Do not confuse it with the allocation percentages.","document_id":%s}' "$DOC_ID"
api_json POST "$BASE/api/chat" "$TOKEN1" "$BODY1"; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
unset BODY1 HTTP_BODY

# 5. Unsupported official attendance-policy question.
printf -v BODY1 '{"question":"What is the official university attendance requirement?","document_id":%s}' "$DOC_ID"
api_json POST "$BASE/api/chat" "$TOKEN1" "$BODY1"; test "$HTTP_STATUS" = 200; printf '%s\n' "$HTTP_BODY"
unset BODY1 HTTP_BODY

# 6. Cross-user document selection; expect safe 404 without document text.
printf -v BODY1 '{"question":"Summarize this document.","document_id":%s}' "$DOC_ID"
api_json POST "$BASE/api/chat" "$TOKEN2" "$BODY1"; test "$HTTP_STATUS" = 404
printf '%s' "$HTTP_BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); expected="The selected document was not found in your document library."; assert d.get("detail")==expected; print("cross-user safe error:",expected)'
unset TOKEN1 TOKEN2 BODY1 HTTP_BODY
```

The server's `/api/health/ai` response must report provider `gemini`; the safe preflight confirms the configured Gemini model/embedding and that the Gemini credential is present without printing it. `OPENAI_API_KEY` is unset. A successful chat operation from this actual configured application therefore exercises its Gemini adapter; inspect server logs only for safe exception type/status and never dump environment variables or request headers. Manually check that returned citations identify the uploaded synthetic document and its actual page metadata. Scenario 2 passes only if five distinct supported points are returned, the document is indexed with more than 12 chunks, and coverage/semantic limitations are explicit; citation identity alone does not establish semantic faithfulness. Scenario 5 passes only if status is `NOT_FOUND`, no official rule/value is invented, and the response states evidence is insufficient. Scenario 6 passes only on access rejection without document content. After recording results, stop the server with Ctrl+C; preserve the temporary directory until report review. No cleanup command is provided here.

### Scenario acceptance criteria

1. **Conversation:** both `/api/chat` calls return HTTP 200 and status `CONVERSATIONAL`; the second answer resolves “the first one” as formative assessment from the same conversation context. No academic citations are expected.
2. **Whole-document summary:** HTTP 200, answer contains exactly five distinct numbered points, uses original document citations with valid pages, includes coverage metadata, and status is not falsely `SUPPORTED` when semantic faithfulness remains unverified (the expected honest status is `PARTIALLY_SUPPORTED`). Citation identity alone is not a semantic-faithfulness pass.
3. **Allocation:** HTTP 200; answer correctly distinguishes 40% ISA allocation and 60% ESA allocation, cites the synthetic evidence page, and the numerical verifier does not confuse values with the separate score.
4. **Individual score:** HTTP 200; answer identifies 32 out of 45 as an individual ISA score, not an allocation percentage, with valid source/page evidence and numerical verification.
5. **Unsupported official rule:** HTTP 200 with status `NOT_FOUND`, no invented attendance threshold, no fabricated citation, and an explanation that synthetic/unverified evidence cannot establish an official university rule.
6. **Cross-user access:** HTTP 404 with the exact non-disclosing detail checked above; response must contain no document text. A 200, broader search, or content-bearing error is FAIL.

For any live-call failure, capture HTTP status, exception type, safe provider error code/message, and model name only. Never capture request headers, environment dumps, tokens, or keys. Do not retry a failed Gemini request blindly.

Do not report any of these as passing until actually run and reviewed. The commands use a temporary database, Chroma directory, uploads path, synthetic test PDF, and two disposable accounts. The existing configured Gemini provider/model is retained; OpenAI is not selected.

### Source-audit completion

Inspected `backend/app/config.py`, `backend/app/main.py`, `backend/app/routes/auth.py`, `backend/app/schemas/auth.py`, `backend/app/routes/conversations.py`, `backend/app/schemas/conversations.py`, `backend/app/routes/chat.py`, `backend/app/routes/documents.py`, `backend/app/schemas/documents.py`, `backend/app/services/ingestion.py`, `backend/app/services/embeddings.py`, `backend/app/services/chat.py`, `backend/app/services/conversations.py`, `backend/app/services/generator.py`, and `backend/app/services/vector_store.py`. Confirmed `backend/.env` exists by checking path existence only; its contents and credentials were not read. `AI_PROVIDER` and `GEMINI_API_KEY` are intentionally unset in Terminal 1 so the existing backend `.env` supplies them; the isolated path variables and disposable `JWT_SECRET_KEY` override only their corresponding settings. `create_embedding_service()` and `create_answer_generator()` both select Gemini based on the loaded provider setting. The preflight asserts provider Gemini, credential presence, cached tokenizer availability, SQLite backend, and three distinct storage locations under the fresh temporary run root before Uvicorn starts.

The report's previous Terminal 2 examples that placed password or bearer values directly in `curl -d`/`-H` arguments have been replaced with a Bash helper that streams JSON on stdin and authorization through a curl config process substitution. The curl commands use `--disable` to ignore any user `.curlrc`; curl supports config files and `@-` request data from stdin as documented in the [official curl manual](https://curl.se/docs/manpage.html). Tokens/passwords are kept in shell variables and are not printed, written to response files, or placed in curl's argv. The multipart upload also uses a curl config stream. Cross-user verification asserts the source-confirmed HTTP 404 detail exactly, without displaying any document content.

**Audit status:** source contracts and the corrected procedure are **SOURCE-REVIEWED**; commands are **NOT EXECUTED**. No live Gemini request was made. No application source, frontend, production data, official evidence, Phase 9A assets, evaluation data, or expected fingerprint was changed by this command audit. The user's reported focused 75-pass and full-suite 374-pass/1-fail results remain attributed to the user and were not rerun here. Phase 8E live acceptance remains **PENDING**.

