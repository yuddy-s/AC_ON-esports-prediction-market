"""Signed, single-use requests for curated fixture registration.

No chain write is performed until the M4 registrar ABI and role grant are frozen.
"""

from datetime import UTC, datetime, timedelta
import hashlib
import json
import secrets

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import is_address, to_checksum_address
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Fixture, FixtureRegistrationJob, FixtureResultObservation, RegistrationChallenge, RegistrationJobEvent


CHALLENGE_LIFETIME = timedelta(minutes=5)
MINIMUM_START_BUFFER = timedelta(minutes=30)
MAX_CHALLENGES_PER_DAY = 12
MAX_JOBS_PER_WALLET_PER_DAY = 3
REAUTHORIZABLE_FAILURES = {"fixture_changed", "fixture_ineligible", "transaction_reverted", "attempts_exhausted"}


class RegistrationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _address(value: str) -> str:
    if not is_address(value):
        raise RegistrationError("invalid_address", "A valid Ethereum wallet address is required")
    return to_checksum_address(value)


def _eligible(session: Session, fixture_id: int, now: datetime) -> Fixture:
    fixture = session.get(Fixture, fixture_id)
    if fixture is None:
        raise RegistrationError("fixture_not_found", "Fixture not found", 404)
    if fixture.match_status != "scheduled" or _utc(fixture.scheduled_start) <= now + MINIMUM_START_BUFFER:
        raise RegistrationError("fixture_ineligible", "Fixture is not scheduled far enough in the future", 409)
    if not fixture.evidence_url or not fixture.evidence_hash or fixture.team_a_id == fixture.team_b_id:
        raise RegistrationError("fixture_ineligible", "Fixture lacks curated source metadata", 409)
    if session.scalar(select(FixtureResultObservation.id).where(FixtureResultObservation.fixture_id == fixture_id)) is not None:
        raise RegistrationError("fixture_ineligible", "Fixture already has an observed result", 409)
    return fixture


def fixture_snapshot(fixture: Fixture) -> dict[str, object]:
    """Canonical data the signer authorizes and the registrar must recheck."""
    return {
        "provider_id": fixture.provider_id,
        "game_id": fixture.game_id,
        "external_match_id": fixture.external_match_id,
        "scheduled_start": _utc(fixture.scheduled_start).isoformat(),
        "team_a_id": fixture.team_a_id,
        "team_a_name": fixture.team_a_name,
        "team_b_id": fixture.team_b_id,
        "team_b_name": fixture.team_b_name,
        "evidence_url": fixture.evidence_url,
        "evidence_hash": fixture.evidence_hash,
        "source_updated_at": _utc(fixture.source_updated_at).isoformat(),
    }


def _snapshot_hash(snapshot: dict[str, object]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def _message(fixture: Fixture, snapshot: dict[str, object], wallet: str, chain_id: int, nonce: str, expires_at: datetime, origin: str) -> str:
    # The exact message and snapshot are stored. Never reconstruct signed content from mutable source fields.
    return (
        "AC_ON fixture registration request\n"
        f"Origin: {origin}\n"
        f"Chain ID: {chain_id}\n"
        f"Fixture ID: {fixture.id}\n"
        f"Source: {fixture.provider_id}/{fixture.game_id}/{fixture.external_match_id}\n"
        f"Fixture snapshot SHA-256: {_snapshot_hash(snapshot)}\n"
        f"Wallet: {wallet}\n"
        f"Nonce: {nonce}\n"
        f"Expires at: {expires_at.isoformat()}\n"
        "This requests registration only. Market creation requires a separate wallet transaction."
    )


def _existing_job(session: Session, fixture_id: int, *, lock: bool = False) -> FixtureRegistrationJob | None:
    statement = select(FixtureRegistrationJob).where(FixtureRegistrationJob.fixture_id == fixture_id)
    if lock:
        statement = statement.with_for_update()
    return session.scalar(statement)


def _allows_new_authorization(job: FixtureRegistrationJob | None) -> bool:
    return job is None or (job.status == "terminal_failure" and job.error_code in REAUTHORIZABLE_FAILURES)


def cleanup_expired_challenges(session: Session, *, now: datetime | None = None) -> int:
    """Retain challenges for one day after expiry, then remove stale auth material."""
    now = now or datetime.now(UTC)
    result = session.execute(delete(RegistrationChallenge).where(
        RegistrationChallenge.expires_at < now - timedelta(days=1)
    ))
    return result.rowcount or 0


def create_challenge(
    session: Session, fixture_id: int, wallet_address: str, chain_id: int, origin: str,
    *, now: datetime | None = None,
) -> tuple[RegistrationChallenge, str]:
    now = now or datetime.now(UTC)
    wallet = _address(wallet_address)
    fixture = _eligible(session, fixture_id, now)
    cleanup_expired_challenges(session, now=now)
    if not _allows_new_authorization(_existing_job(session, fixture_id)):
        raise RegistrationError("already_requested", "Fixture registration has already been requested", 409)
    since = now - timedelta(days=1)
    recent = session.scalar(select(func.count()).select_from(RegistrationChallenge).where(
        RegistrationChallenge.wallet_address == wallet,
        RegistrationChallenge.created_at >= since,
    )) or 0
    if recent >= MAX_CHALLENGES_PER_DAY:
        raise RegistrationError("rate_limited", "Too many registration challenges", 429)
    nonce = secrets.token_hex(32)
    expires_at = now + CHALLENGE_LIFETIME
    snapshot = fixture_snapshot(fixture)
    challenge = RegistrationChallenge(
        fixture_id=fixture_id,
        wallet_address=wallet,
        chain_id=chain_id,
        nonce_hash=hashlib.sha256(nonce.encode()).hexdigest(),
        message=_message(fixture, snapshot, wallet, chain_id, nonce, expires_at, origin),
        fixture_snapshot=snapshot,
        expires_at=expires_at,
        created_at=now,
    )
    session.add(challenge)
    session.flush()
    return challenge, nonce


def request_registration(
    session: Session, fixture_id: int, wallet_address: str, nonce: str, signature: str, chain_id: int,
    *, now: datetime | None = None,
) -> FixtureRegistrationJob:
    now = now or datetime.now(UTC)
    wallet = _address(wallet_address)
    if len(nonce) != 64 or any(c not in "0123456789abcdef" for c in nonce):
        raise RegistrationError("invalid_challenge", "Invalid registration challenge", 400)
    challenge = session.scalar(select(RegistrationChallenge).where(
        RegistrationChallenge.nonce_hash == hashlib.sha256(nonce.encode()).hexdigest()
    ).with_for_update())
    if (
        challenge is None or challenge.fixture_id != fixture_id or challenge.wallet_address != wallet
        or challenge.chain_id != chain_id or challenge.consumed_at is not None
        or _utc(challenge.expires_at) <= now
    ):
        raise RegistrationError("invalid_challenge", "Registration challenge is expired, used, or mismatched", 409)
    try:
        recovered = Account.recover_message(encode_defunct(text=challenge.message), signature=signature)
    except (ValueError, TypeError) as exc:
        raise RegistrationError("invalid_signature", "Invalid wallet signature", 401) from exc
    if recovered != wallet:
        raise RegistrationError("invalid_signature", "Signature does not match the requested wallet", 401)
    fixture = _eligible(session, fixture_id, now)
    if fixture_snapshot(fixture) != challenge.fixture_snapshot:
        raise RegistrationError("fixture_changed", "Fixture changed after the message was signed; request a new challenge", 409)
    existing_job = _existing_job(session, fixture_id, lock=True)
    if not _allows_new_authorization(existing_job):
        raise RegistrationError("already_requested", "Fixture registration has already been requested", 409)
    since = now - timedelta(days=1)
    recent = session.scalar(select(func.count()).select_from(RegistrationChallenge).where(
        RegistrationChallenge.wallet_address == wallet,
        RegistrationChallenge.consumed_at >= since,
    )) or 0
    if recent >= MAX_JOBS_PER_WALLET_PER_DAY:
        raise RegistrationError("rate_limited", "Too many registration requests", 429)
    challenge.consumed_at = now
    if existing_job is None:
        job = FixtureRegistrationJob(
            fixture_id=fixture_id, requested_by=wallet, chain_id=chain_id,
            status="awaiting_abi", fixture_snapshot=challenge.fixture_snapshot,
            attempts=0, created_at=now, updated_at=now,
        )
        session.add(job)
    else:
        job = existing_job
        job.requested_by = wallet
        job.chain_id = chain_id
        job.fixture_snapshot = challenge.fixture_snapshot
        job.status = "awaiting_abi"
        job.transaction_hash = None
        job.error_code = None
        job.attempts = 0
        job.next_attempt_at = None
        job.updated_at = now
    session.flush()
    session.add(RegistrationJobEvent(job_id=job.id, status=job.status,
                                     fixture_snapshot=job.fixture_snapshot, recorded_at=now))
    return job
