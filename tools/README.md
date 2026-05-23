# Revelation Audio

TTS audio from the legacy project was not copied.

Keep the project text-first until the first Revelation vertical slice is accepted, then regenerate audio from the new event text.

## Revelation Room Pipeline

Use the wrapper for the normal source-packet-to-playable-room path:

```sh
python3 tools/revelation_room_pipeline.py \
  --prompt "Generate one action_horror Revelation room..." \
  --corpus-fragments generated/corpus/example_selected_fragments.json \
  --replace-active
```

Budget-check without calling the model:

```sh
python3 tools/revelation_room_pipeline.py \
  --dry-run \
  --prompt "Generate one action_horror Revelation room..." \
  --corpus-fragments generated/corpus/example_selected_fragments.json
```

Reuse an existing blueprint without a paid call:

```sh
python3 tools/revelation_room_pipeline.py \
  --blueprint generated/example_blueprint.json \
  --replace-active
```

Reuse an existing compiled patch:

```sh
python3 tools/revelation_room_pipeline.py \
  --patch generated/example_compiled_patch.json \
  --replace-active
```

The wrapper compiles, validates, applies, optionally slices the active deck to the new room, updates opening glue, checks the doc browser, and runs the Godot room/follow-up smokes.
