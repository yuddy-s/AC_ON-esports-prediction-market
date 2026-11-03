from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.indexer.provider import ChainLog, EthereumLogProvider
from app.models import (
    IndexedContract, IndexedFixtureRegistration, IndexedMarket, IndexedMarketEvent,
    IndexedPosition, IndexedTrade, IndexerCheckpoint, ProcessedLog,
)


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
    m4_enabled: bool = False

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
        session.execute(delete(IndexedPosition).where(
            IndexedPosition.chain_id == contract.chain_id,
            IndexedPosition.contract_address == contract.contract_address,
        ))
        session.execute(delete(IndexedMarketEvent).where(
            IndexedMarketEvent.chain_id == contract.chain_id,
            IndexedMarketEvent.contract_address == contract.contract_address,
        ))
        session.execute(delete(IndexedFixtureRegistration).where(
            IndexedFixtureRegistration.chain_id == contract.chain_id,
            IndexedFixtureRegistration.contract_address == contract.contract_address,
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
            # Autoflush is intentionally disabled; M4 linkage queries the row immediately.
            session.flush()
        elif chain_log.event_name == "TradeExecuted":
            self._apply_trade_executed(session, contract, chain_log)
        if self.config.m4_enabled:
            self._apply_m4_projection(session, contract, chain_log)

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

    def _apply_m4_projection(
        self, session: Session, contract: IndexedContract, chain_log: ChainLog
    ) -> None:
        payload = chain_log.payload
        name = chain_log.event_name
        if name == "FixtureRegistered":
            self._apply_fixture_registered(session, contract, chain_log)
            return
        if name not in M4_MARKET_EVENTS:
            return
        market_id = int(payload["market_id"])
        market = self._market(session, contract, market_id)
        if market is None:
            raise IndexerProjectionError(f"{name} references unknown market {market_id}")

        if name == "MarketCreated":
            fixture_key = str(payload["fixture_key"]).lower()
            market.fixture_key = fixture_key
            registration = session.scalar(select(IndexedFixtureRegistration).where(
                IndexedFixtureRegistration.chain_id == contract.chain_id,
                IndexedFixtureRegistration.contract_address == contract.contract_address,
                IndexedFixtureRegistration.fixture_key == fixture_key,
            ))
            if registration is not None:
                registration.market_id = market_id
        elif name == "TradeExecuted":
            self._change_position(session, contract, chain_log, add=True)
        elif name == "SellExecuted":
            market.yes_quantity = Decimal(str(payload["yes_quantity"]))
            market.no_quantity = Decimal(str(payload["no_quantity"]))
            self._change_position(session, contract, chain_log, add=False)
        elif name == "MarketClosed":
            market.state = "CLOSED"
        elif name == "OutcomeProposed":
            market.state = "PROPOSED"
        elif name == "OutcomeChallenged":
            market.state = "DISPUTED"
        elif name in {"ResolverSelectionRequested", "ResolverSelectionRequestFailed", "ResolverSelectionPending"}:
            market.state = "RESOLVER_SELECTION"
        elif name == "ResolverCommitteeSelected":
            market.state = "RESOLVER_VOTING"
        elif name == "MarketFinalized":
            market.state = "FINALIZED"
            market.final_outcome = int(payload["outcome"])
        elif name == "MarketVoided":
            market.state = "VOID"
            market.final_outcome = 2
        elif name == "PayoutClaimed":
            position = self._position(session, contract, market_id, str(payload["account"]), chain_log.block_number)
            position.yes_shares = Decimal(0)
            position.no_shares = Decimal(0)
            position.claimed = True
            position.payout = Decimal(str(payload["payout"]))

        market.source_block_number = chain_log.block_number
        market.source_block_hash = chain_log.block_hash.lower()
        market.source_transaction_hash = chain_log.transaction_hash.lower()
        market.source_log_index = chain_log.log_index
        session.add(IndexedMarketEvent(
            chain_id=contract.chain_id,
            contract_address=contract.contract_address,
            market_id=market_id,
            event_name=name,
            actor=self._event_actor(payload),
            payload=self._json_safe(payload),
            block_number=chain_log.block_number,
            block_hash=chain_log.block_hash.lower(),
            transaction_hash=chain_log.transaction_hash.lower(),
            log_index=chain_log.log_index,
        ))

    def _apply_fixture_registered(
        self, session: Session, contract: IndexedContract, chain_log: ChainLog
    ) -> None:
        payload = chain_log.payload
        fixture_key = str(payload["fixture_key"]).lower()
        registration = session.scalar(select(IndexedFixtureRegistration).where(
            IndexedFixtureRegistration.chain_id == contract.chain_id,
            IndexedFixtureRegistration.contract_address == contract.contract_address,
            IndexedFixtureRegistration.fixture_key == fixture_key,
        ))
        values = {
            "registrar": str(payload["registrar"]).lower(),
            "data": self._json_safe(payload["data"]),
            "revision_hash": str(payload["revision_hash"]).lower(),
            "block_number": chain_log.block_number,
            "block_hash": chain_log.block_hash.lower(),
            "transaction_hash": chain_log.transaction_hash.lower(),
            "log_index": chain_log.log_index,
        }
        if registration is None:
            registration = IndexedFixtureRegistration(
                chain_id=contract.chain_id, contract_address=contract.contract_address,
                fixture_key=fixture_key, **values,
            )
            session.add(registration)
        else:
            for field, value in values.items():
                setattr(registration, field, value)

    def _change_position(
        self, session: Session, contract: IndexedContract, chain_log: ChainLog, *, add: bool
    ) -> None:
        payload = chain_log.payload
        market_id = int(payload["market_id"])
        position = self._position(
            session, contract, market_id, str(payload["trader"]), chain_log.block_number
        )
        shares = Decimal(str(payload["shares"]))
        field = "yes_shares" if int(payload["outcome"]) == 0 else "no_shares"
        current = Decimal(getattr(position, field))
        updated = current + shares if add else current - shares
        if updated < 0:
            raise IndexerProjectionError(f"{chain_log.event_name} makes {field} negative")
        setattr(position, field, updated)
        position.updated_block_number = chain_log.block_number

    @staticmethod
    def _market(session: Session, contract: IndexedContract, market_id: int) -> IndexedMarket | None:
        return session.scalar(select(IndexedMarket).where(
            IndexedMarket.chain_id == contract.chain_id,
            IndexedMarket.contract_address == contract.contract_address,
            IndexedMarket.market_id == market_id,
        ))

    @staticmethod
    def _position(
        session: Session, contract: IndexedContract, market_id: int, wallet: str, block_number: int
    ) -> IndexedPosition:
        normalized = wallet.lower()
        position = session.scalar(select(IndexedPosition).where(
            IndexedPosition.chain_id == contract.chain_id,
            IndexedPosition.contract_address == contract.contract_address,
            IndexedPosition.market_id == market_id,
            IndexedPosition.wallet_address == normalized,
        ))
        if position is None:
            position = IndexedPosition(
                chain_id=contract.chain_id, contract_address=contract.contract_address,
                market_id=market_id, wallet_address=normalized,
                yes_shares=Decimal(0), no_shares=Decimal(0), claimed=False,
                payout=Decimal(0), updated_block_number=block_number,
            )
            session.add(position)
        return position

    @staticmethod
    def _event_actor(payload: dict[str, object]) -> str | None:
        for field in ("trader", "caller", "proposer", "challenger", "resolver", "account", "creator"):
            value = payload.get(field)
            if isinstance(value, str) and len(value) == 42:
                return value.lower()
        return None

    @classmethod
    def _json_safe(cls, value: object) -> object:
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, dict):
            return {str(key): cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [cls._json_safe(item) for item in value]
        return str(value)

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


M4_MARKET_EVENTS = {
    "MarketCreated", "TradeExecuted", "SellExecuted", "MarketClosed",
    "OutcomeProposed", "OutcomeChallenged", "ChallengeBondResolved",
    "ResolverSelectionRequested", "ResolverSelectionRequestFailed",
    "ResolverSelectionPending", "ResolverCommitteeSelected", "VRFFulfillmentIgnored",
    "ResolverVoteCast", "MarketFinalized", "MarketVoided", "PayoutClaimed",
    "CreatorSurplusWithdrawn",
}
