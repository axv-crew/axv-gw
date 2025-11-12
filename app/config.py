"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- internal signer ---
    INTERNAL_SIGNER_TOKEN: str = ""
    # --- HMAC settings ---
    AXV_HMAC_SECRET: str = ""
    AXV_HMAC_DRIFT_S: int = 300
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(env_prefix="AXV_GW_")

    # Stub data configuration
    stub_path: str = "app/data/status.stub.json"

    # Cache configuration
    cache_ttl_seconds: int = 60

    # External call configuration
    request_timeout_seconds: float = 2.0
    request_max_retries: int = 1

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"


settings = Settings()
