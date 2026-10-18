---
type: Reference
title: Central OpenCodeReview integration
description: Inert repository enrollment for trusted central OCR execution.
sources:
  - id: ocr-enrollment
    resource: .github/ocr-ci.json
---

# Central OpenCodeReview integration

This repository's enrollment[^ocr-enrollment] is inert configuration. It does
not run a PR workflow, receive provider credentials, dispatch another workflow,
or authorize model calls. The previous proposed `ocr-pr-review.yml` is removed.
No repository trigger policy or permission exception is needed for enrollment.

The central controller follows the
[upstream CLI CI recipe](https://github.com/alibaba/open-code-review/blob/1672852136fc87748249d22bce0819f33419ea79/pages/src/content/docs/en/integrations/ci.md):
install pinned OCR, configure an authorized provider, review an immutable Git
range and validate JSON coverage. Custom source-build/signing proofs are not a
prerequisite. No new Azure service is required.

## Trusted central execution

The controller runs only on its trusted default branch's hourly schedule, not a
PR event, manual dispatch, repository dispatch or downstream relay. It polls the
explicit ten-repository inventory with a separately scoped read-only credential.
Only open, non-draft, same-repository PRs by OWNER, MEMBER or COLLABORATOR are
eligible. External forks are skipped, including member-authored forks.

The coordinator revalidates repository, PR number and exact base/head identities
before fetching and immediately before review. It creates a separate temporary
Git repository, fetches only validated objects and computes the merge-base.
Neither target workflow definitions nor target files are checked out or executed.
The helper, package lock and evidence parser always come from central code.

OCR is pinned to `1.13.0`; `npm ci --ignore-scripts` uses integrity-locked packages
outside source without credentials. The launcher updater is disabled. OCR receives
only its provider configuration and allowlisted environment, not the repository
read token or unrelated credentials. A private temporary configuration reads the
provider token from the environment and binds OpenAI `store:false`.

## Required administrator setup before activation

In the private central repository, configure the `ocr-central` environment with
deployment branches restricted to protected `main` and restrict who may change
the controller or environment. Put the following credentials only in that central
environment, never in this repository's PR workflow or ordinary repository secrets:

| Kind | Name | Purpose |
|------|------|---------|
| Secret | `OCR_REPOSITORY_READ_TOKEN` | Dedicated read-only contents and pull-request access to exactly the ten selected repositories |
| Secret | `OCR_LLM_URL` | Explicit HTTPS endpoint without embedded credentials, query or fragment |
| Secret | `OCR_LLM_AUTH_TOKEN` | Approved provider credential |
| Variable | `OCR_LLM_MODEL` | Explicit model or deployment name |
| Variable | `OCR_LLM_PROTOCOL` | `openai`, `openai-responses` or `anthropic` |
| Variable | `OCR_CENTRAL_ENABLED` | Central repository variable, exact `true` only after separate activation approval |

Do not reuse the dedicated baseline-audit token. A centrally scoped GitHub App
installation credential is preferable for ongoing operation; its minting/rotation
integration is not implemented by this preparation. No credential, environment,
Azure identity, resource, provider permission or activation flag is configured
by these changes. An expiring Azure access token is not a durable authentication
solution.

Provider choice, repository-data processing, retention and recurring expenditure
must be authorized before activation. Configure provider-side rate/spend limits.
The administrator must verify environment branch restrictions and credential scope;
the workflow naming an environment does not create its protections.

## Limits, repetition and output

The controller selects at most one eligible PR each hourly invocation. It rotates
over the current sorted candidate list by UTC hour; it does not persist a
deduplication ledger, so unchanged revisions can be reviewed again. This is not
an exactly-once queue or a guaranteed latency/fairness SLA when PRs change.
Enumeration fails closed at 100 open PRs in any repository instead of silently
omitting later pages. The controller timeout is 20 minutes and runs do not overlap.

OCR uses concurrency one, low effort, a 20,000-token advisory budget, two-minute
per-task timeout and a three-minute parent deadline. These are workload bounds,
not a hard dollar cap or approval for recurring usage.

The strict shared parser rejects incomplete coverage, wrong revisions, nonzero
exit, duplicate keys, non-finite JSON and excessive depth/node counts. Explicit
upstream `comments: null` is clean; missing or malformed comments fail.
Only fixed statuses and numeric counts reach central logs. Raw JSON, stderr and
temporary source/configuration are discarded; no comments or artifacts are published.

**This is inactive, counts-only OCR preparation, not actionable finding delivery
or proof of a completed repository review.** Private findings publication remains
unimplemented. Do not make this a required merge check based on installation.
Cloudflare's multi-agent audit is separate and is not executed here.

Rollback: disable `OCR_CENTRAL_ENABLED` in the controller repository and cancel
its owned scheduled run. This repository has no OCR process or provider secret
to disable. Existing security workflows and branch protections are unchanged.

[^ocr-enrollment]: [Inert central OCR enrollment](ocr-ci.json).
