#!/usr/bin/env python3
"""Validate the repository-owned selective upstream synchronization foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_MAPPING_KINDS = {"path", "xcode_target", "xcode_scheme", "generated_artifact"}
REQUIRED_INVARIANTS = {
    "product-identity",
    "seventwos-endpoints",
    "empty-signing-team",
    "inherited-telemetry-disabled",
    "release-readiness-fails-closed",
}


def fail(message: str) -> None:
    print(f"upstream-policy: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing required file: {path}")
    except json.JSONDecodeError as error:
        fail(f"invalid JSON in {path}: {error}")


def canonical_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_invariants(root: Path, invariants: dict[str, Any]) -> None:
    entries = invariants.get("invariants")
    if not isinstance(entries, list):
        fail("invariants must be a list")

    ids = {entry.get("id") for entry in entries if isinstance(entry, dict)}
    missing = REQUIRED_INVARIANTS - ids
    if missing:
        fail(f"missing behavioral invariants: {', '.join(sorted(missing))}")

    for invariant in entries:
        if invariant.get("classification") != "behavioral":
            fail(f"{invariant.get('id')} must be behavioral; path-only tombstones are forbidden")
        sources = invariant.get("sources")
        if not isinstance(sources, list) or not sources:
            fail(f"{invariant.get('id')} must provide source evidence")
        for source in sources:
            path = root / source["path"]
            content = path.read_text(encoding="utf-8")
            for expected in source.get("must_contain", []):
                if expected not in content:
                    fail(f"{invariant['id']} missing required evidence {expected!r} in {source['path']}")
            for forbidden in source.get("must_not_contain", []):
                if forbidden in content:
                    fail(f"{invariant['id']} found forbidden value {forbidden!r} in {source['path']}")


def validate_ledger(path: Path) -> None:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        fail("ledger must contain a genesis entry")
    previous_hash: str | None = None
    for index, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            fail(f"invalid JSONL ledger entry {index}: {error}")
        if entry.get("previous_entry_sha256") != previous_hash:
            fail(f"ledger entry {index} does not chain to the preceding entry")
        if entry.get("entry_sha256") != canonical_hash(entry):
            fail(f"ledger entry {index} has an invalid entry_sha256")
        previous_hash = entry["entry_sha256"]


def validate_workflow(root: Path, state: dict[str, Any]) -> None:
    workflow = root / ".github/workflows/upstream-assessment.yml"
    content = workflow.read_text(encoding="utf-8")
    required = [
        "permissions:\n  contents: read",
        "persist-credentials: false",
        "assess_only",
        state["upstream"]["sha"],
        state["fork"]["develop_sha"],
        "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    ]
    for expected in required:
        if expected not in content:
            fail(f"assessment workflow missing required value {expected!r}")
    for forbidden in ("git merge", "git rebase", "git cherry-pick", "git push", "gh pr create"):
        if forbidden in content:
            fail(f"assessment workflow must remain report-only; found {forbidden!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    policy_dir = root / ".seventwos"

    policy = load_json(policy_dir / "upstream-policy.json")
    state = load_json(policy_dir / "upstream-state.json")
    path_map = load_json(policy_dir / "upstream-path-map.json")
    invariants = load_json(policy_dir / "upstream-invariants.json")

    if policy.get("upstream") != {"repository": "element-hq/element-x-ios", "branch": "develop"}:
        fail("policy must declare element-hq/element-x-ios develop as upstream")
    if policy.get("synchronization", {}).get("default_action") != "assess_only":
        fail("default synchronization action must be assess_only")
    if policy["synchronization"].get("allow_automatic_apply") or policy["synchronization"].get("allow_automatic_merge"):
        fail("automatic apply and merge must remain disabled")

    for source in (state["fork"], state["upstream"]):
        if not SHA_PATTERN.fullmatch(source["sha"] if "sha" in source else source["develop_sha"]):
            fail("state contains an invalid immutable SHA")
    upstream_merge_base = state["merge_bases"]["fork_develop_to_upstream_develop"]
    if upstream_merge_base.get("status") != "unknown" or upstream_merge_base.get("intent") != "human_review_required":
        fail("unavailable upstream merge base must remain explicitly unknown and require human review")

    rules = path_map.get("mapping_rules")
    if not isinstance(rules, list) or REQUIRED_MAPPING_KINDS - {rule.get("kind") for rule in rules}:
        fail("path map must cover paths, targets, schemes, and generated artifacts")
    if not any(rule.get("upstream") == "ElementX" and rule.get("seventwos") == "Seventwos" for rule in rules):
        fail("path map must explicitly map ElementX to Seventwos")

    validate_invariants(root, invariants)
    validate_ledger(policy_dir / "upstream-ledger.jsonl")
    validate_workflow(root, state)
    print("upstream-policy: repository foundation is valid.")


if __name__ == "__main__":
    main()
