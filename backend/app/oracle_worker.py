"""ABI-independent oracle intent and retry state machine; no production signer."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from eth_utils import is_address, to_checksum_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Fixture, FixtureResultObservation, OracleProposalEvent, OracleProposalIntent, OracleResultAssessment,
)
from app.oracle_assessment import assess_imported_results


ProposalState = Literal["closed_unproposed", "proposed_matching", "proposed_conflicting", "not_closed"]
ReceiptState = Literal["pending", "success", "reverted", "unknown"]
MAX_ATTEMPTS = 3


class OracleGatewayUnavailable(RuntimeError):
    """A read or known-pre-submission operation failed."""


class OracleSubmissionUncertain(RuntimeError):
    """A transaction may have reached the chain and cannot be blindly resent."""


@dataclass(frozen=True, slots=True)
class ClosedMarketRef:
    chain_id: int
    contract_address: str
    market_id: int
    fixture_id: int


class OracleGateway(Protocol):
    def closed_markets(self) -> list[ClosedMarketRef]: ...
    def proposal_state(self, market: ClosedMarketRef, intent: OracleProposalIntent | None) -> ProposalState: ...
    def receipt_state(self, transaction_hash: str) -> ReceiptState: ...
    def submit(self, intent: OracleProposalIntent) -> str: ...


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _market_ref(intent: OracleProposalIntent) -> ClosedMarketRef:
    return ClosedMarketRef(intent.chain_id, intent.contract_address, intent.market_id, intent.fixture_id)


def _latest_assessment(session: Session, fixture_id: int) -> OracleResultAssessment | None:
    return session.scalar(
        select(OracleResultAssessment)
        .join(FixtureResultObservation, OracleResultAssessment.observation_id == FixtureResultObservation.id)
        .where(OracleResultAssessment.fixture_id == fixture_id)
        .order_by(FixtureResultObservation.source_updated_at.desc(), FixtureResultObservation.id.desc())
        .limit(1)
    )


def _record(session: Session, intent: OracleProposalIntent, status: str, now: datetime, *, code: str | None = None,
            next_attempt_at: datetime | None = None, transaction_hash: str | None = None) -> None:
    intent.status = status
    intent.error_code = code
    intent.next_attempt_at = next_attempt_at
    if transaction_hash is not None:
        intent.transaction_hash = transaction_hash
    intent.updated_at = now
    session.add(OracleProposalEvent(
        intent_id=intent.id, status=status, error_code=code,
        transaction_hash=intent.transaction_hash, recorded_at=now,
    ))


def plan_proposal(session: Session, market: ClosedMarketRef, gateway: OracleGateway,
                  *, now: datetime | None = None) -> OracleProposalIntent | None:
    """Select the latest assessed result only for a chain-verified closed market."""
    now = now or datetime.now(UTC)
    if market.chain_id <= 0 or market.market_id < 0 or not is_address(market.contract_address):
        raise ValueError("invalid chain market reference")
    address = to_checksum_address(market.contract_address)
    existing = session.scalar(select(OracleProposalIntent).where(
        OracleProposalIntent.chain_id == market.chain_id,
        OracleProposalIntent.contract_address == address,
        OracleProposalIntent.market_id == market.market_id,
    ))
    if existing:
        return existing
    fixture = session.get(Fixture, market.fixture_id)
    if fixture is None:
        return None
    assessment = _latest_assessment(session, fixture.id)
    if assessment is None:
        return None
    observation = session.get(FixtureResultObservation, assessment.observation_id)
    if observation is None:
        return None
    if observation.match_status == "completed" and _utc(observation.source_updated_at) < _utc(fixture.scheduled_start):
        return None
    if gateway.proposal_state(market, None) != "closed_unproposed":
        return None
    intent = OracleProposalIntent(
        chain_id=market.chain_id, contract_address=address, market_id=market.market_id,
        fixture_id=fixture.id, observation_id=observation.id, outcome=assessment.outcome,
        evidence_url=observation.evidence_url, evidence_hash=observation.evidence_hash,
        status="queued", attempts=0, created_at=now, updated_at=now,
    )
    session.add(intent)
    session.flush()
    session.add(OracleProposalEvent(intent_id=intent.id, status="queued", recorded_at=now))
    return intent


def process_proposal(session: Session, intent_id: int, gateway: OracleGateway,
                     *, now: datetime | None = None) -> OracleProposalIntent:
    now = now or datetime.now(UTC)
    intent = session.get(OracleProposalIntent, intent_id, with_for_update=True)
    if intent is None:
        raise ValueError("proposal intent not found")
    if intent.status not in {"queued", "retryable_failure", "submitted"}:
        return intent
    if intent.next_attempt_at and _utc(intent.next_attempt_at) > now:
        return intent
    latest = _latest_assessment(session, intent.fixture_id)
    if latest and latest.observation_id != intent.observation_id and intent.correction_observation_id != latest.observation_id:
        intent.correction_observation_id = latest.observation_id
        session.add(OracleProposalEvent(intent_id=intent.id, status="correction_detected", recorded_at=now,
                                        transaction_hash=intent.transaction_hash))
    try:
        state = gateway.proposal_state(_market_ref(intent), intent)
    except OracleGatewayUnavailable:
        _record(session, intent, "submitted" if intent.transaction_hash else "retryable_failure", now,
                code="chain_unavailable", next_attempt_at=now + timedelta(seconds=30))
        return intent
    if state == "proposed_matching":
        _record(session, intent, "confirmed", now)
        return intent
    if state == "proposed_conflicting":
        _record(session, intent, "terminal_failure", now, code="different_chain_proposal")
        return intent
    if intent.transaction_hash:
        try:
            receipt = gateway.receipt_state(intent.transaction_hash)
        except OracleGatewayUnavailable:
            receipt = "unknown"
        if receipt == "reverted":
            _record(session, intent, "terminal_failure", now, code="transaction_reverted")
        else:
            _record(session, intent, "submitted", now, code="receipt_unknown" if receipt == "unknown" else None,
                    next_attempt_at=now + timedelta(seconds=30))
        return intent
    if intent.correction_observation_id is not None:
        _record(session, intent, "correction_review", now, code="result_corrected_before_submission")
        return intent
    if state == "not_closed":
        _record(session, intent, "terminal_failure", now, code="market_not_closed")
        return intent
    if intent.attempts >= MAX_ATTEMPTS:
        _record(session, intent, "terminal_failure", now, code="attempts_exhausted")
        return intent
    intent.attempts += 1
    try:
        transaction_hash = gateway.submit(intent)
    except OracleGatewayUnavailable:
        _record(session, intent, "retryable_failure", now, code="submission_unavailable",
                next_attempt_at=now + timedelta(seconds=30 * intent.attempts))
        return intent
    except OracleSubmissionUncertain:
        _record(session, intent, "submission_unknown", now, code="manual_reconciliation_required")
        return intent
    if not (isinstance(transaction_hash, str) and transaction_hash.startswith("0x") and len(transaction_hash) == 66):
        _record(session, intent, "submission_unknown", now, code="invalid_transaction_hash")
        return intent
    _record(session, intent, "submitted", now, transaction_hash=transaction_hash,
            next_attempt_at=now + timedelta(seconds=30))
    return intent


def run_oracle_once(session: Session, gateway: OracleGateway, *, now: datetime | None = None) -> int:
    """Assess imports, plan closed markets, and advance due intents; caller commits."""
    now = now or datetime.now(UTC)
    assess_imported_results(session, now=now)
    markets = gateway.closed_markets()
    for market in markets:
        plan_proposal(session, market, gateway, now=now)
    intents = session.scalars(select(OracleProposalIntent).where(
        OracleProposalIntent.status.in_(["queued", "retryable_failure", "submitted"])
    ).order_by(OracleProposalIntent.id).with_for_update(skip_locked=True)).all()
    for intent in intents:
        process_proposal(session, intent.id, gateway, now=now)
    return len(intents)
