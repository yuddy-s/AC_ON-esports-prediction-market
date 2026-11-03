import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract_ci import classify, determine, main, parse_changed_paths


class ContractScopeTests(unittest.TestCase):
    def test_handoff_pr_uses_fast_path(self):
        paths = [
            "deployments/README.md", "docs/agent/CONTRACT_DEPLOYMENT.md",
            "deployments/abi/PredictionMarket.721a6fef039a.4af9297937eb.abi.json",
            "deployments/sepolia-2026-11-02/manifest.post-setup.json",
            "deployments/sepolia-2026-11-02/setup-verification.json",
            "deployments/sepolia-2026-11-02/receipts/07-safe-setup-0x" + "a" * 64 + ".json",
        ]
        self.assertTrue(classify("pull_request", paths))

    def test_executable_config_and_unknown_changes_require_full_checks(self):
        for path in [
            "contracts/src/PredictionMarket.sol", "contracts/test/Resolvers.t.sol",
            "contracts/script/export_handoff.py", "contracts/foundry.toml", "contracts/foundry.lock",
            "contracts/remappings.txt", "contracts/lib/prb-math", "contracts/security-requirements.txt",
            ".gitmodules", ".gitattributes", ".github/workflows/ci.yml", ".github/scripts/contract_ci.py",
            "deployments/build.json", "deployments/event-fixtures.anvil.json",
            "deployments/abi/PredictionMarket.abi.json", "deployments/sepolia-m3.json",
            "frontend/src/App.tsx", "backend/requirements.txt", "docs/helper.py",
            "deployments/sepolia-2026-11-02/unknown.json", "unrecognized.txt",
        ]:
            with self.subTest(path=path):
                self.assertFalse(classify("pull_request", ["README.md", path]))

    def test_pushes_manual_runs_and_empty_diffs_are_full(self):
        for event in ("push", "workflow_dispatch", "schedule", "pull_request_target", ""):
            self.assertFalse(classify(event, ["README.md"]))
        self.assertFalse(classify("pull_request", []))

    def test_rename_or_delete_cannot_hide_source_changes(self):
        paths = parse_changed_paths(b"R100\0contracts/src/Old.sol\0docs/old.md\0D\0contracts/test/Old.t.sol\0")
        self.assertEqual(paths, ["contracts/src/Old.sol", "docs/old.md", "contracts/test/Old.t.sol"])
        self.assertFalse(classify("pull_request", paths))

    def test_document_renames_spaces_and_newlines_parse_without_shell_splitting(self):
        paths = parse_changed_paths(b"R095\0docs/old name.md\0docs/new name.md\0A\0docs/line\nbreak.md\0")
        self.assertEqual(len(paths), 3)
        self.assertTrue(classify("pull_request", paths))

    def test_unsafe_or_lookalike_paths_are_not_documentation(self):
        for path in ("/docs/file.md", "docs/../contracts/README.md", "docs\\file.md", "deployments/x/secret.py", "README.md.sh"):
            self.assertFalse(classify("pull_request", [path]))

    def test_missing_invalid_or_unavailable_base_falls_back_to_full(self):
        for base in ("", "0" * 40, "main", "--help"):
            fast, _, _ = determine(Path.cwd(), "pull_request", base)
            self.assertFalse(fast)
        with patch("contract_ci.changed_paths", side_effect=subprocess.CalledProcessError(128, "git")):
            fast, reason, _ = determine(Path.cwd(), "pull_request", "1" * 40)
            self.assertFalse(fast)
            self.assertIn("unavailable", reason)

    def test_malformed_diff_is_rejected(self):
        for output in (b"A\0README.md", b"R100\0README.md\0", b"?\0README.md\0"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                parse_changed_paths(output)

    def test_output_is_explicit_false_when_detection_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs"
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}), patch.object(
                sys, "argv", ["contract_ci.py", "--event", "pull_request", "--base", "bad"]
            ), patch("builtins.print"):
                main()
            self.assertEqual(output.read_text(), "fast_path=false\n")


if __name__ == "__main__":
    unittest.main()
