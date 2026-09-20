#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "ci_scripts/validate_upstream_policy.py"
SPEC = importlib.util.spec_from_file_location("upstream_policy", VALIDATOR)
policy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(policy)


def append_entry(previous_hash: str) -> str:
    entry = {
        "entry_id": "0002",
        "recorded_at": "2026-09-20T13:00:00Z",
        "event": "assessment-verified",
        "actor": "repository-maintainers",
        "inputs": {
            "fork_develop_sha": "0e66db0c63f8ca348fd047275a787e07f78a6bd7",
            "upstream_develop_sha": "fb49f5b83b30de8b8c52b3b467e9ca29357fc131",
        },
        "decision": "Report-only assessment verified.",
        "previous_entry_sha256": previous_hash,
    }
    entry["entry_sha256"] = policy.canonical_hash(entry)
    return json.dumps(entry, separators=(",", ":"))


class UpstreamPolicyValidatorTests(unittest.TestCase):
    def copy_repository_files(self, root: Path) -> None:
        for relative in (
            ".seventwos",
            "app.yml",
            "Seventwos/Sources/Application/Settings/AppSettings.swift",
            "Components/Secrets/Secrets.swift",
            "ci_scripts/validate_release_readiness.sh",
            ".github/workflows/release-readiness.yml",
            ".github/workflows/upstream-assessment.yml",
        ):
            source = ROOT / relative
            destination = root / relative
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

    def run_validator(self, root: Path, **environment: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            text=True,
            capture_output=True,
            env=os.environ | environment,
            check=False,
        )

    def test_repository_policy_is_valid(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_broken_ledger_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_repository_files(root)
            ledger = root / ".seventwos/upstream-ledger.jsonl"
            entry = json.loads(ledger.read_text(encoding="utf-8"))
            entry["entry_sha256"] = "0" * 64
            ledger.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid entry_sha256", result.stderr)

    def test_rejects_empty_invariant_assertions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_repository_files(root)
            invariants_path = root / ".seventwos/upstream-invariants.json"
            invariants = json.loads(invariants_path.read_text(encoding="utf-8"))
            invariants["invariants"][0]["sources"][0]["must_contain"] = []
            invariants_path.write_text(json.dumps(invariants), encoding="utf-8")
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot be empty", result.stderr)

    def test_rejects_effective_job_permission_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_repository_files(root)
            workflow = root / ".github/workflows/upstream-assessment.yml"
            content = workflow.read_text(encoding="utf-8").replace(
                "  assess:\n    runs-on:", "  assess:\n    permissions:\n      contents: write\n    runs-on:"
            )
            workflow.write_text(content, encoding="utf-8")
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("effective permissions", result.stderr)

    def test_rejects_missing_policy_trigger_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_repository_files(root)
            workflow = root / ".github/workflows/upstream-assessment.yml"
            content = workflow.read_text(encoding="utf-8").replace(
                '      - "CODEOWNERS"\n', "", 1
            )
            workflow.write_text(content, encoding="utf-8")
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("trigger must cover", result.stderr)

    def test_rejects_forged_fork_or_upstream_evidence(self) -> None:
        state = json.loads((ROOT / ".seventwos/upstream-state.json").read_text(encoding="utf-8"))
        state["fork"]["develop_sha"] = "0" * 40
        with self.assertRaises(SystemExit):
            policy.validate_git_evidence(ROOT, state, False)

        state = json.loads((ROOT / ".seventwos/upstream-state.json").read_text(encoding="utf-8"))
        state["upstream"]["sha"] = "0" * 40
        with self.assertRaises(SystemExit):
            policy.validate_git_evidence(ROOT, state, True)

    def test_requires_base_and_rejects_ledger_rewrite_on_protected_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".seventwos").mkdir(parents=True)
            ledger = ROOT / ".seventwos/upstream-ledger.jsonl"
            destination = root / ".seventwos/upstream-ledger.jsonl"
            shutil.copy2(ledger, destination)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            destination.write_text(destination.read_text(encoding="utf-8") + append_entry(json.loads(ledger.read_text())["entry_sha256"]) + "\n", encoding="utf-8")
            policy.validate_ledger_base(root, destination, base, True)
            destination.write_text(destination.read_text(encoding="utf-8").replace('"entry_id":"0001"', '"entry_id":"evil"'), encoding="utf-8")
            with self.assertRaises(SystemExit):
                policy.validate_ledger_base(root, destination, base, True)
            with self.assertRaises(SystemExit):
                policy.validate_ledger_base(root, destination, "", True)


if __name__ == "__main__":
    unittest.main()
