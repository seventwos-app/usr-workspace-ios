---
name: decision-and-design
description: "Use for specifications, architecture or interface design, domain terminology, multi-service planning, or decomposing substantial work into tickets. Connects acceptance criteria to testable interfaces and challenges load-bearing assumptions. Not for routine bounded fixes with an established contract."
---

# Decision and design

## Establish the decision

Read the request, existing implementation, relevant glossary and architecture
decisions before proposing a new abstraction. State the desired outcome,
non-goals, constraints, and observable acceptance criteria. Resolve intent from
available context; ask one focused question only for a material unresolved fork.
In autonomous work, state reversible assumptions and proceed. Authorization,
destructive actions, and external publication are not ordinary assumptions.

Identify the single assumption whose failure would invalidate the plan, and the
cheapest safe experiment that can disprove it. Record an uncertain result as
uncertain; do not disguise a future dependency as an existing capability.

## Choose a useful interface

- Use the project's domain language. Distinguish overloaded terms with concrete
  scenarios and reconcile terminology with code before adding synonyms.
- Compare genuinely different interfaces when the choice is consequential;
  skip alternatives theater for an established small change.
- Prefer substantial behavior behind a small caller-facing contract. Include
  validation, errors, ordering, authorization, configuration, and performance
  obligations, not just a type signature.
- Keep knowledge local: a caller should not need to reproduce the module's
  policy. Reuse existing helpers and isolate dependencies that actually vary.
  Do not introduce an adapter solely for a hypothetical second implementation.
- Choose test seams that exercise the real caller contract. If the architecture
  prevents meaningful regression proof, name that design limitation rather
  than substituting a shallow test.

## Make implementation executable

For substantial work, map each acceptance criterion to its owner, interface,
proof command, and expected result. Break work into end-to-end slices that
produce observable behavior, not separate "all database" and "all UI" phases.
Declare actual dependency edges; parallelize only independent slices with
non-overlapping write ownership. A straightforward task needs no ticket system
or multi-agent fan-out.

Use existing planning and issue-tracker conventions. Do not create tracker
issues or publish a specification without the appropriate authorization.
Record an architecture decision only for a consequential trade-off that will
otherwise be surprising later; do not scaffold empty glossaries or ADR trees.

Before implementation, make failure handling, compatibility, rollout, rollback,
and data ownership explicit where applicable. Cut optional breadth rather than
weakening correctness or security. Hand off the chosen contract, rejected
alternative, assumptions, ordered slices, and acceptance proof.
