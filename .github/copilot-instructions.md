# Copilot Instructions

## Autonomous review policy

Follow [Autonomous review and separation of duties](instructions/autonomous-review.instructions.md) for purpose/outcome challenge, CI evidence reuse, independent finding closure, and bounded Copilot adjudication. Use existing review agents; do not add a routine human approval gate or duplicate review rounds. Preserve mandatory specialist gates, required checks, and action authorization.

## Pull requests and merge authority

- Use a branch and PR for changes targeting the default branch, `main`, or `develop`. The organization-wide [Copilot review and owner-led merge ruleset](https://github.com/organizations/seventwos-app/settings/rules/25233290) requests Copilot review on PR creation and subsequent pushes; draft PRs are reviewed when ready.
- `tcp-a` and `a-tcp` may each merge their own PR after required CI/security checks pass and review threads are resolved. Do not request the other account's approval merely because the author cannot approve their own PR. Human approval count is zero; code-owner, last-push, and extra unattributed-change approvals are not required.
- Agents must check the latest-head Copilot review and address valid findings before recommending merge. Automatic review requests are not a GitHub-enforced review-completion gate and depend on Copilot access/credits; report unavailable or pending review as a blocker, not a completed review.
- Preserve existing security/review agents, required checks, and unrelated protections. Do not impersonate a human approver, switch accounts to manufacture approval, bypass failed gates, or reintroduce cross-user approval requirements.
- This policy removes only cross-user PR approval requirements. It does not authorize an agent to merge, deploy, publish, spend money, or perform destructive actions without the authorization otherwise required for that task.
- Read live GitHub rules for the target branch when resuming PR work. Repository instructions record intent; Graphify is a derived index, not authority for external GitHub settings. Refresh it through the existing workflow after documentation merges; do not claim it has learned unindexed changes.

## Efficient execution and delegation

- Start with the repo's existing instructions, agent catalog, and relevant skill. Inspect the actual diff and reuse existing implementations before adding machinery. Load only context needed for the current phase.
- For a known-owner, bounded, low-risk task with focused proof, the current owner may implement directly without an implementation handoff. Required independent purpose/outcome reviews, customization audits, pre-push review, and risk-triggered specialist gates still apply; direct implementation is not self-approval. Unknown ownership or risk follows existing specialist routing. Delegate substantial independent work, not a continuous investigation already owned by another agent.
- Give each delegate a concrete objective, relevant context, allowed paths, ownership, acceptance checks, and a stop condition. Use the configured model/risk policy rather than overriding pins for speed.
- Parallelize only independent work with non-overlapping write ownership. Keep a continuous investigation with one owner; do not duplicate a delegate's search or implementation. Use background agents only while doing independent work, and collect their result without polling.
- Batch related edits and review feedback. Run the smallest relevant validation; expand only when risk or failures justify it. Do not add a second review tool merely because it is available, retry CI blindly, or treat an installed skill/agent as proof that it runs in CI.
- Reuse validation only for the revision or exact diff, inputs, environment, and coverage it actually proves. Count a hook-run canonical gate as that cycle's run; do not repeat it manually. Preserve deliberately independent security checks and stricter latest-head requirements.
- Give long operations a justified runtime deadline and progress signal. A progress checkpoint or tool initial wait is not a cancellation deadline: do not kill a healthy build just because a checkpoint expires. If an operation-specific deadline expires, cancel only its task-owned process tree, verify termination, and report the failure.
- Preserve the existing review-loop ceiling across resumes: record its wall-clock start, completed cycles, reviewed SHA, pending operations, and any authorized continuation in the existing task/PR record. At the ceiling stop further autonomous corrections and pushes, report the blocker, and keep healthy pending builds separate from the review clock; restarting a session does not reset the budget.
- The coordinating agent owns integration, verifies acceptance evidence, and reports what changed, what remains blocked, and whether the result is merged. Instruction files guide compatible agents; they do not guarantee every tool loads them.

## Engineering discipline routing

Apply these skills only during the matching phase, within the current agent's
existing role and permissions. Load through the client's skill tool when
available, or read the linked document as a reference; never claim a tool ran
when it did not. Existing workflow routers, authorization, read-only boundaries,
specialist review gates, model settings, and publishing rules remain unchanged.
Skip duplicate process when an existing workflow already supplies the evidence.

| Current work | Skill | Relevant owners |
|---|---|---|
| Features, bugs, performance, tests, evaluations | [evidence-first-engineering](skills/evidence-first-engineering/SKILL.md) | Implementing, infrastructure, data, and test specialists |
| Specs, interfaces, architectural trade-offs | [decision-and-design](skills/decision-and-design/SKILL.md) | Architect, planner, and implementing specialist |
| Claims, research, durable docs, instruction changes, conflicting sources | [artifact-integrity](skills/artifact-integrity/SKILL.md) | Reviewers, researchers, fact checkers, writers, and task owner |
| Resume, transfer, blocked work, recurring-failure lessons | [durable-agent-handoff](skills/durable-agent-handoff/SKILL.md) | Current task owner |

Routine acknowledgements and direct one-command lookups need none of these.
Read-only reviewers assess and report evidence; they do not gain edit or
execution authority. These skills do not authorize deployments or publishing.
See the [pinned mirror manifest](skills/engineering-pack.lock.json) for the
authoritative source and digests, and [behavior scenarios](skills/engineering-scenarios.json)
for expected and forbidden behavior. File presence, valid structure, actual
activation, and improved outcomes are separate claims.
