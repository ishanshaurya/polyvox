from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POLYVOX_", env_file=".env", extra="ignore")

    # Local workspaces only — not a permanent multi-tenant media vault
    data_root: str = "./.polyvox_data"
    default_retention_days: int = 14
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
