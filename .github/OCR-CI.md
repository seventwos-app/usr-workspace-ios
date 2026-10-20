---
type: Reference
title: OpenCodeReview enrollment
description: Inert metadata declaring this repository's OCR enrollment status.
sources:
  - id: ocr-enrollment
    resource: .github/ocr-ci.json
  - id: upstream-ci
    resource: https://github.com/alibaba/open-code-review/blob/1672852136fc87748249d22bce0819f33419ea79/pages/src/content/docs/en/integrations/ci.md
---

# OpenCodeReview enrollment

This repository's enrollment[^ocr-enrollment] declares `central-only`
execution, no provider credentials in this repository, and separate
authorization before activation. The enrollment file is metadata; it does not
run OCR, provide review evidence, or authorize model calls.

The [upstream CLI CI recipe](https://github.com/alibaba/open-code-review/blob/1672852136fc87748249d22bce0819f33419ea79/pages/src/content/docs/en/integrations/ci.md)[^upstream-ci]
describes the general integration pattern. It is not evidence that OCR has run
for this repository. This guide makes no claims about the private controller's
implementation, security controls, or completed review coverage.

This enrollment covers OCR only. Cloudflare's security-audit skill is separate
and is not run by this repository's enrollment.

[^ocr-enrollment]: [Inert OCR enrollment metadata](ocr-ci.json).
[^upstream-ci]: [Pinned upstream CI integration guide](https://github.com/alibaba/open-code-review/blob/1672852136fc87748249d22bce0819f33419ea79/pages/src/content/docs/en/integrations/ci.md).
