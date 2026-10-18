#!/usr/bin/env python3
"""Exercise the actual CodeQL workflow's resolved-build-settings guard."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/codeql.yml"


class CodeQLBuildSettingsTests(unittest.TestCase):
    def run_guard(self, settings):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        start = workflow.index("          import json\n")
        end = workflow.index("\n          PY", start)
        script = "\n".join(line[10:] for line in workflow[start:end].splitlines())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps([{"target": "Seventwos", "buildSettings": settings}]),
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, "-c", script, str(path)],
                capture_output=True,
                text=True,
            )

    def test_serial_intel_simulator_settings_pass(self):
        result = self.run_guard({
            "PLATFORM_NAME": "iphonesimulator",
            "ARCHS": "x86_64 arm64",
            "EXCLUDED_ARCHS": "arm64",
            "OTHER_SWIFT_FLAGS": "-DDEBUG -j1",
        })
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_architecture_fails(self):
        result = self.run_guard({
            "PLATFORM_NAME": "iphonesimulator",
            "ARCHS": "arm64",
            "EXCLUDED_ARCHS": "",
            "OTHER_SWIFT_FLAGS": "-j1",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected only x86_64", result.stderr)

    @unittest.skipIf(os.name == "nt", "Requires the macOS/Linux Bash execution environment")
    def test_wrapper_preserves_toolchain_discovery(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        start = workflow.index('          CODEQL_REAL_SWIFTC="$(xcrun --find swiftc)"')
        end = workflow.index("\n      - name: Initialize CodeQL", start)
        script = "\n".join(line[10:] for line in workflow[start:end].splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            toolchain = root / "toolchain/usr"
            (toolchain / "bin").mkdir(parents=True)
            (toolchain / "lib").mkdir()
            (toolchain / "share/swift").mkdir(parents=True)
            features = toolchain / "share/swift/features.json"
            features.write_text('{"features": ["package-name-if-supported"]}', encoding="utf-8")
            compiler = toolchain / "bin/swiftc"
            compiler.write_text("#!/bin/bash\necho 'test compiler'\n", encoding="utf-8")
            compiler.chmod(0o755)
            env = {
                **os.environ,
                "RUNNER_TEMP": directory,
                "GITHUB_ENV": str(root / "env"),
            }
            prelude = f'xcrun() {{ printf "%s\\n" "{compiler}"; }}\n'
            subprocess.run(
                ["bash", "-eu", "-c", prelude + script],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
            )
            wrapper_usr = root / "codeql-swiftc"
            self.assertEqual((wrapper_usr / "share/swift/features.json").read_bytes(), features.read_bytes())
            self.assertEqual((wrapper_usr / "lib").resolve(), (toolchain / "lib").resolve())

    @unittest.skipIf(os.name == "nt", "Requires the macOS/Linux Bash execution environment")
    def test_driver_cap_follows_xcode_arguments(self):
        wrapper = ROOT / "ci_scripts/codeql_swiftc.sh"
        env = {**os.environ, "CODEQL_REAL_SWIFTC": "/usr/bin/printf"}
        result = subprocess.run(
            ["bash", str(wrapper), "%s\n", "-j1", "-j4", "source with spaces.swift"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.splitlines(), [
            "-j1", "-j4", "source with spaces.swift",
            "-j1", "-driver-batch-size-limit", "100",
        ])

    @unittest.skipIf(os.name == "nt", "Requires the macOS/Linux Bash execution environment")
    def test_frontend_invocation_is_unchanged(self):
        wrapper = ROOT / "ci_scripts/codeql_swiftc.sh"
        env = {**os.environ, "CODEQL_REAL_SWIFTC": "/usr/bin/printf"}
        result = subprocess.run(
            ["bash", str(wrapper), "%s\n", "-frontend", "source with spaces.swift"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.splitlines(), ["-frontend", "source with spaces.swift"])


if __name__ == "__main__":
    unittest.main()
