#!/usr/bin/env python3
"""Open Knowledge Format (OKF) v0.2 markdown validator.

Strict conformance checks for every markdown file under `documentation/`,
recursively. This repo is a seventwos-owned fork of an upstream project;
OKF conformance is scoped to the `documentation/` bundle we own and author
going forward, not the inherited upstream markdown corpus (READMEs,
CHANGELOGs, upstream docs, etc.) which predates our stewardship and is
out of scope for this convention.

- Every non-reserved `.md` file under `documentation/` is a **concept**
  and must carry a parseable YAML frontmatter block with a non-empty
  `type` field.
- `documentation/index.md` and `documentation/log.md` are reserved
  (spec §8/§9) and must carry **no** frontmatter, except the bundle-root
  `index.md`, which may carry a frontmatter block containing only
  `okf_version`.
- When present, the optional frontmatter families defined by the spec
  (`tags`, `generated`, `verified`, `status`, `sources`, ...) must have the
  shape the spec defines for them (§5).
- Each `sources[]` entry must carry a non-empty `resource` (§5.1).
- Every markdown footnote label used in the body (`[^id]`) must
  correspond to a `sources[].id` declared in frontmatter, so per-claim
  attribution is always resolvable (§5.1).

See: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

Modes:
  --changed   Check only documentation/ files changed vs. the merge-base
              with the default branch (falls back to the working tree
              diff). Exit non-zero on any violation. This is what CI runs
              on pull requests.
  --all       Scan every markdown file under documentation/. Never fails
              the build; prints a conformance report.

No third-party dependencies: frontmatter is parsed with a small,
purpose-built YAML-subset parser (scalars, flow/block lists, flow/block
mappings), not a general YAML implementation. It intentionally does not
support anchors, multi-document streams, multi-line block scalars, or
other advanced YAML -- the frontmatter this repo's convention produces
never needs them.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ROOT = REPO_ROOT / "documentation"
FRONTMATTER_DELIM = "---"

# Reserved OKF bundle filenames (spec §3.1, §8, §9). Per this repo's
# established convention: only the bundle-root index.md may carry
# frontmatter (an `okf_version` key), and log.md never carries frontmatter.
RESERVED_INDEX_NAME = "index.md"
RESERVED_LOG_NAME = "log.md"
RESERVED_NAMES = {RESERVED_INDEX_NAME, RESERVED_LOG_NAME}

VALID_STATUSES = {"draft", "stable", "deprecated"}

EXCLUDED_DIR_PARTS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "vendor",
    ".copilot",
    ".github",
}

FOOTNOTE_LABEL_RE = re.compile(r"\[\^([^\]]+)\]")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)(?:#[^)]+)?\)")


def is_excluded(path):
    try:
        rel_path = path.relative_to(BUNDLE_ROOT)
    except ValueError:
        return True
    return any(part in EXCLUDED_DIR_PARTS for part in rel_path.parts)


# --------------------------------------------------------------------------
# Minimal YAML-subset parser
# --------------------------------------------------------------------------


class YamlError(ValueError):
    """Raised when the frontmatter cannot be parsed by this subset parser."""


def _split_flow(s):
    """Split a flow collection's inner content on top-level commas."""
    parts = []
    depth = 0
    quote = None
    current = ""
    for ch in s:
        if quote:
            current += ch
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            current += ch
            continue
        if ch in "[{":
            depth += 1
            current += ch
            continue
        if ch in "]}":
            depth -= 1
            current += ch
            continue
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def _parse_scalar_or_flow(s):
    s = s.strip()
    if s == "":
        return None
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [] if not inner else [_parse_scalar_or_flow(p) for p in _split_flow(inner)]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        result = {}
        for pair in _split_flow(inner):
            if ":" not in pair:
                raise YamlError(f"malformed flow mapping entry: {pair!r}")
            k, _, v = pair.partition(":")
            result[k.strip()] = _parse_scalar_or_flow(v.strip())
        return result
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1]
    if s in ("null", "~"):
        return None
    return s


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _parse_block_list(lines, start, indent):
    """Parse a sequence of `- item` lines at `indent`. Returns (list, next_index)."""
    result = []
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        cur_indent = _indent_of(line)
        if cur_indent != indent:
            break
        stripped = line.strip()
        if not stripped.startswith("- "):
            break
        item_content = stripped[2:]
        item_indent = indent + 2
        if ":" in item_content and not item_content.lstrip().startswith(("'", '"', "[", "{")):
            patched = list(lines)
            patched[i] = " " * item_indent + item_content
            value, j = _parse_block_mapping(patched, i, item_indent)
            result.append(value)
            i = j
        else:
            result.append(_parse_scalar_or_flow(item_content))
            i += 1
    return result, i


def _parse_block_mapping(lines, start, indent):
    """Parse `key: value` lines at `indent`. Returns (dict, next_index)."""
    result = {}
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        cur_indent = _indent_of(line)
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise YamlError(f"unexpected indentation at line {i + 1}: {line!r}")
        stripped = line.strip()
        if stripped.startswith("- "):
            break
        if ":" not in stripped:
            raise YamlError(f"expected 'key: value' at line {i + 1}: {line!r}")
        key, _, rest = stripped.partition(":")
        key = key.strip()
        if not key:
            raise YamlError(f"empty key at line {i + 1}: {line!r}")
        rest = rest.strip()
        if rest:
            result[key] = _parse_scalar_or_flow(rest)
            i += 1
            continue
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j < n:
            next_indent = _indent_of(lines[j])
            next_stripped = lines[j].strip()
            if next_indent > indent and next_stripped.startswith("- "):
                value, j = _parse_block_list(lines, j, next_indent)
                result[key] = value
                i = j
                continue
            if next_indent > indent:
                value, j = _parse_block_mapping(lines, j, next_indent)
                result[key] = value
                i = j
                continue
        result[key] = None
        i += 1
    return result, i


class Frontmatter:
    def __init__(self, raw, data, malformed=False, error=None):
        self.raw = raw
        self.data = data
        self.malformed = malformed
        self.error = error

    def get(self, key, default=None):
        return self.data.get(key, default)

    @property
    def keys(self):
        return set(self.data.keys())

    @property
    def has_type(self):
        value = self.data.get("type")
        return isinstance(value, str) and bool(value.strip())

    @property
    def has_okf_version(self):
        value = self.data.get("okf_version")
        return value is not None and bool(str(value).strip())


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return None
    end_line = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIM:
            end_line = i
            break
    if end_line is None:
        return Frontmatter(
            raw="\n".join(lines),
            data={},
            malformed=True,
            error="missing closing '---' delimiter",
        )
    raw = "\n".join(lines[: end_line + 1])
    body_lines = lines[1:end_line]
    try:
        data, _ = _parse_block_mapping(body_lines, 0, 0)
    except YamlError as exc:
        return Frontmatter(raw=raw, data={}, malformed=True, error=str(exc))
    return Frontmatter(raw=raw, data=data, malformed=False)


def frontmatter_body(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIM:
            return "\n".join(lines[i + 1 :])
    return text


def iter_markdown_files():
    if not BUNDLE_ROOT.exists():
        return
    for path in BUNDLE_ROOT.rglob("*.md"):
        if is_excluded(path):
            continue
        yield path


def changed_markdown_files():
    """Best-effort: diff against origin/develop, else HEAD, else working tree.

    Only files under documentation/ are in scope for this repo.
    """
    candidates = [
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "origin/develop...HEAD"],
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
        ["git", "diff", "--name-only", "--diff-filter=ACMR"],
    ]
    for cmd in candidates:
        try:
            out = subprocess.run(
                cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        files = [
            REPO_ROOT / line.strip()
            for line in out.stdout.splitlines()
            if line.strip().endswith(".md")
        ]
        files = [
            f
            for f in files
            if f.exists() and not is_excluded(f) and BUNDLE_ROOT in f.resolve().parents
        ]
        if files:
            return files
    return []


def check_bundle_index():
    """Ensure the documentation/ root index is a complete, non-stale bundle manifest."""
    index_path = BUNDLE_ROOT / RESERVED_INDEX_NAME
    if not index_path.exists():
        return ["documentation/index.md is missing"]

    text = index_path.read_text(encoding="utf-8", errors="replace")
    indexed_paths = {
        (BUNDLE_ROOT / target).resolve()
        for target in MARKDOWN_LINK_RE.findall(frontmatter_body(text))
    }
    concept_paths = {
        path.resolve()
        for path in iter_markdown_files()
        if path.name not in RESERVED_NAMES
    }
    violations = []

    missing_entries = sorted(
        path.relative_to(BUNDLE_ROOT.resolve()).as_posix()
        for path in concept_paths - indexed_paths
    )
    if missing_entries:
        violations.append(
            "missing index.md entry for " + ", ".join(missing_entries)
        )

    stale_entries = sorted(
        path.relative_to(BUNDLE_ROOT.resolve()).as_posix()
        for path in indexed_paths
        if not path.exists()
    )
    if stale_entries:
        violations.append(
            "index.md links to missing document(s): " + ", ".join(stale_entries)
        )

    return violations


def _check_optional_shape(data):
    violations = []

    tags = data.get("tags")
    if tags is not None and not isinstance(tags, list):
        violations.append("'tags' must be a YAML list")

    status = data.get("status")
    if status is not None and status not in VALID_STATUSES:
        violations.append(
            f"'status' must be one of {sorted(VALID_STATUSES)}, got {status!r}"
        )

    generated = data.get("generated")
    if generated is not None:
        if not isinstance(generated, dict):
            violations.append("'generated' must be a mapping with a 'by' field")
        elif not (isinstance(generated.get("by"), str) and generated.get("by").strip()):
            violations.append("'generated.by' is required and must be non-empty")

    if "verified" in data and data.get("verified") is not None:
        verified = data["verified"]
        entries = verified if isinstance(verified, list) else [verified]
        for entry in entries:
            if not isinstance(entry, dict) or not (
                isinstance(entry.get("by"), str) and entry.get("by").strip()
            ):
                violations.append(
                    "each 'verified' entry must be a mapping with a non-empty 'by' field"
                )
                break

    return violations


def _check_sources_and_footnotes(data, body):
    violations = []
    source_ids = set()

    sources = data.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            violations.append("'sources' must be a YAML list of entries")
            sources = []
        for idx, entry in enumerate(sources):
            if not isinstance(entry, dict):
                violations.append(f"'sources[{idx}]' must be a mapping")
                continue
            resource = entry.get("resource")
            if not (isinstance(resource, str) and resource.strip()):
                violations.append(
                    f"'sources[{idx}]' is missing a required non-empty 'resource'"
                )
            sid = entry.get("id")
            if isinstance(sid, str) and sid.strip():
                if sid in source_ids:
                    violations.append(f"'sources' declares duplicate id '{sid}'")
                source_ids.add(sid)

    footnote_labels = set(FOOTNOTE_LABEL_RE.findall(body))
    if footnote_labels:
        if not source_ids:
            violations.append(
                "body uses footnote(s) "
                f"{sorted(footnote_labels)} but frontmatter has no 'sources[].id' "
                "to attribute them to"
            )
        else:
            unmatched = footnote_labels - source_ids
            if unmatched:
                violations.append(
                    f"footnote label(s) {sorted(unmatched)} do not correspond to "
                    "any 'sources[].id'"
                )

    return violations


def check_file(path):
    """Return a list of violation strings for a single file (empty = clean)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    name = path.name
    is_root_index = name == RESERVED_INDEX_NAME and path.parent == BUNDLE_ROOT

    if name == RESERVED_INDEX_NAME:
        if not is_root_index:
            if fm is not None:
                return ["index.md must not have YAML frontmatter (only the bundle-root index.md may)"]
            return []
        if fm is None:
            return ["bundle-root index.md must carry an 'okf_version' frontmatter field"]
        if fm.malformed:
            return [f"malformed frontmatter: {fm.error}"]
        extra_keys = fm.keys - {"okf_version"}
        violations = []
        if extra_keys:
            violations.append(
                f"bundle-root index.md frontmatter may contain only 'okf_version', found extra key(s): {sorted(extra_keys)}"
            )
        if not fm.has_okf_version:
            violations.append("bundle-root index.md frontmatter must include a non-empty 'okf_version'")
        return violations

    if name == RESERVED_LOG_NAME:
        if fm is not None:
            return ["log.md must not have YAML frontmatter"]
        return []

    if fm is None:
        return ["missing YAML frontmatter (no leading '---' block)"]
    if fm.malformed:
        return [f"malformed frontmatter: {fm.error}"]

    violations = []
    if not fm.has_type:
        violations.append("frontmatter present but missing required non-empty 'type' field")
    violations.extend(_check_optional_shape(fm.data))
    violations.extend(_check_sources_and_footnotes(fm.data, frontmatter_body(text)))
    return violations


def run_changed(strict=True):
    files = changed_markdown_files()
    if not files:
        print("okf-validate: no changed documentation/ markdown files.")
        return 0
    failed = False
    for path in files:
        rel = path.relative_to(REPO_ROOT)
        violations = check_file(path)
        if violations:
            failed = True
            for v in violations:
                print(f"FAIL {rel}: {v}")
        else:
            print(f"OK   {rel}")
    index_violations = check_bundle_index()
    if index_violations:
        failed = True
        for violation in index_violations:
            print(f"FAIL documentation/{RESERVED_INDEX_NAME}: {violation}")
    if failed:
        print("\nokf-validate: one or more changed markdown files are non-conformant.")
        return 1 if strict else 0
    print("\nokf-validate: all changed markdown files conform.")
    return 0


def run_all():
    files = list(iter_markdown_files())
    total = len(files)
    clean = 0
    for path in sorted(files):
        rel = path.relative_to(REPO_ROOT)
        violations = check_file(path)
        if violations:
            for v in violations:
                print(f"REPORT {rel}: {v}")
        else:
            clean += 1
    index_violations = check_bundle_index()
    for violation in index_violations:
        print(f"REPORT documentation/{RESERVED_INDEX_NAME}: {violation}")
    if index_violations:
        clean -= 1
    print(f"\nokf-validate baseline: {clean}/{total} markdown files conform.")
    return 0  # report-only, never fails the build


def main():
    parser = argparse.ArgumentParser(description="OKF v0.2 markdown validator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--changed", action="store_true", help="check changed files only (CI mode)")
    group.add_argument("--all", action="store_true", help="scan entire documentation/ bundle, report-only")
    args = parser.parse_args()

    if args.changed:
        return run_changed(strict=True)
    if args.all:
        return run_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
