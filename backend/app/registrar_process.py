"""Single-process registrar worker for Anvil or Sepolia."""

import argparse
import logging
import time

from app.chain_gateways import PredictionMarketRegistrationGateway
from app.config import get_settings
from app.database import SessionLocal
from app.indexer.rpc import EthereumJsonRpcClient
from app.registration_worker import activate_registration_job, next_registration_job


logger = logging.getLogger("acon.registrar")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit approved fixture registrations")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--activate-job", type=int)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.sepolia_rpc_url or not settings.prediction_market_address or not settings.registrar_private_key:
        logger.error("SEPOLIA_RPC_URL, PREDICTION_MARKET_ADDRESS, and REGISTRAR_PRIVATE_KEY are required")
        return 2
    rpc = EthereumJsonRpcClient(settings.sepolia_rpc_url)
    gateway = PredictionMarketRegistrationGateway(
        rpc, settings.prediction_market_address,
        settings.registrar_private_key.get_secret_value(), settings.indexer_chain_id,
        settings.signer_confirmation_depth,
    )
    try:
        if args.activate_job is not None:
            with SessionLocal() as session:
                activate_registration_job(session, args.activate_job)
                session.commit()
        while True:
            with SessionLocal() as session:
                job = next_registration_job(session, gateway)
                session.commit()
                if job:
                    logger.info("registration job=%s status=%s tx=%s", job.id, job.status, job.transaction_hash)
            if args.once:
                return 0
            time.sleep(settings.signer_poll_interval_seconds)
    finally:
        rpc.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(main())
