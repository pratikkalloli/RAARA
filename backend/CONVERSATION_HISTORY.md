# RAARA Conversation History (Phase 6C)

## API

All endpoints require `Authorization: Bearer <access_token>`.

- `POST /api/conversations` creates a conversation owned by the authenticated user. The optional body may contain a title; omitted or blank titles become `New conversation`. Owner IDs in request bodies are rejected.
- `GET /api/conversations` lists only the authenticated user's conversations, newest activity first, with message counts.
- `GET /api/conversations/{conversation_id}` returns ordered messages and each assistant message's complete structured answer, including evidence, citations, sources, status, and validation data.
- `DELETE /api/conversations/{conversation_id}` deletes the owned conversation and its messages in one database transaction. It does not affect documents or ChromaDB.

To save a chat exchange, create a conversation and send its ID with `POST /api/chat`:

```json
{
  "question": "What is the attendance requirement?",
  "prompt_type": "C",
  "conversation_id": 12,
  "idempotency_key": "8d7d7d31-9b72-45db-9f68-8ca4f510d70c"
}
```

`conversation_id` is optional. Without it, `/api/chat` keeps its previous stateless behavior and does not create or persist a conversation. With it, the API validates ownership before retrieval or generation and atomically saves the question and final structured answer only after successful generation. Reuse the same `idempotency_key` UUID when retrying the same request; it prevents duplicate message pairs and returns the saved answer. Reusing a key for another question returns `409`.

Admins can access only their own conversations, like students. Admin role does not grant access to another user's history. Existing legacy messages with no conversation association remain preserved with `conversation_id = NULL`; they are not listed in any user's history.

## Migration and rollback

Startup creates the new `conversations` table and additively adds nullable `conversation_id`, `structured_response`, and `idempotency_key` columns to the existing `conversation_messages` table. The migration is safe to repeat and creates the supporting indexes. Existing message rows retain their IDs, roles, text, and timestamps; new columns remain null for legacy rows. No document, user, upload, or vector data is modified.

There is no automatic rollback because removing the added table/columns would discard conversation history. To roll back application code, keep the additive schema in place; legacy-compatible columns are harmless to earlier code. Do not drop the SQLite database or conversation tables as part of a routine rollback.
