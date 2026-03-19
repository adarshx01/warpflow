from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str = ""

    # JWT
    SECRET_KEY: str
    SECRETS_ENCRYPTION_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/google/callback"


    COOKIE_DOMAIN: str = "localhost"
    COOKIE_SECURE: bool = False  # Here i Need to Set True in production (HTTPS)

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # S3 Storage
    S3_ENDPOINT_URL: str | None = None  # For MinIO, e.g. "http://localhost:9000"
    S3_BUCKET_NAME: str = "warpflow-storage"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"

    # ML Settings
    ML_MAX_DATASET_ROWS: int = 100000
    ML_MAX_FILE_SIZE_MB: int = 50

    # ChromaDB
    CHROMADB_PATH: str = "./storage/chromadb"

    # OpenAI Embeddings
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
