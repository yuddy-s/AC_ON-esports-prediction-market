from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    frontend_origin: str = "http://localhost:5173"
    indexer_chain_id: int = 11155111
    sepolia_rpc_url: str | None = None
    prediction_market_address: str | None = None
    prediction_market_deployment_block: int = Field(default=0, ge=0)
    indexer_confirmation_depth: int = Field(default=3, ge=0)
    indexer_poll_interval_seconds: float = Field(default=5.0, gt=0)
    indexer_block_batch_size: int = Field(default=500, ge=1, le=10_000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
