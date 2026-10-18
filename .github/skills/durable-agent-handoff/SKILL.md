---
name: durable-agent-handoff
description: "Use when resuming work after a context gap, handing a task to another agent, ending a blocked attempt, or extracting lessons after a repeated failure. Reconstructs live state and records actionable evidence. Not for routine acknowledgements or automatic creation of session notes."
---

# Durable agent handoff

## Reconstruct before continuing

Read the task's existing issue, plan, commits, and relevant prior-session record,
then inspect live branch/worktree state, task-owned diff, current checks, and
unresolved review threads when applicable. History explains intent; live state
determines what is still pending. Do not revive retired systems or repeat an
already-owned task based on an old handoff.

Separate confirmed decisions, reversible assumptions, rejected approaches,
unfinished work, and external blockers. Choose the next action that removes the
highest-priority blocker; do not return an undifferentiated menu.

## Hand off evidence, not conversation

Use an existing task record where possible. Create a standalone handoff only
when requested or needed for a real transfer; use the session artifact area or
the user's specified destination, not a new repository scratch document.

Include:

- Outcome, non-goals, task owner, and the reason work is transferring.
- Repository, branch, base revision, worktree location, and task-owned changes;
  distinguish pre-existing user changes and do not revert them.
- Locked decisions and links to canonical specs or ADRs, not duplicate copies.
- Exact checks run and observed results, with unchecked boundaries and blockers.
- Failed hypotheses, evidence rejecting them, and the next concrete action.
- Required skills/tools that are actually available; if unavailable, name the
  missing capability rather than inventing an invocation.

Do not include credentials, customer data, or raw private transcripts. Public
records must not expose internal paths or deployment details. Follow the
destination's disclosure policy.

## Learn from recurrence

After repeated or high-impact failures, connect the lesson to observed evidence.
Describe the general failure class, not just the last complaint. Reuse an
existing guard first; propose or add the smallest authorized deterministic
regression check for mechanical failures. Reserve prose rules for judgment
that a check cannot enforce. Record rationale and removal criteria for any
temporary exception. A retrospective with no actionable gap changes nothing.

## Completion

A fresh agent must be able to distinguish done from pending, locate the current
source of truth, avoid the rejected path, and run the next check without reading
the full conversation. Do not equate a handoff with a merge, deployment, or
verified behavioral improvement.
