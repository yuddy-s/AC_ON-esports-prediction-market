"""Select a lighter test schedule only for known documentation/static-record PRs."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


CONTRACT_NAMES = r"(?:ACONTestToken|MarketPricing|PredictionMarket|ResolverRegistry)"
VERSIONED_ABI = re.compile(rf"deployments/abi/{CONTRACT_NAMES}\.[0-9a-f]{{12}}\.[0-9a-f]{{12}}\.abi\.json")
HANDOFF_FILE = re.compile(
    r"deployments/sepolia-\d{4}-\d{2}-\d{2}/(?:"
    r"manifest(?:\.post-setup)?\.json|build\.snapshot\.json|verification\.json|"
    r"setup-verification\.json|safe-setup\.json|transactions\.json|"
    r"preflight-checks\.json|callback-gas-probe\.json|"
    r"receipts/(?:\d{2}(?:-safe-setup)?|failed)-0x[0-9a-f]{64}\.json)"
)
DOC_EXTENSIONS = {".md", ".png", ".jpg", ".jpeg", ".svg", ".pdf", ".excalidraw", ".docx"}


def is_documentation_change(path):
    parts = PurePosixPath(path).parts
    if not parts or path.startswith("/") or ".." in parts or "\\" in path:
        return False
    if path in {"README.md", "contracts/README.md", "backend/README.md", "frontend/README.md"}:
        return True
    if path.startswith("docs/") and PurePosixPath(path).suffix.lower() in DOC_EXTENSIONS:
        return True
    if path.startswith("deployments/") and path.endswith(".md"):
        return True
    return bool(VERSIONED_ABI.fullmatch(path) or HANDOFF_FILE.fullmatch(path))


def parse_changed_paths(output):
    """Keep both paths of renames/copies; a moved source file must still force full CI."""
    tokens = output.decode("utf-8").split("\0")
    if tokens[-1] != "":
        raise ValueError("Truncated git diff output")
    tokens.pop()
    paths = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not re.fullmatch(r"(?:[ADMTUXB]|[RC]\d{1,3})", status):
            raise ValueError("Unknown change status")
        count = 2 if status[0] in "RC" else 1
        if index + count > len(tokens):
            raise ValueError("Missing changed path")
        paths.extend(tokens[index:index + count])
        index += count
    return paths


def changed_paths(root, base):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", base or "") or int(base, 16) == 0:
        raise ValueError("Missing or invalid base commit")
    result = subprocess.run(
        ["git", "diff", "--name-status", "-z", "--find-renames", base, "HEAD", "--"],
        cwd=root, capture_output=True, check=True,
    )
    return parse_changed_paths(result.stdout)


def classify(event, paths):
    return event == "pull_request" and bool(paths) and all(is_documentation_change(path) for path in paths)


def determine(root, event, base):
    if event != "pull_request":
        return False, "Non-PR events always run the full contract checks", []
    try:
        paths = changed_paths(root, base)
    except (ValueError, OSError, subprocess.CalledProcessError):
        return False, "Change detection unavailable; running full contract checks", []
    fast = classify(event, paths)
    reason = "Known documentation/static-record-only PR" if fast else "Executable, build, unknown, or empty change set"
    return fast, reason, paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--base", default=os.environ.get("CI_BASE_SHA", ""))
    args = parser.parse_args()
    fast, reason, paths = determine(args.root, args.event, args.base)
    print(json.dumps({"fast_path": fast, "reason": reason, "changed_paths": paths}, indent=2))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as stream:
            stream.write(f"fast_path={'true' if fast else 'false'}\n")


if __name__ == "__main__":
    main()
