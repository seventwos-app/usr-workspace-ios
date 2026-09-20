#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "ci_scripts/validate_upstream_policy.py"


class UpstreamPolicyValidatorTests(unittest.TestCase):
    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_repository_policy_is_valid(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_broken_ledger_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["cp", "-R", str(ROOT / ".seventwos"), str(root)], check=True)
            (root / "app.yml").write_text((ROOT / "app.yml").read_text(encoding="utf-8"), encoding="utf-8")
            for relative in (
                "Seventwos/Sources/Application/Settings/AppSettings.swift",
                "Components/Secrets/Secrets.swift",
                "ci_scripts/validate_release_readiness.sh",
                ".github/workflows/release-readiness.yml",
                ".github/workflows/upstream-assessment.yml",
            ):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            ledger = root / ".seventwos/upstream-ledger.jsonl"
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            entry["entry_sha256"] = "0" * 64
            ledger.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid entry_sha256", result.stderr)


if __name__ == "__main__":
    unittest.main()
