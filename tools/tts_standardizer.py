#!/usr/bin/env python3
"""Build a standardized, deduplicated TTS script from active Revelation content."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
SCRIPT_PATH = ROOT / "audio" / "tts_script.json"
REPORT_PATH = ROOT / "audio" / "tts_standardization_report.md"
SPEAKER_PROFILE_PATH = ROOT / "audio" / "tts_speaker_profiles.json"
CHOICE_WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
MAX_SPOKEN_WORDS = 22
MAX_BUTTON_WORDS = 6
MIN_HARD_CHUNK_WORDS = 8
ABBREVIATION_TOKENS = {
    "Dr.": "Dr<dot>",
    "Lt.": "Lt<dot>",
    "Mr.": "Mr<dot>",
    "Mrs.": "Mrs<dot>",
    "Ms.": "Ms<dot>",
    "St.": "St<dot>",
}
BAD_CHUNK_END_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "but",
    "for",
    "from",
    "in",
    "of",
    "or",
    "the",
    "to",
    "with",
}
BAD_CHUNK_START_WORDS = {
    "and",
    "but",
    "or",
}
SPEAKER_ALIASES = {
    "": "narrator",
    "system": "narrator",
    "narrator": "narrator",
    "captain": "narrator",
    "sitrep": "sitrep",
    "institute operations": "operations",
    "operations": "operations",
    "evidence control": "evidence_control",
    "evidence_control": "evidence_control",
    "public affairs": "public_affairs",
    "public_affairs": "public_affairs",
    "medical": "medical",
    "brooks": "brooks",
    "torah": "torah",
    "lt mara owen": "lt_mara_owen",
    "lt_mara_owen": "lt_mara_owen",
    "agent caleb ross": "agent_caleb_ross",
    "agent_caleb_ross": "agent_caleb_ross",
    "dr lenora saye": "dr_lenora_saye",
    "dr_lenora_saye": "dr_lenora_saye",
    "dr samira iyad": "dr_samira_iyad",
    "dr_samira_iyad": "dr_samira_iyad",
}
OFFICER_DISPLAY_NAMES = {
    "torah": "Torah",
    "brooks": "Brooks",
    "lt_mara_owen": "Lt. Mara Owen",
    "dr_samira_iyad": "Dr. Samira Iyad",
    "agent_caleb_ross": "Agent Caleb Ross",
    "specialist_mina_park": "Specialist Mina Park",
    "dr_lenora_saye": "Dr. Lenora Saye",
}
SPEAKER_PROFILES = {
    "narrator": {
        "display_name": "Narrator",
        "category": "narrator",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "voice_family": "current_default",
        "pitch_semitones": 0.0,
        "speed": 1.0,
        "texture": "clean neutral narration",
        "delivery": "plain report cadence; do not perform character emotion",
    },
    "sitrep": {
        "display_name": "SITREP",
        "category": "system",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "onyx",
        "voice_family": "low_neutral_dispatch",
        "pitch_semitones": -1.5,
        "speed": 0.96,
        "texture": "dry operations channel",
        "delivery": "clipped, procedural, low affect",
    },
    "operations": {
        "display_name": "Operations",
        "category": "department",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "cedar",
        "voice_family": "mid_neutral_dispatch",
        "pitch_semitones": -0.5,
        "speed": 0.98,
        "texture": "secure channel, administrative",
        "delivery": "controlled command-room cadence",
    },
    "evidence_control": {
        "display_name": "Evidence Control",
        "category": "department",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "sage",
        "voice_family": "narrow_mid_documentary",
        "pitch_semitones": 0.8,
        "speed": 0.95,
        "texture": "chain-of-custody clerk",
        "delivery": "precise, careful, paper-forward",
    },
    "medical": {
        "display_name": "Medical",
        "category": "department",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "coral",
        "voice_family": "soft_clinical_neutral",
        "pitch_semitones": 1.0,
        "speed": 0.94,
        "texture": "clinic intercom",
        "delivery": "measured, diagnostic, no melodrama",
    },
    "public_affairs": {
        "display_name": "Public Affairs",
        "category": "department",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "shimmer",
        "voice_family": "smooth_public_liaison",
        "pitch_semitones": 1.8,
        "speed": 1.02,
        "texture": "polished institutional",
        "delivery": "careful, diplomatic, slightly too clean",
    },
    "brooks": {
        "display_name": "Brooks",
        "category": "character",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "marin",
        "voice_family": "low_female_field_sergeant",
        "pitch_semitones": -1.2,
        "speed": 1.02,
        "texture": "worn field command, female",
        "delivery": "direct, economical, protective under pressure; female field-sergeant presence",
    },
    "lt_mara_owen": {
        "display_name": "Lt. Mara Owen",
        "category": "character",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "marin",
        "voice_family": "steady_low_officer",
        "pitch_semitones": -0.8,
        "speed": 1.0,
        "texture": "disciplined field officer",
        "delivery": "clear tactical restraint; tension stays under the words",
    },
    "agent_caleb_ross": {
        "display_name": "Agent Caleb Ross",
        "category": "character",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "echo",
        "voice_family": "tight_mid_investigator",
        "pitch_semitones": -0.2,
        "speed": 1.04,
        "texture": "evidence-room investigator",
        "delivery": "fastidious, suspicious, legally exact",
    },
    "dr_lenora_saye": {
        "display_name": "Dr. Lenora Saye",
        "category": "character",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "nova",
        "voice_family": "cool_precise_scientist",
        "pitch_semitones": 0.6,
        "speed": 0.97,
        "texture": "analytical lab lead",
        "delivery": "controlled, precise, emotionally withheld",
    },
    "dr_samira_iyad": {
        "display_name": "Dr. Samira Iyad",
        "category": "character",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "fable",
        "voice_family": "warm_clinical_physician",
        "pitch_semitones": 1.4,
        "speed": 0.93,
        "texture": "quiet clinical authority",
        "delivery": "gentle but firm; concern stays practical",
    },
    "torah": {
        "display_name": "Torah",
        "category": "character",
        "provider": "openai",
        "model": "gpt-4o-mini-tts",
        "voice": "verse",
        "voice_family": "low_player_commander",
        "pitch_semitones": -1.0,
        "speed": 0.98,
        "texture": "restrained command presence",
        "delivery": "minimal, deliberate, morally weighted",
    },
}


@dataclass(frozen=True)
class Cue:
    clip_id: str
    text: str
    role: str
    source: str
    speaker_id: str = "narrator"
    event_id: str = ""
    room_id: str = ""
    action: str = ""
    text_key: str = ""
    generation_key: str = ""


def load_json(path: Path) -> dict[str, Any]:
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


def normalize_space(text: Any) -> str:
    return " ".join(str(text).replace("\n", " ").split())


def normalize_spoken_phrase(text: Any) -> str:
    phrase = normalize_space(text)
    phrase = phrase.strip(" ,;:\"'")
    while phrase.endswith(("..", "!!", "??")):
        phrase = phrase[:-1]
    if phrase and phrase[-1] not in ".!?":
        phrase += "."
    return phrase


def has_terminal_punctuation(text: str) -> bool:
    return re.search(r"[.!?]['\")\]]*$", text.strip()) is not None


def split_spoken_phrases(text: Any, max_words: int = MAX_SPOKEN_WORDS) -> list[str]:
    normalized = normalize_space(text)
    if not normalized:
        return []
    protected = normalized
    for abbreviation, token in ABBREVIATION_TOKENS.items():
        protected = protected.replace(abbreviation, token)
    raw_parts = [
        part
        for part in re.split(r"(?<=[.!?])\s+", protected)
        if part.strip()
    ]
    phrases: list[str] = []
    for raw_part in raw_parts:
        part = raw_part.strip()
        for abbreviation, token in ABBREVIATION_TOKENS.items():
            part = part.replace(token, abbreviation)
        if not part:
            continue
        words = part.split()
        if len(words) <= max_words and not (":" in part and len(words) > 10):
            phrases.append(normalize_spoken_phrase(part))
            continue
        phrases.extend(split_long_phrase(part, max_words))
    return phrases


def split_long_phrase(text: str, max_words: int = MAX_SPOKEN_WORDS) -> list[str]:
    clauses = [clause.strip() for clause in re.split(r"(?<=[,;:])\s+", text) if clause.strip()]
    phrases: list[str] = []
    current: list[str] = []
    for clause in clauses:
        clause_words = trim_bad_leading_words(clause.split())
        if len(clause_words) > max_words:
            if current:
                phrases.append(normalize_spoken_phrase(" ".join(current)))
                current = []
            phrases.extend(split_hard_word_chunks(clause_words, max_words))
            continue
        if current and len(current) + len(clause_words) > max_words and len(current) > 4:
            phrases.append(normalize_spoken_phrase(" ".join(current)))
            current = []
        current.extend(clause_words)
        if clause.rstrip().endswith(":") and len(current) > 4:
            phrases.append(normalize_spoken_phrase(" ".join(current)))
            current = []
    if current:
        phrases.append(normalize_spoken_phrase(" ".join(current)))
    return phrases


def split_hard_word_chunks(words: list[str], max_words: int = MAX_SPOKEN_WORDS) -> list[str]:
    phrases: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        while end - start > MIN_HARD_CHUNK_WORDS and words[end - 1].lower().strip(" ,;:.!?\"'") in BAD_CHUNK_END_WORDS:
            end -= 1
        if len(words) - end > 0 and len(words) - end < MIN_HARD_CHUNK_WORDS:
            end = len(words)
        chunk = trim_bad_leading_words(words[start:end])
        phrases.append(normalize_spoken_phrase(" ".join(chunk)))
        start = end
    return phrases


def text_key(text: str) -> str:
    return hashlib.sha256(normalize_spoken_phrase(text).lower().encode("utf-8")).hexdigest()


def generation_key(speaker_id: str, key: str) -> str:
    return hashlib.sha256(f"{speaker_id}:{key}".encode("utf-8")).hexdigest()


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return value or "cue"


def speaker_id_for(value: Any, default: str = "narrator") -> str:
    normalized = normalize_space(value).lower()
    if normalized in SPEAKER_ALIASES:
        return SPEAKER_ALIASES[normalized]
    if not normalized:
        return default
    return slug(normalized)


def voice_speaker_id_for_event_line(event: dict[str, Any]) -> str:
    speaker_id = speaker_id_for(event.get("speaker", "narrator"))
    if bool(event.get("direct_quote", False)) or bool(event.get("spoken_by_speaker", False)):
        return speaker_id
    return "narrator"


def voice_speaker_id_for_result(result: dict[str, Any]) -> str:
    if bool(result.get("direct_quote", False)) or bool(result.get("spoken_by_speaker", False)):
        return speaker_id_for(result.get("speaker", "narrator"))
    return "narrator"


def speaker_profile_for(speaker_id: str) -> dict[str, Any]:
    if speaker_id in SPEAKER_PROFILES:
        profile = SPEAKER_PROFILES[speaker_id].copy()
    else:
        profile = {
            "display_name": speaker_id.replace("_", " ").title(),
            "category": "uncatalogued",
            "provider": "openai",
            "model": "gpt-4o-mini-tts",
            "voice": "alloy",
            "voice_family": "unassigned",
            "pitch_semitones": 0.0,
            "speed": 1.0,
            "texture": "needs casting",
            "delivery": "assign before final clip generation",
        }
    profile["id"] = speaker_id
    profile["pitch_unit"] = "semitones"
    profile["pitch"] = pitch_scale_from_semitones(float(profile["pitch_semitones"]))
    profile["call"] = {
        "provider": profile["provider"],
        "model": profile["model"],
        "voice": profile["voice"],
        "pitch": profile["pitch"],
        "speed": profile["speed"],
        "pitch_semitones": profile["pitch_semitones"],
        "instructions": "%s. Target pitch offset: %+0.1f semitones. Target speed: %.2fx." % (
            profile["delivery"],
            float(profile["pitch_semitones"]),
            float(profile["speed"]),
        ),
    }
    return profile


def pitch_scale_from_semitones(semitones: float) -> float:
    return round(math.pow(2.0, semitones / 12.0), 3)


def compact_button_label(text: Any, max_words: int = MAX_BUTTON_WORDS, max_chars: int = 42) -> str:
    label = normalize_space(text)
    words = label.split()
    if max_words > 0 and len(words) > max_words:
        clipped_words = trim_bad_terminal_words(words[:max_words])
        label = " ".join(clipped_words).rstrip(",;:") + "..."
    if len(label) > max_chars:
        clipped_words = trim_bad_terminal_words(label[: max_chars - 3].rstrip().split())
        label = " ".join(clipped_words).rstrip(",;:") + "..."
    return label


def trim_bad_terminal_words(words: list[str]) -> list[str]:
    clipped = list(words)
    while len(clipped) > 1 and clipped[-1].lower().strip(" ,;:.!?\"'") in BAD_CHUNK_END_WORDS:
        clipped.pop()
    return clipped


def trim_bad_leading_words(words: list[str]) -> list[str]:
    clipped = list(words)
    while len(clipped) > 1 and clipped[0].lower().strip(" ,;:.!?\"'") in BAD_CHUNK_START_WORDS:
        clipped.pop(0)
    return clipped


def event_records(events: dict[str, Any]) -> list[tuple[str, str, dict[str, Any], bool]]:
    records: list[tuple[str, str, dict[str, Any], bool]] = []
    room_events = events.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, room_event_list in room_events.items():
            if not isinstance(room_event_list, list):
                continue
            for event in room_event_list:
                if isinstance(event, dict):
                    records.append((str(room_id), str(event.get("id", "")), event, False))
    special_events = events.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                records.append((str(event.get("room_id", "")), str(event.get("id", event_id)), event, True))
    return records


def action_results(event: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    results = event.get("action_results", {})
    if not isinstance(results, dict):
        return []
    values: list[tuple[str, dict[str, Any]]] = []
    for action, result in results.items():
        if isinstance(result, dict):
            values.append((str(action), result))
    return values


def display_buttons(event: dict[str, Any]) -> list[dict[str, Any]]:
    choices = event.get("choices", [])
    if str(event.get("type", "")) == "interlude" and isinstance(choices, list) and choices:
        event_id = str(event.get("id", "event"))
        generated: list[dict[str, Any]] = []
        for index, choice in enumerate(choices):
            label = normalize_space(choice)
            if not label:
                continue
            generated.append({
                "label": compact_button_label(label, max_words=0, max_chars=96),
                "action": f"debrief_choice:{event_id}:{index}",
                "voice_aliases": [f"choice {index + 1}", f"option {index + 1}"],
                "generated_from_choices": True,
            })
        return generated

    buttons = event.get("buttons", [])
    if isinstance(buttons, list) and buttons:
        return [button for button in buttons if isinstance(button, dict)]
    if not isinstance(choices, list):
        return []
    event_id = str(event.get("id", "event"))
    generated: list[dict[str, Any]] = []
    for index, choice in enumerate(choices):
        label = normalize_space(choice)
        if not label:
            continue
        generated.append({
            "label": compact_button_label(label),
            "action": f"debrief_choice:{event_id}:{index}",
            "voice_aliases": [f"choice {index + 1}", f"option {index + 1}"],
            "generated_from_choices": True,
        })
    return generated


def choice_text(index: int, label: str) -> str:
    number = CHOICE_WORDS[index] if index < len(CHOICE_WORDS) else str(index + 1)
    clean_label = normalize_space(label).rstrip(".")
    return normalize_spoken_phrase(f"Choice {number}. {clean_label}.")


def officer_display_name(officer_id: str, fallback_name: str = "") -> str:
    fallback = normalize_space(fallback_name)
    if fallback:
        return fallback
    return OFFICER_DISPLAY_NAMES.get(officer_id, officer_id)


def operation_plan_lines(event: dict[str, Any]) -> list[str]:
    plans = event.get("operation_plans", [])
    if not isinstance(plans, list) or not plans:
        return []
    lines = ["Proposals:"]
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        officer_id = str(plan.get("officer_id", ""))
        officer_name = officer_display_name(officer_id, str(plan.get("officer_name", "")))
        plan_text = str(plan.get("intent", plan.get("tactical_step", plan.get("yield", "unlisted plan"))))
        risk_text = str(plan.get("risk", "unlisted risk"))
        lines.append(f"{officer_name}: {plan_text} Risk: {risk_text}.")
    return lines


def add_cue(cues: list[Cue], clip_id: str, text: str, role: str, source: str, speaker_id: str = "narrator", event_id: str = "", room_id: str = "", action: str = "") -> None:
    spoken = normalize_spoken_phrase(text)
    if not spoken:
        return
    key = text_key(spoken)
    cues.append(Cue(
        clip_id=clip_id,
        text=spoken,
        role=role,
        source=source,
        speaker_id=speaker_id_for(speaker_id),
        event_id=event_id,
        room_id=room_id,
        action=action,
        text_key=key,
        generation_key=generation_key(speaker_id_for(speaker_id), key),
    ))


QUOTE_RE = re.compile(r"(?:\"([^\"]{3,})\"|“([^”]{3,})”|‘([^’]{3,})’|(?<![A-Za-z])'([^']{3,})'(?![A-Za-z]))")


def add_phrase_cues(cues: list[Cue], prefix: str, text: str, role: str, source: str, speaker_id: str = "narrator", event_id: str = "", room_id: str = "", action: str = "") -> None:
    phrases = split_spoken_phrases(text)
    for index, phrase in enumerate(phrases, start=1):
        suffix = "" if len(phrases) == 1 else "_part_%d" % index
        add_cue(cues, f"{prefix}{suffix}", phrase, role, source, speaker_id, event_id, room_id, action)


def add_quote_aware_phrase_cues(cues: list[Cue], prefix: str, text: str, role: str, source: str, quote_speaker_id: str, event_id: str = "", room_id: str = "", action: str = "") -> None:
    segments = quote_aware_segments(text, quote_speaker_id)
    if len(segments) == 1:
        add_phrase_cues(cues, prefix, segments[0][0], role, source, segments[0][1], event_id, room_id, action)
        return
    segment_number = 1
    for segment_text, segment_speaker_id, segment_kind in segments:
        phrases = split_spoken_phrases(segment_text)
        for phrase_index, phrase in enumerate(phrases, start=1):
            add_cue(
                cues,
                f"{prefix}_{segment_kind}_{segment_number}_part_{phrase_index}",
                phrase,
                role,
                source,
                segment_speaker_id,
                event_id,
                room_id,
                action,
            )
        segment_number += 1


def quote_aware_segments(text: str, quote_speaker_id: str) -> list[tuple[str, str, str]]:
    normalized = normalize_space(text)
    if not normalized:
        return []
    segments: list[tuple[str, str, str]] = []
    cursor = 0
    for match in QUOTE_RE.finditer(normalized):
        if match.start() > cursor:
            narration = normalized[cursor:match.start()].strip(" ,;:")
            if narration:
                segments.append((narration, "narrator", "narration"))
        quote = next((group for group in match.groups() if group is not None), "").strip(" ,;:")
        if quote:
            segments.append((quote, attributed_quote_speaker(normalized[:match.start()], quote_speaker_id), "quote"))
        cursor = match.end()
    if cursor < len(normalized):
        narration = normalized[cursor:].strip(" ,;:")
        if narration:
            segments.append((narration, "narrator", "narration"))
    return segments or [(normalized, "narrator", "narration")]


def attributed_quote_speaker(before_quote: str, fallback_speaker_id: str) -> str:
    context = before_quote[-320:].lower()
    if "torah writes" in context and "and says" in context:
        return "torah"
    patterns = [
        ("dr_samira_iyad", ["iyad", "samira"]),
        ("dr_lenora_saye", ["saye", "lenora"]),
        ("lt_mara_owen", ["owen", "mara"]),
        ("agent_caleb_ross", ["ross", "caleb"]),
        ("brooks", ["brooks"]),
        ("torah", ["torah"]),
    ]
    speech_markers = [" says", " said", " voice", " comms", " radio", " reports", " calls", " keys", " over comms", " through the"]
    best: tuple[int, str] | None = None
    for speaker_id, names in patterns:
        for name in names:
            name_index = context.rfind(name)
            if name_index == -1:
                continue
            after_name = context[name_index:]
            if any(marker in after_name for marker in speech_markers) or after_name.strip().endswith(f"{name}:"):
                if best is None or name_index > best[0]:
                    best = (name_index, speaker_id)
    if best is not None:
        return best[1]
    if fallback_speaker_id != "narrator":
        return fallback_speaker_id
    return "narrator"


def room_cues(rooms: dict[str, Any]) -> list[Cue]:
    cues: list[Cue] = []
    for room in rooms.get("rooms", []):
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("id", ""))
        if not room_id:
            continue
        if str(room.get("type", "")) == "mission":
            add_cue(cues, f"{room_id}_sitrep", "SITREP:", "room_header", f"rooms.{room_id}", speaker_id="narrator", room_id=room_id)
            detection = normalize_space(room.get("detection_report", ""))
            if detection:
                add_quote_aware_phrase_cues(cues, f"{room_id}_detection", f"DETECTION: {detection}", "room_detection", f"rooms.{room_id}.detection_report", "narrator", room_id=room_id)
            current = normalize_space(room.get("current_situation", ""))
            if current:
                add_quote_aware_phrase_cues(cues, f"{room_id}_current", f"CURRENT: {current}", "room_current", f"rooms.{room_id}.current_situation", "narrator", room_id=room_id)
        for key, role in (
            ("first_visit_description", "room_first_visit"),
            ("return_description", "room_return"),
        ):
            value = normalize_space(room.get(key, ""))
            if value:
                add_quote_aware_phrase_cues(cues, f"{room_id}_{key}", value, role, f"rooms.{room_id}.{key}", "narrator", room_id=room_id)
    return cues


def event_cues(events: dict[str, Any]) -> list[Cue]:
    cues: list[Cue] = []
    for room_id, event_id, event, is_special in event_records(events):
        if not event_id:
            continue
        speaker_id = voice_speaker_id_for_event_line(event)
        event_source = f"{'special_events' if is_special else 'room_events.%s' % room_id}.{event_id}"
        for line_index, line_key in enumerate(("line_1", "line_2"), start=1):
            value = normalize_space(event.get(line_key, ""))
            if value:
                add_quote_aware_phrase_cues(cues, f"{event_id}_line_{line_index}", value, "event_line", f"{event_source}.{line_key}", speaker_id_for(event.get("speaker", "narrator")), event_id=event_id, room_id=room_id)
        for button_index, button in enumerate(display_buttons(event)):
            label = normalize_space(button.get("label", ""))
            if not label:
                continue
            add_cue(cues, f"{event_id}_choice_{button_index + 1}", choice_text(button_index, label), "choice", f"{event_source}.buttons[{button_index}].label", event_id=event_id, room_id=room_id, action=str(button.get("action", "")))
        plan_lines = operation_plan_lines(event)
        for plan_line_index, plan_line in enumerate(plan_lines):
            if plan_line_index == 0:
                add_cue(cues, f"{event_id}_proposals_header", plan_line, "operation_plan_header", f"{event_source}.operation_plans.header", event_id=event_id, room_id=room_id)
            else:
                add_quote_aware_phrase_cues(cues, f"{event_id}_proposal_{plan_line_index}", plan_line, "operation_plan", f"{event_source}.operation_plans[{plan_line_index - 1}]", speaker_id_for(event.get("speaker", "narrator")), event_id=event_id, room_id=room_id)
        for action, result in action_results(event):
            lines = result.get("lines", [])
            if not isinstance(lines, list):
                continue
            for result_index, result_line in enumerate(lines, start=1):
                value = normalize_space(result_line)
                if value:
                    safe_action = slug(action)
                    result_speaker = voice_speaker_id_for_result(result)
                    quote_speaker = speaker_id_for(result.get("speaker", result_speaker))
                    add_quote_aware_phrase_cues(cues, f"{event_id}_{safe_action}_result_{result_index}", value, "result_line", f"{event_source}.action_results.{action}.lines[{result_index - 1}]", quote_speaker, event_id=event_id, room_id=room_id, action=action)
        plans = event.get("operation_plans", [])
        if isinstance(plans, list):
            for plan_index, plan in enumerate(plans):
                if not isinstance(plan, dict):
                    continue
                action = str(plan.get("action", "")).strip()
                outcomes = plan.get("outcomes", {})
                if not action or not isinstance(outcomes, dict):
                    continue
                for band, outcome in outcomes.items():
                    if not isinstance(outcome, dict):
                        continue
                    lines = outcome.get("lines", [])
                    if not isinstance(lines, list):
                        continue
                    safe_action = slug(action)
                    safe_band = slug(str(band))
                    result_speaker = voice_speaker_id_for_result(outcome)
                    quote_speaker = speaker_id_for(outcome.get("speaker", result_speaker))
                    for result_index, result_line in enumerate(lines, start=1):
                        value = normalize_space(result_line)
                        if value:
                            add_quote_aware_phrase_cues(
                                cues,
                                f"{event_id}_{safe_action}_{safe_band}_result_{result_index}",
                                value,
                                "operation_result_line",
                                f"{event_source}.operation_plans[{plan_index}].outcomes.{band}.lines[{result_index - 1}]",
                                quote_speaker,
                                event_id=event_id,
                                room_id=room_id,
                                action=action,
                            )
    return cues


def standardization_findings(rooms: dict[str, Any], events: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    def check_generated_phrases(location: str, text: str, role: str) -> None:
        phrases = split_spoken_phrases(text)
        for index, phrase in enumerate(phrases, start=1):
            word_count = len(phrase.split())
            if word_count > MAX_SPOKEN_WORDS + MIN_HARD_CHUNK_WORDS:
                add(
                    f"{location}.phrase_{index}",
                    "high",
                    f"{role} phrase exceeds generated clip limit ({word_count} words)",
                    "Adjust the splitter or source punctuation before final clip generation.",
                )
            if not has_terminal_punctuation(phrase):
                add(
                    f"{location}.phrase_{index}",
                    "low",
                    "generated phrase lacks terminal punctuation",
                    "End generated spoken phrases with punctuation.",
                )

    for room in rooms.get("rooms", []):
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("id", "<missing>"))
        for key in ("detection_report", "current_situation", "first_visit_description", "return_description"):
            text = normalize_space(room.get(key, ""))
            if not text:
                continue
            check_generated_phrases(f"rooms.{room_id}.{key}", text, "room narration")

    for room_id, event_id, event, is_special in event_records(events):
        event_source = f"{'special_events' if is_special else 'room_events.%s' % room_id}.{event_id or '<missing>'}"
        speaker_id = speaker_id_for(event.get("speaker", ""))
        if speaker_id not in SPEAKER_PROFILES:
            add(f"{event_source}.speaker", "high", f"uncatalogued speaker '{event.get('speaker', '')}'", "Add a speaker profile before final clip generation.")
        for line_key in ("line_1", "line_2"):
            text = normalize_space(event.get(line_key, ""))
            if not text:
                add(f"{event_source}.{line_key}", "high", "missing TTS line", "Every voiced event should have line_1 and line_2, even if one is short.")
                continue
            check_generated_phrases(f"{event_source}.{line_key}", text, "event prompt")
            if not has_terminal_punctuation(text):
                add(f"{event_source}.{line_key}", "low", "missing terminal punctuation", "End spoken prompt lines with punctuation.")

        buttons = display_buttons(event)
        if not buttons:
            add(event_source, "high", "no spoken choices", "Add at least one button with label, action, and voice_aliases.")
        seen_labels: dict[str, int] = {}
        seen_actions: dict[str, int] = {}
        for index, button in enumerate(buttons):
            location = f"{event_source}.buttons[{index}]"
            label = normalize_space(button.get("label", ""))
            action = str(button.get("action", "")).strip()
            aliases = button.get("voice_aliases", [])
            if not label:
                add(location, "high", "missing button label", "Button labels are the spoken choice text source.")
                continue
            label_key = label.lower().rstrip(".")
            if label_key in seen_labels:
                add(location, "medium", f"duplicate visible label with button {seen_labels[label_key] + 1}", "Use distinct command labels before TTS so choice audio is not ambiguous.")
            else:
                seen_labels[label_key] = index
            if action:
                if action in seen_actions:
                    add(location, "low", f"duplicate action with button {seen_actions[action] + 1}", "Duplicate actions are allowed only when the choices are flavor-equivalent.")
                else:
                    seen_actions[action] = index
            if len(label.split()) > MAX_BUTTON_WORDS:
                add(location, "medium", f"long button label ({len(label.split())} words)", "Move nuance into narration; keep spoken choices short.")
            if not isinstance(aliases, list) or not aliases:
                add(location, "high", "missing voice aliases", "Add 2-5 short aliases before recording.")

    return findings


def uniquify_duplicate_actions(event: dict[str, Any]) -> bool:
    buttons = event.get("buttons", [])
    if not isinstance(buttons, list) or not buttons:
        return False

    action_counts: dict[str, int] = {}
    for button in buttons:
        if isinstance(button, dict):
            action = str(button.get("action", "")).strip()
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1

    duplicate_actions = {action for action, count in action_counts.items() if count > 1}
    if not duplicate_actions:
        return False

    changed = False
    action_rewrites: dict[str, list[str]] = {}
    used_actions = {str(button.get("action", "")).strip() for button in buttons if isinstance(button, dict)}
    for button in buttons:
        if not isinstance(button, dict):
            continue
        action = str(button.get("action", "")).strip()
        if action not in duplicate_actions:
            continue
        label_slug = slug(str(button.get("label", ""))).replace("_", "-")
        if not label_slug:
            label_slug = "choice"
        candidate = f"{action}:{label_slug}"
        suffix = 2
        while candidate in used_actions:
            candidate = f"{action}:{label_slug}-{suffix}"
            suffix += 1
        button["action"] = candidate
        used_actions.add(candidate)
        action_rewrites.setdefault(action, []).append(candidate)
        changed = True

    plans = event.get("operation_plans", [])
    if isinstance(plans, list):
        rewrite_offsets: dict[str, int] = {}
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            action = str(plan.get("action", "")).strip()
            replacements = action_rewrites.get(action, [])
            if not replacements:
                continue
            offset = rewrite_offsets.get(action, 0)
            if offset < len(replacements):
                plan["action"] = replacements[offset]
                rewrite_offsets[action] = offset + 1
                changed = True
    elif isinstance(plans, dict):
        for action, replacements in action_rewrites.items():
            plan = plans.pop(action, None)
            if not isinstance(plan, dict) or not replacements:
                continue
            plans[replacements[0]] = plan
            plans[replacements[0]]["action"] = replacements[0]
            changed = True

    return changed


def apply_safe_standardization(events: dict[str, Any]) -> bool:
    changed = False
    for _room_id, _event_id, event, _is_special in event_records(events):
        changed = uniquify_duplicate_actions(event) or changed
    return changed


def build_script(rooms: dict[str, Any], events: dict[str, Any]) -> dict[str, Any]:
    cues = room_cues(rooms) + event_cues(events)
    canonical: dict[str, dict[str, Any]] = {}
    active_speaker_ids = sorted({cue.speaker_id for cue in cues} | {"narrator"})
    speaker_ids = sorted(set(SPEAKER_PROFILES) | set(active_speaker_ids))
    for cue in cues:
        record = canonical.setdefault(cue.generation_key, {
            "generation_key": cue.generation_key,
            "text_key": cue.text_key,
            "text": cue.text,
            "speaker_id": cue.speaker_id,
            "uses": [],
        })
        record["uses"].append(cue.clip_id)

    duplicate_savings = len(cues) - len(canonical)
    return {
        "schema_version": 1,
        "source_files": [str(ROOMS_PATH.relative_to(ROOT)), str(EVENTS_PATH.relative_to(ROOT))],
        "summary": {
            "cue_count": len(cues),
            "unique_text_count": len({cue.text_key for cue in cues}),
            "unique_generation_count": len(canonical),
            "deduped_clip_savings": duplicate_savings,
            "max_spoken_words_per_phrase": MAX_SPOKEN_WORDS,
            "speaker_count": len(speaker_ids),
            "active_speaker_count": len(active_speaker_ids),
        },
        "speaker_profiles": [speaker_profile_for(speaker_id) for speaker_id in speaker_ids],
        "clips": [
            {
                "id": cue.clip_id,
                "text": cue.text,
                "text_key": cue.text_key,
                "generation_key": cue.generation_key,
                "role": cue.role,
                "speaker_id": cue.speaker_id,
                "voice_source": "direct_quote" if cue.speaker_id not in {"narrator", "sitrep", "operations", "evidence_control", "medical", "public_affairs"} else "channel_or_narration",
                "source": cue.source,
                "room_id": cue.room_id,
                "event_id": cue.event_id,
                "action": cue.action,
            }
            for cue in cues
        ],
        "canonical_texts": sorted(canonical.values(), key=lambda item: (str(item["speaker_id"]), str(item["text"]).lower())),
    }


def build_report(script: dict[str, Any], findings: list[dict[str, str]]) -> str:
    summary = script.get("summary", {})
    speaker_profiles = script.get("speaker_profiles", [])
    lines = [
        "# TTS Standardization Report",
        "",
        f"- Cues: {summary.get('cue_count', 0)}",
        f"- Unique spoken texts: {summary.get('unique_text_count', 0)}",
        f"- Unique speaker/text clips: {summary.get('unique_generation_count', summary.get('unique_text_count', 0))}",
        f"- Speaker profiles: {summary.get('speaker_count', 0)}",
        f"- Deduped clip savings: {summary.get('deduped_clip_savings', 0)}",
        f"- Max phrase length: {summary.get('max_spoken_words_per_phrase', MAX_SPOKEN_WORDS)} words",
        "",
        "## Speaker Profiles",
        "",
    ]
    for profile in speaker_profiles:
        lines.append("- `{id}`: {display_name}; voice `{voice}`; pitch {pitch:.3f}; speed {speed:.2f}. {delivery}".format(**profile))
    quote_clips = [
        clip for clip in script.get("clips", [])
        if isinstance(clip, dict) and "_quote_" in str(clip.get("id", ""))
    ]
    lines.extend([
        "",
        "## Direct Quote Cues",
        "",
        f"- Quote cue count: {len(quote_clips)}",
    ])
    by_speaker: dict[str, int] = {}
    for clip in quote_clips:
        speaker_id = str(clip.get("speaker_id", "narrator"))
        by_speaker[speaker_id] = by_speaker.get(speaker_id, 0) + 1
    for speaker_id, count in sorted(by_speaker.items()):
        lines.append(f"- `{speaker_id}`: {count}")
    lines.extend([
        "",
        "## Findings",
        "",
    ])
    if not findings:
        lines.append("No standardization findings.")
    else:
        for finding in findings:
            lines.append("- **{severity}** `{location}`: {issue} Recommendation: {recommendation}".format(**finding))
    lines.extend([
        "",
        "## Generation Notes",
        "",
        "- Generate one audio asset per `canonical_texts[].generation_key`. This preserves distinct voices when different speakers say the same text.",
        "- Map every `clips[].id` that uses the same `generation_key` to the same generated audio file in `audio/tts_manifest.json`.",
        "- Use `speaker_profiles[].call` or `audio/tts_speaker_profiles.json` to select provider, model, voice, pitch, speed, and instructions for each speaker.",
        "- For OpenAI Speech API generation, pass `call.model`, `call.voice`, `call.pitch`, `call.speed`, clip text, and `call.instructions`.",
        "- Character voices are reserved for explicit direct quotes or records marked `direct_quote`/`spoken_by_speaker`; related narration stays on narrator or institutional channel voices.",
        "- Findings evaluate generated phrase chunks, not raw source paragraph length.",
        "- Runtime event clips still use IDs such as `event_id_line_1` and `event_id_choice_1`; result lines can be matched through `text_key` fallback.",
        "- This pass does not rewrite room/event prose. Treat findings as the cleanup queue before paid TTS.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script-out", type=Path, default=SCRIPT_PATH)
    parser.add_argument("--report-out", type=Path, default=REPORT_PATH)
    parser.add_argument("--profiles-out", type=Path, default=SPEAKER_PROFILE_PATH)
    parser.add_argument("--check", action="store_true", help="Exit non-zero if blocker findings remain.")
    parser.add_argument("--fail-on", choices=["high", "medium", "low"], default="high", help="Lowest finding severity that fails --check.")
    parser.add_argument("--apply-safe", action="store_true", help="Apply deterministic event cleanup before writing the TTS script.")
    args = parser.parse_args()

    rooms = load_json(ROOMS_PATH)
    events = load_json(EVENTS_PATH)
    if args.apply_safe and apply_safe_standardization(events):
        write_json(EVENTS_PATH, events)
        events = load_json(EVENTS_PATH)
    script = build_script(rooms, events)
    findings = standardization_findings(rooms, events)
    script["findings"] = findings

    write_json(args.script_out, script)
    write_json(args.profiles_out, {
        "schema_version": 1,
        "source_script": str(args.script_out.relative_to(ROOT)),
        "speaker_profiles": script["speaker_profiles"],
    })
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(build_report(script, findings), encoding="utf-8")

    print(f"TTS_STANDARDIZER wrote {args.script_out.relative_to(ROOT)}")
    print(f"TTS_STANDARDIZER wrote {args.profiles_out.relative_to(ROOT)}")
    print(f"TTS_STANDARDIZER wrote {args.report_out.relative_to(ROOT)}")
    print("TTS_STANDARDIZER cues={cue_count} unique_texts={unique_text_count} unique_generation={unique_generation_count} speakers={speaker_count} findings={findings}".format(
        cue_count=script["summary"]["cue_count"],
        unique_text_count=script["summary"]["unique_text_count"],
        unique_generation_count=script["summary"]["unique_generation_count"],
        speaker_count=script["summary"]["speaker_count"],
        findings=len(findings),
    ))
    severity_rank = {"low": 1, "medium": 2, "high": 3}
    fail_threshold = severity_rank[args.fail_on]
    blocking_findings = [
        finding for finding in findings
        if severity_rank.get(str(finding.get("severity", "low")), 1) >= fail_threshold
    ]
    if args.check and blocking_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
