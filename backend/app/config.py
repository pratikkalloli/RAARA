from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "RAARA"
    environment: str = "development"
    database_url: str = "sqlite:///./raara.db"
    groq_api_key: str | None = None
    jwt_secret_key: str | None = None
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    groq_chat_model: str | None = None
    groq_request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    groq_max_retries: int = Field(default=2, ge=0, le=5)
    groq_max_output_tokens: int = Field(default=1200, ge=128, le=4096)
    ai_provider: str = "groq"
    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = Field(default=384, ge=384, le=384)
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "raara_documents_groq_local_384"
    max_upload_size_mb: int = 20
    upload_dir: str = "../documents/raw"
    embedding_batch_size: int = 100
    chunk_size_tokens: int = 700
    chunk_overlap_tokens: int = 100
    retrieval_top_k: int = 5
    retrieval_min_relevance: float = 0.35
    conversation_history_max_messages: int = Field(default=6, ge=0, le=20)
    conversation_history_max_chars: int = Field(default=6000, ge=0, le=20000)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def active_embedding_model(self) -> str:
        return self.embedding_model

    @property
    def active_embedding_dimensions(self) -> int:
        return self.embedding_dimensions

    @property
    def active_embedding_collection_name(self) -> str:
        """Use an isolated collection for local 384-dimensional vectors."""
        return "raara_documents_groq_local_384"

    @property
    def active_chat_model(self) -> str:
        if not self.groq_chat_model or not self.groq_chat_model.strip():
            raise ValueError("GROQ_CHAT_MODEL is required; set it to a model available to your Groq account.")
        return self.groq_chat_model.strip()

    @property
    def active_api_key(self) -> str | None:
        if self.groq_api_key is None:
            return None
        normalized = self.groq_api_key.strip()
        return normalized or None

    @property
    def active_embedding_provider(self) -> str:
        return "local"

    def validate_runtime_configuration(self, *, require_credentials: bool = False) -> None:
        if self.ai_provider.strip().casefold() != "groq":
            raise ValueError("AI_PROVIDER must be 'groq'. Gemini and OpenAI providers are not active.")
        if self.embedding_provider.strip().casefold() != "local":
            raise ValueError("EMBEDDING_PROVIDER must be 'local'.")
        if self.embedding_model != "sentence-transformers/all-MiniLM-L6-v2":
            raise ValueError("EMBEDDING_MODEL must be sentence-transformers/all-MiniLM-L6-v2.")
        if self.embedding_dimensions != 384:
            raise ValueError("EMBEDDING_DIMENSIONS must be 384 for the configured local model.")
        _ = self.active_chat_model
        if require_credentials and not self.active_api_key:
            raise ValueError("GROQ_API_KEY is required. Add a valid Groq API key to backend/.env.")

settings = Settings()
