from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    frontend_origin: str = "http://localhost:5173"
    indexer_chain_id: int = 11155111
    sepolia_rpc_url: str | None = None
    prediction_market_address: str | None = None
    prediction_market_deployment_block: int = Field(default=0, ge=0)
    indexer_confirmation_depth: int = Field(default=2, ge=0)
    indexer_poll_interval_seconds: float = Field(default=5.0, gt=0)
    # Alchemy's Sepolia eth_getLogs endpoint rejects wider ranges on the
    # configured plan. Ten-block batches work consistently and remain
    # overrideable for providers with larger limits.
    indexer_block_batch_size: int = Field(default=10, ge=1, le=10_000)
    indexer_rpc_timeout_seconds: float = Field(default=10.0, gt=0)
    indexer_rpc_max_attempts: int = Field(default=3, ge=1, le=10)
    indexer_rpc_backoff_seconds: float = Field(default=0.5, ge=0)
    prediction_market_abi_path: str | None = None
    registrar_private_key: SecretStr | None = None
    proposer_private_key: SecretStr | None = None
    signer_confirmation_depth: int = Field(default=2, ge=0)
    signer_poll_interval_seconds: float = Field(default=5.0, gt=0)
    pandascore_use_approved: bool = False
    pandascore_api_token: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
