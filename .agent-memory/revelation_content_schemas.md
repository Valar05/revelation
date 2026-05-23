# Revelation Content Schemas

## Mission Record

Required fields:

- `id`
- `name`
- `type`: `mission`
- `room_role`
- `encounter_family`
- `operation_type`
- `description`
- `first_visit_description`
- `detection_report`
- `current_situation`
- `deployment_manifest`
- `officer_reports`
- `resource_stakes`
- `character_state_stakes`
- `followup_vectors`
- `progression_state`
- `procedure_hooks`
- `corpus_influences`

Recommended fields:

- `recurring_character_ids`
- `mission_mode`: `investigation`, `action_horror`, `containment`, or `base_fallout`
- `action_profile` for action-horror rooms
- `interlude_vectors`
- `state_reads`
- `state_writes`
- `failure_modes`
- `artifact_vectors`

`character_state_stakes` should usually matter more than food, fuel, or water. Track who becomes less available, less trusting, more contaminated, more defiant, more withdrawn, or more useful under stress.

`deployment_manifest` is the scene-orientation layer. It must tell the player-facing writer who is deployed, where they are, why they are present, who is remote or absent, and what their visible state suggests.

Each manifest entry should include:

- `officer_id`
- `name`
- `mission_role`
- `physical_position`
- `assigned_reason`
- `visible_state`

The manifest must also survive into visible prose. `first_visit_description` or `current_situation` should answer: where is the squad, who is holding command, who is on point, where is Torah, who is handling evidence or instruments, and who is remote.

## Action Profile

Action-horror mission records require `action_profile`.

Required fields:

- `physical_threat`: what can hurt people now
- `contact_state`: how the squad is already in contact or about to be hit
- `field_manual_drill`: the procedure basis for the tactical response
- `tactical_objective`: what the squad must accomplish under pressure
- `symbolic_close`: what source-derived rule must be addressed beyond force
- `not_monster_of_week`: why this is a biblical/symbolic event rather than a generic creature fight

Action rooms should surface this profile in visible prose. The player should know the squad is under contact, what field problem they face, and why combat alone cannot resolve the anomaly.

## Event Record

Required fields:

- `id`
- `type`
- `speaker`
- `line_1`
- `line_2`
- `buttons`
- `action_results`

Choice events should also include:

- `story_thread`
- `corpus_influences`
- `story_followups`
- `state_reads`
- `interlude_hooks`
- `operation_plans`

For mission-entry choices, each button must represent a named character's plan. If that character is unavailable, injured, contaminated beyond the plan limit, or in a blocked mental state, the choice should not appear.

Each `operation_plans` entry should include:

- `action`
- `officer_id`
- `primary_skill`
- `tactical_step` for action-horror rooms
- `base_success`
- `yield`
- `risk`
- `minimum_availability`
- `blocked_mental_states`
- `outcomes`

The `outcomes` object should include at least:

- `success`
- `partial`
- `failure`

High-risk plans should also include:

- `strong_success`
- `catastrophe`

Each button result should include at least one of:

- `state_changes`
- `environment_state_changes`
- `resource_changes`
- `story_followup`
- `interlude_hook`
- durable branch-specific consequence text

## Follow-Up Record

Follow-ups are not filler. Required fields:

- `id`
- `type`: `story`, `debrief`, `interlude`, or `base_incident`
- `speaker`
- `line_1`
- `line_2`
- `buttons`
- `action_results`
- `story_thread`
- `trigger_conditions` or a parent `story_followups` entry
- `state_reads`
- `state_writes`
- `corpus_influences`

A follow-up should do at least one:

- escalate the original problem
- transform the problem into a new domain
- force a resource or personnel tradeoff
- change a specific character's morale, mental state, loyalty, trust, contamination, or availability
- expose hidden character state
- resolve the thread at cost
- queue an interlude or later mission

## Interlude Record

Required fields:

- `id`
- `type`: `interlude`
- `interlude_type`
- `trigger_conditions`
- `state_reads`
- `state_writes`
- `featured_characters`
- `visible_text`
- `choices`
- `outcomes`
- `followup_hooks`
- `corpus_anchors`
- `tone_notes`

Valid `interlude_type` values:

- `debrief`
- `smoke_break`
- `meal`
- `clinic`
- `barracks`
- `lab_window`
- `logistics`
- `command_corridor`

## Artifact Record

Required fields:

- `id`
- `name`
- `source_mission`
- `containment_status`
- `observed_behavior`
- `known_risks`
- `unknowns`
- `state_effects`
- `study_options`
- `interlude_hooks`
- `corpus_influences`

## Squad Arc Record

Required fields:

- `character_id`
- `arc_id`
- `current_stage`
- `visible_behavior`
- `hidden_state_reads`
- `state_writes`
- `trigger_events`
- `interlude_beats`
- `failure_or_breakpoint`
- `recovery_or_concession`

## Base Incident Record

Required fields:

- `id`
- `type`: `base_incident`
- `incident_domain`
- `trigger_conditions`
- `visible_text`
- `choices`
- `outcomes`
- `state_reads`
- `state_writes`
- `followup_hooks`
- `corpus_influences`

Useful `incident_domain` values:

- `containment`
- `research`
- `security`
- `medical`
- `psych`
- `logistics`
- `command`
- `public_exposure`
