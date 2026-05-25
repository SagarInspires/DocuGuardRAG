from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuGuard RAG"

    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"

    chunk_size: int = 500
    chunk_overlap: int = 80

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_db_dir: str = "data/chroma_db"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash-lite"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()