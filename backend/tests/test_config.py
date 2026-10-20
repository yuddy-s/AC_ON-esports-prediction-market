from pathlib import Path

from app.config import Settings


def test_default_confirmation_depth_is_two(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("INDEXER_CONFIRMATION_DEPTH", raising=False)

    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'config.db'}",
        _env_file=None,
    )

    assert settings.indexer_confirmation_depth == 2
    assert settings.indexer_rpc_timeout_seconds == 10
    assert settings.indexer_rpc_max_attempts == 3
    assert settings.indexer_rpc_backoff_seconds == 0.5


def test_example_environment_uses_two_confirmations() -> None:
    example = Path(__file__).parents[1] / ".env.example"

    assert "INDEXER_CONFIRMATION_DEPTH=2" in example.read_text(encoding="utf-8").splitlines()


def test_example_environment_documents_rpc_worker_settings() -> None:
    example = (Path(__file__).parents[1] / ".env.example").read_text(encoding="utf-8")

    assert "INDEXER_RPC_TIMEOUT_SECONDS=10" in example
    assert "INDEXER_RPC_MAX_ATTEMPTS=3" in example
    assert "INDEXER_RPC_BACKOFF_SECONDS=0.5" in example
    assert "PREDICTION_MARKET_ABI_PATH=" in example

