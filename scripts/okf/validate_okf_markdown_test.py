#!/usr/bin/env python3
"""Focused unit tests for scripts/okf/validate_okf_markdown.py.

Run with: python3 -m unittest scripts/okf/validate_okf_markdown_test.py -v

No third-party test dependencies (stdlib unittest only), matching the
validator's own no-third-party-dependency stance.
"""
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_okf_markdown as okf  # noqa: E402


def write(bundle_root, name, content):
    path = bundle_root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class OkfBundleTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir_obj = tempfile.TemporaryDirectory()
        self.repo_root = Path(self._tmpdir_obj.name)
        self.bundle_root = self.repo_root / "documentation"
        self.bundle_root.mkdir()
        self._orig_repo_root = okf.REPO_ROOT
        self._orig_bundle_root = okf.BUNDLE_ROOT
        okf.REPO_ROOT = self.repo_root
        okf.BUNDLE_ROOT = self.bundle_root

    def tearDown(self):
        okf.REPO_ROOT = self._orig_repo_root
        okf.BUNDLE_ROOT = self._orig_bundle_root
        self._tmpdir_obj.cleanup()

    def _write(self, name, content):
        return write(self.bundle_root, name, content)


class ConceptFrontmatterTests(OkfBundleTestCase):
    def test_missing_frontmatter_fails(self):
        text = "# No frontmatter\n\nJust a body.\n"
        self.assertEqual(
            okf.check_file(self._write("concept.md", text)),
            ["missing YAML frontmatter (no leading '---' block)"],
        )

    def test_missing_closing_delimiter_is_malformed(self):
        text = "---\ntype: Note\n\n# Body\n"
        violations = okf.check_file(self._write("concept.md", text))
        self.assertTrue(any("malformed frontmatter" in v for v in violations))

    def test_missing_type_fails(self):
        text = "---\ntitle: Untyped\n---\n\n# Body\n"
        violations = okf.check_file(self._write("concept.md", text))
        self.assertIn(
            "frontmatter present but missing required non-empty 'type' field",
            violations,
        )

    def test_minimal_valid_concept_passes(self):
        text = "---\ntype: Specification\n---\n\n# Body\n"
        self.assertEqual(okf.check_file(self._write("concept.md", text)), [])

    def test_tags_must_be_a_list(self):
        text = "---\ntype: Specification\ntags: heuristic\n---\n\nBody\n"
        violations = okf.check_file(self._write("concept.md", text))
        self.assertIn("'tags' must be a YAML list", violations)

    def test_status_must_be_known_value(self):
        text = "---\ntype: Specification\nstatus: wip\n---\n\nBody\n"
        violations = okf.check_file(self._write("concept.md", text))
        self.assertTrue(any(v.startswith("'status' must be one of") for v in violations))


class SourcesAndFootnoteTests(OkfBundleTestCase):
    def test_source_missing_resource_fails(self):
        text = (
            "---\ntype: Metric\n"
            "sources:\n"
            "  - id: schema\n"
            "    title: Schema\n"
            "---\n\nBody\n"
        )
        violations = okf.check_file(self._write("concept.md", text))
        self.assertTrue(
            any("missing a required non-empty 'resource'" in v for v in violations)
        )

    def test_footnote_matching_source_id_passes(self):
        text = (
            "---\ntype: Metric\n"
            "sources:\n"
            "  - id: schema\n"
            "    resource: https://example.com/schema\n"
            "---\n\n"
            "The value is derived.[^schema]\n\n"
            "[^schema]: Schema reference\n"
        )
        self.assertEqual(okf.check_file(self._write("concept.md", text)), [])


class ReservedFileTests(OkfBundleTestCase):
    def test_root_index_with_only_okf_version_passes(self):
        text = '---\nokf_version: "0.2"\n---\n\n# Index\n'
        self.assertEqual(okf.check_file(self._write("index.md", text)), [])

    def test_root_index_missing_okf_version_fails(self):
        text = "# Index\n\nno frontmatter here\n"
        violations = okf.check_file(self._write("index.md", text))
        self.assertTrue(any("must carry an 'okf_version'" in v for v in violations))

    def test_log_with_frontmatter_fails(self):
        text = "---\ntype: Log\n---\n\n# Update Log\n"
        violations = okf.check_file(self._write("log.md", text))
        self.assertEqual(violations, ["log.md must not have YAML frontmatter"])

    def test_log_without_frontmatter_passes(self):
        text = "# Update Log\n\n## 2026-01-01\n* **Init**: Started.\n"
        self.assertEqual(okf.check_file(self._write("log.md", text)), [])


class BundleScopeTests(unittest.TestCase):
    """Guards that the validator only scans documentation/, not the whole repo."""

    def test_files_outside_documentation_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            bundle_root = repo_root / "documentation"
            bundle_root.mkdir()
            write(repo_root, "README.md", "# Not part of the OKF bundle\n")
            included = write(bundle_root, "concept.md", "---\ntype: Note\n---\n")
            orig_repo_root, orig_bundle_root = okf.REPO_ROOT, okf.BUNDLE_ROOT
            try:
                okf.REPO_ROOT = repo_root
                okf.BUNDLE_ROOT = bundle_root
                self.assertEqual(list(okf.iter_markdown_files()), [included])
            finally:
                okf.REPO_ROOT, okf.BUNDLE_ROOT = orig_repo_root, orig_bundle_root

    def test_missing_documentation_dir_yields_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            bundle_root = repo_root / "documentation"
            orig_repo_root, orig_bundle_root = okf.REPO_ROOT, okf.BUNDLE_ROOT
            try:
                okf.REPO_ROOT = repo_root
                okf.BUNDLE_ROOT = bundle_root
                self.assertEqual(list(okf.iter_markdown_files()), [])
            finally:
                okf.REPO_ROOT, okf.BUNDLE_ROOT = orig_repo_root, orig_bundle_root


if __name__ == "__main__":
    unittest.main()
