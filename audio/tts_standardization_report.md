# TTS Standardization Report

- Cues: 5666
- Unique spoken texts: 3452
- Unique speaker/text clips: 3463
- Speaker profiles: 12
- Deduped clip savings: 2203
- Max phrase length: 22 words

## Speaker Profiles

- `agent_caleb_ross`: Agent Caleb Ross; voice `echo`; pitch 0.989; speed 1.04. fastidious, suspicious, legally exact
- `brooks`: Brooks; voice `marin`; pitch 0.933; speed 1.02. direct, economical, protective under pressure; female field-sergeant presence
- `dr_lenora_saye`: Dr. Lenora Saye; voice `nova`; pitch 1.035; speed 0.97. controlled, precise, emotionally withheld
- `dr_samira_iyad`: Dr. Samira Iyad; voice `fable`; pitch 1.084; speed 0.93. gentle but firm; concern stays practical
- `evidence_control`: Evidence Control; voice `sage`; pitch 1.047; speed 0.95. precise, careful, paper-forward
- `lt_mara_owen`: Lt. Mara Owen; voice `marin`; pitch 0.955; speed 1.00. clear tactical restraint; tension stays under the words
- `medical`: Medical; voice `coral`; pitch 1.059; speed 0.94. measured, diagnostic, no melodrama
- `narrator`: Narrator; voice `alloy`; pitch 1.000; speed 1.00. plain report cadence; do not perform character emotion
- `operations`: Operations; voice `cedar`; pitch 0.972; speed 0.98. controlled command-room cadence
- `public_affairs`: Public Affairs; voice `shimmer`; pitch 1.110; speed 1.02. careful, diplomatic, slightly too clean
- `sitrep`: SITREP; voice `onyx`; pitch 0.917; speed 0.96. clipped, procedural, low affect
- `torah`: Torah; voice `verse`; pitch 0.944; speed 0.98. minimal, deliberate, morally weighted

## Direct Quote Cues

- Quote cue count: 383
- `agent_caleb_ross`: 35
- `brooks`: 28
- `dr_lenora_saye`: 81
- `dr_samira_iyad`: 36
- `lt_mara_owen`: 43
- `narrator`: 118
- `torah`: 42

## Findings

No standardization findings.

## Generation Notes

- Generate one audio asset per `canonical_texts[].generation_key`. This preserves distinct voices when different speakers say the same text.
- Map every `clips[].id` that uses the same `generation_key` to the same generated audio file in `audio/tts_manifest.json`.
- Use `speaker_profiles[].call` or `audio/tts_speaker_profiles.json` to select provider, model, voice, pitch, speed, and instructions for each speaker.
- For OpenAI Speech API generation, pass `call.model`, `call.voice`, `call.pitch`, `call.speed`, clip text, and `call.instructions`.
- Character voices are reserved for explicit direct quotes or records marked `direct_quote`/`spoken_by_speaker`; related narration stays on narrator or institutional channel voices.
- Findings evaluate generated phrase chunks, not raw source paragraph length.
- Runtime event clips still use IDs such as `event_id_line_1` and `event_id_choice_1`; result lines can be matched through `text_key` fallback.
- This pass does not rewrite room/event prose. Treat findings as the cleanup queue before paid TTS.
