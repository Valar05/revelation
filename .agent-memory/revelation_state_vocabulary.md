# Revelation State Vocabulary

## Purpose

State keys are the contract between missions, follow-ups, interludes, hidden squad simulation, and generation audits. Generated content should use these keys instead of inventing local names.

The player should not see exact numbers. These keys are for internal state, hidden modifiers, trigger conditions, and authored consequence planning.

## Namespacing

Use dotted keys:

- `squad.*` for whole-team state
- `torah.*` for Torah
- `brooks.*` for Brooks
- `character.<id>.*` for recurring personnel
- `resource.*` for mission equipment and Institute support
- `institute.*` for command/base pressure
- `artifact.<id>.*` for recovered objects
- `site.<id>.*` for mission location state
- `thread.<id>.*` for narrative arc state

## Core Squad Keys

Squad keys are aggregate pressure signals. They should not replace individual member state.

- `squad.morale`
- `squad.stress`
- `squad.cohesion`
- `squad.fatigue`
- `squad.readiness`
- `squad.loyalty`
- `squad.trust_in_torah`
- `squad.trust_in_brooks`
- `squad.refusal_risk`
- `squad.mutiny_risk`
- `squad.contamination`

## Character Keys

Each recurring member should have separate morale and mental state. The squad aggregate can shift because individuals change, but interludes should usually name the person whose behavior reveals the pressure.

- `torah.stress`
- `torah.morale`
- `torah.mental_state`
- `torah.contamination`
- `torah.resonance_load`
- `torah.control`
- `torah.trust_in_command`
- `torah.injury`
- `torah.language_instability`
- `brooks.stress`
- `brooks.morale`
- `brooks.mental_state`
- `brooks.fatigue`
- `brooks.trust_in_torah`
- `brooks.command_confidence`
- `brooks.loyalty`
- `character.<id>.morale`
- `character.<id>.mental_state`
- `character.<id>.stress`
- `character.<id>.fatigue`
- `character.<id>.injury`
- `character.<id>.contamination`
- `character.<id>.loyalty`
- `character.<id>.availability`
- `character.<id>.arc_stage`

Recommended `mental_state` values:

- `steady`
- `strained`
- `spooked`
- `fixated`
- `withdrawn`
- `angry`
- `dissociated`
- `ritualizing`
- `defiant`
- `unfit`
- `recovering`

## Resource Keys

Food, water, and fuel are not core Revelation pressure stats. The Institute normally provides them. They may appear as scene texture, site-specific deprivation, or a temporary incident modifier, but they should not drive the main roguelike economy.

Core resource/support keys:

- `resource.medical_supplies`
- `resource.ammunition`
- `resource.ppe`
- `resource.containment_seals`
- `resource.scripture_arrays`
- `resource.field_sensors`
- `resource.transport`
- `resource.lab_capacity`
- `resource.psych_capacity`
- `resource.clean_rooms`
- `resource.replacement_personnel`

Occasional incident-only keys:

- `resource.food`
- `resource.water`
- `resource.fuel`

## Institute Keys

- `institute.command_confidence`
- `institute.political_pressure`
- `institute.public_exposure`
- `institute.research_pressure`
- `institute.quarantine_load`
- `institute.staff_fatigue`
- `institute.security_posture`
- `institute.ethics_pressure`
- `institute.psych_backlog`
- `institute.personnel_shortage`

## Mission/Site Keys

- `site.<id>.containment`
- `site.<id>.civilian_risk`
- `site.<id>.resonance`
- `site.<id>.symbolic_contamination`
- `site.<id>.artifact_present`
- `site.<id>.evidence_integrity`
- `site.<id>.public_exposure`
- `site.<id>.structural_risk`

## Thread Keys

- `thread.<id>.stage`
- `thread.<id>.pressure`
- `thread.<id>.unresolved_hook`
- `thread.<id>.followup_due`
- `thread.<id>.interlude_due`
- `thread.<id>.resolved`

## Legacy Aliases To Retire

These may exist in early prototype data but should not be used in new generation:

- `morale` -> `squad.morale` for aggregate changes, or `character.<id>.morale` for individual changes
- `unrest` -> `squad.refusal_risk` or `squad.mutiny_risk`
- `crew.morale` -> `squad.morale`
- `symbolic_contamination` -> `squad.contamination`, `torah.contamination`, or `site.<id>.symbolic_contamination`
- `institutional_pressure` -> `institute.political_pressure` or `institute.command_confidence`
- `squad_stress` -> `squad.stress`
- `civilian_risk` -> `site.<id>.civilian_risk`

## State Writing Rules

- Every meaningful branch should write at least one character, squad, institute, artifact, or site state key, or queue a follow-up.
- Long branches should write more durable state than short branches.
- Follow-ups should read at least one previous state/tag and write a new state, not merely restate the premise.
- Interludes should expose hidden state through behavior, not numeric narration.
- Resource keys should focus on field support: medical supplies, PPE, containment seals, sensors, lab capacity, clean rooms, psych capacity, and replacement personnel.
- If a branch visibly affects one squad member, write that member's state directly instead of only changing `squad.morale`.
- Use `squad.morale` when the whole team climate changes, not as a substitute for individual morale.
- Do not use food/fuel/water as default rewards or penalties unless a specific mission makes supply, shelter, or civilian care the point.
