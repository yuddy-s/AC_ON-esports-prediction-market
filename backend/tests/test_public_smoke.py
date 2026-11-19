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


def _handler(
    request: httpx.Request,
    *,
    stale: bool = False,
    preflight_cors: str = FRONTEND,
    get_cors: str | None = FRONTEND,
    lag_blocks: int = 2,
) -> httpx.Response:
    if str(request.url).rstrip("/") == FRONTEND:
        return httpx.Response(200, text="AC_ON")
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok", "database": "available"})
    if request.method == "OPTIONS" and request.url.path == "/api/v2/indexer/status":
        return httpx.Response(200, headers={"access-control-allow-origin": preflight_cors})
    if request.url.path == "/api/v2/indexer/status":
        updated = NOW - timedelta(minutes=10) if stale else NOW
        headers = {"access-control-allow-origin": get_cors} if get_cors is not None else {}
        return httpx.Response(200, json={
            "configured": True,
            "chain_id": 11155111,
            "contract_address": ADDRESS.lower(),
            "deployment_block": 12051223,
            "abi_version": ABI,
            "latest_observed_block": 12100002,
            "last_safe_block": 12100002 - lag_blocks,
            "updated_at": updated.isoformat(),
        }, headers=headers)
    return httpx.Response(404)


def test_public_smoke_accepts_matching_healthy_stack() -> None:
    with httpx.Client(transport=httpx.MockTransport(_handler)) as client:
        result = verify_public_stack(
            client, api_base_url=API, frontend_url=FRONTEND, manifest=_manifest(),
            max_indexer_age_seconds=120, max_indexer_lag_blocks=20, now=NOW,
        )
    assert result["status"] == "pass"
    assert result["indexer"]["safe_block"] == 12100000


@pytest.mark.parametrize(
    ("handler", "message"),
    [
        (lambda request: _handler(request, stale=True), "stale"),
        (
            lambda request: _handler(request, preflight_cors="https://wrong.example"),
            "CORS origin mismatch",
        ),
        (lambda request: _handler(request, get_cors=None), "CORS GET origin mismatch"),
        (lambda request: _handler(request, lag_blocks=48_779), "block lag exceeds limit"),
    ],
)
def test_public_smoke_rejects_unready_stack(handler, message: str) -> None:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match=message):
            verify_public_stack(
                client, api_base_url=API, frontend_url=FRONTEND, manifest=_manifest(),
                max_indexer_age_seconds=120, max_indexer_lag_blocks=20, now=NOW,
            )
