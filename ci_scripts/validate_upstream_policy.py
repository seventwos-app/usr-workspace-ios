#!/usr/bin/env python3
"""Validate the repository-owned selective upstream synchronization foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as error:  # pragma: no cover - exercised by CI setup
    yaml = None
    YAML_IMPORT_ERROR = error
else:
    YAML_IMPORT_ERROR = None


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_MAPPING_KINDS = {"path", "xcode_target", "xcode_scheme", "generated_artifact"}
REQUIRED_INVARIANTS = {
    "product-identity",
    "seventwos-endpoints",
    "empty-signing-team",
    "inherited-telemetry-disabled",
    "release-readiness-fails-closed",
}
POLICY_PATHS = (
    ".seventwos/upstream-policy.json",
    ".seventwos/upstream-state.json",
    ".seventwos/upstream-path-map.json",
    ".seventwos/upstream-invariants.json",
    ".seventwos/upstream-ledger.jsonl",
)
POLICY_WORKFLOW_PATH = ".github/workflows/upstream-assessment.yml"
POLICY_TRIGGER_PATHS = {
    ".seventwos/**",
    "ci_scripts/validate_upstream_policy.py",
    "ci_scripts/validate_upstream_policy_test.py",
    ".github/workflows/upstream-assessment.yml",
    "CODEOWNERS",
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


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        fail(f"PyYAML is required for structural workflow validation: {YAML_IMPORT_ERROR}")
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    except yaml.YAMLError as error:
        fail(f"invalid workflow YAML: {error}")
    if not isinstance(document, dict):
        fail("workflow must be a mapping")
    return document


def require_behavioral_source(invariant: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        fail(f"{invariant.get('id')} has an invalid source assertion")
    expected = source.get("must_contain", [])
    forbidden = source.get("must_not_contain", [])
    if not isinstance(expected, list) or not isinstance(forbidden, list):
        fail(f"{invariant['id']} assertions must be lists")
    if not expected and not forbidden:
        fail(f"{invariant['id']} source assertions cannot be empty")
    if not all(isinstance(value, str) and value for value in [*expected, *forbidden]):
        fail(f"{invariant['id']} assertions must contain non-empty strings")


def validate_invariants(root: Path, invariants: dict[str, Any]) -> None:
    entries = invariants.get("invariants")
    if not isinstance(entries, list):
        fail("invariants must be a list")

    by_id = {entry.get("id"): entry for entry in entries if isinstance(entry, dict)}
    missing = REQUIRED_INVARIANTS - set(by_id)
    if missing:
        fail(f"missing behavioral invariants: {', '.join(sorted(missing))}")

    for invariant_id in REQUIRED_INVARIANTS:
        invariant = by_id[invariant_id]
        if invariant.get("classification") != "behavioral":
            fail(f"{invariant_id} must be behavioral; path-only tombstones are forbidden")
        sources = invariant.get("sources")
        if not isinstance(sources, list) or not sources:
            fail(f"{invariant_id} must provide source evidence")
        for source in sources:
            require_behavioral_source(invariant, source)
            path = root / source["path"]
            try:
                content = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                fail(f"{invariant_id} source is missing: {source['path']}")
            for expected in source.get("must_contain", []):
                if expected not in content:
                    fail(f"{invariant_id} missing required evidence {expected!r} in {source['path']}")
            for forbidden in source.get("must_not_contain", []):
                if forbidden in content:
                    fail(f"{invariant_id} found forbidden value {forbidden!r} in {source['path']}")


def read_ledger(path: Path) -> list[dict[str, Any]]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        fail("ledger must contain a genesis entry")
    entries = []
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
        entries.append(entry)
        previous_hash = entry["entry_sha256"]
    return entries


def validate_ledger_base(root: Path, current_ledger: Path, base_ref: str, require_base_ref: bool) -> None:
    if require_base_ref and not base_ref:
        fail("POLICY_BASE_SHA is required for pull_request, push, and merge_group validation")
    if not base_ref:
        return

    base_tree = run_git(root, "ls-tree", "-r", "--name-only", base_ref, "--", *POLICY_PATHS)
    if base_tree.returncode:
        fail(f"cannot inspect policy base {base_ref}: {base_tree.stderr.strip()}")
    base_paths = set(base_tree.stdout.splitlines())
    ledger_path = ".seventwos/upstream-ledger.jsonl"
    if ledger_path not in base_paths:
        if base_paths:
            fail("ledger may be introduced only with the complete policy foundation")
        current_entries = read_ledger(current_ledger)
        if len(current_entries) != 1 or current_entries[0].get("event") != "baseline-recorded":
            fail("first policy introduction must contain only a valid baseline-recorded genesis ledger entry")
        return

    base_ledger = run_git(root, "show", f"{base_ref}:{ledger_path}")
    if base_ledger.returncode:
        fail(f"cannot read ledger from policy base {base_ref}: {base_ledger.stderr.strip()}")
    current_lines = [line for line in current_ledger.read_text(encoding="utf-8").splitlines() if line]
    base_lines = [line for line in base_ledger.stdout.splitlines() if line]
    if len(current_lines) < len(base_lines) or current_lines[: len(base_lines)] != base_lines:
        fail("ledger is append-only: existing base entries must remain byte-for-byte unchanged")


def validate_ledger_state_binding(ledger: list[dict[str, Any]], state: dict[str, Any]) -> None:
    latest = ledger[-1].get("inputs")
    expected = {
        "fork_develop_sha": state["fork"]["develop_sha"],
        "upstream_develop_sha": state["upstream"]["sha"],
    }
    if not isinstance(latest, dict) or any(latest.get(key) != value for key, value in expected.items()):
        fail("latest ledger transition must bind the recorded fork and upstream SHAs")


def permission_map_is_read_only(value: Any) -> bool:
    return isinstance(value, dict) and value == {"contents": "read"}


def validate_workflow(root: Path, state: dict[str, Any]) -> None:
    workflow = read_yaml(root / POLICY_WORKFLOW_PATH)
    triggers = workflow.get("on")
    if not isinstance(triggers, dict):
        fail("assessment workflow must define structured triggers")
    for trigger in ("pull_request", "push"):
        config = triggers.get(trigger)
        if not isinstance(config, dict):
            fail(f"assessment workflow must trigger on {trigger}")
        paths = config.get("paths")
        if not isinstance(paths, list) or not POLICY_TRIGGER_PATHS.issubset(set(paths)):
            fail(f"{trigger} trigger must cover every policy-owned path")
    push_branches = triggers["push"].get("branches")
    if not isinstance(push_branches, list) or "develop" not in push_branches:
        fail("push trigger must include protected develop")
    if not isinstance(triggers.get("merge_group"), dict):
        fail("assessment workflow must trigger on merge_group")
    if not permission_map_is_read_only(workflow.get("permissions")):
        fail("workflow effective default permissions must be exactly contents: read")

    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or "assess" not in jobs:
        fail("assessment workflow must define an assess job")
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            fail(f"workflow job {job_name} must be a mapping")
        job_permissions = job.get("permissions", workflow["permissions"])
        if not permission_map_is_read_only(job_permissions):
            fail(f"workflow job {job_name} effective permissions must be exactly contents: read")

    serialized = json.dumps(workflow, sort_keys=True)
    for required in (
        "persist-credentials",
        "false",
        "assess_only",
        state["upstream"]["sha"],
        state["fork"]["develop_sha"],
        "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        "POLICY_BASE_SHA",
        "github.event.merge_group.base_sha",
    ):
        if required not in serialized:
            fail(f"assessment workflow missing required value {required!r}")
    for forbidden in ("git merge", "git rebase", "git cherry-pick", "git push", "gh pr create"):
        if forbidden in serialized:
            fail(f"assessment workflow must remain report-only; found {forbidden!r}")


def validate_git_evidence(root: Path, state: dict[str, Any], verify_remote: bool) -> None:
    fork_sha = state["fork"]["develop_sha"]
    if run_git(root, "cat-file", "-e", f"{fork_sha}^{{commit}}").returncode:
        fail("recorded fork SHA is not a local commit")
    if run_git(root, "merge-base", "--is-ancestor", fork_sha, "HEAD").returncode:
        fail("recorded fork SHA is not an ancestor of the assessed commit")
    if not verify_remote:
        return

    upstream = state["upstream"]
    remote_url = f"https://github.com/{upstream['repository']}.git"
    resolution = run_git(root, "ls-remote", remote_url, f"refs/heads/{upstream['branch']}")
    if resolution.returncode:
        fail(f"cannot resolve upstream ref read-only: {resolution.stderr.strip()}")
    resolved = resolution.stdout.split()
    if len(resolved) < 2 or resolved[0] != upstream["sha"] or resolved[1] != f"refs/heads/{upstream['branch']}":
        fail("recorded upstream SHA does not match the configured upstream repository/ref")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--verify-remote", action="store_true")
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
    ledger = read_ledger(policy_dir / "upstream-ledger.jsonl")
    validate_ledger_state_binding(ledger, state)
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    validate_ledger_base(
        root,
        policy_dir / "upstream-ledger.jsonl",
        os.environ.get("POLICY_BASE_SHA", ""),
        event_name in {"pull_request", "push", "merge_group"},
    )
    validate_workflow(root, state)
    validate_git_evidence(root, state, args.verify_remote)
    print("upstream-policy: repository foundation is valid.")


if __name__ == "__main__":
    main()
