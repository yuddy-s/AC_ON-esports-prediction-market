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
from sqlalchemy.orm import Session

from app.database import Base, get_session
from app.fixture_data import FixtureImportDocument, deterministic_mock
from app.fixture_service import import_document
from app.main import app
from app.models import Fixture, FixtureRegistrationJob, RegistrationChallenge
from app.registration_service import RegistrationError, create_challenge, request_registration


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
            assert client.post("/api/fixtures/1/registration-requests", json={
                "wallet_address": wallet.address, "nonce": challenge["nonce"], "signature": signature,
            }).status_code == 409
    finally:
        app.dependency_overrides.clear()
