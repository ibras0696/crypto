"""Configuration module: loads environment variables and constants.
Use pydantic-settings for typed env management.
"""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "CryptoSwap"
    DEBUG: bool = True
    SECRET_KEY: str = "CHANGE_ME"  # replace in prod
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "crypto"
    POSTGRES_USER: str = "crypto"
    POSTGRES_PASSWORD: str = "crypto"

    REDIS_URL: str = "redis://redis:6379/0"

    BINANCE_PUBLIC_URL: AnyUrl | None = "https://api.binance.com"  # base public REST endpoint
    RATE_CACHE_TTL: int = 30  # seconds for Redis rate cache
    # KYC related limits (very simplified, per order and per day total amount_from across all currencies)
    UNVERIFIED_ORDER_MAX: float = 100.0
    UNVERIFIED_DAILY_VOLUME_MAX: float = 500.0
    ALLOWED_RATE_QUOTES: list[str] = ["USDT"]  # quotes we construct default pairs with

    CORS_ORIGINS: List[str] = []
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 120
    METRICS_ENABLED: bool = True


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
