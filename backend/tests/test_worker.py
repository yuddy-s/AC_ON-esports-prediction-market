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
