---
type: Reference
title: OpenCodeReview CI
description: Read-only upstream CLI integration, activation and privacy boundaries.
sources:
  - id: ocr-workflow
    resource: .github/workflows/ocr-pr-review.yml
---

# OpenCodeReview CI

This workflow[^ocr-workflow] follows the
[upstream CLI CI recipe](https://github.com/alibaba/open-code-review/blob/1672852136fc87748249d22bce0819f33419ea79/pages/src/content/docs/en/integrations/ci.md):
install OCR, configure an
LLM, review an immutable Git range and parse its JSON. It pins CLI `1.13.0` and
checks `ocr.run-manifest/v1` coverage. It does not depend on the separate custom
source-build/signing proof workflow.

## Configuration and activation

**Activation is blocked by an unresolved credential boundary.** A trusted-base
checkout protects the helper, not the `pull_request` workflow definition. An
eligible same-repository PR can modify that definition. Do not configure provider
secrets or enable execution under this design. A separately reviewed trusted
execution and credential-release mechanism is required first; the author filter
and read-only GitHub token do not solve this problem.

Installation is not activation or review evidence. An authorized administrator
must approve the provider, sending repository content to it and recurring
usage/spending before setting repository variable `OCR_CI_ENABLED=true`.
Credentials being present is not authorization. No Azure resources, identities
or permissions are provisioned by this workflow.

Configure these in GitHub Actions settings, never in source or chat:

| Kind | Name | Purpose |
|------|------|---------|
| Secret | `OCR_LLM_URL` | HTTPS inference endpoint, without embedded credentials, query or fragment |
| Secret | `OCR_LLM_AUTH_TOKEN` | Provider credential; mapped to OCR's `OCR_LLM_TOKEN` |
| Variable | `OCR_LLM_MODEL` | Explicit model or deployment name |
| Variable | `OCR_LLM_PROTOCOL` | `openai`, `openai-responses` or `anthropic` |
| Variable | `OCR_CI_ENABLED` | Exact string `true` only after activation authorization |

The table specifies the expected interface, not permission to store credentials.
Repository or organization secrets accessible to PR-modified workflows do not
satisfy the unresolved credential boundary. Do not reuse unrelated audit
credentials or Azure identities.
Managed-identity authentication requires an approved CI identity integration;
storing an expiring Azure access token is not a durable substitute.

## Trust and privacy

The workflow uses `pull_request`, not `pull_request_target`, and has only
`contents: read` permissions. Only non-draft, same-repository PRs authored by an
OWNER, MEMBER or COLLABORATOR are eligible. External fork PRs are skipped, not
reviewed, even when their author is an organization member.

The job checks out the immutable trusted base SHA. Its trusted helper fetches
the PR's objects with a temporary read credential, verifies the exact head and
computes the merge-base. It never checks out the head or runs target builds,
tests, package scripts or commands. Installation of the pinned upstream npm
package occurs separately outside the source tree, without provider credentials.
Its checked-in npm lockfile pins integrity hashes for the launcher and all six
platform packages. `npm ci --ignore-scripts` installs only the lockfile contents;
package lifecycle scripts are not executed.

OCR receives only its allowlisted provider environment and a temporary HOME.
The GitHub token and unrelated environment secrets are not passed to OCR.
Its npm launcher's detached auto-updater is disabled with `OCR_NO_UPDATE=1`.
A mode-0600 temporary configuration binds endpoint, model, protocol and
`store:false` together for OpenAI-compatible requests; a fixed token command
reads the provider token from the environment rather than storing its value.
Captured JSON/stderr are size-bounded, remain temporary and are discarded.
Only fixed status and numeric counts reach logs and the step summary. No finding
content, file paths, raw provider errors, PR comments or artifacts are published.

This deliberately uses the documented **CLI**, not the upstream composite
action: the latter needs write permissions and prints final raw results, which
conflicts with several repositories' policies. Those policies are not weakened.
Any repository that prohibits automatic workflows altogether must keep the PR
blocked until a separate compatible policy decision; installation must not
silently bypass its validator.

## Limits, coverage and finding access

The job ceiling is 15 minutes. OCR runs one task at a time, low effort, a
20,000-token advisory budget and two-minute per-task timeout; each owned command
has a three-minute parent deadline. A newer event cancels the same PR's old job.
These are workload controls, **not** a hard dollar cap or aggregate spending
limit. Configure provider-side budgets/rate limits before activation.

Incomplete, budget-exhausted, malformed, wrong-range and nonzero-exit results
fail closed. The shared bounded JSON parser rejects duplicate keys, non-finite
constants, excessive nesting and excessive node counts. An explicit
`comments: null` is a valid upstream clean representation; a missing or malformed
comments field still fails. Success means coverage of OCR's selected range, not every repository
file, proven model quality or absence of vulnerabilities. Skips and missing
configuration are not clean reviews.

**This is counts-only CI, not actionable finding delivery.** Authorized owners
must run OCR locally for details until an approved private publisher is added.
Keep the check advisory until provider and coverage behavior have been observed;
do not add it as a required merge check solely because the workflow is installed.

Cloudflare's multi-agent `security-audit-skill` is not executed here and remains
separate work. An OCR result does not establish Cloudflare coverage.

Rollback: set `OCR_CI_ENABLED=false`, cancel owned running reviews and revert the
additive workflow if necessary. No branch protection changes are made.

[^ocr-workflow]: [Read-only OpenCodeReview workflow](workflows/ocr-pr-review.yml).
