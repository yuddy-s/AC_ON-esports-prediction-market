"""ABI-independent registrar state machine. No production signer is configured here."""

from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FixtureRegistrationJob, RegistrationJobEvent
from app.registration_service import RegistrationError, _eligible, _utc, fixture_snapshot


RegistrationState = Literal["absent", "matching", "conflicting"]
ReceiptState = Literal["pending", "success", "reverted", "unknown"]
MAX_SUBMISSION_ATTEMPTS = 3


class GatewayUnavailable(RuntimeError):
    """Failure known to have happened before transaction submission."""


class SubmissionUncertain(RuntimeError):
    """Submission may have reached the chain; never blindly resend."""


class RegistrationGateway(Protocol):
    def registration_state(self, snapshot: dict[str, object]) -> RegistrationState: ...
    def receipt_state(self, transaction_hash: str) -> ReceiptState: ...
    def submit(self, snapshot: dict[str, object]) -> str: ...


def _transition(
    session: Session, job: FixtureRegistrationJob, status: str, now: datetime,
    *, error_code: str | None = None, transaction_hash: str | None = None,
    next_attempt_at: datetime | None = None,
) -> None:
    job.status = status
    job.error_code = error_code
    if transaction_hash is not None:
        job.transaction_hash = transaction_hash
    job.next_attempt_at = next_attempt_at
    job.updated_at = now
    session.add(RegistrationJobEvent(
        job_id=job.id, status=status, error_code=error_code,
        transaction_hash=job.transaction_hash, fixture_snapshot=job.fixture_snapshot, recorded_at=now,
    ))


def activate_registration_job(session: Session, job_id: int, *, now: datetime | None = None) -> FixtureRegistrationJob:
    """Operator-only activation after a real ABI/gateway is configured."""
    now = now or datetime.now(UTC)
    job = session.get(FixtureRegistrationJob, job_id, with_for_update=True)
    if job is None or job.status != "awaiting_abi":
        raise ValueError("job is not awaiting an ABI")
    try:
        fixture = _eligible(session, job.fixture_id, now)
    except RegistrationError:
        _transition(session, job, "terminal_failure", now, error_code="fixture_ineligible")
        return job
    if fixture_snapshot(fixture) != job.fixture_snapshot:
        _transition(session, job, "terminal_failure", now, error_code="fixture_changed")
    else:
        _transition(session, job, "queued", now)
    return job


def process_registration_job(
    session: Session, job_id: int, gateway: RegistrationGateway,
    *, now: datetime | None = None,
) -> FixtureRegistrationJob:
    """Perform one bounded step; caller commits, and must run only one registrar process."""
    now = now or datetime.now(UTC)
    job = session.get(FixtureRegistrationJob, job_id, with_for_update=True)
    if job is None:
        raise ValueError("registration job not found")
    if job.status not in {"queued", "retryable_failure", "submitted"}:
        return job
    if job.next_attempt_at and _utc(job.next_attempt_at) > now:
        return job
    try:
        chain_state = gateway.registration_state(job.fixture_snapshot)
    except GatewayUnavailable:
        _transition(session, job, "submitted" if job.transaction_hash else "retryable_failure", now,
                    error_code="chain_unavailable", next_attempt_at=now + timedelta(seconds=30))
        return job
    if chain_state == "matching":
        _transition(session, job, "confirmed", now)
        return job
    if chain_state == "conflicting":
        _transition(session, job, "terminal_failure", now, error_code="chain_registration_conflict")
        return job

    if job.transaction_hash:
        try:
            receipt_state = gateway.receipt_state(job.transaction_hash)
        except GatewayUnavailable:
            receipt_state = "unknown"
        if receipt_state == "reverted":
            _transition(session, job, "terminal_failure", now, error_code="transaction_reverted")
        else:
            # A successful receipt alone is insufficient: wait for a matching contract read.
            code = "receipt_unknown" if receipt_state == "unknown" else None
            _transition(session, job, "submitted", now, error_code=code,
                        next_attempt_at=now + timedelta(seconds=30))
        return job

    try:
        fixture = _eligible(session, job.fixture_id, now)
    except RegistrationError:
        _transition(session, job, "terminal_failure", now, error_code="fixture_ineligible")
        return job
    if fixture_snapshot(fixture) != job.fixture_snapshot:
        _transition(session, job, "terminal_failure", now, error_code="fixture_changed")
        return job

    if job.attempts >= MAX_SUBMISSION_ATTEMPTS:
        _transition(session, job, "terminal_failure", now, error_code="attempts_exhausted")
        return job
    job.attempts += 1
    try:
        transaction_hash = gateway.submit(job.fixture_snapshot)
    except GatewayUnavailable:
        _transition(session, job, "retryable_failure", now, error_code="submission_unavailable",
                    next_attempt_at=now + timedelta(seconds=30 * job.attempts))
        return job
    except SubmissionUncertain:
        _transition(session, job, "submission_unknown", now, error_code="manual_reconciliation_required")
        return job
    if not (isinstance(transaction_hash, str) and transaction_hash.startswith("0x") and len(transaction_hash) == 66):
        _transition(session, job, "submission_unknown", now, error_code="invalid_transaction_hash")
        return job
    _transition(session, job, "submitted", now, transaction_hash=transaction_hash,
                next_attempt_at=now + timedelta(seconds=30))
    return job


def next_registration_job(session: Session, gateway: RegistrationGateway, *, now: datetime | None = None) -> FixtureRegistrationJob | None:
    """Process one due job; PostgreSQL row locks protect concurrent callers."""
    now = now or datetime.now(UTC)
    job = session.scalar(
        select(FixtureRegistrationJob)
        .where(FixtureRegistrationJob.status.in_(["queued", "retryable_failure", "submitted"]))
        .where((FixtureRegistrationJob.next_attempt_at.is_(None)) | (FixtureRegistrationJob.next_attempt_at <= now))
        .order_by(FixtureRegistrationJob.created_at, FixtureRegistrationJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    return process_registration_job(session, job.id, gateway, now=now) if job else None
