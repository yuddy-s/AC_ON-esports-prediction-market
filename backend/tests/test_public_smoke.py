from datetime import UTC, datetime, timedelta

import httpx
import pytest

from scripts.smoke_public import verify_public_stack


NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
FRONTEND = "https://acon.example"
API = "https://acon-api.example"
ADDRESS = "0x03ae48f03C7822540a91DA2168602bd49dC510E9"
ABI = "PredictionMarket.721a6fef039a.4af9297937eb.abi.json"


def _manifest() -> dict[str, object]:
    return {
        "chain_id": 11155111,
        "contracts": {"PredictionMarket": {
            "address": ADDRESS,
            "deployment_block": 12051223,
            "abi_path": f"deployments/abi/{ABI}",
        }},
    }


def _handler(request: httpx.Request, *, stale: bool = False, cors: str = FRONTEND) -> httpx.Response:
    if str(request.url).rstrip("/") == FRONTEND:
        return httpx.Response(200, text="AC_ON")
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok", "database": "available"})
    if request.method == "OPTIONS" and request.url.path == "/api/v2/indexer/status":
        return httpx.Response(200, headers={"access-control-allow-origin": cors})
    if request.url.path == "/api/v2/indexer/status":
        updated = NOW - timedelta(minutes=10) if stale else NOW
        return httpx.Response(200, json={
            "configured": True,
            "chain_id": 11155111,
            "contract_address": ADDRESS.lower(),
            "deployment_block": 12051223,
            "abi_version": ABI,
            "latest_observed_block": 12100002,
            "last_safe_block": 12100000,
            "updated_at": updated.isoformat(),
        })
    return httpx.Response(404)


def test_public_smoke_accepts_matching_healthy_stack() -> None:
    with httpx.Client(transport=httpx.MockTransport(_handler)) as client:
        result = verify_public_stack(
            client, api_base_url=API, frontend_url=FRONTEND, manifest=_manifest(),
            max_indexer_age_seconds=120, now=NOW,
        )
    assert result["status"] == "pass"
    assert result["indexer"]["safe_block"] == 12100000


@pytest.mark.parametrize(
    ("handler", "message"),
    [
        (lambda request: _handler(request, stale=True), "stale"),
        (lambda request: _handler(request, cors="https://wrong.example"), "CORS origin mismatch"),
    ],
)
def test_public_smoke_rejects_stale_or_wrong_origin(handler, message: str) -> None:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match=message):
            verify_public_stack(
                client, api_base_url=API, frontend_url=FRONTEND, manifest=_manifest(),
                max_indexer_age_seconds=120, now=NOW,
            )
