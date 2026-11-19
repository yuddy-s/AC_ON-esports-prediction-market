"""Read-only M5 smoke check for the public frontend, API, and indexer."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx


def _url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid public URL: {value!r}")
    return value.rstrip("/")


def _manifest_market(document: dict[str, object]) -> tuple[int, str, int, str]:
    contracts = document.get("contracts")
    if not isinstance(contracts, dict):
        raise ValueError("manifest contracts object is missing")
    market = contracts.get("PredictionMarket")
    if not isinstance(market, dict):
        raise ValueError("manifest PredictionMarket entry is missing")
    chain_id = document.get("chain_id")
    address = market.get("address")
    deployment_block = market.get("deployment_block")
    abi_path = market.get("abi_path")
    if not isinstance(chain_id, int) or not isinstance(address, str):
        raise ValueError("manifest chain ID or market address is invalid")
    if not isinstance(deployment_block, int) or not isinstance(abi_path, str):
        raise ValueError("manifest market deployment block or ABI path is invalid")
    return chain_id, address, deployment_block, Path(abi_path).name


def verify_public_stack(
    client: httpx.Client,
    *,
    api_base_url: str,
    frontend_url: str,
    manifest: dict[str, object],
    max_indexer_age_seconds: int,
    max_indexer_lag_blocks: int = 20,
    now: datetime | None = None,
) -> dict[str, object]:
    if max_indexer_age_seconds < 1 or max_indexer_lag_blocks < 0:
        raise ValueError("indexer age must be positive and block lag must be non-negative")
    api = _url(api_base_url)
    frontend = _url(frontend_url)
    expected_chain, expected_address, expected_block, expected_abi = _manifest_market(manifest)

    frontend_response = client.get(frontend)
    frontend_response.raise_for_status()
    health_response = client.get(f"{api}/health")
    health_response.raise_for_status()
    health = health_response.json()
    if health.get("status") != "ok" or health.get("database") != "available":
        raise ValueError("public API health or database status is not healthy")

    cors_response = client.options(
        f"{api}/api/v2/indexer/status",
        headers={"Origin": frontend, "Access-Control-Request-Method": "GET"},
    )
    cors_response.raise_for_status()
    allowed_origin = cors_response.headers.get("access-control-allow-origin")
    if allowed_origin != frontend:
        raise ValueError(f"CORS origin mismatch: expected {frontend}, received {allowed_origin!r}")

    status_response = client.get(f"{api}/api/v2/indexer/status", headers={"Origin": frontend})
    status_response.raise_for_status()
    get_allowed_origin = status_response.headers.get("access-control-allow-origin")
    if get_allowed_origin != frontend:
        raise ValueError(
            f"CORS GET origin mismatch: expected {frontend}, received {get_allowed_origin!r}"
        )
    status = status_response.json()
    expected = {
        "chain_id": expected_chain,
        "contract_address": expected_address.lower(),
        "deployment_block": expected_block,
        "abi_version": expected_abi,
    }
    actual = {
        "chain_id": status.get("chain_id"),
        "contract_address": str(status.get("contract_address") or "").lower(),
        "deployment_block": status.get("deployment_block"),
        "abi_version": status.get("abi_version"),
    }
    if not status.get("configured") or actual != expected:
        raise ValueError(f"indexer configuration mismatch: expected {expected}, received {actual}")
    safe_block = status.get("last_safe_block")
    latest_block = status.get("latest_observed_block")
    if not isinstance(safe_block, int) or not isinstance(latest_block, int) or safe_block < expected_block:
        raise ValueError("indexer has not reached the deployment block")
    if safe_block > latest_block:
        raise ValueError("indexer safe block is ahead of its observed head")
    lag_blocks = latest_block - safe_block
    if lag_blocks > max_indexer_lag_blocks:
        raise ValueError(
            f"indexer block lag exceeds limit: lag={lag_blocks}, limit={max_indexer_lag_blocks}"
        )
    updated_text = status.get("updated_at")
    if not isinstance(updated_text, str):
        raise ValueError("indexer update timestamp is missing")
    updated_at = datetime.fromisoformat(updated_text.replace("Z", "+00:00")).astimezone(UTC)
    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    age_seconds = (checked_at - updated_at).total_seconds()
    if age_seconds < -60 or age_seconds > max_indexer_age_seconds:
        raise ValueError(f"indexer update is stale or invalid: age={age_seconds:.0f}s")

    return {
        "schema_version": 1,
        "checked_at": checked_at.isoformat().replace("+00:00", "Z"),
        "frontend_url": frontend,
        "api_base_url": api,
        "health": "pass",
        "cors": "pass",
        "indexer": {
            **expected,
            "latest_observed_block": latest_block,
            "safe_block": safe_block,
            "lag_blocks": lag_blocks,
            "max_lag_blocks": max_indexer_lag_blocks,
            "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
            "age_seconds": int(age_seconds),
            "max_age_seconds": max_indexer_age_seconds,
        },
        "status": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--max-indexer-age-seconds", type=int, default=120)
    parser.add_argument("--max-indexer-lag-blocks", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.max_indexer_age_seconds < 1:
        parser.error("--max-indexer-age-seconds must be positive")
    if args.max_indexer_lag_blocks < 0:
        parser.error("--max-indexer-lag-blocks must be non-negative")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            result = verify_public_stack(
                client,
                api_base_url=args.api_base_url,
                frontend_url=args.frontend_url,
                manifest=manifest,
                max_indexer_age_seconds=args.max_indexer_age_seconds,
                max_indexer_lag_blocks=args.max_indexer_lag_blocks,
            )
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"public smoke failed: {exc}\n")
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
