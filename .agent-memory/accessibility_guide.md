# Revelation Accessibility Guide

This game is text/audio-first.
The project is dropping support for visual presentation beyond text, decisions, status, inventory, and command feedback. No required information may exist only in art, color, animation, or layout.

## North Star

The game must be fully playable without looking at the screen.

Every turn must make clear:
- what packet, object, signal, or ship crisis is active
- what changed
- what choices are legal
- what each choice is likely to cost
- what state pressures are rising or falling
- what the player can say next

## Room Text Model

Rooms need two text descriptions:
- `first_visit_description`: relatively longer; establishes function, threat, route logic, and what the room seems to want
- `return_description`: shorter; confirms identity and highlights changed pressure or persistence

Both descriptions should be captain-facing reports, officer briefings, logs, or procedural transcripts.
Event text should follow packet text and should not repeat the same description unless something changed.

## Legacy Content Boundary

Existing visual-first room records are legacy.

New accessibility audits should judge forward content against the text-only room model, not against whether old image-backed rooms have parity.

## Command Model

The speech system should feed text into the same command parser used for typed commands.

Core commands:
- one
- two
- three
- repeat
- repeat choices
- status
- inventory
- help
- confirm
- cancel
- pause
- continue
- slower
- faster

Context commands:
- seal
- scan
- vent
- reroute
- repair
- quarantine
- translate
- dock
- jettison
- descend
- listen
- chart
- study

## Event Requirements

Every button must have:
- label
- action
- voice_aliases

Voice aliases should be short, distinct, and natural to say.

Example:

```json
{
  "label": "Quarantine the sample",
  "action": "quarantine",
  "voice_aliases": ["quarantine", "isolate", "seal sample"]
}
```

## TTS Rules

Narration should be phrase-based.

Avoid:
- long paragraphs
- nested clauses
- visual-only descriptions
- choices hidden inside prose
- multiple mechanical changes in one unbroken sentence

Prefer:
- short room narration
- short pressure line
- numbered choices
- explicit result lines
- status summaries on request

## Result Rules

After every action, audio must state the important mechanical change.

Examples:
- "Pressure stability falls."
- "Quarantine watch started."
- "Hull material recovered."
- "Navigation certainty falls."
- "Officer trust changed."

## Ambiguity Rules

If a spoken command maps to more than one legal action, ask for confirmation.

If a command is unknown, say:
- "I did not match that."
- "Say repeat choices, status, or a choice number."

The parser should never invent actions.
It may only choose from current legal buttons and global commands.

## Ending Rules

Every ending must explain cause.

The player should be able to ask why:
- "why"
- "explain"
- "what happened"

The answer should summarize the pressure path without explaining the black hole definitively.

## Audit Rules

Flag:
- buttons without voice aliases
- duplicate aliases within one encounter
- aliases that collide with global commands
- visible-only information
- missing state-change result text
- overly long TTS lines
- generic or ambiguous button labels
- ending text without cause
- any required information carried only by sprite, color, or animation
