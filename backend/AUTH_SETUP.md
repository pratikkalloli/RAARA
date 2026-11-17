# RAARA Authentication and Document Review Setup (Phase 6A/6B)

## Configuration

Authentication requires `JWT_SECRET_KEY` with at least 32 bytes of random material. The value in `.env.example` is a rejected placeholder. Keep the real key in an untracked `.env` file or an environment variable; do not commit it or put it in application logs.

From `backend`, create `.env` only if it does not already exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Generate a secret without printing it to the terminal and set it for the current PowerShell process:

```powershell
$env:JWT_SECRET_KEY = (& .\.venv311\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
```

Keep that shell open while running the backend. For persistent deployments, supply `JWT_SECRET_KEY` through the deployment secret manager. To clear the current shell value:

```powershell
Remove-Item Env:JWT_SECRET_KEY
```

`ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 30 and accepts values from 1 through 1440.

## Database migration

Application initialization calls SQLAlchemy `create_all()` and idempotent document/user migrations. Phase 6B adds nullable uploader/reviewer IDs, review timestamp/note, and a vector synchronization status to `documents`; existing rows receive null ownership/audit fields and `synced` as the initial vector state. Existing records, PDFs, and Chroma entries are retained. Restarting the backend applies the additive columns. There is no data rollback step because no existing table or row is dropped. Removing these columns or the users table manually is not a normal rollback.

## Create the first administrator

From `backend`, with `JWT_SECRET_KEY` configured in the current shell and the database URL set as usual:

```powershell
.\.venv311\Scripts\python.exe -m app.scripts.bootstrap_admin
```

The command prompts for username, email, and password; password input is hidden and requested twice. It refuses to run if an administrator already exists. It uses the same `DATABASE_URL` configuration as the application and stores an Argon2 hash only. There is no public administrator registration endpoint and application startup does not create an administrator.

## Authentication API

Student registration (role is assigned by the server):

```json
POST /api/auth/register
{
  "username": "student.one",
  "email": "student@example.edu",
  "password": "a-long-unique-password"
}
```

Login accepts either username or email in `identifier`:

```json
POST /api/auth/login
{
  "identifier": "student@example.edu",
  "password": "a-long-unique-password"
}
```

The response contains `access_token`, `token_type`, `expires_in`, and a safe user profile. Use `Authorization: Bearer <access_token>` with `GET /api/auth/me`. Public registration rejects extra fields such as `role`.

## Document access and review (Phase 6B)

- `GET /api/documents` requires a bearer token. Students see only documents they uploaded; administrators can see all documents. An optional `verification_status` query parameter accepts `unverified`, `verified`, or `rejected`.
- `POST /api/documents/upload` now requires a bearer token and assigns ownership from the authenticated user. Client-supplied uploader IDs are not accepted.
- `POST /api/chat` now requires a bearer token. Student retrieval is scoped to that student's uploaded documents; administrator retrieval can use all indexed documents. The chat JSON body and response shape are unchanged.
- `GET /api/admin/documents/pending` requires an administrator token and lists indexed documents awaiting review.
- `POST /api/admin/documents/{document_id}/verification` accepts `{"decision":"verified"|"rejected","review_note":"optional"}` and requires an administrator token.
- If vector metadata synchronization fails, the SQL decision remains visible with `vector_sync_status: "pending"`, chat retrieval excludes the document, and the response is 503. Retry with `POST /api/admin/documents/{document_id}/verification/retry-sync`.

Only an administrator's review status is recorded. A `verified` state means internally reviewed; it does not prove that a university officially issued or authenticated the document. Rejected documents are excluded from retrieval, and unverified evidence retains its existing warning.

Conversation persistence, ownership, endpoints, and migration behavior are documented in [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md).
