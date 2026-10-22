"""Validate a completed public Sepolia deployment manifest and exact ABI files."""

import argparse
from pathlib import Path

from app.indexer.handoff import load_deployment_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        handoff = load_deployment_handoff(args.manifest)
    except ValueError as exc:
        parser.exit(1, f"invalid deployment handoff: {exc}\n")
    print(
        f"valid Sepolia handoff: market={handoff.market.address} "
        f"deployment_block={handoff.market.deployment_block} "
        f"abi_version={handoff.market.abi_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
