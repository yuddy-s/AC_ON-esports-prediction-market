import pytest

from tests.test_postgres_integration import _validated_test_database_url


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://user@db.example.com/acon_ci",
        "postgresql+psycopg://user@localhost/acon_production",
        "sqlite+pysqlite:///./acon_ci.db",
    ],
)
def test_postgres_integration_rejects_unsafe_targets(monkeypatch, url: str) -> None:
    monkeypatch.setenv("TEST_POSTGRES_URL", url)
    with pytest.raises(RuntimeError):
        _validated_test_database_url()


def test_postgres_integration_accepts_local_disposable_target(monkeypatch) -> None:
    monkeypatch.setenv(
        "TEST_POSTGRES_URL", "postgresql+psycopg://acon@localhost:5432/acon_ci"
    )
    url = _validated_test_database_url()
    assert url.host == "localhost"
    assert url.database == "acon_ci"
