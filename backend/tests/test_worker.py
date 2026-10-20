from contextlib import nullcontext
from threading import Event
from types import SimpleNamespace

import pytest

from app.indexer.service import SyncResult
from app.indexer.worker import PollingIndexerWorker
from app.indexer import worker as worker_module


class FakeIndexer:
    def __init__(self) -> None:
        self.sync_calls = 0
        self.rebuild_calls = 0

    def sync_once(self, _session) -> SyncResult:
        self.sync_calls += 1
        return SyncResult(10, 8, 2, 1, False)

    def rebuild(self, _session) -> SyncResult:
        self.rebuild_calls += 1
        return SyncResult(10, 8, 2, 1, True)


def test_worker_supports_once_and_rebuild() -> None:
    indexer = FakeIndexer()
    worker = PollingIndexerWorker(
        indexer, poll_interval=0.01, session_factory=lambda: nullcontext(object())
    )

    assert worker.run_once().processed_logs == 2
    assert worker.run_once(rebuild=True).rebuilt_after_reorg is True
    assert indexer.sync_calls == 1
    assert indexer.rebuild_calls == 1


def test_worker_stops_before_another_poll() -> None:
    indexer = FakeIndexer()
    stopped = Event()
    stopped.set()
    worker = PollingIndexerWorker(
        indexer,
        poll_interval=0.01,
        stop_event=stopped,
        session_factory=lambda: nullcontext(object()),
    )

    worker.run_forever()

    assert indexer.sync_calls == 0


def test_worker_fails_closed_when_live_configuration_is_missing(monkeypatch) -> None:
    settings = SimpleNamespace(
        sepolia_rpc_url=None,
        prediction_market_address=None,
        prediction_market_abi_path=None,
    )
    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="SEPOLIA_RPC_URL.*PREDICTION_MARKET_ADDRESS.*ABI_PATH"):
        worker_module.build_worker()


def test_worker_rejects_wrong_rpc_chain_before_database_use(monkeypatch) -> None:
    settings = SimpleNamespace(
        sepolia_rpc_url="https://rpc.example",
        prediction_market_address="0x" + "11" * 20,
        prediction_market_abi_path="unused.json",
        indexer_chain_id=11155111,
        indexer_rpc_timeout_seconds=10,
        indexer_rpc_max_attempts=3,
        indexer_rpc_backoff_seconds=0.5,
    )

    class WrongChainRpc:
        instance = None

        def __init__(self, *_args, **_kwargs) -> None:
            self.closed = False
            WrongChainRpc.instance = self

        def chain_id(self) -> int:
            return 1

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "EthereumJsonRpcClient", WrongChainRpc)

    with pytest.raises(ValueError, match="expected 11155111, received 1"):
        worker_module.build_worker()

    assert WrongChainRpc.instance is not None
    assert WrongChainRpc.instance.closed is True
