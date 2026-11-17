from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def migrate_document_schema(bind: Engine | Connection | None = None) -> None:
    """Add Phase 2 document fields to existing SQLite databases without losing rows."""
    target = bind or engine
    if target.dialect.name != "sqlite":
        return

    additions = {
        "document_name": "VARCHAR(255) NOT NULL DEFAULT ''",
        "document_type": "VARCHAR(64) NOT NULL DEFAULT 'policy'",
        "academic_year": "VARCHAR(32)",
        "version": "VARCHAR(32) NOT NULL DEFAULT '1'",
        "effective_date": "VARCHAR(32)",
        "source_type": "VARCHAR(64) NOT NULL DEFAULT 'uploaded'",
        "storage_path": "TEXT",
        "page_count": "INTEGER",
        "chunk_count": "INTEGER",
        "vector_sync_status": "VARCHAR(16) NOT NULL DEFAULT 'synced'",
        "uploaded_by_user_id": "INTEGER REFERENCES users(id)",
        "reviewed_by_user_id": "INTEGER REFERENCES users(id)",
        "reviewed_at": "DATETIME",
        "review_note": "TEXT",
    }
    with target.begin() as connection:
        if "documents" not in inspect(connection).get_table_names():
            return
        columns = {column["name"] for column in inspect(connection).get_columns("documents")}
        for name, declaration in additions.items():
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE documents ADD COLUMN {name} {declaration}")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_documents_uploaded_by_user_id ON documents (uploaded_by_user_id)"
        )
        if "filename" in columns:
            connection.execute(text("UPDATE documents SET document_name = filename WHERE document_name = ''"))


def migrate_user_schema(bind: Engine | Connection | None = None) -> None:
    """Create the users table if missing without changing any existing tables or rows."""
    from app.database.models import User

    User.__table__.create(bind=bind or engine, checkfirst=True)


def migrate_conversation_schema(bind: Engine | Connection | None = None) -> None:
    """Add conversation ownership and response fields without rewriting legacy messages."""
    target = bind or engine
    if target.dialect.name != "sqlite":
        return

    from app.database.models import Conversation

    Conversation.__table__.create(bind=target, checkfirst=True)
    additions = {
        "conversation_id": "INTEGER REFERENCES conversations(id) ON DELETE CASCADE",
        "structured_response": "JSON",
        "idempotency_key": "VARCHAR(36)",
    }
    with target.begin() as connection:
        if "conversation_messages" not in inspect(connection).get_table_names():
            return
        columns = {column["name"] for column in inspect(connection).get_columns("conversation_messages")}
        for name, declaration in additions.items():
            if name not in columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE conversation_messages ADD COLUMN {name} {declaration}"
                )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_conversation_messages_conversation_created "
            "ON conversation_messages (conversation_id, created_at, id)"
        )
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_messages_conversation_idempotency_key "
            "ON conversation_messages (conversation_id, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL AND role = 'user'"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS trg_conversation_messages_role_insert "
            "BEFORE INSERT ON conversation_messages "
            "WHEN NEW.role NOT IN ('user', 'assistant') "
            "BEGIN SELECT RAISE(ABORT, 'conversation message role must be user or assistant'); END"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS trg_conversation_messages_role_update "
            "BEFORE UPDATE OF role ON conversation_messages "
            "WHEN NEW.role NOT IN ('user', 'assistant') "
            "BEGIN SELECT RAISE(ABORT, 'conversation message role must be user or assistant'); END"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS trg_conversation_messages_idempotency_insert "
            "BEFORE INSERT ON conversation_messages "
            "WHEN NEW.idempotency_key IS NOT NULL AND NEW.conversation_id IS NULL "
            "BEGIN SELECT RAISE(ABORT, 'idempotency key requires a conversation'); END"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER IF NOT EXISTS trg_conversation_messages_idempotency_update "
            "BEFORE UPDATE OF idempotency_key, conversation_id ON conversation_messages "
            "WHEN NEW.idempotency_key IS NOT NULL AND NEW.conversation_id IS NULL "
            "BEGIN SELECT RAISE(ABORT, 'idempotency key requires a conversation'); END"
        )
