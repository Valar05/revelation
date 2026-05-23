# Revelation Orientation

Revelation is a sibling Godot project ported from the Nightmare Voyage text-choice stack. The project keeps the working console, command parser, run manager, encounter deck, delayed follow-up scheduler, resource/morale result reporting, room docs, and validation tooling.

The creative target is no longer ship descent horror. Revelation is a procedural symbolic horror roguelike about Institute containment squads investigating anomalies as theology, language, ritual, and myth begin altering physical reality.

## Current State

- Godot project name: `Revelation`.
- Main scene: `res://world.tscn`.
- Active content track: `revelation_packets_v1`.
- Active data files: `rooms_post_update.json`, `events_post_update.json`, `encounter_decks_post_update.json`.
- Initial vertical slice: Institute briefing plus `choir_beneath_floorboards`.
- Runtime still contains some inherited compatibility names such as `ship_dashboard`, `biomass`, `symbiote`, and old placeholder art. Treat these as scaffolding until renamed or replaced.

## What Was Ported

- Text-first console UI and command input.
- Run/deck/event loading.
- Delayed story follow-up queue.
- Hidden operation-plan odds and stress modifiers.
- Result delta reporting for morale/resources.
- Room/event doc browser.
- Bootstrap and smoke-test workflow.

## What Must Not Be Ported As Content

- Verne/Lovecraft maritime room corpus.
- Nightmare Voyage room premises, ship descent lore, officer cast, or black-hole language.
- Fleshpunk body-horror setting language.

## New Corpus Direction

Primary sources should be license-compatible and tracked with attribution:

- Public-domain Bible translations.
- Public-domain Torah/Hebrew Bible translations and references.
- Public-domain Quran translations or licensed translations approved for project use.
- SCP Wiki material only under its CC BY-SA 3.0 requirements, with article-level attribution and share-alike implications recorded.

The corpus should provide symbolic situations, procedural containment texture, theological language pressure, artifact patterns, and escalation structures. It should not be copied wholesale into mission prose.

## Acceptance Bar

A Revelation mission should include:

- SITREP or field report framing.
- A concrete anomaly with measurable symbolic behavior.
- A squad-level operational choice.
- Hidden squad/equipment/stress modifiers.
- A consequence that changes contamination, squad state, artifact state, civilian outcome, Institute pressure, or future mission text.
- Follow-up arcs for squad members, researchers, artifacts, or institutions.

Tone: restrained, professional, tired, procedural, symbolically charged, and theologically ambiguous.
