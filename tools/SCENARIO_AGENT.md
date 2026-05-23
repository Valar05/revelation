# Nightmare Voyage Scenario Agent

Generate scenario patches:

```sh
OPENAI_API_KEY=... python tools/scenario_agent.py generate --room brined_lifeboat_raft --count 3
```

Generate within a broad category:

```sh
python tools/scenario_agent.py categories
OPENAI_API_KEY=... python tools/scenario_agent.py generate --room brined_lifeboat_raft --category recovery --count 2
```

Review the project voice guide:

```sh
python tools/scenario_agent.py vibe
python tools/scenario_agent.py lore-guide
python tools/scenario_agent.py accessibility-guide
```

Generate a local sample without OpenAI:

```sh
python tools/scenario_agent.py generate --room brined_lifeboat_raft --mock
```

Validate a patch:

```sh
python tools/scenario_agent.py validate generated/scenario_patch.json
```

Rebuild spoken alias clouds across the current deck:

```sh
python tools/scenario_agent.py backfill-voice-aliases
python tools/scenario_agent.py backfill-voice-aliases --dry-run
```

Validate the current event data:

```sh
python tools/scenario_agent.py validate-events
python tools/scenario_agent.py validate-events --strict-actions
python tools/scenario_agent.py audit-writing
python tools/scenario_agent.py audit-accessibility
python tools/scenario_agent.py audit-accessibility --fail-on-findings
```

Critique a patch or the current event file against the vibe guide:

```sh
python tools/scenario_agent.py critique --patch generated/scenario_patch.json --out generated/patch_critique.json
python tools/scenario_agent.py critique --focus "Suggest new event types, encounters, and vibe guide updates."
```

Critique balance and run feel against the vibe guide:

```sh
python tools/scenario_agent.py balance-context
python tools/scenario_agent.py balance-critique --out generated/balance_critique.json
python tools/scenario_agent.py remember-balance generated/balance_critique.json --notes "Use this as current run-feel direction."
```

Critique blind first-time fun, whether visible packets/choices build into a run, and whether ship pressure is directing play toward outcomes:

```sh
python tools/scenario_agent.py fun-context
python tools/scenario_agent.py fun-critique --out generated/fun_critique.json
python tools/scenario_agent.py remember-fun generated/fun_critique.json --notes "Use this as current fun-loop direction."
```

Plan character-driven story architecture from the current repo data:

```sh
python tools/corpus_agent.py nightmare-fragments
python tools/corpus_agent.py nightmare-index
python tools/corpus_agent.py nightmare-context --limit 12
python tools/corpus_agent.py nightmare-index-context --gaps
python tools/scenario_agent.py story-architect-context
python tools/scenario_agent.py story-architect --out generated/story_architect.json
python tools/scenario_agent.py remember-story-architecture generated/story_architect.json --notes "Use this as current story-spine direction."
```

Generate and apply a story pilot patch from the current architecture:

```sh
python tools/scenario_agent.py story-pilot --corpus-fragment <fragment_id> --corpus-need <need_id> --out generated/story_pilot_patch.json
python tools/scenario_agent.py apply-story-pilot generated/story_pilot_patch.json --dry-run
python tools/scenario_agent.py apply-story-pilot generated/story_pilot_patch.json
```

Critique lore continuity, officer reporting, and captain-facing knowledge boundaries:

```sh
python tools/scenario_agent.py lore-context
python tools/scenario_agent.py lore-critique --out generated/lore_critique.json
python tools/scenario_agent.py remember-lore generated/lore_critique.json --notes "Use this as current lore direction."
```

Critique eyes-free playability, command aliases, and TTS/audio UX:

```sh
python tools/scenario_agent.py accessibility-context
python tools/scenario_agent.py accessibility-critique --out generated/accessibility_critique.json
python tools/scenario_agent.py remember-accessibility generated/accessibility_critique.json --notes "Use this as current accessibility direction."
```

Brainstorm new lore with gameplay hooks:

```sh
python tools/scenario_agent.py lore-brainstorm-context
python tools/scenario_agent.py lore-brainstorm --out generated/lore_brainstorm.json
python tools/scenario_agent.py remember-lore-brainstorm generated/lore_brainstorm.json --notes "Promote these lore hooks."
```

During play, inherited balance telemetry may still use Fleshpunk-era filenames until the runtime systems are fully renamed.

Build and audit phrase-sized TTS clips:

```sh
python tools/tts_manifest.py refresh
python tools/tts_manifest.py refresh --check
python tools/tts_manifest.py audit --fail-on-findings
python tools/tts_manifest.py plan
```

Generate clips with OpenAI Nova voice when ready:

```sh
OPENAI_API_KEY=... python tools/tts_manifest.py generate --category system
OPENAI_API_KEY=... python tools/tts_manifest.py generate
```

Use mock generation for pipeline tests without API calls:

```sh
python tools/tts_manifest.py generate --mock --category system --limit 3
```

Store critique guidance so future generation sees it:

```sh
python tools/scenario_agent.py remember-critique generated/content_critique.json --notes "Use this as the current creative direction."
```

Apply a JSON-only patch to `events.json`:

```sh
python tools/scenario_agent.py apply generated/scenario_patch.json
```

Record feedback so future generations adapt:

```sh
python tools/scenario_agent.py remember generated/scenario_patch.json --accepted --notes "Good tone; make risk clearer next time."
python tools/scenario_agent.py remember generated/scenario_patch.json --rejected --notes "Too generic; avoid fantasy language."
```

Notes:

- By default, the agent must use existing action ids from `run_manager.gd`.
- Event `type` values must match one of the category ids in `.agent-memory/event_categories.json`.
- Use `--allow-new-actions` only when you want it to propose engine work.
- The model can suggest mutations, symbiotes, or enemies, but this first tool only applies event patches automatically.
- `voice_aliases` are auto-generated from the button label, action, and nearby narration when patches are generated or applied, so new events get a spoken command cloud without hand-editing each room.
- Memory lives in `.agent-memory/`.
