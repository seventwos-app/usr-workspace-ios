#!/usr/bin/env python3
"""Exercise the actual CodeQL workflow's resolved-build-settings guard."""

import json
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

    def test_missing_swift_driver_cap_fails(self):
        result = self.run_guard({
            "PLATFORM_NAME": "iphonesimulator",
            "ARCHS": "x86_64",
            "EXCLUDED_ARCHS": "arm64",
            "OTHER_SWIFT_FLAGS": "-DDEBUG",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing Swift driver concurrency cap", result.stderr)

    def test_wrong_architecture_fails(self):
        result = self.run_guard({
            "PLATFORM_NAME": "iphonesimulator",
            "ARCHS": "arm64",
            "EXCLUDED_ARCHS": "",
            "OTHER_SWIFT_FLAGS": "-j1",
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected only x86_64", result.stderr)


if __name__ == "__main__":
    unittest.main()
