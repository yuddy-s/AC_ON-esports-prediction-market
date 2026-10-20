from pathlib import Path

from app.config import Settings


def test_default_confirmation_depth_is_two(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("INDEXER_CONFIRMATION_DEPTH", raising=False)

    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'config.db'}",
        _env_file=None,
    )

    assert settings.indexer_confirmation_depth == 2


def test_example_environment_uses_two_confirmations() -> None:
    example = Path(__file__).parents[1] / ".env.example"

    assert "INDEXER_CONFIRMATION_DEPTH=2" in example.read_text(encoding="utf-8").splitlines()

