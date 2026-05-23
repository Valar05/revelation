# Revelation Audio

TTS audio from the legacy project was not copied.

Keep the project text-first until the first Revelation vertical slice is accepted, then regenerate audio from the new event text.

## Pre-Generation Standardization

Run this before generating or paying for TTS:

```sh
python tools/tts_standardizer.py
```

It writes:

- `audio/tts_script.json`: canonical spoken cues, phrase chunks, clip IDs, text keys, and deduplicated canonical texts.
- `audio/tts_speaker_profiles.json`: speaker IDs, display names, provider/model/voice assignments, pitch offsets, speed, texture, delivery notes, and per-speaker call settings.
- `audio/tts_standardization_report.md`: cleanup findings for long prompts, long choice labels, missing aliases, duplicate actions, and other TTS risks.

The standardizer does not rewrite room or event prose. It creates the stable spoken surface for generation and highlights content that should be cleaned before recording.

Generation should prefer one audio file per `canonical_texts[].generation_key`. Every `clips[].id` with the same `generation_key` can point to that same file in `audio/tts_manifest.json`. This keeps dedupe safe across speakers: the same text spoken by two different characters must generate two separate clips.

For OpenAI Speech API generation, use `speaker_profiles[].call.model`, `speaker_profiles[].call.voice`, `speaker_profiles[].call.pitch`, `speaker_profiles[].call.speed`, the clip text, and `speaker_profiles[].call.instructions`. `pitch` is the 1.0-based call scalar; `pitch_semitones` is retained as design metadata.

Speaker voice profiles are for explicit spoken dialogue only. If a line is narration, report prose, or merely related to a character/channel label, it stays on `narrator` unless the event/result is marked `direct_quote` or `spoken_by_speaker`.

Start with one generated clip per speaker:

```sh
python tools/generate_tts_clips.py --sample-speakers
```

Generate one scenario and its linked follow-ups:

```sh
python tools/generate_tts_clips.py --scenario room_borrowed_separation
```

Then generate the rest:

```sh
python tools/generate_tts_clips.py
```

The generator is resumable. It writes files under `audio/generated/` and updates `audio/tts_manifest.json` after each successful generated clip.

Runtime supports both direct event clip IDs, such as `root_event_line_1`, and text-key fallback for standardized phrase chunks. That lets shared phrases like `SITREP.`, `Detection.`, and `Choice one. Concede.` be recorded once and reused.
