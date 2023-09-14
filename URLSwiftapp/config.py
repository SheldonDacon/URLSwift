# shortener_app/config.py

from pydantic import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    env_name: str = "Local"
    base_url: str = "http://localhost:8000"
    db_url: str = "sqlite:///./shortener.db"

    class Config:
        env_file = "URLshortener.env"


@lru_cache (maxsize=None)
def get_settings() -> Settings:
    settings = Settings()
    print(f"Loading settings for: {settings.env_name}")
    return settings
