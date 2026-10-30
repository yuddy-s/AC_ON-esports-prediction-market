"""Signed, single-use requests for curated fixture registration.

No chain write is performed until the M4 registrar ABI and role grant are frozen.
"""

from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import is_address, to_checksum_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Fixture, FixtureRegistrationJob, FixtureResultObservation, RegistrationChallenge


CHALLENGE_LIFETIME = timedelta(minutes=5)
MINIMUM_START_BUFFER = timedelta(minutes=30)
MAX_CHALLENGES_PER_DAY = 12
MAX_JOBS_PER_WALLET_PER_DAY = 3


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
        raise RegistrationError("fixture_ineligible", "Fixture lacks verified source metadata", 409)
    if session.scalar(select(FixtureResultObservation.id).where(FixtureResultObservation.fixture_id == fixture_id)) is not None:
        raise RegistrationError("fixture_ineligible", "Fixture already has an observed result", 409)
    return fixture


def _message(fixture: Fixture, wallet: str, chain_id: int, nonce: str, expires_at: datetime, origin: str) -> str:
    # The exact message is stored, then recovered. Never reconstruct it from mutable fixture fields.
    return (
        "AC_ON fixture registration request\n"
        f"Origin: {origin}\n"
        f"Chain ID: {chain_id}\n"
        f"Fixture ID: {fixture.id}\n"
        f"Source: {fixture.provider_id}/{fixture.game_id}/{fixture.external_match_id}\n"
        f"Wallet: {wallet}\n"
        f"Nonce: {nonce}\n"
        f"Expires at: {expires_at.isoformat()}\n"
        "This requests registration only. Market creation requires a separate wallet transaction."
    )


def create_challenge(
    session: Session, fixture_id: int, wallet_address: str, chain_id: int, origin: str,
    *, now: datetime | None = None,
) -> tuple[RegistrationChallenge, str]:
    now = now or datetime.now(UTC)
    wallet = _address(wallet_address)
    fixture = _eligible(session, fixture_id, now)
    if session.scalar(select(FixtureRegistrationJob.id).where(FixtureRegistrationJob.fixture_id == fixture_id)) is not None:
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
    challenge = RegistrationChallenge(
        fixture_id=fixture_id,
        wallet_address=wallet,
        chain_id=chain_id,
        nonce_hash=hashlib.sha256(nonce.encode()).hexdigest(),
        message=_message(fixture, wallet, chain_id, nonce, expires_at, origin),
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
    _eligible(session, fixture_id, now)
    if session.scalar(select(FixtureRegistrationJob.id).where(FixtureRegistrationJob.fixture_id == fixture_id)) is not None:
        raise RegistrationError("already_requested", "Fixture registration has already been requested", 409)
    since = now - timedelta(days=1)
    recent = session.scalar(select(func.count()).select_from(FixtureRegistrationJob).where(
        FixtureRegistrationJob.requested_by == wallet,
        FixtureRegistrationJob.created_at >= since,
    )) or 0
    if recent >= MAX_JOBS_PER_WALLET_PER_DAY:
        raise RegistrationError("rate_limited", "Too many registration requests", 429)
    challenge.consumed_at = now
    job = FixtureRegistrationJob(
        fixture_id=fixture_id, requested_by=wallet, chain_id=chain_id,
        status="awaiting_abi", attempts=0, created_at=now, updated_at=now,
    )
    session.add(job)
    session.flush()
    return job
