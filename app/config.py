# app/config.py
"""Global settings for AXV Gateway.

Ten moduł łączy:
- stare potrzeby gateway'a (log_level itp.),
- nowe ustawienia dla K4 AXV Status Endpoint.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings for AXV Gateway."""

    # --- Logging / Environment ---
    log_level: str = "INFO"
    environment: str = "local"  # np. local / stage / prod

    # --- K4: AXV Status Endpoint ---
    # URL healthz gateway'a (sam siebie)
    gateway_healthz_url: str = "http://127.0.0.1:8000/axv/healthz"
    # URL healthz n8n (puste = wyłączone sprawdzanie)
    n8n_healthz_url: str = ""
    # Timeout dla checków (sekundy)
    healthcheck_timeout: float = 2.0

    model_config = SettingsConfigDict(
        env_prefix="AXV_",          # AXV_GW_HEALTHZ_URL itd.
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instancja używana w całej appce
settings = Settings()
