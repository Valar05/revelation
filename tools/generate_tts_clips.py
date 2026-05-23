#!/usr/bin/env python3
"""Generate Revelation TTS clips from audio/tts_script.json."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "audio" / "tts_script.json"
MANIFEST_PATH = ROOT / "audio" / "tts_manifest.json"
OUTPUT_DIR = ROOT / "audio" / "generated"
EVENTS_PATH = ROOT / "events_post_update.json"
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"


def load_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return fallback or {}
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def profile_map(script: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for profile in script.get("speaker_profiles", []):
        if isinstance(profile, dict):
            speaker_id = str(profile.get("id", "")).strip()
            if speaker_id:
                profiles[speaker_id] = profile
    return profiles


def existing_manifest_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    clips = manifest.get("clips", [])
    if isinstance(clips, list):
        return [clip for clip in clips if isinstance(clip, dict)]
    if isinstance(clips, dict):
        entries: list[dict[str, Any]] = []
        for clip_id, clip_file in clips.items():
            entries.append({"id": str(clip_id), "file": str(clip_file)})
        return entries
    return []


def manifest_index(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in entries:
        generation_key = str(entry.get("generation_key", "")).strip()
        if generation_key:
            index[generation_key] = entry
    return index


def clip_ids_by_generation(script: dict[str, Any]) -> dict[str, list[str]]:
    by_generation: dict[str, list[str]] = {}
    for clip in script.get("clips", []):
        if not isinstance(clip, dict):
            continue
        generation_key = str(clip.get("generation_key", "")).strip()
        clip_id = str(clip.get("id", "")).strip()
        if generation_key and clip_id:
            by_generation.setdefault(generation_key, []).append(clip_id)
    return by_generation


def is_good_sample_text(text: Any) -> bool:
    words = str(text).split()
    if len(words) < 6:
        return False
    first = words[0].lower().strip(" ,;:.!?\"'")
    if first in {"and", "but", "or"}:
        return False
    return any(char.isalpha() for char in str(text))


def iter_event_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "event_id":
                event_id = str(child).strip()
                if event_id:
                    refs.append(event_id)
            else:
                refs.extend(iter_event_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(iter_event_refs(child))
    return refs


def scenario_event_ids(room_id: str, events_path: Path = EVENTS_PATH) -> set[str]:
    if not room_id:
        return set()
    events = load_json(events_path)
    special_events = events.get("special_events", {})
    if not isinstance(special_events, dict):
        special_events = {}
    event_ids: set[str] = set()
    room_events = events.get("room_events", {})
    if isinstance(room_events, dict):
        for event in room_events.get(room_id, []) or []:
            if isinstance(event, dict):
                event_id = str(event.get("id", "")).strip()
                if event_id:
                    event_ids.add(event_id)

    pending = list(event_ids)
    while pending:
        event_id = pending.pop()
        event = special_events.get(event_id)
        if not isinstance(event, dict):
            continue
        for ref in iter_event_refs(event):
            if ref not in event_ids:
                event_ids.add(ref)
                pending.append(ref)

    # Follow room events into special events too.
    if isinstance(room_events, dict):
        for event in room_events.get(room_id, []) or []:
            if not isinstance(event, dict):
                continue
            for ref in iter_event_refs(event):
                if ref not in event_ids:
                    event_ids.add(ref)
                    pending.append(ref)
        while pending:
            event_id = pending.pop()
            event = special_events.get(event_id)
            if not isinstance(event, dict):
                continue
            for ref in iter_event_refs(event):
                if ref not in event_ids:
                    event_ids.add(ref)
                    pending.append(ref)
    return event_ids


def generation_keys_for_scenario(script: dict[str, Any], room_id: str) -> set[str]:
    event_ids = scenario_event_ids(room_id)
    generation_keys: set[str] = set()
    for clip in script.get("clips", []):
        if not isinstance(clip, dict):
            continue
        clip_room_id = str(clip.get("room_id", ""))
        clip_event_id = str(clip.get("event_id", ""))
        if clip_room_id == room_id or clip_event_id in event_ids:
            generation_key = str(clip.get("generation_key", "")).strip()
            if generation_key:
                generation_keys.add(generation_key)
    return generation_keys


def generation_keys_for_clip_prefixes(script: dict[str, Any], prefixes: list[str]) -> set[str]:
    if not prefixes:
        return set()
    generation_keys: set[str] = set()
    for clip in script.get("clips", []):
        if not isinstance(clip, dict):
            continue
        clip_id = str(clip.get("id", "")).strip()
        if not any(clip_id.startswith(prefix) for prefix in prefixes):
            continue
        generation_key = str(clip.get("generation_key", "")).strip()
        if generation_key:
            generation_keys.add(generation_key)
    return generation_keys


def manifest_payload(script: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    entries_by_generation = manifest_index(entries)
    aliases = clip_ids_by_generation(script)
    text_by_generation: dict[str, str] = {}
    for item in script.get("canonical_texts", []):
        if not isinstance(item, dict):
            continue
        generation_key = str(item.get("generation_key", "")).strip()
        if generation_key:
            text_by_generation[generation_key] = str(item.get("text", ""))
    clips: list[dict[str, Any]] = []
    for clip in script.get("clips", []):
        if not isinstance(clip, dict):
            continue
        generation_key = str(clip.get("generation_key", "")).strip()
        clip_id = str(clip.get("id", "")).strip()
        if not generation_key or not clip_id or generation_key not in entries_by_generation:
            continue
        source_entry = entries_by_generation[generation_key]
        clips.append({
            "id": clip_id,
            "file": source_entry["file"],
            "text": clip.get("text", text_by_generation.get(generation_key, "")),
            "text_key": clip.get("text_key", ""),
            "generation_key": generation_key,
            "speaker_id": clip.get("speaker_id", source_entry.get("speaker_id", "")),
        })
    generated_entries: list[dict[str, Any]] = []
    for entry in entries_by_generation.values():
        enriched = entry.copy()
        generation_key = str(enriched.get("generation_key", "")).strip()
        if generation_key and "text" not in enriched:
            enriched["text"] = text_by_generation.get(generation_key, "")
        generated_entries.append(enriched)
    return {
        "schema_version": 2,
        "source_script": "audio/tts_script.json",
        "generated_clip_count": len(entries_by_generation),
        "runtime_clip_count": len(clips),
        "clips": clips,
        "generated": sorted(generated_entries, key=lambda item: str(item.get("generation_key", ""))),
        "aliases": aliases,
    }


def output_path_for(item: dict[str, Any], response_format: str) -> Path:
    speaker_id = str(item.get("speaker_id", "narrator")).strip() or "narrator"
    generation_key = str(item.get("generation_key", "")).strip()
    if not generation_key:
        raise ValueError("canonical text is missing generation_key")
    return OUTPUT_DIR / speaker_id / f"{generation_key}.{response_format}"


def api_payload(item: dict[str, Any], profile: dict[str, Any], response_format: str) -> dict[str, Any]:
    call = profile.get("call", {})
    if not isinstance(call, dict):
        call = {}
    payload: dict[str, Any] = {
        "model": str(call.get("model", profile.get("model", "gpt-4o-mini-tts"))),
        "voice": str(call.get("voice", profile.get("voice", "alloy"))),
        "input": str(item.get("text", "")),
        "response_format": response_format,
    }
    instructions = str(call.get("instructions", "")).strip()
    if instructions:
        payload["instructions"] = instructions
    for key in ("pitch", "speed"):
        if key in call:
            payload[key] = call[key]
    return payload


def request_clip(api_key: str, payload: dict[str, Any], timeout: int) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_SPEECH_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI TTS request failed: HTTP {error.code}: {detail}") from error


def generate(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set.")

    script = load_json(args.script)
    profiles = profile_map(script)
    manifest_entries = existing_manifest_entries(load_json(args.manifest, {"clips": []}))
    generated = manifest_index(manifest_entries)
    canonical_texts = [item for item in script.get("canonical_texts", []) if isinstance(item, dict)]
    selected_keys: set[str] = set()
    if args.scenario:
        scenario_keys = generation_keys_for_scenario(script, args.scenario)
        selected_keys.update(scenario_keys)
        canonical_texts = [
            item for item in canonical_texts
            if str(item.get("generation_key", "")).strip() in scenario_keys
        ]
    if args.clip_id_prefix:
        prefix_keys = generation_keys_for_clip_prefixes(script, args.clip_id_prefix)
        selected_keys.update(prefix_keys)
        canonical_texts = [
            item for item in canonical_texts
            if str(item.get("generation_key", "")).strip() in prefix_keys
        ]
    pending = [
        item for item in canonical_texts
        if args.force or str(item.get("generation_key", "")).strip() not in generated
    ]
    if args.speaker:
        pending = [item for item in pending if str(item.get("speaker_id", "")) == args.speaker]
    if args.sample_speakers:
        sampled_by_speaker: dict[str, dict[str, Any]] = {}
        fallback_by_speaker: dict[str, dict[str, Any]] = {}
        for item in pending:
            speaker_id = str(item.get("speaker_id", "narrator")).strip() or "narrator"
            fallback_by_speaker.setdefault(speaker_id, item)
            if speaker_id in sampled_by_speaker:
                continue
            if is_good_sample_text(item.get("text", "")):
                sampled_by_speaker[speaker_id] = item
        pending = [
            sampled_by_speaker.get(speaker_id, fallback_by_speaker[speaker_id])
            for speaker_id in sorted(fallback_by_speaker)
        ]
    if args.limit > 0:
        pending = pending[: args.limit]

    if args.dry_run:
        print(f"TTS_GENERATE_DRY_RUN pending={len(pending)} existing={len(generated)}")
        if args.scenario:
            print(f"scenario={args.scenario} selected_unique={len(canonical_texts)}")
        for item in pending[: min(len(pending), 20)]:
            speaker_id = str(item.get("speaker_id", "narrator"))
            profile = profiles.get(speaker_id, profiles.get("narrator", {}))
            call = profile.get("call", {}) if isinstance(profile.get("call", {}), dict) else {}
            print(f"- {speaker_id} voice={call.get('voice', profile.get('voice', 'alloy'))} pitch={call.get('pitch', profile.get('pitch', 1.0))} text={item.get('text', '')}")
        return 0

    completed = 0
    for item in pending:
        speaker_id = str(item.get("speaker_id", "narrator")).strip() or "narrator"
        profile = profiles.get(speaker_id, profiles.get("narrator", {}))
        clip_path = output_path_for(item, args.response_format)
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        payload = api_payload(item, profile, args.response_format)
        audio = request_clip(api_key, payload, args.timeout)
        clip_path.write_bytes(audio)
        generation_key = str(item.get("generation_key", "")).strip()
        generated[generation_key] = {
            "generation_key": generation_key,
            "text": item.get("text", ""),
            "text_key": item.get("text_key", ""),
            "speaker_id": speaker_id,
            "file": "res://" + str(clip_path.relative_to(ROOT)),
            "voice": payload.get("voice", ""),
            "model": payload.get("model", ""),
            "pitch": payload.get("pitch", 1.0),
            "speed": payload.get("speed", 1.0),
        }
        write_json(args.manifest, manifest_payload(script, list(generated.values())))
        completed += 1
        print("TTS_GENERATED %d/%d speaker=%s voice=%s pitch=%s file=%s" % (
            completed,
            len(pending),
            speaker_id,
            payload.get("voice", ""),
            payload.get("pitch", 1.0),
            clip_path.relative_to(ROOT),
        ))
        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"TTS_GENERATE_DONE generated={completed} existing={len(generated) - completed} total={len(generated)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=SCRIPT_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--response-format", default="mp3", choices=["mp3", "opus", "aac", "flac", "wav", "pcm"])
    parser.add_argument("--limit", type=int, default=0, help="Maximum new generated clips. 0 means all pending clips.")
    parser.add_argument("--speaker", default="", help="Only generate one speaker_id.")
    parser.add_argument("--scenario", default="", help="Only generate clips used by a room and its linked follow-up events.")
    parser.add_argument("--clip-id-prefix", action="append", default=[], help="Only generate clips whose runtime id starts with this prefix. Can be repeated.")
    parser.add_argument("--force", action="store_true", help="Regenerate selected clips even if their generation_key is already present.")
    parser.add_argument("--sample-speakers", action="store_true", help="Generate the first pending clip for each speaker.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    return generate(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
