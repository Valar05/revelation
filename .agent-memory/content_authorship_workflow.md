# Revelation Content Authorship Workflow

This project separates prose authorship from code integration.

## Rule

Codex agents should not be the primary author of large surfaces of final player-facing prose. For missions, SITREPs, outcome reports, artifact notes, dialogue, and debriefs, use the scenario/writing path, critique the result, then integrate accepted patches.

Codex may write schemas, tooling, tests, mechanical glue, exact user-supplied text, tiny labels, and emergency JSON repairs.

## Required Content Pipeline

1. Gather context:

```sh
python tools/project_bootstrap.py --strict
python tools/scenario_agent.py context
python tools/scenario_agent.py content-authorship
python tools/room_doc_browser.py --host 127.0.0.1 --port 3000
```

2. Choose license-compatible corpus anchors. For Revelation, anchors should come from public-domain scripture translations, compatible Quran translations, and SCP Wiki material only with CC BY-SA 3.0 attribution/share-alike obligations tracked.

3. Generate or draft mission data from source circumstance, procedure, evidence, escalation, and consequence. Do not copy sacred text or SCP article prose as flavor.

4. Critique for voice, restraint, procedural clarity, symbolic specificity, and readable mission structure.

5. Validate active content:

```sh
python tools/project_bootstrap.py --strict
godot --headless --quit --path .
godot --headless --path /storage/emulated/0/Documents/GodotProjects/revelation --script /storage/emulated/0/Documents/GodotProjects/revelation/tools/post_update_room_smoke.gd
godot --headless --path /storage/emulated/0/Documents/GodotProjects/revelation --script /storage/emulated/0/Documents/GodotProjects/revelation/tools/story_followup_smoke.gd
```

## Voice Gate

All generated prose must obey `.agent-memory/revelation_style.md`. The house voice is restrained, professional, tired, procedural, symbolically charged, and theologically ambiguous.

Corpus influence changes the operational structure of a mission, not the surface costume of the prose. Scripture and SCP material should become original Institute incidents, squad procedures, symbolic hazards, artifact behavior, and follow-up consequences.
