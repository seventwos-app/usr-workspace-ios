---
name: evidence-first-engineering
description: "Use for feature implementation, bug diagnosis, performance regressions, test design, or evaluating whether an engineering change actually works. Requires symptom-specific proof, independent expected results, and one behavior slice at a time. Not for prose-only edits or read-only factual lookups."
---

# Evidence-first engineering

Use the repository's existing runners, interfaces, glossary, and decisions. This
discipline complements existing debugging and validation skills; do not run a
second process when the active workflow already supplies the same evidence.

## Establish the proof

1. Identify the user-visible behavior, the real caller interface, and the
   smallest command that can distinguish correct from incorrect behavior.
2. Reuse the nearest meaningful test seam. State what it covers and misses;
   consult the user only when choosing it would change a material contract.
3. Derive expected results from the requirement, an independently worked
   example, or authoritative fixtures, never by re-running the implementation.
4. For a bug, run the proof against the broken state and capture the specific
   failure. Import failures, missing dependencies, and unrelated errors are not
   a valid red. Minimize inputs without losing the original symptom.
5. If reproduction is unavailable, report the missing access or artifact.
   Inspection may narrow hypotheses, but do not present an untested patch as a
   verified fix. Do not instrument production without authorization.

## Implement in vertical slices

- For new behavior: one failing behavior test, minimal implementation, then
  rerun the test. Repeat for the next behavior, rather than bulk-writing tests
  against an imagined implementation.
- For non-obvious bugs: rank a small set of falsifiable hypotheses. Probe one
  variable at a time and reject hypotheses whose predicted result fails.
  A clear deterministic defect does not require a ceremonial hypothesis list.
- For performance: record the baseline, representative workload, and required
  threshold before editing. Compare on the same setup; report variation.
- For intermittent bugs: record seed, trial count, failures, and environment.
  A single green rerun is not evidence that a flake is fixed.
- Refactor only after green, preserve the behavior contract, and rerun proof.
  Do not add speculative adapters or mock the function under test.

## Check the checker

For a new test or evaluation, demonstrate that a representative wrong result is
rejected. Prefer a wrong-output fixture or an isolated temporary copy; never
mutate an unrelated working tree. Record the observed rejection and restore
task-owned temporary changes before finishing.

For model evaluations, additionally separate training/examples from holdouts,
identify label provenance, keep the rubric independent of the candidate's
answer, and disclose shared-model judging bias. Multiple model votes are not
independent ground truth.

## Finish and stop

Rerun the original scenario, then the nearest affected suite. For cross-boundary
changes prove the authority, contract, consumer, and user flow as applicable.
Remove task-owned debug instrumentation. Preserve stricter existing checks.
After two failed corrections of the same hypothesis, reassess rather than
patch-looping; disclose remaining unproved boundaries.

Handoff evidence: requirement -> test/interface -> observed red -> observed
green -> affected-boundary proof -> residual risk. A check not run is not green.
