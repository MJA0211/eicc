from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EICC_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./eicc.db"
    demo_mode: bool = True
    secure_cookies: bool = False
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"]
    admin_email: str = ""
    admin_password: str = ""
    session_hours: int = 8


@lru_cache
def settings() -> Settings:
    return Settings()
