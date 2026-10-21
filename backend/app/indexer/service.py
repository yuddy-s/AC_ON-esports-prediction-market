from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.indexer.provider import ChainLog, EthereumLogProvider
from app.models import IndexedContract, IndexedMarket, IndexedTrade, IndexerCheckpoint, ProcessedLog


logger = logging.getLogger("acon.indexer.service")


class IndexerProjectionError(RuntimeError):
    pass


class IndexerReorganizationError(IndexerProjectionError):
    """Raised when the canonical chain changes while a block range is processed."""


@dataclass(frozen=True, slots=True)
class IndexerConfig:
    chain_id: int
    contract_address: str
    deployment_block: int
    confirmation_depth: int = 2
    block_batch_size: int = 500
    abi_version: str = "milestone-3-foundation"

    def __post_init__(self) -> None:
        if self.deployment_block < 0:
            raise ValueError("deployment_block must be non-negative")
        if self.confirmation_depth < 0:
            raise ValueError("confirmation_depth must be non-negative")
        if self.block_batch_size < 1:
            raise ValueError("block_batch_size must be positive")
        if not self.contract_address:
            raise ValueError("contract_address is required")


@dataclass(frozen=True, slots=True)
class SyncResult:
    latest_observed_block: int
    last_safe_block: int | None
    processed_logs: int
    batches: int
    rebuilt_after_reorg: bool


class EventIndexer:
    def __init__(self, provider: EthereumLogProvider, config: IndexerConfig) -> None:
        self.provider = provider
        self.config = config
        self.address = config.contract_address.lower()

    def sync_once(self, session: Session) -> SyncResult:
        contract, checkpoint = self._ensure_state(session)
        latest_block = self.provider.latest_block()
        checkpoint.latest_observed_block = latest_block
        checkpoint.updated_at = datetime.now(UTC)
        session.commit()

        rebuilt = self._reset_if_reorganized(session, contract, checkpoint)
        safe_head = latest_block - self.config.confirmation_depth
        logger.info(
            "indexer head observed=%s safe=%s next=%s contract=%s",
            latest_block,
            safe_head,
            checkpoint.next_block,
            self.address,
        )
        processed_count = 0
        batch_count = 0

        while checkpoint.next_block <= safe_head:
            from_block = checkpoint.next_block
            to_block = min(from_block + self.config.block_batch_size - 1, safe_head)
            logger.info("indexer range start=%s end=%s", from_block, to_block)
            batch_processed_before = processed_count

            try:
                end_block_hash_before = self.provider.block_hash(to_block)
                logs = self.provider.get_logs(self.address, from_block, to_block)
                for chain_log in sorted(logs, key=lambda item: (item.block_number, item.log_index)):
                    self._validate_log(chain_log, from_block, to_block)
                    if self._already_processed(session, chain_log):
                        continue
                    self._apply_projection(session, contract, chain_log)
                    session.add(self._processed_log(contract, chain_log))
                    # The session disables autoflush globally. Flush each normalized event so
                    # later logs in the same atomic batch can see its projection and identity.
                    session.flush()
                    processed_count += 1

                end_block_hash_after = self.provider.block_hash(to_block)
                if end_block_hash_before.lower() != end_block_hash_after.lower():
                    raise IndexerReorganizationError(
                        f"canonical block {to_block} changed while processing range "
                        f"{from_block}-{to_block}"
                    )

                checkpoint.next_block = to_block + 1
                checkpoint.last_safe_block = to_block
                checkpoint.last_safe_block_hash = end_block_hash_after
                checkpoint.latest_observed_block = latest_block
                checkpoint.updated_at = datetime.now(UTC)
                session.commit()
                batch_count += 1
                logger.info(
                    "indexer range committed start=%s end=%s logs=%s next=%s",
                    from_block,
                    to_block,
                    processed_count - batch_processed_before,
                    checkpoint.next_block,
                )
            except Exception:
                session.rollback()
                logger.exception("indexer range rolled back start=%s end=%s", from_block, to_block)
                raise

        return SyncResult(
            latest_observed_block=latest_block,
            last_safe_block=checkpoint.last_safe_block,
            processed_logs=processed_count,
            batches=batch_count,
            rebuilt_after_reorg=rebuilt,
        )

    def rebuild(self, session: Session) -> SyncResult:
        contract, checkpoint = self._ensure_state(session)
        self._clear_projections(session, contract, checkpoint)
        session.commit()
        return self.sync_once(session)

    def _ensure_state(self, session: Session) -> tuple[IndexedContract, IndexerCheckpoint]:
        contract = session.scalar(
            select(IndexedContract).where(
                IndexedContract.chain_id == self.config.chain_id,
                IndexedContract.contract_address == self.address,
            )
        )
        if contract is None:
            contract = IndexedContract(
                chain_id=self.config.chain_id,
                contract_address=self.address,
                deployment_block=self.config.deployment_block,
                abi_version=self.config.abi_version,
                active=True,
            )
            session.add(contract)
            session.flush()
        elif (
            contract.deployment_block != self.config.deployment_block
            or contract.abi_version != self.config.abi_version
            or not contract.active
        ):
            raise IndexerProjectionError(
                "registered deployment block, ABI version, or active state differs from indexer configuration"
            )

        checkpoint = session.get(IndexerCheckpoint, contract.id)
        if checkpoint is None:
            checkpoint = IndexerCheckpoint(
                indexed_contract_id=contract.id,
                next_block=contract.deployment_block,
                last_safe_block=None,
                last_safe_block_hash=None,
                latest_observed_block=None,
                updated_at=datetime.now(UTC),
            )
            session.add(checkpoint)
        session.commit()
        return contract, checkpoint

    def _reset_if_reorganized(
        self, session: Session, contract: IndexedContract, checkpoint: IndexerCheckpoint
    ) -> bool:
        if checkpoint.last_safe_block is None or checkpoint.last_safe_block_hash is None:
            return False
        canonical_hash = self.provider.block_hash(checkpoint.last_safe_block)
        if canonical_hash.lower() == checkpoint.last_safe_block_hash.lower():
            return False
        self._clear_projections(session, contract, checkpoint)
        session.commit()
        return True

    def _clear_projections(
        self, session: Session, contract: IndexedContract, checkpoint: IndexerCheckpoint
    ) -> None:
        filters = (
            IndexedMarket.chain_id == contract.chain_id,
            IndexedMarket.contract_address == contract.contract_address,
        )
        session.execute(delete(IndexedTrade).where(
            IndexedTrade.chain_id == contract.chain_id,
            IndexedTrade.contract_address == contract.contract_address,
        ))
        session.execute(delete(IndexedMarket).where(*filters))
        session.execute(delete(ProcessedLog).where(ProcessedLog.indexed_contract_id == contract.id))
        checkpoint.next_block = contract.deployment_block
        checkpoint.last_safe_block = None
        checkpoint.last_safe_block_hash = None
        checkpoint.updated_at = datetime.now(UTC)

    def _validate_log(self, chain_log: ChainLog, from_block: int, to_block: int) -> None:
        if chain_log.chain_id != self.config.chain_id:
            raise IndexerProjectionError("log chain ID does not match indexer configuration")
        if chain_log.contract_address.lower() != self.address:
            raise IndexerProjectionError("log contract address does not match indexer configuration")
        if not from_block <= chain_log.block_number <= to_block:
            raise IndexerProjectionError("provider returned a log outside the requested block range")

    @staticmethod
    def _already_processed(session: Session, chain_log: ChainLog) -> bool:
        identity = session.scalar(
            select(ProcessedLog.id).where(
                ProcessedLog.chain_id == chain_log.chain_id,
                ProcessedLog.transaction_hash == chain_log.transaction_hash.lower(),
                ProcessedLog.log_index == chain_log.log_index,
            )
        )
        return identity is not None

    def _apply_projection(
        self, session: Session, contract: IndexedContract, chain_log: ChainLog
    ) -> None:
        if chain_log.event_name == "MarketCreated":
            self._apply_market_created(session, contract, chain_log)
        elif chain_log.event_name == "TradeExecuted":
            self._apply_trade_executed(session, contract, chain_log)

    def _apply_market_created(
        self, session: Session, contract: IndexedContract, chain_log: ChainLog
    ) -> None:
        payload = chain_log.payload
        market_id = int(payload["market_id"])
        market = session.scalar(
            select(IndexedMarket).where(
                IndexedMarket.chain_id == contract.chain_id,
                IndexedMarket.contract_address == contract.contract_address,
                IndexedMarket.market_id == market_id,
            )
        )
        values = {
            "question": str(payload["question"]),
            "trading_deadline": datetime.fromtimestamp(int(payload["trading_deadline"]), UTC),
            "state": "OPEN",
            "creator": str(payload["creator"]).lower(),
            "source_block_number": chain_log.block_number,
            "source_block_hash": chain_log.block_hash.lower(),
            "source_transaction_hash": chain_log.transaction_hash.lower(),
            "source_log_index": chain_log.log_index,
        }
        if market is None:
            market = IndexedMarket(
                chain_id=contract.chain_id,
                contract_address=contract.contract_address,
                market_id=market_id,
                yes_quantity=Decimal(0),
                no_quantity=Decimal(0),
                **values,
            )
            session.add(market)
        else:
            for field, value in values.items():
                setattr(market, field, value)

    def _apply_trade_executed(
        self, session: Session, contract: IndexedContract, chain_log: ChainLog
    ) -> None:
        payload = chain_log.payload
        market_id = int(payload["market_id"])
        market = session.scalar(
            select(IndexedMarket).where(
                IndexedMarket.chain_id == contract.chain_id,
                IndexedMarket.contract_address == contract.contract_address,
                IndexedMarket.market_id == market_id,
            )
        )
        if market is None:
            raise IndexerProjectionError(f"trade references unknown market {market_id}")

        yes_quantity = Decimal(str(payload["yes_quantity"]))
        no_quantity = Decimal(str(payload["no_quantity"]))
        trade = IndexedTrade(
            chain_id=contract.chain_id,
            contract_address=contract.contract_address,
            market_id=market_id,
            trader=str(payload["trader"]).lower(),
            outcome=int(payload["outcome"]),
            shares=Decimal(str(payload["shares"])),
            cost=Decimal(str(payload["cost"])),
            yes_quantity=yes_quantity,
            no_quantity=no_quantity,
            block_number=chain_log.block_number,
            block_hash=chain_log.block_hash.lower(),
            transaction_hash=chain_log.transaction_hash.lower(),
            log_index=chain_log.log_index,
        )
        session.add(trade)
        market.yes_quantity = yes_quantity
        market.no_quantity = no_quantity
        market.source_block_number = chain_log.block_number
        market.source_block_hash = chain_log.block_hash.lower()
        market.source_transaction_hash = chain_log.transaction_hash.lower()
        market.source_log_index = chain_log.log_index

    @staticmethod
    def _processed_log(contract: IndexedContract, chain_log: ChainLog) -> ProcessedLog:
        return ProcessedLog(
            indexed_contract_id=contract.id,
            chain_id=chain_log.chain_id,
            contract_address=chain_log.contract_address.lower(),
            block_number=chain_log.block_number,
            block_hash=chain_log.block_hash.lower(),
            transaction_hash=chain_log.transaction_hash.lower(),
            log_index=chain_log.log_index,
            event_name=chain_log.event_name,
            payload=chain_log.payload,
        )
