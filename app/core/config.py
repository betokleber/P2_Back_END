import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/eventos_db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "prod-secret-placeholder")
    PORT: int = int(os.getenv("PORT", 8000))

settings = Settings()