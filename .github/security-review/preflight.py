#!/usr/bin/env python3
"""Public-safe, offline foundation checks. This file never invokes an AI scanner."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.dont_write_bytecode = True
LIMIT = 1_000_000
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
CONFIG = {
    "schema_version": 1, "execution_enabled": False, "state": "foundation_only",
    "deployment": "deployment_pending", "ocr": "disabled", "cloudflare": "blocked",
}
ERROR_STATUS = {"schema_version": 1, "status": "error", "paid_execution": False,
                "deployment": "deployment_pending", "source_sha": None}


def require(condition):
    if not condition:
        raise ValueError("invalid-foundation-input")


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def same(left, right):
    """Structural equality without Python's false==0 / true==1 coercion."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def parse(raw):
    require(len(raw) <= LIMIT)
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: require(False))
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        require(depth <= 64 and count <= 50000)
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    return value


def read_bytes(root, relative):
    """No-follow bounded regular-file reads; candidate files are inert data."""
    relative = Path(relative)
    require(not relative.is_absolute() and relative.parts and ".." not in relative.parts)
    root = Path(root)
    # Do not resolve away symlinks before checking them.
    path = Path(os.path.abspath(root))
    for parent in (path, *path.parents):
        require(not parent.is_symlink())
    for part in relative.parts:
        path /= part
        require(not path.is_symlink())
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= LIMIT)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(LIMIT + 1)
        after = os.fstat(fd)
        require(len(raw) == before.st_size and len(raw) <= LIMIT
                and (before.st_ino, before.st_size, before.st_mtime_ns)
                == (after.st_ino, after.st_size, after.st_mtime_ns))
        return raw
    finally:
        os.close(fd)


def read(root, relative):
    return parse(read_bytes(root, relative))


def sha(value):
    require(isinstance(value, str) and SHA.fullmatch(value) is not None)
    return value


def safe_path(value):
    require(isinstance(value, str) and value and not value.startswith("/")
            and "\\" not in value and ":" not in value
            and all(p not in ("", ".", "..") for p in value.split("/"))
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


def dedup_key(source_sha, lane, base_sha, head_sha):
    """Key for a future trusted controller; no controller or publisher exists here."""
    require(lane in ("ocr-advisory-pr-diff", "cloudflare-high-risk-pr-and-default-audit"))
    fields = [sha(source_sha), lane, sha(base_sha), sha(head_sha)]
    return hashlib.sha256("\0".join(fields).encode()).hexdigest()


def check_ocr(document, base_sha, head_sha, exit_code):
    """Accept only fully covered pinned diff reviews, never legacy success or scan."""
    sha(base_sha)
    sha(head_sha)
    require(type(exit_code) is int and exit_code == 0 and isinstance(document, dict))
    require(document.get("status") == "complete")
    summary = document.get("summary")
    require(isinstance(summary, dict) and type(summary.get("budget_exceeded", False)) is bool
            and not summary.get("budget_exceeded", False))
    warnings = document.get("warnings", [])
    # This strict foundation has no warning-waiver mechanism.
    require(isinstance(warnings, list) and not warnings)
    manifest = document.get("manifest")
    require(isinstance(manifest, dict) and manifest.get("terminal_state") == "complete"
            and manifest.get("schema_version") == "ocr.run-manifest/v1"
            and manifest.get("operation") == "review" and manifest.get("run_failure") is None)
    frozen = manifest.get("input")
    execution = manifest.get("execution")
    require(isinstance(frozen, dict) and frozen.get("mode") == "range"
            and frozen.get("resolved_base") == base_sha and frozen.get("resolved_head") == head_sha)
    require(isinstance(execution, dict) and execution.get("ocr_version") == "v1.13.0")
    coverage = manifest.get("coverage")
    require(isinstance(coverage, dict)
            and set(coverage) == {"selected", "completed", "reused", "failed", "waived"})
    sets = {}
    identities = {}
    selected = {}
    for name, entries in coverage.items():
        require(isinstance(entries, list) and len(entries) <= 10000)
        ids = set()
        for item in entries:
            require(isinstance(item, dict))
            identity = item.get("item_id")
            require(isinstance(identity, str) and HASH.fullmatch(identity) is not None
                    and identity not in ids)
            safe_path(item.get("path"))
            fingerprint = item.get("fingerprint")
            require(isinstance(fingerprint, str) and HASH.fullmatch(fingerprint) is not None)
            # Pinned manifestItemID hashes both paths; coverageItem omits
            # old_path for additions AND ordinary modifications (old == new).
            if "old_path" in item:
                old = item["old_path"]
                safe_path(old)
                candidates = (old,)
            else:
                candidates = ("", item["path"])
            matched = [old for old in candidates if identity == hashlib.sha256(
                "\0".join(["review", "range", old, item["path"]]).encode()).hexdigest()]
            require(len(matched) == 1)
            old = matched[0]
            # Failure/waiver detail is never allowed to masquerade as reviewed evidence.
            require(not item.get("classification") and not item.get("reason"))
            canonical = (item["path"], old, item.get("fingerprint"))
            require(identity not in identities or identities[identity] == canonical)
            identities[identity] = canonical
            ids.add(identity)
            if name == "selected":
                selected[identity] = fingerprint
        sets[name] = ids
    require(sets["selected"] and not sets["failed"] and not sets["waived"]
            and not (sets["completed"] & sets["reused"])
            and sets["selected"] == sets["completed"] | sets["reused"])
    # Match upstream agent.sourceArtifactSHA256/hashFields length-prefixed framing.
    digest = hashlib.sha256()
    for identity in sorted(selected):
        for field in (identity, selected[identity]):
            raw = field.encode()
            digest.update(len(raw).to_bytes(8, "big"))
            digest.update(raw)
    require(frozen.get("source_artifact_sha256") == digest.hexdigest())
    return "complete"


def preflight(root, source_sha):
    sha(source_sha)
    config = read(root, ".github/security-review/config.json")
    require(same(config, CONFIG))
    trusted = Path(__file__).resolve().parents[2]
    workflow = ".github/workflows/ai-review-foundation.yml"
    require(same(read(root, workflow), read(trusted, workflow)))
    require(read_bytes(root, ".github/security-review/preflight.py")
            == Path(__file__).read_bytes())
    return {"schema_version": 1, "status": "disabled", "paid_execution": False,
            "deployment": "deployment_pending", "source_sha": source_sha}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(preflight(args.root, args.source_sha), sort_keys=True))
        return 0  # Preflight success only; status explicitly says disabled.
    except (ValueError, OSError, RecursionError, TypeError):
        print(json.dumps(ERROR_STATUS, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
