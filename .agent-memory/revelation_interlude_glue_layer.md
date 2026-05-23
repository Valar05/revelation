# Revelation Interlude Glue Layer

## Purpose

Interludes are the connective tissue between missions. They make consequences visible before the next SITREP and give characters room to show stress, loyalty, resentment, injury, contamination, fatigue, faith, and doubt without turning every beat into an anomaly event.

This layer should be generated and indexed as first-class content, not treated as incidental flavor.

## Core Beat Types

- Debrief: formal review, transcript dispute, redaction argument, command pressure, medical clearance.
- Smoke break: informal squad read, gallows humor, avoidance, quiet confession, Brooks pressure valve.
- Meal: appetite loss, avoidance, shared table tension, small kindness, who sits apart.
- Clinic: injury check, contamination screen, psych evaluation, sleep medication, refusal to clear personnel.
- Barracks: insomnia, gear maintenance, prayer, argument, isolation, relationship damage.
- Lab window: artifact observation, scientist fatigue, contradictory readout, procedural disagreement.
- Logistics: PPE, containment seals, field sensors, medical supplies, clean rooms, psych capacity, transport availability, broken equipment.
- Command corridor: Institute politics, concessions, disciplinary threat, reassignment pressure.

## Placement

Every mission should produce at least one interlude candidate.

- After clean success: quiet decompression or subtle unresolved residue.
- After partial success: debrief friction and visible stress cost.
- After failure: command pressure, casualties, blame, refusal, quarantine, morale drop.
- Before next mission: logistics, readiness, squad availability, or character relationship state.

Longer arcs should alternate mission pressure with interlude pressure. The interlude should not simply repeat the mission mystery. It should show what the mission did to people and systems.

## State Hooks

Interludes must read from hidden and visible state:

- squad stress
- individual stress
- individual morale
- individual mental state
- morale
- contamination
- injury
- fatigue
- loyalty
- trust in Torah
- trust in Brooks
- command confidence
- medical supplies
- PPE
- containment seals
- field sensors
- psych capacity
- clean rooms
- artifact possession
- civilian casualties
- prior choice tags
- unresolved follow-up hooks

Interludes may write state:

- recover small stress
- expose hidden stress
- worsen morale
- trigger refusal
- restore trust
- create resentment
- unlock concession
- consume medicine, PPE, seals, lab capacity, psych capacity, or personnel availability
- flag quarantine
- queue follow-up mission
- alter officer/squad availability

## Generation Contract

Each interlude record should include:

- `id`
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

Player choices should be small but consequential. Examples:

- tell command the full truth or redact unstable details
- give the squad a night off or keep them in readiness
- spend medical supplies on one person or preserve stock
- permit a smoke break despite contamination protocol
- let Brooks handle the squad or make Torah speak directly
- clear a shaken specialist or hold them out of the next mission
- spend psych capacity on one person or keep the whole squad rotating
- quarantine a useful specialist or clear them under observation

## Character Reflection Rules

Characters should not announce their stats. They reveal state through behavior.

- High stress: clipped speech, repeated checks, ritualized cleaning, silence, irritation.
- Low individual morale: refusal, lateness, cynicism, gear neglect, distrust of command.
- Altered mental state: inappropriate calm, repeated phrases, avoidance of names, fixation on procedure, distorted memory.
- Contamination: sensory slips, language fixation, resonance response, impossible memory.
- Injury: guarded movement, concealed pain, overcompensation, medical evasion.
- Ordinary-life disruption: appetite loss, smoking more than usual, sitting apart, sleeping in gear, avoiding certain rooms.
- Loyalty damage: compliance without warmth, indirect challenges, side conversations.
- Recovery: appetite returns, jokes land, sleep improves, someone volunteers.

## Corpus Anchors

Use the expanded corpus as follows:

- FEMA/NIMS and EOC: debrief structure, command roles, reporting language.
- CDC/OSHA: quarantine, PPE, decontamination, exposure management, clinic posture.
- CDC/NIOSH stress sources: traumatic incident stress, judgment under stress, responder behavior.
- Army tactical/team sources: morale, unit cohesion, leader pressure, readiness, patrol aftermath.
- Scripture/apocrypha/folklore: symbolic residue, names, witness, purity, judgment, angelic or ritual pressure.

Do not use these sources as bulk quotation. Use them as circumstances, procedures, and symbolic scaffolding.

## Arc Function

Interludes should advance at least one of:

- character arc
- squad cohesion
- Institute politics
- field-support pressure
- contamination escalation
- artifact risk
- theological uncertainty
- follow-up chain

If an interlude does not change player understanding, state, or future pressure, cut it.

## Example Arc Shapes

- Mission success, civilian saved, squad spooked. Meal beat shows nobody eating. Next mission starts with weaker individual morale unless Brooks gets time to settle them.
- Artifact recovered. Lab window beat finds it responding to staff names. Player can isolate it, study it, or destroy evidence. Each choice changes command trust and contamination risk.
- Torah uses resonance. Clinic beat clears him physically but not linguistically; he stops using one ordinary word. Brooks notices but does not report it unless pushed.
- Quarantine after a successful recovery. Clinic beat forces a choice between clearing Ross, holding Iyad, or delaying the whole squad. The choice affects availability and trust.
- Clean tactical win. Smoke break reveals one operator heard command orders before Brooks gave them. Follow-up becomes a comms trust problem, not a repeated anomaly description.
- Individual morale split. Brooks remains steady, Ross becomes defiant, and Iyad becomes withdrawn. The squad aggregate looks serviceable, but the next mission changes depending on who is asked to lead the risky step.

## Acceptance Criteria

The glue layer is working when:

- every mission can queue at least one meaningful between-mission beat,
- interludes expose hidden state without numeric UI,
- interludes distinguish individual morale and mental state from the squad aggregate,
- morale, mental state, stress, injury, contamination, trust, and availability appear in ordinary life,
- follow-ups continue through debriefs and downtime instead of only mission rooms,
- characters feel more persistent after interludes than before them.
