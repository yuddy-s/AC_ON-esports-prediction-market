from app.database import _connect_args


def test_sqlite_connection_args_allow_cross_thread_test_clients() -> None:
    assert _connect_args("sqlite+pysqlite:///./test.db") == {"check_same_thread": False}


def test_psycopg_connection_args_disable_automatic_prepared_statements() -> None:
    assert _connect_args("postgresql+psycopg://user:password@pooler.example/test") == {
        "prepare_threshold": None
    }


def test_other_postgresql_drivers_keep_default_connection_args() -> None:
    assert _connect_args("postgresql+psycopg2://user:password@localhost/test") == {}
