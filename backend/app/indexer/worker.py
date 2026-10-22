import argparse
import logging
from pathlib import Path
import signal
from threading import Event
import time

from app.config import get_settings
from app.database import SessionLocal
from app.indexer.decoder import DecodingEthereumLogProvider, JsonAbiLogDecoder
from app.indexer.rpc import EthereumJsonRpcClient, RpcError, RpcTransientError
from app.indexer.service import EventIndexer, IndexerConfig, IndexerReorganizationError


logger = logging.getLogger("acon.indexer")


class PollingIndexerWorker:
    def __init__(
        self,
        indexer: EventIndexer,
        *,
        poll_interval: float,
        stop_event: Event | None = None,
        session_factory=SessionLocal,
    ) -> None:
        self.indexer = indexer
        self.poll_interval = poll_interval
        self.stop_event = stop_event or Event()
        self.session_factory = session_factory

    def run_once(self, *, rebuild: bool = False):
        with self.session_factory() as session:
            result = self.indexer.rebuild(session) if rebuild else self.indexer.sync_once(session)
        logger.info(
            "indexer sync complete head=%s safe=%s logs=%s batches=%s rebuilt=%s",
            result.latest_observed_block,
            result.last_safe_block,
            result.processed_logs,
            result.batches,
            result.rebuilt_after_reorg,
        )
        return result

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except (RpcTransientError, IndexerReorganizationError) as exc:
                logger.warning("transient indexer failure; retrying next poll: %s", exc)
            if self.stop_event.wait(self.poll_interval):
                break

    def stop(self, *_args: object) -> None:
        self.stop_event.set()


def build_worker() -> tuple[PollingIndexerWorker, EthereumJsonRpcClient]:
    settings = get_settings()
    missing = []
    if not settings.sepolia_rpc_url:
        missing.append("SEPOLIA_RPC_URL")
    if not settings.prediction_market_address:
        missing.append("PREDICTION_MARKET_ADDRESS")
    if not settings.prediction_market_abi_path:
        missing.append("PREDICTION_MARKET_ABI_PATH")
    if missing:
        raise ValueError(f"missing required indexer configuration: {', '.join(missing)}")
    rpc = EthereumJsonRpcClient(
        settings.sepolia_rpc_url,
        timeout_seconds=settings.indexer_rpc_timeout_seconds,
        max_attempts=settings.indexer_rpc_max_attempts,
        backoff_seconds=settings.indexer_rpc_backoff_seconds,
    )
    try:
        actual_chain_id = rpc.chain_id()
        if actual_chain_id != settings.indexer_chain_id:
            raise ValueError(
                "RPC chain ID mismatch: "
                f"expected {settings.indexer_chain_id}, received {actual_chain_id}"
            )
        abi_path = Path(settings.prediction_market_abi_path)
        decoder = JsonAbiLogDecoder(abi_path)
    except Exception:
        rpc.close()
        raise
    provider = DecodingEthereumLogProvider(rpc, decoder, settings.indexer_chain_id)
    indexer = EventIndexer(
        provider,
        IndexerConfig(
            chain_id=settings.indexer_chain_id,
            contract_address=settings.prediction_market_address,
            deployment_block=settings.prediction_market_deployment_block,
            confirmation_depth=settings.indexer_confirmation_depth,
            block_batch_size=settings.indexer_block_batch_size,
            abi_version=abi_path.name,
        ),
    )
    return PollingIndexerWorker(indexer, poll_interval=settings.indexer_poll_interval_seconds), rpc


def main() -> int:
    parser = argparse.ArgumentParser(description="Index confirmed AC_ON Ethereum events")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="run one synchronization pass")
    mode.add_argument("--rebuild", action="store_true", help="clear and rebuild derived projections")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        worker, rpc = build_worker()
    except (ValueError, OSError, RpcError) as exc:
        logger.error("indexer startup error: %s", exc)
        return 2
    signal.signal(signal.SIGINT, worker.stop)
    signal.signal(signal.SIGTERM, worker.stop)
    try:
        if args.once or args.rebuild:
            worker.run_once(rebuild=args.rebuild)
        else:
            worker.run_forever()
    finally:
        rpc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
