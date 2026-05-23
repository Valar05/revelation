# Revelation Agent Roles

## Purpose

These are role contracts for future generation workflows. They can be implemented as scenario-agent modes, separate prompts, or external agents. Do not multiply agents until the validation rails are useful.

## Mission Architect

Owns:

- mission skeleton
- objectives
- branch map
- state reads/writes
- follow-up chain
- interlude hooks
- failure modes

Must not write final prose without corpus anchors and continuity review.

## Corpus Curator

Owns:

- selecting source chunks
- rejecting weak anchors
- checking active/inactive corpus status
- identifying missing source coverage
- summarizing usable circumstances, not copying passages

Must cite chunk IDs from `generated/corpus/index/chunks.jsonl`.

## Interlude Writer

Owns:

- debriefs
- smoke breaks
- meals
- clinic checks
- barracks beats
- lab-window beats
- logistics and command-corridor scenes

Must show state through behavior. Must not expose numeric stats.

## Continuity Auditor

Owns:

- unresolved threads
- follow-up depth
- branch differentiation
- character state consistency
- whether interludes carry mission consequences
- whether a long arc escalates, mutates, or resolves

This is the most important role before bulk content generation.

## Mechanics Auditor

Owns:

- state key validity
- individual morale, mental state, trust, and field-support tradeoffs
- hidden-stat branch implications
- failure chance plausibility
- morale/refusal/mutiny pressure
- inventory/resource mode compatibility

Must reject single-result branches that do not model different risks.

## License Auditor

Owns:

- active corpus source checks
- SCP exclusion unless approved
- attribution/share-alike flags
- public-domain/government/permissive status
- blocked or mirrored source notes

Must fail content that cites inactive sources as active anchors.

## Recommended Workflow

1. Corpus Curator selects anchors.
2. Mission Architect builds skeleton and state hooks.
3. Interlude Writer adds between-mission consequence beats.
4. Continuity Auditor checks progression.
5. Mechanics Auditor checks state/resource logic.
6. License Auditor checks source status.
7. Scenario writer generates final prose only after the skeleton passes.
