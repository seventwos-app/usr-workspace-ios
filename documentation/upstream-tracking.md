---
type: Reference
status: draft
---

# Upstream Tracking

This fork tracks [element-hq/element-x-ios](https://github.com/element-hq/element-x-ios),
licensed AGPL-3.0. This document is the seventwos record of our sync
state with upstream; update it (and add a `log.md` entry) every time
`develop` is rebased/merged against upstream.

## Fork relationship

* **Upstream**: `element-hq/element-x-ios`, default branch `develop`.
* **Our branch**: `develop` (this repo's default branch).
* **Sync model**: pull-based. We periodically merge or rebase upstream
  `develop` into ours; we do not push changes upstream.

## Last known sync point

* **Recorded**: 2026-09-17
* **Our `develop` HEAD**: `f639d960e73785431719c638dd0846bc991e0204`
* **Upstream `develop` HEAD at time of recording**: `de13fa5438b9dbf0ff96efd2ba3160e952fa9d6d`
* **Divergence**: upstream was **9 commits ahead** of our last sync point
  (per `gh api repos/element-hq/element-x-ios/compare/<our-sha>...<upstream-sha>`).

## Upstream changes since fork

No upstream sync has been performed yet since this tracking document was
created; the 9-commit gap above is outstanding. Record each sync as a
dated entry below once performed.

### Sync log

* _(none yet — this document was seeded before the first tracked sync)_

## Process for the next sync

1. Compare current `develop` HEAD against upstream `develop` HEAD.
2. Merge or rebase upstream changes into `develop`.
3. Re-run `python3 scripts/okf/validate_okf_markdown.py --all` to confirm
   the `documentation/` bundle is unaffected.
4. Update this file's **Last known sync point** and append a **Sync log**
   entry summarizing what upstream changed (feature areas, breaking
   changes, version bumps) and any adaptation needed on our side.
5. Add a corresponding `log.md` entry.
