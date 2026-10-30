from collections.abc import Generator
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_collection.db")

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, get_session
from app.fixture_data import FixtureImportDocument, deterministic_mock
from app.fixture_service import import_document
from app.main import app
from app.models import Fixture, FixtureRegistrationJob, RegistrationChallenge, RegistrationJobEvent
from app.registration_service import RegistrationError, cleanup_expired_challenges, create_challenge, request_registration
from app.registration_worker import (
    GatewayUnavailable, SubmissionUncertain, activate_registration_job, process_registration_job,
)


@pytest.fixture()
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'registration.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        sample = deterministic_mock().model_dump(mode="json")
        sample["fixtures"][0]["match_status"] = "scheduled"
        sample["results"] = []
        import_document(session, FixtureImportDocument.model_validate(sample))
        fixture = session.get(Fixture, 1)
        assert fixture is not None
        session.commit()
        yield session
    engine.dispose()


def _signed_request(session: Session, wallet, *, now: datetime) -> tuple[str, str]:
    challenge, nonce = create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=now)
    session.commit()
    signature = Account.sign_message(encode_defunct(text=challenge.message), wallet.key).signature.hex()
    return nonce, signature


def test_signed_request_is_single_use_and_never_claims_chain_registration(session: Session) -> None:
    wallet = Account.create()
    now = datetime(2029, 12, 1, tzinfo=UTC)
    nonce, signature = _signed_request(session, wallet, now=now)
    job = request_registration(session, 1, wallet.address, nonce, signature, 11155111, now=now)
    session.commit()
    assert job.status == "awaiting_abi"
    assert job.transaction_hash is None
    assert session.scalar(select(func.count()).select_from(RegistrationChallenge)) == 1
    assert session.scalar(select(func.count()).select_from(FixtureRegistrationJob)) == 1
    with pytest.raises(RegistrationError, match="expired, used, or mismatched"):
        request_registration(session, 1, wallet.address, nonce, signature, 11155111, now=now)


def test_rejects_wrong_wallet_chain_expiry_and_bad_signature(session: Session) -> None:
    wallet = Account.create()
    other = Account.create()
    now = datetime(2029, 12, 1, tzinfo=UTC)
    nonce, signature = _signed_request(session, wallet, now=now)
    for address, chain, when, signed in [
        (other.address, 11155111, now, signature),
        (wallet.address, 31337, now, signature),
        (wallet.address, 11155111, now + timedelta(minutes=5), signature),
        (wallet.address, 11155111, now, Account.sign_message(encode_defunct(text="wrong"), other.key).signature.hex()),
        (wallet.address, 11155111, now, "0xzz"),
    ]:
        with pytest.raises(RegistrationError):
            request_registration(session, 1, address, nonce, signed, chain, now=when)
        session.rollback()
    assert session.scalar(select(func.count()).select_from(FixtureRegistrationJob)) == 0


def test_fixture_eligibility_and_request_deduplication(session: Session) -> None:
    wallet = Account.create()
    now = datetime(2029, 12, 1, tzinfo=UTC)
    fixture = session.get(Fixture, 1)
    assert fixture is not None
    fixture.match_status = "completed"
    session.commit()
    with pytest.raises(RegistrationError, match="not scheduled"):
        create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=now)
    fixture.match_status = "scheduled"
    session.commit()
    nonce, signature = _signed_request(session, wallet, now=now)
    request_registration(session, 1, wallet.address, nonce, signature, 11155111, now=now)
    session.commit()
    with pytest.raises(RegistrationError, match="already been requested"):
        create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=now)


def test_fixture_snapshot_prevents_changed_metadata_after_signature(session: Session) -> None:
    wallet = Account.create()
    now = datetime(2029, 12, 1, tzinfo=UTC)
    nonce, signature = _signed_request(session, wallet, now=now)
    fixture = session.get(Fixture, 1)
    assert fixture is not None
    fixture.team_a_name = "Changed Name"
    session.commit()
    with pytest.raises(RegistrationError) as error:
        request_registration(session, 1, wallet.address, nonce, signature, 11155111, now=now)
    assert error.value.code == "fixture_changed"


def test_expired_challenge_cleanup_preserves_recent_rate_window(session: Session) -> None:
    wallet = Account.create()
    old = datetime(2029, 12, 1, tzinfo=UTC)
    create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=old)
    create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=old + timedelta(hours=2))
    session.commit()
    assert cleanup_expired_challenges(session, now=old + timedelta(days=1, hours=1)) == 1
    assert session.scalar(select(func.count()).select_from(RegistrationChallenge)) == 1


def test_challenge_rate_limit_is_enforced_per_wallet(session: Session) -> None:
    wallet = Account.create()
    now = datetime(2029, 12, 1, tzinfo=UTC)
    for _ in range(12):
        create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=now)
    session.commit()
    with pytest.raises(RegistrationError) as error:
        create_challenge(session, 1, wallet.address, 11155111, "http://localhost:5173", now=now)
    assert error.value.code == "rate_limited"


def test_database_constraint_prevents_two_jobs_for_one_fixture(session: Session) -> None:
    wallet = Account.create()
    now = datetime(2029, 12, 1, tzinfo=UTC)
    nonce, signature = _signed_request(session, wallet, now=now)
    job = request_registration(session, 1, wallet.address, nonce, signature, 11155111, now=now)
    session.commit()
    session.add(FixtureRegistrationJob(
        fixture_id=1, requested_by=wallet.address, chain_id=11155111,
        fixture_snapshot=job.fixture_snapshot, status="queued", attempts=0,
        created_at=now, updated_at=now,
    ))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert session.scalar(select(func.count()).select_from(FixtureRegistrationJob)) == 1


class FakeRegistrationGateway:
    def __init__(self) -> None:
        self.state = "absent"
        self.receipt = "pending"
        self.submit_calls = 0
        self.fail_before_submit = False
        self.uncertain_submit = False

    def registration_state(self, _snapshot):
        return self.state

    def receipt_state(self, _transaction_hash):
        return self.receipt

    def submit(self, _snapshot):
        self.submit_calls += 1
        if self.fail_before_submit:
            raise GatewayUnavailable("offline")
        if self.uncertain_submit:
            raise SubmissionUncertain("unknown")
        return "0x" + "ab" * 32


def _activated_job(session: Session, *, now: datetime) -> FixtureRegistrationJob:
    wallet = Account.create()
    nonce, signature = _signed_request(session, wallet, now=now)
    job = request_registration(session, 1, wallet.address, nonce, signature, 11155111, now=now)
    activate_registration_job(session, job.id, now=now)
    session.commit()
    assert job.status == "queued"
    return job


def test_worker_never_confirms_from_receipt_alone_or_resubmits_known_hash(session: Session) -> None:
    now = datetime(2029, 12, 1, tzinfo=UTC)
    job = _activated_job(session, now=now)
    gateway = FakeRegistrationGateway()
    process_registration_job(session, job.id, gateway, now=now)
    assert job.status == "submitted" and gateway.submit_calls == 1
    gateway.receipt = "success"
    process_registration_job(session, job.id, gateway, now=now + timedelta(seconds=31))
    assert job.status == "submitted" and gateway.submit_calls == 1
    gateway.state = "matching"
    process_registration_job(session, job.id, gateway, now=now + timedelta(seconds=62))
    session.commit()
    assert job.status == "confirmed" and gateway.submit_calls == 1
    assert [event.status for event in session.scalars(select(RegistrationJobEvent).order_by(RegistrationJobEvent.id))] == [
        "awaiting_abi", "queued", "submitted", "submitted", "confirmed"
    ]


def test_worker_retries_only_known_pre_submit_failure(session: Session) -> None:
    now = datetime(2029, 12, 1, tzinfo=UTC)
    job = _activated_job(session, now=now)
    gateway = FakeRegistrationGateway()
    gateway.fail_before_submit = True
    process_registration_job(session, job.id, gateway, now=now)
    assert job.status == "retryable_failure" and job.attempts == 1
    gateway.fail_before_submit = False
    process_registration_job(session, job.id, gateway, now=now + timedelta(seconds=10))
    assert gateway.submit_calls == 1  # not due yet
    process_registration_job(session, job.id, gateway, now=now + timedelta(seconds=31))
    assert job.status == "submitted" and gateway.submit_calls == 2


def test_uncertain_submission_requires_manual_reconciliation(session: Session) -> None:
    now = datetime(2029, 12, 1, tzinfo=UTC)
    job = _activated_job(session, now=now)
    gateway = FakeRegistrationGateway()
    gateway.uncertain_submit = True
    process_registration_job(session, job.id, gateway, now=now)
    assert job.status == "submission_unknown" and job.transaction_hash is None
    process_registration_job(session, job.id, gateway, now=now + timedelta(hours=1))
    assert gateway.submit_calls == 1


def test_worker_rechecks_snapshot_and_ineligibility_before_submission(session: Session) -> None:
    now = datetime(2029, 12, 1, tzinfo=UTC)
    job = _activated_job(session, now=now)
    fixture = session.get(Fixture, 1)
    assert fixture is not None
    fixture.team_b_name = "Changed"
    session.commit()
    gateway = FakeRegistrationGateway()
    process_registration_job(session, job.id, gateway, now=now)
    assert job.status == "terminal_failure" and job.error_code == "fixture_changed"
    assert gateway.submit_calls == 0


def test_registration_api_returns_job_status(session: Session) -> None:
    wallet = Account.create()

    def override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            response = client.post("/api/fixtures/1/registration-challenges", json={"wallet_address": wallet.address})
            assert response.status_code == 201
            challenge = response.json()
            signature = Account.sign_message(encode_defunct(text=challenge["message"]), wallet.key).signature.hex()
            job = client.post("/api/fixtures/1/registration-requests", json={
                "wallet_address": wallet.address, "nonce": challenge["nonce"], "signature": signature,
            })
            assert job.status_code == 202
            assert job.json()["status"] == "awaiting_abi"
            assert client.get("/api/fixtures/1/registration").json()["id"] == job.json()["id"]
            assert client.get("/api/fixtures/1").json()["registration_request_status"] == "awaiting_abi"
            assert client.get("/api/fixtures").json()["items"][0]["registration_request_status"] == "awaiting_abi"
            assert client.post("/api/fixtures/1/registration-requests", json={
                "wallet_address": wallet.address, "nonce": challenge["nonce"], "signature": signature,
            }).status_code == 409
    finally:
        app.dependency_overrides.clear()
