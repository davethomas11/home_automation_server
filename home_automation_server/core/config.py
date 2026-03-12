"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/home_automation_server.db"
    log_level: str = "INFO"
    # Scan timeout in seconds
    scan_timeout: float = 5.0


settings = Settings()

