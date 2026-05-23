# Revelation Scenario Generation Process

Revelation scenarios use a three-layer corpus contract.

## Layer Contract

1. **What comes from religious text.**
   The anomaly's symbolic engine must come from scripture, apocrypha, or license-compatible religious material. This layer defines what is happening: judgment, naming, cleansing, covenant, flood, exile, witness, sacrifice, threshold, forbidden instruction, or another concrete religious structure.

2. **How comes from procedure documents.**
   Player choices, equipment, consequences, and branch logic must come from procedure: incident command, isolation, sampling, decontamination, triage, cordon, lockout, evidence custody, staff rotation, reporting, or after-action care.

3. **Structure comes from public-domain weird fiction.**
   The scenario's story shape may borrow public-domain weird-fiction structure: local testimony, archive trail, bad site history, field instruments failing, sample analysis, delayed realization, official uncertainty, and an aftermath that changes how ordinary infrastructure feels.

## Action-Horror Lane

Some missions are not evidence audits. If the source presents plague, beasts, war, pursuit, judgment, or violence, the generated room should use an action-horror mission mode.

In action-horror rooms:

- The anomaly must be physically dangerous before the squad arrives.
- The squad must make contact with the threat in the root event, not only observe aftermath.
- At least one plan must use field manual procedure as procedure: react to contact, establish security, suppress/fix, bound, breach, clear, evacuate casualties, break contact, cordon, or contain.
- At least one plan must use Torah as a symbolic asset to close or redirect the source rule, with risk to nearby personnel.
- The threat is not solved by "shoot it until it stops" unless the source rule has also been addressed.
- Outcome prose must include physical action, positional movement, equipment use, and a consequence to an individual squad member's stress, morale, mental state, injury, fatigue, contamination, loyalty, or availability.
- The fear of God should be present as scale, judgment, awe, and human smallness under pressure, not as melodrama or sermonizing.

The player is still authorizing character plans rather than controlling moment-to-moment combat. The scene should feel like a trained combat/containment team applying field doctrine under symbolic conditions.

## Violent Resolution Lane

Some religious problems can be solved, or partially solved, by violence against the correct target: an idol broken, an altar demolished, a beast slain, a gate breached, a false object burned, or a weapon disabled.

When a request calls for a violent solution:

- Violence must target an anomaly, object, structure, beast, or active threat, not helpless civilians or procedural suspects.
- At least one player plan should be a force option using an implemented action such as `destroy`, `intercept`, `seal`, or `torah_speaks` when symbolic force is the violent act.
- The force option may be morally correct, costly, or incomplete, but it cannot be decorative.
- The scenario must also explain why ordinary force is insufficient if the source rule is not addressed.
- The closure should distinguish between tactical neutralization and spiritual/moral resolution.

Do not reuse foundational examples as default source shapes. The locust swarm established the action lane, but future rooms should pull different religious problems unless the user explicitly asks for locusts.

The process is source-first. Do not begin with a modern procedural incident and attach religious labels afterward.

Required order:

1. `source_mechanism`: what action, sin, witness, judgment, reversal, or ritual structure occurs in the religious source.
2. `symbolic_rule`: the if/then anomaly rule derived from that mechanism.
3. `active_manifestation`: what symbolic energy is doing now, before the squad arrives.
4. `modern_incident_logic`: why this present-day site/person/system triggered that rule.
5. mission deployment, choices, outcomes, resolution, and interlude.

The Institute deploys because symbolic energy is actively manifesting as a result of sin. It does not deploy the squad merely to audit old records or solve a cold case.

If the religious source could be removed without changing the mission premise, active manifestation, and closure condition, the room fails.

If the field manual source could be removed from an action-horror room without changing the squad's choices, movement, equipment use, and failure modes, the room fails.

## Required Output

Each mission room must include:

- `source_mechanism` and `symbolic_rule`.
- `scenario_generation_contract` with `what_from`, `how_from`, and `structure_from`.
- `religious_subtext` that names a specific motif and visible requirements.
- A deployable patch shape:
  - `events` contains only root room events as `{room_id, event}`.
  - `special_events` contains queued follow-ups, resolution beats, debriefs, and cooldown interludes.
  - `story_followups` on root events target ids in `special_events`, not additional room events.
- `corpus_anchor_points` with at least one anchor for each layer:
  - `religious_what`
  - `procedural_how`
  - `weird_fiction_structure`
- `corpus_influences` as rich source objects, not bare source ids. Each influence must include source fingerprint, structural transfer, visible details, and payoff.
- Character-owned `operation_plans`.
- Runtime-valid operation plans:
  - `action` must match a button action.
  - `officer_id` must use the internal id, such as `brooks`, `specialist_mina_park`, `dr_lenora_saye`, or `torah`.
  - `base_success` must be a probability, not a percentage.
  - outcomes must be objects with `lines` plus durable `environment_state_changes` or `resource_changes`.
- Branch outcomes where success and fallout can coexist.
- At least one `interlude` follow-up for cooldown, debrief, smoke break, meal, clinic, lab, command corridor, or washdown.
- Interlude metadata: `interlude_type`, `state_reads`, `state_writes`, `featured_characters`, `visible_text`, `choices`, `outcomes`, `followup_hooks`, and `corpus_anchors`.

## Quality Bar

The religious layer must be structural, not decorative. A verse should become an operational rule, object behavior, classification, timing, or consequence.

The procedure layer must create real choices. Characters propose plans; hidden character state changes the odds; failures backfire on the person who proposed the plan.

The weird-fiction layer must shape escalation, not diction. Avoid mythos names, purple prose, and stock Lovecraft terms. Borrow evidence logic, not costume.

The interlude must change personnel state or future pressure. It should not merely repeat the mission phenomenon.

Corpus anchors and character stakes must survive into player-facing prose. Hidden `anchors`, `corpus_influences`, `character_state_stakes`, or `operation_plans` are not sufficient by themselves.

For every major anchor, at least one concrete visible detail should appear in room text, event text, outcome prose, or interlude prose. Examples: a timing gap, a marked doorway, a repeated name, a custody tag, a sealed form, a threshold rule, a bodily hesitation, or a procedural contradiction.

For every plan owner, at least one outcome should show that character behaving under pressure. Examples: silence, a delayed signature, refusing coffee, checking a door frame twice, avoiding a recording, insisting on evidence custody, or breaking procedure for a named reason.

Every mission must include a deployment manifest and must surface it in the opening prose. The player should know who is present, where they are, what their role is, and why a given character owns a choice before the choice is offered.

## Pipeline Acceptance

Generated content is not considered usable until it passes:

- `python3 tools/scenario_agent.py validate <patch> --strict-tradeoffs`
- `python3 tools/project_bootstrap.py --strict`
- `python3 tools/revelation_content_auditor.py --strict`

If a generated patch requires manual conversion from room events into special events, manual officer-id repair, percentage-to-probability repair, string outcome conversion, or corpus-anchor enrichment, the pipeline is wrong. Fix the schema, prompt, or validator first.

## Credit-Conservative Generation

The preferred Revelation path is blueprint first, patch second.

Use `tools/revelation_blueprint_agent.py` to ask the model for a compact room blueprint only. The model should spend tokens on modern incident logic, religious cause, procedural choices, character-owned plans, and player-facing prose. It should not spend tokens recreating final Godot patch boilerplate.

Use `tools/revelation_blueprint_compiler.py` to deterministically compile an accepted blueprint into a scenario patch.

Before any paid generation call, run a dry budget check:

```sh
python3 tools/revelation_blueprint_agent.py --dry-run --prompt "..." --corpus-fragments generated/corpus/brothers_door_selected_fragments.json --corpus-limit 5
```

The default input budget is intentionally strict. If the dry run exceeds it, reduce corpus count, source excerpt length, or request scope. Do not compensate by sending the entire project context.

The first paid pass must be treated as the acceptance attempt, not a brainstorming pass. The prompt should include:

- one concrete room request;
- a compact selected corpus packet;
- the intended root sin or investigation question if known;
- the expected closure shape;
- explicit constraints for modern plausibility.

Do not run paid critique on a bad room by default. If generation fails validation, prefer repairing the blueprint schema, compiler defaults, or prompt contract first.
