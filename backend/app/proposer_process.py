"""Single-process reviewed-result proposer worker for Anvil or Sepolia."""

import argparse
import logging
import time

from app.chain_gateways import PredictionMarketOracleGateway
from app.config import get_settings
from app.database import SessionLocal
from app.indexer.rpc import EthereumJsonRpcClient
from app.oracle_worker import run_oracle_once


logger = logging.getLogger("acon.proposer")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit independently reviewed result proposals")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.sepolia_rpc_url or not settings.prediction_market_address or not settings.proposer_private_key:
        logger.error("SEPOLIA_RPC_URL, PREDICTION_MARKET_ADDRESS, and PROPOSER_PRIVATE_KEY are required")
        return 2
    rpc = EthereumJsonRpcClient(settings.sepolia_rpc_url)
    gateway = PredictionMarketOracleGateway(
        rpc, settings.prediction_market_address,
        settings.proposer_private_key.get_secret_value(), settings.indexer_chain_id,
        settings.signer_confirmation_depth,
    )
    try:
        while True:
            with SessionLocal() as session:
                count = run_oracle_once(session, gateway)
                session.commit()
                logger.info("proposal intents processed=%s", count)
            if args.once:
                return 0
            time.sleep(settings.signer_poll_interval_seconds)
    finally:
        rpc.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(main())
