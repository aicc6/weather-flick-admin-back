import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Admin
    ADMIN_EMAIL: str = "admin@weatherflick.com"
    ADMIN_PASSWORD: str = "admin123"

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]

    class Config:
        env_file = ".env"


settings = Settings()
