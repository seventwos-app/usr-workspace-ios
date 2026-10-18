# OpenCodeReview CI

This repository uses the upstream OpenCodeReview PR action, pinned to commit
`1672852136fc87748249d22bce0819f33419ea79` and CLI version `1.13.0`.
It does not require the separate custom source-build/signing proof workflow.

## Configuration and activation

Installation is not activation or evidence that a review ran. The workflow is
inactive until an authorized administrator sets repository variable
`OCR_CI_ENABLED=true`. Do not set it merely because credentials are available.
First authorize the provider, sending repository content to that provider, and
recurring usage/spending. No Azure resources or permissions are provisioned.

Configure these through GitHub Actions settings, never in source or chat:

| Kind | Name | Purpose |
|------|------|---------|
| Secret | `OCR_LLM_URL` | HTTPS inference endpoint; no embedded credentials or query string |
| Secret | `OCR_LLM_AUTH_TOKEN` | Provider credential, mapped by upstream to `OCR_LLM_TOKEN` |
| Variable | `OCR_LLM_MODEL` | Explicit model or deployment name |
| Variable | `OCR_LLM_PROTOCOL` | `openai`, `openai-responses` or `anthropic` |
| Variable | `OCR_CI_ENABLED` | Exact string `true` after activation authorization |
| Variable | `OCR_PUBLIC_FINDINGS_APPROVED` | Exact string `true` only if public PR findings are explicitly authorized |

Use an organization secret with selected-repository access where available,
otherwise scoped repository secrets. Do not reuse an unrelated Azure identity or
GitHub audit credential. Azure short-lived managed-identity authentication needs
its own approved CI identity integration; a stored expiring access token is not
a durable replacement.

## Execution and privacy

Opened, updated, reopened and ready-for-review PRs trigger the workflow. Only
non-draft PRs whose author association is OWNER, MEMBER or COLLABORATOR are
eligible. Untrusted external contributors are not automatically given access to
provider quota; their skipped run is **not** a review. There is no comment-trigger
or scheduled spending surface.

The pinned upstream action checks out the trusted base and fetches the PR head
as Git objects. This workflow adds no head checkout, target build or test.
It reviews the Git range and publishes upstream's sticky summary and inline
comments. Findings are visible to everyone who can read that PR. Public
repositories fail before invocation unless public findings publication is
explicitly authorized. If findings must stay private, leave that authorization
unset and do not enable this publication path; a private findings sink is a
separate integration.

No raw review artifacts or live progress streaming are enabled. However, the
pinned upstream action always prints the final JSON and captured stderr to its
job log. Public publication authorization therefore covers both logs and PR
comments; disabling artifacts does not make the log private. Credentials
are supplied only to configuration validation and the pinned upstream action,
never interpolated into shell source. GitHub masks configured secret values,
but that is not a guarantee that arbitrary secrets already in repository files
or model-generated findings cannot appear in comments. Do not send sensitive
data to an unapproved provider or authorize public output as a substitute for
secret scanning.

## Limits and evidence

Each job has a 15-minute ceiling, one review task at a time, low effort,
60-second request timeout, two-minute task timeout and a 20,000-token upstream
budget. A new event cancels the preceding run for that PR. These are workload
controls, **not** a hard dollar cap or organization-wide spending limit.
Upstream may finish an in-flight round and publish partial findings after
exhausting its token budget; exit zero alone does not prove complete coverage.
Provider-side budgets/rate limits and recurring spending authorization remain
necessary before activation.

Keep this advisory rather than a required merge check until actual provider,
publication and coverage behavior have been observed. Record the reviewed head,
run URL, selected/covered/failed files and partial status; never label a skipped
or unconfigured run as a clean audit.

Cloudflare's `security-audit-skill` is not run by this action. Its genuine
multi-agent audit runtime remains separate and must not be claimed as installed
or verified by an OCR result.

Rollback: set `OCR_CI_ENABLED=false` first, cancel owned running reviews, then
revert the additive workflow if needed. No branch protection changes are made.
