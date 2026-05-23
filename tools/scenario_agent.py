#!/usr/bin/env python3
"""Generate, validate, apply, and remember scenario patches."""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / ".agent-memory"
GENERATED_DIR = ROOT / "generated"
CORPUS_SEEDS_PATH = GENERATED_DIR / "corpus" / "fleshpunk_seeds.json"
CORPUS_FRAGMENTS_PATH = GENERATED_DIR / "corpus" / "nightmare_voyage_fragments.json"
CORPUS_INDEX_PATH = GENERATED_DIR / "corpus" / "nightmare_voyage_corpus_index.json"
REVELATION_CORPUS_CHUNKS_PATH = GENERATED_DIR / "corpus" / "index" / "chunks.jsonl"

LEGACY_EVENTS_PATH = ROOT / "events.json"
LEGACY_ROOMS_PATH = ROOT / "room_dialogue.json"
LEGACY_DECKS_PATH = ROOT / "encounter_decks.json"
POST_UPDATE_EVENTS_PATH = ROOT / "events_post_update.json"
POST_UPDATE_ROOMS_PATH = ROOT / "rooms_post_update.json"
POST_UPDATE_DECKS_PATH = ROOT / "encounter_decks_post_update.json"
EVENTS_PATH = POST_UPDATE_EVENTS_PATH if POST_UPDATE_EVENTS_PATH.exists() else LEGACY_EVENTS_PATH
ROOMS_PATH = POST_UPDATE_ROOMS_PATH if POST_UPDATE_ROOMS_PATH.exists() else LEGACY_ROOMS_PATH
DECKS_PATH = POST_UPDATE_DECKS_PATH if POST_UPDATE_DECKS_PATH.exists() else LEGACY_DECKS_PATH
ENEMIES_PATH = ROOT / "enemies.json"
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"
CATEGORIES_PATH = MEMORY_DIR / "event_categories.json"
VIBE_GUIDE_PATH = MEMORY_DIR / "vibe_guide.md"
LORE_GUIDE_PATH = MEMORY_DIR / "lore_guide.md"
SETTING_BACKBONE_PATH = MEMORY_DIR / "setting_backbone.md"
STORY_ROOM_CONTRACT_PATH = MEMORY_DIR / "story_room_contract.md"
ENDING_MAZE_ARCHITECTURE_PATH = MEMORY_DIR / "ending_maze_architecture.md"
HYMN_CORPUS_VOICE_PATH = MEMORY_DIR / "hymn_corpus_voice.md"
CONTENT_AUTHORSHIP_WORKFLOW_PATH = MEMORY_DIR / "content_authorship_workflow.md"
ACCESSIBILITY_GUIDE_PATH = MEMORY_DIR / "accessibility_guide.md"
REVELATION_FOUNDATIONAL_PATH = MEMORY_DIR / "revelation_foundational_systems.md"
REVELATION_STYLE_PATH = MEMORY_DIR / "revelation_style.md"
REVELATION_CORPUS_STRATEGY_PATH = MEMORY_DIR / "revelation_corpus_strategy.md"
REVELATION_CORPUS_RETRIEVAL_CONTRACT_PATH = MEMORY_DIR / "revelation_corpus_retrieval_contract.md"
REVELATION_INTERLUDE_LAYER_PATH = MEMORY_DIR / "revelation_interlude_glue_layer.md"
REVELATION_STATE_VOCABULARY_PATH = MEMORY_DIR / "revelation_state_vocabulary.md"
REVELATION_CONTENT_SCHEMAS_PATH = MEMORY_DIR / "revelation_content_schemas.md"
REVELATION_PROGRESSION_RULES_PATH = MEMORY_DIR / "revelation_progression_rules.md"
NIGHTMARE_BRIEF_PATH = MEMORY_DIR / "nightmare_voyage_brief.md"
NIGHTMARE_ROOM_STRUCTURE_PATH = MEMORY_DIR / "nightmare_voyage_room_structure.md"
CORPUS_ROOM_GENERATION_PATH = MEMORY_DIR / "corpus_room_generation.md"
CRITIQUE_MEMORY_PATH = MEMORY_DIR / "critic_guidance.jsonl"
BALANCE_MEMORY_PATH = MEMORY_DIR / "balance_guidance.jsonl"
FUN_MEMORY_PATH = MEMORY_DIR / "fun_guidance.jsonl"
LORE_MEMORY_PATH = MEMORY_DIR / "lore_guidance.jsonl"
LORE_BRAINSTORM_MEMORY_PATH = MEMORY_DIR / "lore_brainstorm_guidance.jsonl"
STORY_ARCHITECTURE_MEMORY_PATH = MEMORY_DIR / "story_architecture_guidance.jsonl"
ACCESSIBILITY_MEMORY_PATH = MEMORY_DIR / "accessibility_guidance.jsonl"

DEFAULT_MODEL = os.environ.get("SCENARIO_AGENT_MODEL", "gpt-5")
TRADEOFF_EXEMPT_EVENT_TYPES = {"transition", "interlude"}
NIGHTMARE_STORY_ENGINE_CONTENT_TRACK = "nightmare_voyage_packets_v1"
REVELATION_STORY_ENGINE_CONTENT_TRACK = "revelation_packets_v1"
STORY_ENGINE_CONTENT_TRACK = NIGHTMARE_STORY_ENGINE_CONTENT_TRACK
NARROW_ROOM_ROLES = {
    "ambush",
    "aftermath_report",
    "captain_log",
    "character_encounter",
    "compartment_failure",
    "detection_report",
    "enemy_encounter",
    "interception",
    "mutation_offer",
    "officer_briefing",
    "recovery_operation",
    "quiet_passage",
    "recovery_beat",
    "rest_beat",
    "simple_passage",
    "shipboard_dispute",
    "signal_anomaly",
    "symbiote_offer",
}


def commandable_button_count(event: dict[str, Any]) -> int:
    buttons = event.get("buttons", [])
    count = sum(1 for button in buttons if isinstance(button, dict)) if isinstance(buttons, list) else 0
    if str(event.get("type", "")) == "symbiote":
        symbiote_choices = event.get("symbiote_choices", [])
        explicit_choice_count = 0
        if isinstance(symbiote_choices, list):
            explicit_choice_count = sum(1 for choice in symbiote_choices if str(choice).strip())
            count += explicit_choice_count
        if explicit_choice_count == 0 and event.get("symbiote_choice_count") is not None:
            count += max(int(event.get("symbiote_choice_count", 0)), 0)
    return count


def is_tradeoff_exempt_event(event: dict[str, Any]) -> bool:
    if str(event.get("type", "")) in TRADEOFF_EXEMPT_EVENT_TYPES:
        return True
    if str(event.get("ending_id", "")).strip():
        return True
    if bool(event.get("game_over_on_combat", False)):
        return True
    buttons = event.get("buttons", [])
    if isinstance(buttons, list) and buttons:
        actions = {str(button.get("action", "")) for button in buttons if isinstance(button, dict)}
        if actions == {"restart_run"}:
            return True
    return False


def is_narrow_room_role(room_record: dict[str, Any]) -> bool:
    room_role = str(room_record.get("room_role", "")).strip()
    if room_role in NARROW_ROOM_ROLES:
        return True
    tags = room_record.get("tags", [])
    if isinstance(tags, list) and any(str(tag) in NARROW_ROOM_ROLES for tag in tags):
        return True
    return False
ENVIRONMENT_GROUP_KEYS = {
    "encounter_family",
    "environment_id",
    "environment",
    "environment_family",
    "object_class",
    "operation_type",
}
INSTANCE_SITUATION_KEYS = {
    "instance_premise",
    "current_situation",
    "situation",
    "instance_role",
}
ENVIRONMENT_ECHO_KEYS = {
    "environment_echoes",
    "followup_vectors",
    "later_instance_echoes",
    "environment_memory_states",
    "memory_states",
}
CORPUS_INFLUENCE_KEYS = {
    "corpus_influences",
    "corpus_anchors",
    "source_anchors",
    "source_text_anchors",
}
ROOM_MEMORY_KEYS = {
    "black_hole_state_changes",
    "captain_policy_changes",
    "crew_state_changes",
    "room_state_changes",
    "room_memory_flags",
    "ship_state_changes",
    "environment_state_changes",
    "environment_memory_flags",
    "memory_key",
    "memory_changes",
    "officer_state_changes",
    "route_state_changes",
    "actor_state_changes",
    "faction_state_changes",
    "infrastructure_state_change",
    "beast_state_change",
    "character_state_change",
    "scientific_progress_changes",
}
ACTION_RESULT_KEYS = {
    "action_results",
    "outcomes",
    "result_lines_by_action",
    "room_result_lines",
    "button_results",
    "action_consequences",
}

EXISTING_ACTION_RE = re.compile(r'^\s*"([^"]+)":\s*$', re.MULTILINE)
VOICE_ALIAS_MAX_WORDS = 4
VOICE_ALIAS_MIN_WORDS = 1
VOICE_ALIAS_MAX_PER_BUTTON = 5
FORWARD_ACTIONS = {
    "proceed",
    "restart_run",
    "intercept",
    "avoid",
    "observe",
    "destroy",
    "dock",
    "recover",
    "quarantine",
    "jettison",
    "repair",
    "reroute",
    "seal",
    "vent",
    "ration",
    "wake_officer",
    "send_party",
    "recall_party",
    "brooks_handles",
    "clear_iyad",
    "clinic",
    "continue_analysis",
    "extend_eval",
    "full_disclosure",
    "hold_iyad",
    "report_word_gap",
    "return_ross",
    "support_owen",
    "torah_speaks",
    "watch_quietly",
}
VOICE_ALIAS_STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "back",
    "be",
    "away",
    "by",
    "for",
    "from",
    "go",
    "i",
    "in",
    "into",
    "it",
    "my",
    "near",
    "of",
    "on",
    "or",
    "out",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "this",
    "to",
    "up",
    "with",
}
VOICE_ALIAS_BLOCKLIST = {
    "confirm",
    "help",
    "inventory",
    "options",
    "pause",
    "repeat",
    "repeat choices",
    "continue",
    "resume",
    "status",
}
VOICE_ALIAS_ACTION_SEEDS = {
    "activate_symbiote": ["activate", "wake symbiote", "use symbiote", "trigger symbiote", "bond"],
    "browse_wares": ["approach", "merchant", "trade", "exchange", "barter"],
    "buy_mutation": ["buy", "purchase", "take mutation", "claim mutation", "mutation"],
    "combat": ["fight", "attack", "strike", "engage", "kill"],
    "cut_green_spine": ["cut", "green spine", "spine", "sever", "slice"],
    "drink_pool": ["drink", "sip", "pool", "clean pulse", "take a sip"],
    "leave_merchant": ["walk away", "refuse merchant", "decline merchant", "back off", "leave merchant"],
    "leave_symbiote": ["leave symbiote", "decline symbiote", "refuse symbiote", "no bond", "walk away"],
    "proceed": ["advance", "move on", "carry on", "go forward", "step through"],
    "retreat": ["retreat", "withdraw", "back away", "fall back", "pull back"],
    "study_pool": ["study", "inspect", "sample", "listen", "read"],
    "take_mutation": ["take mutation", "claim mutation", "choose mutation", "mutation", "buy mutation"],
    "take_symbiote": ["bond", "take symbiote", "claim symbiote", "choose symbiote", "accept symbiote"],
    "vent_red_split": ["vent", "cut vent", "cut a vent", "open vent", "vent the wall"],
}
VOICE_ALIAS_FAMILY_SEEDS = {
    "approach": ["approach", "merchant", "trade", "exchange", "barter"],
    "back": ["back away", "back off", "withdraw", "leave", "retreat"],
    "bond": ["bond", "take symbiote", "claim symbiote", "accept symbiote", "choose symbiote"],
    "buy": ["buy", "purchase", "take mutation", "claim mutation", "mutation"],
    "cut": ["cut", "slice", "sever", "open vent", "vent"],
    "drink": ["drink", "sip", "take a sip", "clean pulse", "breathe"],
    "leave": ["leave", "walk away", "withdraw", "back away", "retreat"],
    "mark": ["mark", "trace", "tag", "branch", "select branch"],
    "move": ["move", "continue", "advance", "go on", "step through"],
    "proceed": ["proceed", "advance", "move on", "carry on", "go forward"],
    "retreat": ["retreat", "withdraw", "back away", "fall back", "pull back"],
    "study": ["study", "inspect", "sample", "listen", "read"],
    "take": ["take", "claim", "choose", "accept"],
    "vent": ["vent", "cut vent", "cut a vent", "open vent", "breach"],
}
REVELATION_OFFICER_IDS = {
    "torah",
    "brooks",
    "lt_mara_owen",
    "dr_samira_iyad",
    "agent_caleb_ross",
    "specialist_mina_park",
    "dr_lenora_saye",
}
REVELATION_REQUIRED_INTERLUDE_FIELDS = (
    "interlude_type",
    "state_reads",
    "state_writes",
    "featured_characters",
    "visible_text",
    "choices",
    "outcomes",
    "followup_hooks",
    "corpus_anchors",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def active_content_track() -> str:
    try:
        return str(load_json(ROOMS_PATH).get("content_track", ""))
    except Exception:
        return ""


def is_revelation_project() -> bool:
    return active_content_track() == REVELATION_STORY_ENGINE_CONTENT_TRACK


def project_label() -> str:
    return "Revelation" if is_revelation_project() else "Nightmare Voyage"


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def room_ids() -> list[str]:
    return [str(room["id"]) for room in load_json(ROOMS_PATH).get("rooms", [])]


def mutation_ids() -> list[str]:
    return [str(item["id"]) for item in load_json(MUTATIONS_PATH).get("mutations", [])]


def symbiote_ids() -> list[str]:
    return [str(item["id"]) for item in load_json(SYMBIOTES_PATH).get("symbiotes", [])]


def enemy_ids() -> list[str]:
    return [str(item["id"]) for item in load_json(ENEMIES_PATH).get("enemies", [])]


def event_categories() -> list[dict[str, Any]]:
    payload = load_json(CATEGORIES_PATH) if CATEGORIES_PATH.exists() else {"categories": []}
    categories = payload.get("categories", [])
    if not isinstance(categories, list):
        return []
    return [category for category in categories if isinstance(category, dict)]


def event_category_ids() -> list[str]:
    return [str(category.get("id", "")) for category in event_categories() if category.get("id")]


def get_event_category(category_id: str) -> dict[str, Any]:
    for category in event_categories():
        if str(category.get("id", "")) == category_id:
            return category
    return {}


def existing_event_ids() -> set[str]:
    payload = load_json(EVENTS_PATH)
    ids: set[str] = set()
    for events in payload.get("room_events", {}).values():
        for event in events:
            if isinstance(event, dict):
                ids.add(str(event.get("id", "")))
    for event_id in payload.get("special_events", {}).keys():
        ids.add(str(event_id))
    return ids


def existing_actions() -> set[str]:
    source = read_text(RUN_MANAGER_PATH)
    action_source = source
    if "func _apply_action_effects" in source:
        action_source = source.split("func _apply_action_effects", 1)[1]
        if "func _with_director_lines" in action_source:
            action_source = action_source.split("func _with_director_lines", 1)[0]
        if "func _add_biomass" in action_source:
            action_source = action_source.split("func _add_biomass", 1)[0]
    actions = set(EXISTING_ACTION_RE.findall(action_source))
    actions.update({"proceed", "restart_run"})
    return actions.intersection(FORWARD_ACTIONS)


def base_action_id(action: str) -> str:
    text = str(action)
    if ":" in text:
        return text.split(":", 1)[0]
    return text


def slugify_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "seed"


def _source_seed_filters_are_active(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "source_seeds", "")
        or getattr(args, "source_seed", None)
        or getattr(args, "source_work", "")
        or getattr(args, "source_motif", "")
    )


def load_source_seed_context(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not _source_seed_filters_are_active(args):
        return []

    seed_path = Path(args.source_seeds) if getattr(args, "source_seeds", "") else CORPUS_SEEDS_PATH
    if not seed_path.is_absolute():
        seed_path = ROOT / seed_path
    payload = load_json(seed_path)
    seeds = payload.get("seeds", [])
    if not isinstance(seeds, list):
        raise ValueError(f"{seed_path.name} must contain a seeds array")

    requested_ids = set(getattr(args, "source_seed", None) or [])
    source_work = str(getattr(args, "source_work", "") or "")
    source_motif = str(getattr(args, "source_motif", "") or "")
    target_room = str(getattr(args, "room", "") or "")
    selected: list[dict[str, Any]] = []
    for seed in seeds:
        if not isinstance(seed, dict):
            continue
        if requested_ids and str(seed.get("id", "")) not in requested_ids:
            continue
        if source_work and str(seed.get("source_id", "")) != source_work:
            continue
        if source_motif and str(seed.get("motif_id", "")) != source_motif:
            continue
        if target_room:
            suggested_rooms = [str(room) for room in seed.get("suggested_rooms", []) if str(room)]
            if suggested_rooms and target_room not in suggested_rooms:
                continue
        selected.append(_compact_source_seed(seed))

    limit = int(getattr(args, "source_seed_count", 3) or 3)
    return selected[:max(limit, 1)]


def _compact_source_seed(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(seed.get("id", "")),
        "source_id": str(seed.get("source_id", "")),
        "source_title": str(seed.get("source_title", "")),
        "source_author": str(seed.get("source_author", "")),
        "motif_id": str(seed.get("motif_id", "")),
        "motif_group": str(seed.get("motif_group", "")),
        "source_signal": seed.get("source_signal", {}),
        "fleshpunk_seed": str(seed.get("fleshpunk_seed", "")),
        "mechanic_direction": str(seed.get("mechanic_direction", "")),
        "suggested_rooms": seed.get("suggested_rooms", []),
        "suggested_existing_actions": seed.get("suggested_existing_actions", []),
        "generation_guardrails": seed.get("generation_guardrails", []),
    }


def _compact_corpus_fragment(fragment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(fragment.get("id", "")),
        "source_id": str(fragment.get("source_id", "")),
        "source_title": str(fragment.get("source_title", "")),
        "source_author": str(fragment.get("source_author", "")),
        "line_start": int(fragment.get("line_start", 0) or 0),
        "line_end": int(fragment.get("line_end", 0) or 0),
        "source_excerpt": str(fragment.get("source_excerpt", "")),
        "source_circumstance": str(fragment.get("source_circumstance", "")),
        "nightmare_room_seed": str(fragment.get("nightmare_room_seed", "")),
        "escalation_thread": fragment.get("escalation_thread", []),
        "ship_state_hooks": fragment.get("ship_state_hooks", []),
        "suggested_actions": fragment.get("suggested_actions", []),
        "generation_rules": fragment.get("generation_rules", []),
    }


def load_corpus_fragment_context(args: argparse.Namespace, default_limit: int = 12) -> list[dict[str, Any]]:
    fragment_path = Path(getattr(args, "corpus_fragments", "") or CORPUS_FRAGMENTS_PATH)
    if not fragment_path.is_absolute():
        fragment_path = ROOT / fragment_path
    if not fragment_path.exists():
        return []
    payload = load_json(fragment_path)
    fragments = payload.get("fragments", [])
    if not isinstance(fragments, list):
        return []

    requested_ids = set(getattr(args, "corpus_fragment", None) or [])
    source_work = str(getattr(args, "source_work", "") or "")
    selected: list[dict[str, Any]] = []
    for fragment in fragments:
        if not isinstance(fragment, dict):
            continue
        if requested_ids and str(fragment.get("id", "")) not in requested_ids:
            continue
        if source_work and str(fragment.get("source_id", "")) != source_work:
            continue
        selected.append(_compact_corpus_fragment(fragment))

    limit = int(getattr(args, "corpus_fragment_count", default_limit) or default_limit)
    return selected[:max(limit, 1)]


def _compact_corpus_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(artifact.get("id", "")),
        "need_id": str(artifact.get("need_id", "")),
        "role": str(artifact.get("role", "")),
        "source_id": str(artifact.get("source_id", "")),
        "source_title": str(artifact.get("source_title", "")),
        "source_author": str(artifact.get("source_author", "")),
        "line_start": int(artifact.get("line_start", 0) or 0),
        "line_end": int(artifact.get("line_end", 0) or 0),
        "source_excerpt": str(artifact.get("source_excerpt", "")),
        "room_need": str(artifact.get("room_need", "")),
        "nightmare_use": str(artifact.get("nightmare_use", "")),
        "matched_terms": artifact.get("matched_terms", []),
        "suggested_actions": artifact.get("suggested_actions", []),
        "state_hooks": artifact.get("state_hooks", []),
    }


def _compact_revelation_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    text = str(chunk.get("text", ""))
    return {
        "id": str(chunk.get("chunk_id", "")),
        "need_id": "revelation_corpus_chunk",
        "role": str(chunk.get("category", "")),
        "source_id": str(chunk.get("source_id", "")),
        "source_title": str(chunk.get("title", "")),
        "source_author": "",
        "line_start": 0,
        "line_end": 0,
        "source_excerpt": text[:1400],
        "room_need": "Recontextualize this source chunk into a Revelation mission premise, religious subtext, procedure, evidence detail, follow-up, or interlude.",
        "nightmare_use": "",
        "revelation_use": "Use the chunk as a concrete source mechanism. Preserve circumstance, procedure, contradiction, sequence, threshold, or classification; do not copy prose.",
        "matched_terms": chunk.get("keywords", []),
        "suggested_actions": [],
        "state_hooks": [],
    }


def _load_revelation_chunk_index(index_path: Path, args: argparse.Namespace, default_limit: int) -> dict[str, Any]:
    source_filters = set(getattr(args, "corpus_source", None) or [])
    role_filters = set(getattr(args, "corpus_role", None) or [])
    selected: list[dict[str, Any]] = []
    with index_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(chunk, dict):
                continue
            if source_filters and str(chunk.get("source_id", "")) not in source_filters:
                continue
            if role_filters and str(chunk.get("category", "")) not in role_filters:
                continue
            selected.append(_compact_revelation_chunk(chunk))

    requested_ids = set(getattr(args, "corpus_need", None) or [])
    if requested_ids:
        selected = [item for item in selected if item.get("id") in requested_ids or item.get("need_id") in requested_ids]

    limit = int(getattr(args, "corpus_index_count", default_limit) or default_limit)
    return {
        "index_path": str(index_path.relative_to(ROOT)) if index_path.is_relative_to(ROOT) else str(index_path),
        "composition_rules": [
            "For Revelation, combine at least one religious_subtext anchor with one procedural anchor.",
            "The religious anchor must appear as a specific playable object, phrase, threshold, classification, timing, or follow-up consequence.",
            "Use corpus_anchor_points with source_fingerprint, playable_transform, required_visible_details, and followup_payoff.",
        ],
        "artifacts": selected[:max(limit, 1)],
        "coverage_gaps": [
            {
                "need_id": "active_anomaly_case_corpus",
                "role": "case_structure",
                "coverage_status": "gap",
                "room_need": "Modern SCP-like case texture without CC BY-SA obligations.",
                "gap_note": "Fill with project-authored Institute procedure and public-domain/government source structure.",
            }
        ],
    }


def load_corpus_index_context(args: argparse.Namespace, default_limit: int = 12) -> dict[str, Any]:
    default_path = REVELATION_CORPUS_CHUNKS_PATH if is_revelation_project() and REVELATION_CORPUS_CHUNKS_PATH.exists() else CORPUS_INDEX_PATH
    index_path = Path(getattr(args, "corpus_index", "") or default_path)
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    if not index_path.exists():
        return {"artifacts": [], "coverage_gaps": []}
    if index_path.suffix == ".jsonl":
        return _load_revelation_chunk_index(index_path, args, default_limit)
    payload = load_json(index_path)
    artifacts = payload.get("artifacts", [])
    coverage_gaps = payload.get("coverage_gaps", [])
    if not isinstance(artifacts, list):
        artifacts = []
    if not isinstance(coverage_gaps, list):
        coverage_gaps = []

    need_filters = set(getattr(args, "corpus_need", None) or [])
    source_filters = set(getattr(args, "corpus_source", None) or [])
    role_filters = set(getattr(args, "corpus_role", None) or [])
    selected: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        if need_filters and str(artifact.get("need_id", "")) not in need_filters:
            continue
        if source_filters and str(artifact.get("source_id", "")) not in source_filters:
            continue
        if role_filters and str(artifact.get("role", "")) not in role_filters:
            continue
        selected.append(_compact_corpus_artifact(artifact))

    limit = int(getattr(args, "corpus_index_count", default_limit) or default_limit)
    compact_gaps = [
        {
            "need_id": str(gap.get("need_id", "")),
            "role": str(gap.get("role", "")),
            "coverage_status": str(gap.get("coverage_status", "")),
            "room_need": str(gap.get("room_need", "")),
            "gap_note": str(gap.get("gap_note", "")),
        }
        for gap in coverage_gaps[:12]
        if isinstance(gap, dict)
    ]
    return {
        "index_path": str(index_path.relative_to(ROOT)) if index_path.is_relative_to(ROOT) else str(index_path),
        "composition_rules": payload.get("composition_rules", []),
        "artifacts": selected[:max(limit, 1)],
        "coverage_gaps": compact_gaps,
    }


def enrich_patch_voice_aliases(patch: dict[str, Any]) -> dict[str, Any]:
    events = patch.get("events", [])
    if not isinstance(events, list):
        return patch
    for item in events:
        if not isinstance(item, dict):
            continue
        event = item.get("event")
        if not isinstance(event, dict):
            continue
        _enrich_event_voice_aliases(event, replace_existing=False)
    return patch


def enrich_events_payload_voice_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for events in room_events.values():
            if not isinstance(events, list):
                continue
            for event in events:
                if isinstance(event, dict):
                    _enrich_event_voice_aliases(event, replace_existing=True)
    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event in special_events.values():
            if isinstance(event, dict):
                _enrich_event_voice_aliases(event, replace_existing=True)
    return payload


def _enrich_event_voice_aliases(event: dict[str, Any], replace_existing: bool) -> None:
    buttons = event.get("buttons", [])
    if not isinstance(buttons, list) or not buttons:
        return
    event_text = " ".join([
        str(event.get("line_1", "")),
        str(event.get("line_2", "")),
    ]).strip()
    button_candidates: list[list[dict[str, Any]]] = []
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            button_candidates.append([])
            continue
        candidates = _voice_alias_candidates_for_button(button, event_text, index)
        button_candidates.append(candidates)
    resolved = _resolve_voice_alias_candidates(button_candidates)
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            continue
        if replace_existing:
            generated = resolved.get(index, [])
            if generated:
                button["voice_aliases"] = generated
        else:
            merged = _merge_voice_aliases(button.get("voice_aliases", []), resolved.get(index, []))
            if merged:
                button["voice_aliases"] = merged


def _resolve_voice_alias_candidates(button_candidates: list[list[dict[str, Any]]]) -> dict[int, list[str]]:
    winner_by_alias: dict[str, dict[str, Any]] = {}
    for candidates in button_candidates:
        for candidate in candidates:
            alias = str(candidate.get("alias", "")).strip()
            if not alias or alias in VOICE_ALIAS_BLOCKLIST:
                continue
            existing = winner_by_alias.get(alias)
            if existing is None or _voice_alias_is_better(candidate, existing):
                winner_by_alias[alias] = candidate

    resolved: dict[int, list[tuple[float, str]]] = {}
    for alias, candidate in winner_by_alias.items():
        index = int(candidate.get("index", -1))
        if index < 0:
            continue
        resolved.setdefault(index, []).append((float(candidate.get("score", 0.0)), alias))

    output: dict[int, list[str]] = {}
    for index, aliases in resolved.items():
        aliases.sort(key=lambda item: (-item[0], item[1]))
        output[index] = [alias for _, alias in aliases[:VOICE_ALIAS_MAX_PER_BUTTON]]
    return output


def _voice_alias_is_better(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    candidate_score = float(candidate.get("score", 0.0))
    existing_score = float(existing.get("score", 0.0))
    if candidate_score != existing_score:
        return candidate_score > existing_score
    candidate_words = int(candidate.get("word_count", 0))
    existing_words = int(existing.get("word_count", 0))
    if candidate_words != existing_words:
        return candidate_words < existing_words
    candidate_length = len(str(candidate.get("alias", "")))
    existing_length = len(str(existing.get("alias", "")))
    if candidate_length != existing_length:
        return candidate_length < existing_length
    return int(candidate.get("index", 0)) < int(existing.get("index", 0))


def _merge_voice_aliases(existing_aliases: Any, generated_aliases: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for alias in existing_aliases if isinstance(existing_aliases, list) else []:
        normalized = _normalize_voice_alias(str(alias))
        if _is_valid_voice_alias(normalized) and normalized not in seen:
            merged.append(normalized)
            seen.add(normalized)
    for alias in generated_aliases:
        normalized = _normalize_voice_alias(alias)
        if _is_valid_voice_alias(normalized) and normalized not in seen:
            merged.append(normalized)
            seen.add(normalized)
    return merged[:VOICE_ALIAS_MAX_PER_BUTTON]


def _voice_alias_candidates_for_button(button: dict[str, Any], event_text: str, index: int) -> list[dict[str, Any]]:
    label = str(button.get("label", ""))
    action = str(button.get("action", ""))
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_phrase(phrase: str, score: float, source: str) -> None:
        normalized = _normalize_voice_alias(phrase)
        if not _is_valid_voice_alias(normalized) or normalized in seen:
            return
        seen.add(normalized)
        candidates.append({
            "alias": normalized,
            "score": score,
            "source": source,
            "index": index,
            "word_count": len(normalized.split()),
        })

    for existing in button.get("voice_aliases", []):
        add_phrase(str(existing), 1.0, "existing")
    for phrase in _voice_alias_phrases_from_family(label, action):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 1.0), "family")
    for phrase in _voice_alias_phrases_from_action(action):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 0.98), "action")
    for phrase in _voice_alias_phrases_from_text(label):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 0.84), "label")
    for phrase in _voice_alias_phrases_from_text(event_text):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 0.66), "event_text")

    candidates.sort(key=lambda item: (-float(item.get("score", 0.0)), int(item.get("word_count", 0)), str(item.get("alias", ""))))
    return candidates


def _voice_alias_phrases_from_action(action: str) -> list[str]:
    phrases: list[str] = []
    base = str(action).split(":", 1)[0].replace("_", " ").strip()
    if base:
        phrases.append(base)
    if action in VOICE_ALIAS_ACTION_SEEDS:
        phrases.extend(VOICE_ALIAS_ACTION_SEEDS[action])
    if base in VOICE_ALIAS_ACTION_SEEDS:
        phrases.extend(VOICE_ALIAS_ACTION_SEEDS[base])
    if ":" in action:
        suffix = str(action.split(":", 1)[1]).replace("_", " ").strip()
        if suffix:
            phrases.extend([suffix, f"{base} {suffix}".strip()])
    return _dedupe_alias_phrases(phrases)


def _voice_alias_phrases_from_family(label: str, action: str) -> list[str]:
    phrases: list[str] = []
    for family_key in _voice_alias_family_keys(label, action):
        phrases.extend(VOICE_ALIAS_FAMILY_SEEDS.get(family_key, []))
    return _dedupe_alias_phrases(phrases)


def _voice_alias_family_keys(label: str, action: str) -> list[str]:
    keys: list[str] = []
    normalized_label = _normalize_voice_alias(label)
    normalized_action = _normalize_voice_alias(action).replace("_", " ")
    for phrase, key in (
        ("cut a vent", "cut"),
        ("cut vent", "cut"),
        ("vent the wall", "vent"),
        ("back away", "back"),
        ("back off", "back"),
        ("walk away", "leave"),
        ("leave", "leave"),
        ("approach", "approach"),
        ("trade", "approach"),
        ("exchange", "approach"),
        ("merchant", "approach"),
        ("drink", "drink"),
        ("sip", "drink"),
        ("study", "study"),
        ("inspect", "study"),
        ("sample", "study"),
        ("retreat", "retreat"),
        ("move", "move"),
        ("proceed", "proceed"),
        ("bond", "bond"),
        ("activate", "bond"),
        ("take mutation", "buy"),
        ("purchase", "buy"),
        ("claim mutation", "buy"),
        ("mark", "mark"),
    ):
        if phrase in normalized_label or phrase in normalized_action:
            if key not in keys:
                keys.append(key)

    raw_label_tokens = normalized_label.split()
    if raw_label_tokens:
        first = str(raw_label_tokens[0])
        if first in VOICE_ALIAS_FAMILY_SEEDS and first not in keys:
            keys.append(first)
    raw_action_tokens = normalized_action.split()
    if raw_action_tokens:
        first_action = str(raw_action_tokens[0])
        if first_action in VOICE_ALIAS_FAMILY_SEEDS and first_action not in keys:
            keys.append(first_action)
    if "vent" in normalized_action and "cut" not in keys:
        keys.insert(0, "cut")
    if "merchant" in normalized_action and "approach" not in keys:
        keys.append("approach")
    if "symbiote" in normalized_action and "bond" not in keys:
        keys.append("bond")
    return keys[:3]


def _voice_alias_phrases_from_text(text: str) -> list[str]:
    normalized = _normalize_voice_alias(text)
    if not normalized:
        return []
    phrases: list[str] = []
    for chunk in re.split(r"[.!?;:,/\\-]+", normalized):
        tokens = _voice_alias_tokens(chunk)
        if not tokens:
            continue
        if len(tokens) <= VOICE_ALIAS_MAX_WORDS:
            phrases.append(" ".join(tokens))
        for token in tokens:
            phrases.append(token)
        for size in range(2, min(VOICE_ALIAS_MAX_WORDS, len(tokens)) + 1):
            for start in range(0, len(tokens) - size + 1):
                window = tokens[start:start + size]
                phrases.append(" ".join(window))
    return _dedupe_alias_phrases(phrases)


def _voice_alias_score_for_phrase(phrase: str, base_score: float) -> float:
    tokens = _voice_alias_tokens(phrase)
    if not tokens:
        return 0.0
    score = base_score
    if len(tokens) == 1:
        score += 0.03
    elif len(tokens) == 2:
        score += 0.05
    elif len(tokens) == 3:
        score += 0.02
    else:
        score -= 0.04
    if len(" ".join(tokens)) > 24:
        score -= 0.03
    if any(token in {"merchant", "spine", "pulse", "symbiote", "mutation"} for token in tokens):
        score += 0.03
    return score


def _voice_alias_tokens(text: str) -> list[str]:
    normalized = _normalize_voice_alias(text)
    if not normalized:
        return []
    tokens = [token for token in normalized.split() if token and token not in VOICE_ALIAS_STOP_WORDS]
    compacted: list[str] = []
    for token in tokens:
        if len(token) < 3 and token not in {"cut", "sip", "buy"}:
            continue
        compacted.append(token)
    return compacted[:VOICE_ALIAS_MAX_WORDS]


def _normalize_voice_alias(text: str) -> str:
    normalized = str(text).lower().strip()
    normalized = normalized.replace("/", " ").replace("\\", " ")
    normalized = re.sub(r"[^a-z0-9\s']", " ", normalized)
    normalized = normalized.replace("'", "")
    normalized = " ".join(normalized.split())
    return normalized


def _is_valid_voice_alias(alias: str) -> bool:
    if not alias:
        return False
    if alias in VOICE_ALIAS_BLOCKLIST:
        return False
    if len(alias.split()) > VOICE_ALIAS_MAX_WORDS:
        return False
    if len(alias.split()) < VOICE_ALIAS_MIN_WORDS:
        return False
    if len(alias) > 28:
        return False
    return True


def _dedupe_alias_phrases(phrases: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        normalized = _normalize_voice_alias(phrase)
        if _is_valid_voice_alias(normalized) and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def load_vibe_guide() -> str:
    return read_text(VIBE_GUIDE_PATH)


def load_lore_guide() -> str:
    return read_text(LORE_GUIDE_PATH)


def load_setting_backbone() -> str:
    return read_text(SETTING_BACKBONE_PATH)


def load_story_room_contract() -> str:
    return read_text(STORY_ROOM_CONTRACT_PATH)


def load_ending_maze_architecture() -> str:
    return read_text(ENDING_MAZE_ARCHITECTURE_PATH)


def load_hymn_corpus_voice() -> str:
    return read_text(HYMN_CORPUS_VOICE_PATH)


def load_content_authorship_workflow() -> str:
    return read_text(CONTENT_AUTHORSHIP_WORKFLOW_PATH)


def load_accessibility_guide() -> str:
    return read_text(ACCESSIBILITY_GUIDE_PATH)


def load_nightmare_brief() -> str:
    return read_text(NIGHTMARE_BRIEF_PATH)


def load_nightmare_room_structure() -> str:
    return read_text(NIGHTMARE_ROOM_STRUCTURE_PATH)


def load_corpus_room_generation() -> str:
    return read_text(CORPUS_ROOM_GENERATION_PATH)


def load_revelation_core_guides() -> str:
    parts = [
        "# Revelation Foundational Systems\n" + read_text(REVELATION_FOUNDATIONAL_PATH),
        "# Revelation Style\n" + read_text(REVELATION_STYLE_PATH),
        "# Revelation Corpus Strategy\n" + read_text(REVELATION_CORPUS_STRATEGY_PATH),
        "# Revelation Corpus Retrieval Contract\n" + read_text(REVELATION_CORPUS_RETRIEVAL_CONTRACT_PATH),
        "# Revelation Interlude Layer\n" + read_text(REVELATION_INTERLUDE_LAYER_PATH),
        "# Revelation State Vocabulary\n" + read_text(REVELATION_STATE_VOCABULARY_PATH),
        "# Revelation Content Schemas\n" + read_text(REVELATION_CONTENT_SCHEMAS_PATH),
        "# Revelation Progression Rules\n" + read_text(REVELATION_PROGRESSION_RULES_PATH),
        "# Content Authorship Workflow\n" + load_content_authorship_workflow(),
    ]
    return "\n\n".join(part for part in parts if part.strip())


def load_recent_memory(limit: int = 12, include_core_guides: bool = True) -> str:
    parts = []
    if include_core_guides:
        if is_revelation_project():
            parts.append(load_revelation_core_guides())
        else:
            parts.extend(
                [
                    "# Foundational Brief\n" + load_nightmare_brief(),
                    "# Vibe Guide\n" + load_vibe_guide(),
                    "# Lore Guide\n" + load_lore_guide(),
                    "# Setting Backbone\n" + load_setting_backbone(),
                    "# Story Room Contract\n" + load_story_room_contract(),
                    "# Encounter Packet Structure\n" + load_nightmare_room_structure(),
                    "# Corpus-First Room Generation\n" + load_corpus_room_generation(),
                    "# Ending Maze Architecture\n" + load_ending_maze_architecture(),
                    "# Hymn Corpus Voice\n" + load_hymn_corpus_voice(),
                    "# Content Authorship Workflow\n" + load_content_authorship_workflow(),
                    "# Accessibility Guide\n" + load_accessibility_guide(),
                    "# Style Memory\n" + read_text(MEMORY_DIR / "fleshpunk_style.md"),
                    "# Inspiration Sources\n" + read_text(MEMORY_DIR / "inspiration_sources.md"),
                    "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
                ]
            )
    else:
        parts.extend(
            [
                "# Inspiration Sources\n" + read_text(MEMORY_DIR / "inspiration_sources.md"),
                "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
            ]
        )
    for name in ("accepted_scenarios.jsonl", "rejected_scenarios.jsonl"):
        path = MEMORY_DIR / name
        if not path.exists():
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Recent " + name + "\n" + "\n".join(recent))
    if CRITIQUE_MEMORY_PATH.exists():
        lines = [line for line in CRITIQUE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Critic Guidance\n" + "\n".join(recent))
    if BALANCE_MEMORY_PATH.exists():
        lines = [line for line in BALANCE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Balance Guidance\n" + "\n".join(recent))
    if FUN_MEMORY_PATH.exists():
        lines = [line for line in FUN_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Fun Guidance\n" + "\n".join(recent))
    if LORE_MEMORY_PATH.exists():
        lines = [line for line in LORE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Lore Guidance\n" + "\n".join(recent))
    if LORE_BRAINSTORM_MEMORY_PATH.exists():
        lines = [line for line in LORE_BRAINSTORM_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Lore Brainstorm Guidance\n" + "\n".join(recent))
    if STORY_ARCHITECTURE_MEMORY_PATH.exists():
        lines = [line for line in STORY_ARCHITECTURE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Story Architecture Guidance\n" + "\n".join(recent))
    if ACCESSIBILITY_MEMORY_PATH.exists():
        lines = [line for line in ACCESSIBILITY_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Accessibility Guidance\n" + "\n".join(recent))
    return "\n\n".join(parts)


def recent_jsonl_block(path: Path, title: str, limit: int = 6) -> str:
    if not path.exists():
        return ""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    recent = lines[-limit:]
    if not recent:
        return ""
    return "# " + title + "\n" + "\n".join(recent)


def load_lore_brainstorm_memory(limit: int = 6) -> str:
    parts = [
        "# Inspiration Sources\n" + read_text(MEMORY_DIR / "inspiration_sources.md"),
        "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
    ]
    for path, title in (
        (LORE_MEMORY_PATH, "Lore Guidance"),
        (LORE_BRAINSTORM_MEMORY_PATH, "Lore Brainstorm Guidance"),
        (STORY_ARCHITECTURE_MEMORY_PATH, "Story Architecture Guidance"),
        (FUN_MEMORY_PATH, "Fun Guidance"),
    ):
        block = recent_jsonl_block(path, title, limit=limit)
        if block:
            parts.append(block)
    return "\n\n".join(parts)


def game_context() -> dict[str, Any]:
    decks = load_json(DECKS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    room_summaries = []
    for room in rooms_payload.get("rooms", []):
        if not isinstance(room, dict):
            continue
        summary = {
            "id": str(room.get("id", "")),
            "name": str(room.get("name", "")),
            "type": str(room.get("type", "")),
            "encounter_family": str(room.get("encounter_family", "")),
            "operation_type": str(room.get("operation_type", "")),
            "description": str(room.get("description", "")),
            "current_situation": str(room.get("current_situation", "")),
        }
        if is_revelation_project():
            summary["religious_subtext"] = room.get("religious_subtext", {})
            summary["corpus_anchor_points"] = room.get("corpus_anchor_points", [])[:5]
            summary["character_state_stakes"] = room.get("character_state_stakes", {})
        room_summaries.append(summary)
    return {
        "project": project_label(),
        "content_track": active_content_track(),
        "rooms": room_ids(),
        "room_summaries": room_summaries,
        "existing_actions": sorted(existing_actions()),
        "existing_mutations": mutation_ids(),
        "existing_symbiotes": symbiote_ids(),
        "existing_enemies": enemy_ids(),
        "event_categories": event_categories(),
        "single_choice_room_gaps": room_tradeoff_findings(),
        "room_depth_findings": room_depth_findings(),
        "room_story_findings": room_story_findings(),
        "base_player_stats": decks.get("base_player_stats", {}),
        "resource_files": {
            "events": EVENTS_PATH.name,
            "rooms": ROOMS_PATH.name,
            "mutations": "mutations.json",
            "symbiotes": "symbiotes.json",
            "enemies": "enemies.json",
        },
    }


def lite_game_context() -> dict[str, Any]:
    """Small generation context for source-driven drafts that do not need full audits."""
    return {
        "project": project_label(),
        "content_track": active_content_track(),
        "rooms": room_ids(),
        "existing_actions": sorted(existing_actions()),
        "event_categories": event_categories(),
        "resource_files": {
            "events": EVENTS_PATH.name,
            "rooms": ROOMS_PATH.name,
            "mutations": "mutations.json",
            "symbiotes": "symbiotes.json",
            "enemies": "enemies.json",
        },
    }


def event_type_counts() -> dict[str, int]:
    payload = load_json(EVENTS_PATH)
    counts: dict[str, int] = {}
    for events in payload.get("room_events", {}).values():
        if not isinstance(events, list):
            continue
        for event in events:
            if isinstance(event, dict):
                event_type = str(event.get("type", "unknown"))
                counts[event_type] = counts.get(event_type, 0) + 1
    for event in payload.get("special_events", {}).values():
        if isinstance(event, dict):
            event_type = str(event.get("type", "unknown"))
            counts[event_type] = counts.get(event_type, 0) + 1
    return dict(sorted(counts.items()))


def room_event_counts() -> dict[str, int]:
    payload = load_json(EVENTS_PATH)
    counts: dict[str, int] = {}
    for room_id, events in payload.get("room_events", {}).items():
        counts[str(room_id)] = len(events) if isinstance(events, list) else 0
    return dict(sorted(counts.items()))


def room_tradeoff_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = []

    def add(location: str, severity: str, issue: str, recommendation: str, button_count: int, event_type: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
            "button_count": str(button_count),
            "event_type": event_type,
        })

    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", ""))
            if event_type in TRADEOFF_EXEMPT_EVENT_TYPES:
                continue
            button_count = commandable_button_count(event)
            if button_count < 2:
                event_id = str(event.get("id", "unknown"))
                add(
                    f"room_events.{room_id}.{event_id}",
                    "high",
                    f"single-choice room ({button_count} commandable button{'s' if button_count != 1 else ''})",
                    "Add a second legal choice with a distinct cost, delayed consequence, or alternative pressure axis. Transition events may stay exempt.",
                    button_count,
                    event_type or "unknown",
                )

    for finding in room_depth_findings():
        findings.append({
            "location": finding["location"],
            "severity": finding["severity"],
            "issue": finding["issue"],
            "recommendation": finding["recommendation"],
            "button_count": "n/a",
            "event_type": "room_depth",
        })
    for finding in room_story_findings():
        findings.append({
            "location": finding["location"],
            "severity": finding["severity"],
            "issue": finding["issue"],
            "recommendation": finding["recommendation"],
            "button_count": "n/a",
            "event_type": "room_story",
        })

    return findings


def _has_delayed_consequence(event: dict[str, Any]) -> bool:
    delayed_keys = {
        "delayed_consequence",
        "reaction",
        "reaction_tags",
        "on_repeat",
        "director_hook",
        "room_state_changes",
        "future_effect",
        "memory_key",
        "pressure_axis",
        "character_state_change",
        "beast_state_change",
        "infrastructure_state_change",
        "story_followups",
    }
    if any(key in event for key in delayed_keys):
        return True
    text = "%s %s" % (event.get("line_1", ""), event.get("line_2", ""))
    text_lower = text.lower()
    delayed_terms = {
        "later",
        "again",
        "return",
        "remembers",
        "remember",
        "learns",
        "learn",
        "claim",
        "debt",
        "mark",
        "scent",
        "tracks",
        "future",
        "next",
        "behind me",
    }
    return any(term in text_lower for term in delayed_terms)


def _has_interactable_actor(event: dict[str, Any]) -> bool:
    actor_keys = {
        "character_id",
        "beast_id",
        "animal_id",
        "infrastructure_actor",
        "organ_actor",
        "system_actor",
        "faction_id",
        "enemy_id",
        "symbiote_id",
        "mutation_id",
    }
    if any(str(event.get(key, "")).strip() for key in actor_keys):
        return True
    symbiote_choices = event.get("symbiote_choices", [])
    if isinstance(symbiote_choices, list) and any(str(choice).strip() for choice in symbiote_choices):
        return True
    if event.get("symbiote_choice_count") is not None:
        return True
    text = "%s %s" % (event.get("line_1", ""), event.get("line_2", ""))
    text_lower = text.lower()
    actor_terms = {
        "mouth",
        "mouths",
        "organ",
        "room",
        "beast",
        "animal",
        "parasite",
        "merchant",
        "chorus",
        "tool",
        "larder",
        "scale",
        "map",
        "airlock",
        "bearing",
        "canvas",
        "collar",
        "compartment",
        "engineer",
        "gauge",
        "lamp",
        "lens",
        "lifeboat",
        "lifeboats",
        "manifold",
        "marshal",
        "navigator",
        "observatory",
        "quartermaster",
        "registry",
        "shutter",
        "signal",
        "surgeon",
        "tube",
        "lock",
        "rings",
        "ribs",
        "tissue",
        "valve",
        "plate",
        "pressure plate",
        "seam",
        "wall",
        "body",
        "bodies",
        "symbiote",
        "symbiotes",
    }
    return any(term in text_lower for term in actor_terms)


def _has_only_immediate_stat_surface(event: dict[str, Any]) -> bool:
    immediate_keys = {
        "biomass",
        "biomass_cost",
        "damage",
        "break_damage",
        "heal",
        "shield",
        "mutation_id",
        "enemy_id",
    }
    if not any(key in event for key in immediate_keys):
        return False
    return not _has_delayed_consequence(event)


def _is_story_engine_track(rooms_payload: dict[str, Any]) -> bool:
    return str(rooms_payload.get("content_track", "")) in {
        NIGHTMARE_STORY_ENGINE_CONTENT_TRACK,
        REVELATION_STORY_ENGINE_CONTENT_TRACK,
    }


def _has_environment_group(room_record: dict[str, Any]) -> bool:
    return any(room_record.get(key) for key in ENVIRONMENT_GROUP_KEYS)


def _has_instance_situation(record: dict[str, Any]) -> bool:
    if any(record.get(key) for key in INSTANCE_SITUATION_KEYS):
        return True
    text = "%s %s" % (record.get("line_1", ""), record.get("line_2", ""))
    return bool(text.strip())


def _has_environment_echo_plan(room_record: dict[str, Any]) -> bool:
    return any(room_record.get(key) for key in ENVIRONMENT_ECHO_KEYS)


def _environment_id_for_room(room_id: str, room_record: dict[str, Any]) -> str:
    for key in ENVIRONMENT_GROUP_KEYS:
        value = str(room_record.get(key, "")).strip()
        if value:
            return value
    return room_id


def _corpus_influence_records(room_record: dict[str, Any]) -> list[dict[str, Any]]:
    for key in CORPUS_INFLUENCE_KEYS:
        if key not in room_record:
            continue
        records = room_record.get(key, [])
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
    return []


def _has_specific_corpus_influence(room_record: dict[str, Any]) -> bool:
    for record in _corpus_influence_records(room_record):
        has_source = bool(str(record.get("seed_id", "")).strip() or str(record.get("source_title", "")).strip())
        has_specific_moment = bool(
            str(record.get("source_moment", "")).strip()
            or str(record.get("writing_influence", "")).strip()
            or str(record.get("source_bit", "")).strip()
            or str(record.get("source_excerpt", "")).strip()
            or str(record.get("source_detail", "")).strip()
            or str(record.get("character_function", "")).strip()
        )
        has_application = bool(
            str(record.get("room_application", "")).strip()
            or str(record.get("room_reflection", "")).strip()
            or str(record.get("transform", "")).strip()
            or str(record.get("mechanic_reflection", "")).strip()
        )
        if has_source and has_specific_moment and has_application:
            return True
    return False


def _has_ending_vector(room_record: dict[str, Any]) -> bool:
    vectors = room_record.get("ending_vectors", [])
    return isinstance(vectors, list) and any(isinstance(vector, dict) and vector.get("id") for vector in vectors)


def _has_mutation_hooks(room_record: dict[str, Any]) -> bool:
    hooks = room_record.get("mutation_hooks", [])
    if isinstance(hooks, list) and any(isinstance(hook, dict) and hook.get("capability") for hook in hooks):
        return True
    adaptation_hooks = room_record.get("adaptation_hooks", [])
    equipment_hooks = room_record.get("equipment_hooks", [])
    procedure_hooks = room_record.get("procedure_hooks", [])
    return any(
        isinstance(hooks_value, list)
        and any(isinstance(hook, dict) and (hook.get("capability") or hook.get("equipment") or hook.get("procedure")) for hook in hooks_value)
        for hooks_value in (adaptation_hooks, equipment_hooks, procedure_hooks)
    )


def _has_room_memory_change(event: dict[str, Any]) -> bool:
    return any(event.get(key) for key in ROOM_MEMORY_KEYS)


def _has_action_specific_result(event: dict[str, Any]) -> bool:
    if any(event.get(key) for key in ACTION_RESULT_KEYS):
        return True
    buttons = event.get("buttons", [])
    if not isinstance(buttons, list):
        return False
    button_result_keys = {
        "result_lines",
        "outcome",
        "consequence",
        "room_state_changes",
        "memory_key",
    }
    return any(isinstance(button, dict) and any(button.get(key) for key in button_result_keys) for button in buttons)


def _followups_are_default_only(event: dict[str, Any]) -> bool:
    followups = event.get("story_followups")
    if not isinstance(followups, dict):
        return False
    return bool(followups) and set(str(key) for key in followups.keys()) == {"default"}


def _commandable_button_count(event: dict[str, Any]) -> int:
    return commandable_button_count(event)


def _room_infrastructure_records(room_record: dict[str, Any]) -> list[dict[str, Any]]:
    records = room_record.get("animal_infrastructure", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _event_mentions_room_infrastructure(event: dict[str, Any], room_record: dict[str, Any]) -> bool:
    records = _room_infrastructure_records(room_record)
    if not records:
        return False
    parts: list[str] = [
        str(event.get("line_1", "")),
        str(event.get("line_2", "")),
        str(event.get("infrastructure_actor", "")),
        str(event.get("animal_infrastructure", "")),
    ]
    buttons = event.get("buttons", [])
    if isinstance(buttons, list):
        for button in buttons:
            if isinstance(button, dict):
                parts.append(str(button.get("label", "")))
                parts.append(str(button.get("action", "")))
    text = " ".join(parts).lower().replace("_", " ")
    for record in records:
        record_parts = [
            str(record.get("id", "")).replace("_", " "),
            str(record.get("function", "")),
        ]
        possible = record.get("possible_interactions", [])
        if isinstance(possible, list):
            record_parts.extend(str(item).replace("_", " ") for item in possible)
        signature = " ".join(record_parts).lower()
        signature_terms = [
            term
            for term in re.findall(r"[a-z0-9]+", signature)
            if len(term) > 3 and term not in {"with", "that", "they", "from", "into", "after", "before", "room", "work"}
        ]
        if signature_terms and any(term in text for term in signature_terms):
            return True
    return False


def room_depth_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    findings: list[dict[str, str]] = []
    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and room.get("id")
    }
    story_engine_track = _is_story_engine_track(rooms_payload)
    environment_event_counts: dict[str, int] = {}
    if story_engine_track:
        for room_id, events in room_events.items():
            room_record = rooms_by_id.get(str(room_id), {})
            environment_id = _environment_id_for_room(str(room_id), room_record)
            event_count = len(events) if isinstance(events, list) else 0
            environment_event_counts[environment_id] = environment_event_counts.get(environment_id, 0) + event_count

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            add(f"room_events.{room_id}", "high", "room events are not a list", "Room depth cannot be evaluated until events are structured.")
            continue
        room_location = f"room_events.{room_id}"
        room_record = rooms_by_id.get(str(room_id), {})
        narrow_room = is_narrow_room_role(room_record)
        environment_id = _environment_id_for_room(str(room_id), room_record)
        family_event_count = environment_event_counts.get(environment_id, len(events)) if story_engine_track else len(events)
        if family_event_count < 3 and not narrow_room:
            add(
                room_location,
                "high",
                f"thin environment family: only {family_event_count} event{'s' if family_event_count != 1 else ''}",
                "Add enough distinct room instances or events inside this environment family to support action, reaction, and delayed consequences before calling it complete.",
            )
        if story_engine_track and not _has_environment_group(room_record):
            add(
                room_location,
                "medium",
                "room lacks explicit environment grouping",
                "Add environment_id or environment_family so this room is one instance of a larger environment type, not a literal room the player is expected to revisit.",
            )
        if story_engine_track and not narrow_room and not _has_environment_echo_plan(room_record):
            add(
                room_location,
                "medium",
                "environment has no echo plan",
                "Add environment_echoes, later_instance_echoes, or environment_memory_states describing how choices can surface in later similar rooms.",
            )
        if story_engine_track and not _has_specific_corpus_influence(room_record):
            add(
                room_location,
                "high",
                "room lacks a specific corpus writing influence",
                "Add corpus_influences with source title/seed, the specific source moment or authorial move, the writing energy to import, and how it changes this room's prose.",
            )
        if story_engine_track and not narrow_room and not _has_ending_vector(room_record):
            add(
                room_location,
                "high",
                "environment has no ending vector",
                "Add ending_vectors naming the ending this environment can pull toward, what behavior feeds it, and what diverts it.",
            )
        if story_engine_track and not narrow_room and not _has_mutation_hooks(room_record):
            add(
                room_location,
                "medium",
                "environment has no adaptation/equipment/procedure openings",
                "Add adaptation_hooks, equipment_hooks, or procedure_hooks with concrete capability tags that can alter future choices in this environment.",
            )

        actor_found = False
        delayed_found = False
        memory_found = False
        infrastructure_used = False
        for event in events:
            if not isinstance(event, dict):
                continue
            actor_found = actor_found or _has_interactable_actor(event)
            delayed_found = delayed_found or _has_delayed_consequence(event)
            memory_found = memory_found or _has_room_memory_change(event)
            infrastructure_used = infrastructure_used or _event_mentions_room_infrastructure(event, room_record)
            event_id = str(event.get("id", "unknown"))
            location = f"{room_location}.{event_id}"
            if story_engine_track and not _has_action_specific_result(event):
                add(
                    location,
                    "high",
                    "post-update event relies on generic legacy action results",
                    "Add action_results or per-button result lines/state changes so outcomes name this room's mechanism instead of only reporting shared stats.",
                )
            if story_engine_track and _commandable_button_count(event) > 1 and _followups_are_default_only(event):
                add(
                    f"{location}.story_followups",
                    "medium",
                    "all choices enqueue the same default follow-up",
                    "Prefer action-specific follow-ups, or document why every choice awakens the same later character/faction beat.",
                )
            if _has_only_immediate_stat_surface(event):
                add(
                    location,
                    "high",
                    "immediate stat exchange without delayed consequence",
                    "Attach the choice to future room text, route state, deck pressure, character posture, beast behavior, claim, debt, scent, or pursuit.",
                )
            if not _has_interactable_actor(event):
                add(
                    location,
                    "medium",
                    "no clear interactable actor or infrastructure system",
                    "Name the officer, department, ship system, instrument, object, signal, or recovery process the captain can influence.",
                )
            if str(event.get("enemy_id", "")) and not any(key in event for key in ("beast_state_change", "infrastructure_actor", "reaction_tags", "delayed_consequence")):
                add(
                    location,
                    "high",
                    "beast/enemy appears only as attack surface",
                    "Give the beast an infrastructure role and a non-combat interaction path before or alongside combat.",
                )

        if not delayed_found and not narrow_room:
            add(
                room_location,
                "high",
                "room lacks explicit delayed consequence or memory hook",
                "At least one event should change later instance text, deck pressure, route state, actor state, claim, debt, pursuit, or available choices.",
            )
        if story_engine_track and not memory_found:
            add(
                room_location,
                "high",
                "environment lacks explicit memory/state changes",
                "Add environment_state_changes, environment_memory_flags, actor_state_changes, route_state_changes, or faction_state_changes so choices can alter later room instances or pressure.",
            )
        if story_engine_track and _room_infrastructure_records(room_record) and not infrastructure_used:
            add(
                room_location,
                "medium",
                "declared animal infrastructure is not used by events",
                "Mention and manipulate at least one declared infrastructure actor in room events, choices, or action results.",
            )
        if not actor_found:
            add(
                room_location,
                "medium",
                "room lacks an interactable character, beast, animal, or infrastructure actor",
                "Make the room more than scenery by assigning a behaving system the player can influence.",
            )

    return findings


def _has_story_anchor(event: dict[str, Any]) -> bool:
    story_keys = {
        "character_id",
        "faction_id",
        "storyline_id",
        "story_stage",
        "source_character_function",
        "animal_infrastructure",
        "recurring_character_id",
        "cross_run_story_hook",
    }
    if any(str(event.get(key, "")).strip() for key in story_keys):
        return True
    text = "%s %s" % (event.get("line_1", ""), event.get("line_2", ""))
    text_lower = text.lower()
    story_terms = {
        "chorus",
        "black hole",
        "captain",
        "chaplain",
        "chief engineer",
        "engineer",
        "expedition marshal",
        "infirmary",
        "lifeboat",
        "lifeboats",
        "marshal",
        "natural philosopher",
        "navigator",
        "observatory",
        "quartermaster",
        "registry",
        "signal",
        "surgeon",
        "merchant",
        "operator",
        "operators",
        "survey",
        "rite",
        "ledger",
        "larder",
        "toll",
        "ferry",
        "beetle",
        "larva",
        "larval",
        "mites",
        "hounds",
        "mouths",
        "chapel",
        "map",
    }
    return any(term in text_lower for term in story_terms)


def room_story_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    special_events = payload.get("special_events", {})
    if not isinstance(special_events, dict):
        special_events = {}
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and room.get("id")
    }
    findings: list[dict[str, str]] = []
    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            continue
        room_location = f"room_events.{room_id}"
        room_record = rooms_by_id.get(str(room_id), {})
        narrow_room = is_narrow_room_role(room_record)
        room_text = " ".join([
            str(room_record.get("first_visit_description", "")),
            str(room_record.get("return_description", "")),
            " ".join(str(tag) for tag in room_record.get("tags", []) if str(tag)),
        ])
        room_story_anchor = _has_story_anchor({"line_1": room_text, "line_2": ""})
        report_frame_terms = {
            "captain",
            "report",
            "reports",
            "officer",
            "briefing",
            "log",
            "navigator",
            "engineer",
            "surgeon",
            "quartermaster",
            "marshal",
            "philosopher",
        }
        report_frame = any(term in room_text.lower() for term in report_frame_terms)
        explicit_story_keys = [
            "officer_reports",
            "crew_state_hooks",
            "ship_state_hooks",
            "resource_stakes",
            "black_hole_anomaly",
            "followup_vectors",
            "progression_state",
        ]
        required_story_keys = explicit_story_keys
        if narrow_room:
            required_story_keys = [
                "officer_reports",
                "crew_state_hooks",
                "ship_state_hooks",
                "resource_stakes",
                "progression_state",
            ]
        missing_story_keys = [key for key in required_story_keys if not room_record.get(key)]
        story_events = [event for event in events if isinstance(event, dict) and _has_story_anchor(event)]
        delayed_events = [event for event in events if isinstance(event, dict) and _has_delayed_consequence(event)]
        story_followup_refs: list[str] = []
        for event in events:
            if isinstance(event, dict):
                story_followup_refs.extend(_story_followup_event_ids(event))
                for followup in _story_followup_entries(event):
                    if int(followup.get("delay_rooms", 0)) < 1 and not bool(followup.get("immediate", False)):
                        add(
                            f"{room_location}.{str(event.get('id', 'unknown'))}.story_followups",
                            "high",
                            "story follow-up fires too soon",
                            "Set delay_rooms to at least 1 for later beats, or set immediate:true when the current deck would otherwise repeat the same room before debrief.",
                        )
        if missing_story_keys:
            add(
                room_location,
                "high",
                "room lacks complete explicit story backbone",
                "Add non-empty room metadata for: %s." % ", ".join(missing_story_keys),
            )
        if not story_events and not room_story_anchor:
            add(
                room_location,
                "high",
                "room is not anchored to the setting backbone",
                "Tie the room to a faction, recurring character trace, animal infrastructure role, or cross-run storyline.",
            )
        if not delayed_events and not narrow_room:
            add(
                room_location,
                "high",
                "room story has no later-instance or delayed motion",
                "Add a story hook that returns as altered later-instance text, debt, scent, route dependency, faction posture, animal behavior, deck pressure, or ending pressure.",
            )
        if (story_events or room_story_anchor) and not report_frame and not any(any(term in ("%s %s" % (event.get("line_1", ""), event.get("line_2", ""))).lower() for term in report_frame_terms) for event in story_events):
            add(
                room_location,
                "medium",
                "story anchor lacks captain-facing reporting frame",
                "Keep story motion in captain-facing reports, officer briefings, logs, or procedural transcripts.",
            )
        if not story_followup_refs and not narrow_room:
            add(
                room_location,
                "high",
                "room story does not enqueue follow-up events",
                "Progress character/faction stories by queueing one-shot special events or later environment echoes from room events, not by relying on literal room revisits.",
            )
        for followup_id in story_followup_refs:
            location = f"{room_location}.story_followups.{followup_id}"
            followup = special_events.get(followup_id, {})
            if not isinstance(followup, dict):
                add(
                    location,
                    "high",
                    "story follow-up references missing special event",
                    "Add the referenced special event or remove the story_followups entry.",
                )
                continue
            if bool(followup.get("reactivate_on_reshuffle", True)):
                add(
                    location,
                    "high",
                    "story follow-up can retrigger in same run",
                    "Set reactivate_on_reshuffle to false and use a trigger_key so character/faction beats are one-shot per run.",
                )

    return findings


def _story_followup_event_ids(event: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for followup in _story_followup_entries(event):
        event_id = str(followup.get("event_id", ""))
        if event_id:
            ids.append(event_id)
    return sorted(set(ids))


def _story_followup_entries(event: dict[str, Any]) -> list[dict[str, Any]]:
    followups = event.get("story_followups")
    entries: list[dict[str, Any]] = []

    def add_from_value(value: Any) -> None:
        if isinstance(value, str) and value:
            entries.append({"event_id": value})
        elif isinstance(value, dict):
            entries.append(value)

    if isinstance(followups, str):
        add_from_value(followups)
    elif isinstance(followups, dict):
        for value in followups.values():
            add_from_value(value)
    elif isinstance(followups, list):
        for value in followups:
            add_from_value(value)

    return entries


def action_balance_notes() -> dict[str, Any]:
    return {
        "danger": {
            "state_meaning": "attention and response pressure",
            "damage_scaling": "player combat damage is multiplied by 1 + danger * 0.5",
            "enemy_pressure_scaling": "at danger_notice_threshold and above, enemy ambush chance and initiative receive small increases",
            "bpm_scaling": "base_bpm + danger * danger_bpm_step",
            "presentation": "at danger_notice_threshold and above, encounter text adds an attention pressure line by event type",
            "actions_that_raise": ["leave_merchant", "run", "overdraw_amber"],
            "actions_that_lower": ["listen_at_green_split", "mark_red_branch"],
        },
        "corruption": {
            "state_meaning": "identity drift and body-system contamination",
            "actions_that_raise": [
                "take_mutation",
                "take_symbiote",
                "drink_pool",
                "harvest_eggs",
                "seal_amber_wound",
                "take_green_tunnel",
                "open_red_artery",
            ],
            "actions_that_lower": ["study_pool"],
            "trigger": "corruption_spike_room appears each corruption_spike_threshold",
        },
        "resources": {
            "biomass_sources": [
                "combat rewards",
                "harvest_eggs",
                "siphon_amber",
                "overdraw_amber",
                "cut_green_spine",
                "open_red_artery",
            ],
            "recovery_sources": ["drink_pool", "seal_amber_wound", "take_green_tunnel"],
        },
        "cadence": {
            "special_events": ["symbiote_every", "merchant_every", "danger_notice_threshold", "corruption_spike_threshold"],
            "deck_shape": ["starter_rooms", "draw_rules", "room_pools"],
        },
        "instrumentation": {
            "choice_log": "run_manager.gd writes action, event, and before/after run state to user://fleshpunk_run_balance_log.jsonl",
        },
    }


def balance_context() -> dict[str, Any]:
    return {
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "actions": sorted(existing_actions()),
        "action_balance_notes": action_balance_notes(),
        "enemies": load_json(ENEMIES_PATH).get("enemies", []),
        "mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def _short_visible_lines(value: Any, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            lines.append(text)
        if len(lines) >= limit:
            break
    return lines


def _blind_choice_read(event: dict[str, Any]) -> list[dict[str, Any]]:
    buttons = event.get("buttons", [])
    action_results = event.get("action_results", {})
    story_followups = event.get("story_followups", {})
    choices: list[dict[str, Any]] = []
    if not isinstance(buttons, list):
        return choices

    for button in buttons:
        if not isinstance(button, dict):
            continue
        label = str(button.get("label", "")).strip()
        if not label:
            continue
        action = str(button.get("action", "")).strip()
        action_result = action_results.get(action, {}) if isinstance(action_results, dict) else {}
        followup = story_followups.get(action, {}) if isinstance(story_followups, dict) else {}
        choice: dict[str, Any] = {"label": label}
        result_lines = _short_visible_lines(action_result.get("lines", [])) if isinstance(action_result, dict) else []
        if result_lines:
            choice["result_lines"] = result_lines
        if isinstance(followup, dict):
            queued_line = str(followup.get("queued_line", "")).strip()
            if queued_line:
                choice["queued_followup_line"] = queued_line
        choices.append(choice)
    return choices


def _blind_event_read(event: dict[str, Any]) -> dict[str, Any]:
    visible_event: dict[str, Any] = {
        "id": str(event.get("id", "")).strip(),
        "type": str(event.get("type", "")).strip(),
    }
    line_1 = str(event.get("line_1", "")).strip()
    line_2 = str(event.get("line_2", "")).strip()
    if line_1:
        visible_event["line_1"] = line_1
    if line_2:
        visible_event["line_2"] = line_2
    choices = _blind_choice_read(event)
    if choices:
        visible_event["choices"] = choices
    return visible_event


def blind_player_text_context() -> dict[str, Any]:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and str(room.get("id", "")).strip()
    }
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    visible_rooms: list[dict[str, Any]] = []

    if isinstance(room_events, dict):
        for room_id in sorted(room_events.keys()):
            room = rooms_by_id.get(str(room_id), {})
            room_read: dict[str, Any] = {
                "room_id": str(room_id),
                "name": str(room.get("name", "")).strip(),
                "first_visit_description": str(room.get("first_visit_description", "")).strip(),
                "return_description": str(room.get("return_description", "")).strip(),
                "events": [],
            }
            events = room_events.get(room_id, [])
            if isinstance(events, list):
                room_read["events"] = [_blind_event_read(event) for event in events if isinstance(event, dict)]
            visible_rooms.append(room_read)

    visible_special_events: list[dict[str, Any]] = []
    special_event_values: list[Any] = []
    if isinstance(special_events, dict):
        special_event_values = list(special_events.values())
    elif isinstance(special_events, list):
        special_event_values = special_events
    for event in special_event_values:
        if isinstance(event, dict):
            visible_special_events.append(_blind_event_read(event))

    return {
        "read_rule": "Judge this as a first-time player with no design notes, lore primer, system knowledge, or author intent. Use only these visible room descriptions, event lines, result lines, queued follow-up lines, and choice labels.",
        "opening_room_id": str(decks_payload.get("opening_room_id", "")).strip(),
        "rooms": visible_rooms,
        "special_events": visible_special_events,
    }


def _story_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def story_architect_context() -> dict[str, Any]:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    rooms = rooms_payload.get("rooms", [])
    recurring_characters: dict[str, dict[str, Any]] = {}
    storyline_ids: dict[str, int] = {}
    faction_ids: dict[str, int] = {}
    room_story_inventory: list[dict[str, Any]] = []
    followup_refs: list[dict[str, Any]] = []

    if isinstance(rooms, list):
        for room in rooms:
            if not isinstance(room, dict):
                continue
            room_id = str(room.get("id", "")).strip()
            if not room_id:
                continue
            room_characters = _story_list(room.get("recurring_character_ids", []))
            for character_id in room_characters:
                record = recurring_characters.setdefault(character_id, {"id": character_id, "rooms": []})
                record["rooms"].append(room_id)
            for storyline_id in _story_list(room.get("storyline_ids", [])):
                storyline_ids[storyline_id] = storyline_ids.get(storyline_id, 0) + 1
            for faction_id in _story_list(room.get("faction_ids", [])):
                faction_ids[faction_id] = faction_ids.get(faction_id, 0) + 1
            room_story_inventory.append({
                "room_id": room_id,
                "name": str(room.get("name", "")).strip(),
                "instance_premise": str(room.get("instance_premise", "")).strip(),
                "recurring_character_ids": room_characters,
                "storyline_ids": _story_list(room.get("storyline_ids", [])),
                "faction_ids": _story_list(room.get("faction_ids", [])),
                "progression_state": room.get("progression_state", {}),
                "cross_run_story_hooks": room.get("cross_run_story_hooks", []),
            })

    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_id = str(event.get("id", "")).strip()
                story_followups = event.get("story_followups", {})
                if not isinstance(story_followups, dict):
                    continue
                for action_id, followup in story_followups.items():
                    if not isinstance(followup, dict):
                        continue
                    followup_refs.append({
                        "source_room_id": str(room_id),
                        "source_event_id": event_id,
                        "source_action": str(action_id),
                        "followup_event_id": str(followup.get("event_id", "")).strip(),
                        "trigger_key": str(followup.get("trigger_key", "")).strip(),
                        "delay_rooms": followup.get("delay_rooms"),
                        "queued_line": str(followup.get("queued_line", "")).strip(),
                    })

    special_event_summaries: list[dict[str, Any]] = []
    special_event_values: list[tuple[str, Any]] = []
    if isinstance(special_events, dict):
        special_event_values = [(str(event_id), event) for event_id, event in special_events.items()]
    elif isinstance(special_events, list):
        special_event_values = [(str(index), event) for index, event in enumerate(special_events)]
    for event_id, event in special_event_values:
        if not isinstance(event, dict):
            continue
        special_event_summaries.append({
            "id": str(event.get("id", event_id)).strip(),
            "type": str(event.get("type", "")).strip(),
            "line_1": str(event.get("line_1", "")).strip(),
            "line_2": str(event.get("line_2", "")).strip(),
            "buttons": [str(button.get("label", "")).strip() for button in event.get("buttons", []) if isinstance(button, dict)],
            "trigger_key": str(event.get("trigger_key", "")).strip(),
            "reactivate_on_reshuffle": event.get("reactivate_on_reshuffle"),
        })

    return {
        "goal": "Find the missing story spine and propose character-driven follow-up encounters grounded in current data.",
        "active_content": {
            "rooms_path": str(ROOMS_PATH.relative_to(ROOT)),
            "events_path": str(EVENTS_PATH.relative_to(ROOT)),
            "decks_path": str(DECKS_PATH.relative_to(ROOT)),
            "opening_room_id": str(decks_payload.get("opening_room_id", "")).strip(),
            "room_count": len(rooms) if isinstance(rooms, list) else 0,
            "room_event_count": sum(len(events) for events in room_events.values() if isinstance(events, list)) if isinstance(room_events, dict) else 0,
            "special_event_count": len(special_event_summaries),
        },
        "blind_player_text_context": blind_player_text_context(),
        "room_story_inventory": room_story_inventory,
        "recurring_character_inventory": sorted(recurring_characters.values(), key=lambda item: item["id"]),
        "storyline_counts": dict(sorted(storyline_ids.items())),
        "faction_counts": dict(sorted(faction_ids.items())),
        "story_followup_refs": followup_refs,
        "special_event_summaries": special_event_summaries,
        "recent_guidance": load_recent_memory(limit=4, include_core_guides=True),
    }


def fun_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    pressure_axes = {
        "corruption": {
            "desired_role": "Overusing mutations, symbiotes, pools, or invasive body choices should push the clone toward a corruption ending.",
            "current_signals": ["take_mutation", "take_symbiote", "drink_pool", "harvest_eggs", "seal_amber_wound", "take_green_tunnel", "open_red_artery"],
        },
        "danger": {
            "desired_role": "Fleeing, refusing, greedy noise, and avoiding combat should make the organism notice Hymn until the hunter comes.",
            "current_signals": ["leave_merchant", "run", "rush_red_split", "track_hatchling", "disturb_green_spores"],
        },
        "balance": {
            "desired_role": "The best ending should require staying near neutral: enough power to survive, not enough repeated pressure to be claimed by an ending.",
            "current_gap": "Ending routing and explicit imbalance feedback are not implemented yet.",
        },
    }
    return {
        "blind_player_text_context": blind_player_text_context(),
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "events": room_events,
        "special_events": special_events,
        "actions": sorted(existing_actions()),
        "single_choice_room_gaps": room_tradeoff_findings(),
        "room_depth_findings": room_depth_findings(),
        "room_story_findings": room_story_findings(),
        "pressure_axes": pressure_axes,
        "enemies": load_json(ENEMIES_PATH).get("enemies", []),
        "mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def lore_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    return {
        "vibe_guide": load_vibe_guide(),
        "lore_guide": load_lore_guide(),
        "setting_backbone": load_setting_backbone(),
        "style_memory": read_text(MEMORY_DIR / "fleshpunk_style.md"),
        "events": events_payload,
        "event_type_counts": event_type_counts(),
        "actions": sorted(existing_actions()),
        "knowledge_rules": {
            "hymn_clone_ignorance": "Hymn does not know she is a clone. Her narration must not state clone facts.",
            "chorus": "Hymn reports to Chorus frequently, asks for instruction or confirmation, and Chorus is never heard directly.",
            "speaker_labels": "No visible speaker labels such as Her:. All displayed text should read as first-person narration.",
            "tts": "Narration should be phrase-based and suitable for Nova voice TTS.",
        },
        "continuity_risks": [
            "Narration revealing clone knowledge directly.",
            "Game-over copy using outside-the-character language.",
            "Corruption endings that are ambiguous instead of showing loss of boundary and agency.",
            "Events that use fleshy imagery without explaining what the organism functionally does.",
            "Merchant scenes that feel like a shop UI instead of a predatory exchange system.",
        ],
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def lore_brainstorm_context() -> dict[str, Any]:
    event_samples: list[dict[str, Any]] = []
    events_payload = load_json(EVENTS_PATH)
    for room_id, events in events_payload.get("room_events", {}).items():
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            event_samples.append(compact_event(str(room_id), event))
    for event_id, event in events_payload.get("special_events", {}).items():
        if isinstance(event, dict):
            sample = compact_event("special_events", event)
            sample["special_event_id"] = str(event_id)
            event_samples.append(sample)
    return {
        "lore_guide": load_lore_guide(),
        "setting_backbone": load_setting_backbone(),
        "vibe_guide": load_vibe_guide(),
        "style_memory": read_text(MEMORY_DIR / "fleshpunk_style.md"),
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "rooms": load_json(ROOMS_PATH).get("rooms", []),
        "event_samples": event_samples,
        "enemies": load_json(ENEMIES_PATH).get("enemies", []),
        "mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "actions": sorted(existing_actions()),
        "required_hook_shape": {
            "safe_reveal": "What Hymn can learn now without breaking her knowledge boundary.",
            "deferred_secret": "What remains hidden for later.",
            "gameplay_hook": "The mechanical consequence or opportunity this lore creates.",
            "story_motion": "How the idea can change across rooms or across runs without Hymn knowing the clone premise.",
            "related_systems": ["danger", "corruption", "merchant", "deck", "enemy", "symbiote", "mutation", "ending", "lore_fragment", "faction", "animal_infrastructure", "environment_memory"],
        },
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def accessibility_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    event_samples: list[dict[str, Any]] = []
    for room_id, events in events_payload.get("room_events", {}).items():
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    event_samples.append(compact_event(str(room_id), event))
    for event_id, event in events_payload.get("special_events", {}).items():
        if isinstance(event, dict):
            sample = compact_event("special_events", event)
            sample["special_event_id"] = str(event_id)
            event_samples.append(sample)
    return {
        "accessibility_guide": load_accessibility_guide(),
        "vibe_guide": load_vibe_guide(),
        "lore_guide": load_lore_guide(),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "event_samples": event_samples,
        "actions": sorted(existing_actions()),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "local_accessibility_findings": event_accessibility_findings(),
        "global_commands": [
            "one",
            "two",
            "three",
            "repeat",
            "repeat choices",
            "status",
            "inventory",
            "help",
            "confirm",
            "cancel",
            "pause",
            "continue",
            "slower",
            "faster",
        ],
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def compact_event(room_id: str, event: dict[str, Any]) -> dict[str, Any]:
    buttons = event.get("buttons", [])
    actions = []
    if isinstance(buttons, list):
        actions = [button.get("action") for button in buttons if isinstance(button, dict) and button.get("action")]
    compact_buttons = []
    if isinstance(buttons, list):
        for button in buttons:
            if isinstance(button, dict):
                compact_buttons.append({
                    "label": button.get("label"),
                    "action": button.get("action"),
                    "voice_aliases": button.get("voice_aliases", []),
                })
    compact: dict[str, Any] = {
        "room_id": room_id,
        "id": event.get("id"),
        "type": event.get("type"),
        "line_1": event.get("line_1"),
        "line_2": event.get("line_2"),
        "actions": actions,
        "buttons": compact_buttons,
    }
    for key in ("enemy_id", "scene_path", "symbiote_choices", "mutation_choices", "reactivate_on_reshuffle"):
        if key in event:
            compact[key] = event[key]
    return compact


def patch_schema() -> dict[str, Any]:
    outcome_schema = {
        "type": "object",
        "properties": {
            "lines": {"type": "array", "items": {"type": "string"}},
            "resource_changes": {"type": "object"},
            "environment_state_changes": {"type": "array"},
            "stress_changes": {"type": "array"},
            "operation_state_changes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["lines", "environment_state_changes"],
        "additionalProperties": True,
    }
    operation_plan_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "officer_id": {"type": "string"},
            "officer_name": {"type": "string"},
            "primary_skill": {"type": "string"},
            "base_success": {"type": "number"},
            "yield": {"type": "string"},
            "risk": {"type": "string"},
            "minimum_availability": {"type": "integer"},
            "blocked_mental_states": {"type": "array", "items": {"type": "string"}},
            "outcomes": {
                "type": "object",
                "properties": {
                    "strong_success": outcome_schema,
                    "success": outcome_schema,
                    "partial": outcome_schema,
                    "failure": outcome_schema,
                    "catastrophe": outcome_schema,
                },
                "required": ["success", "partial", "failure"],
                "additionalProperties": False,
            },
            "corpus_anchor_points": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["action", "officer_id", "primary_skill", "base_success", "yield", "risk", "outcomes"],
        "additionalProperties": True,
    }
    corpus_influence_schema = {
        "type": "object",
        "properties": {
            "seed_id": {"type": "string"},
            "source_id": {"type": "string"},
            "source_title": {"type": "string"},
            "source_chunk_id": {"type": "string"},
            "source_moment": {"type": "string"},
            "writing_influence": {"type": "string"},
            "room_application": {"type": "string"},
            "followup_application": {"type": "string"},
            "interlude_application": {"type": "string"},
            "source_fingerprint": {"type": "array", "items": {"type": "string"}},
            "structural_transfer": {"type": "string"},
            "required_visible_details": {"type": "array", "items": {"type": "string"}},
            "followup_payoff": {"type": "string"},
        },
        "required": ["source_chunk_id", "source_fingerprint", "structural_transfer", "required_visible_details", "followup_payoff"],
        "additionalProperties": True,
    }
    corpus_anchor_schema = {
        "type": "object",
        "properties": {
            "source_id": {"type": "string"},
            "source_chunk_id": {"type": "string"},
            "anchor_role": {"type": "string"},
            "source_fingerprint": {"type": "array", "items": {"type": "string"}},
            "playable_transform": {"type": "string"},
            "required_visible_details": {"type": "array", "items": {"type": "string"}},
            "followup_payoff": {"type": "string"},
        },
        "required": ["source_id", "source_chunk_id", "anchor_role", "source_fingerprint", "playable_transform", "required_visible_details", "followup_payoff"],
        "additionalProperties": True,
    }
    button_schema = {
        "type": "object",
        "properties": {
            "label": {"type": "string"},
            "action": {"type": "string"},
            "voice_aliases": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["label", "action"],
        "additionalProperties": True,
    }
    event_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string"},
            "speaker": {"type": "string"},
            "line_1": {"type": "string"},
            "line_2": {"type": "string"},
            "visible_text": {"type": "string"},
            "buttons": {"type": "array", "items": button_schema},
            "action_results": {"type": "object"},
            "story_followups": {"type": "object"},
            "operation_plans": {"type": "array", "items": {"type": "object"}},
            "corpus_influences": {"type": "array", "items": {"type": "object"}},
            "corpus_anchor_points": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["id", "type", "speaker", "line_1", "line_2", "buttons"],
        "additionalProperties": True,
    }
    room_record_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string"},
            "description": {"type": "string"},
            "first_visit_description": {"type": "string"},
            "return_description": {"type": "string"},
            "detection_report": {"type": "string"},
            "current_situation": {"type": "string"},
            "scenario_generation_contract": {"type": "object"},
            "religious_subtext": {"type": "object"},
            "officer_reports": {"type": "array", "items": {"type": "object"}},
            "procedure_hooks": {"type": "array", "items": {"type": "object"}},
            "corpus_influences": {"type": "array", "items": {"type": "object"}},
            "corpus_anchor_points": {"type": "array", "items": {"type": "object"}},
            "character_state_stakes": {"type": "object"},
            "interlude_vectors": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "id",
            "name",
            "type",
            "description",
            "first_visit_description",
            "return_description",
            "detection_report",
            "current_situation",
            "scenario_generation_contract",
            "religious_subtext",
            "officer_reports",
            "procedure_hooks",
            "corpus_influences",
            "corpus_anchor_points",
            "character_state_stakes",
            "interlude_vectors",
        ],
        "additionalProperties": True,
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "design_goal": {"type": "string"},
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "event": event_schema,
                    },
                    "required": ["room_id", "event"],
                    "additionalProperties": False,
                },
            },
            "special_events": {"type": "array", "items": event_schema},
            "room_records": {"type": "array", "items": room_record_schema},
            "deck_pool_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pool": {"type": "string"},
                        "room_id": {"type": "string"},
                    },
                    "required": ["pool", "room_id"],
                    "additionalProperties": False,
                },
            },
            "mutations": {"type": "array", "items": {"type": "object"}},
            "symbiotes": {"type": "array", "items": {"type": "object"}},
            "enemies": {"type": "array", "items": {"type": "object"}},
            "required_engine_changes": {"type": "array", "items": {"type": "string"}},
            "inspiration_notes": {"type": "array", "items": {"type": "string"}},
            "self_critique": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "events",
            "special_events",
            "room_records",
            "deck_pool_updates",
            "mutations",
            "symbiotes",
            "enemies",
            "required_engine_changes",
            "inspiration_notes",
            "self_critique",
        ],
        "additionalProperties": False,
    }


def critique_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "vibe_alignment_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "issue": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "target", "issue", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "event_type_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "purpose": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["id", "label", "purpose", "why"],
                    "additionalProperties": False,
                },
            },
            "encounter_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "room_id": {"type": "string"},
                        "concept": {"type": "string"},
                        "tradeoff": {"type": "string"},
                        "required_engine_changes": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["category", "room_id", "concept", "tradeoff", "required_engine_changes"],
                    "additionalProperties": False,
                },
            },
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "action_system_suggestions": {"type": "array", "items": {"type": "string"}},
            "next_generation_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "vibe_alignment_score",
            "findings",
            "event_type_suggestions",
            "encounter_suggestions",
            "vibe_doc_updates",
            "action_system_suggestions",
            "next_generation_prompt",
        ],
        "additionalProperties": False,
    }


def balance_critique_schema() -> dict[str, Any]:
    lever_item = {
        "type": "object",
        "properties": {
            "lever": {"type": "string"},
            "current_value": {"type": "string"},
            "run_feel_effect": {"type": "string"},
            "vibe_effect": {"type": "string"},
            "tweak_direction": {"type": "string"},
            "risk": {"type": "string"},
        },
        "required": ["lever", "current_value", "run_feel_effect", "vibe_effect", "tweak_direction", "risk"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "run_feel_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "vibe_balance_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "balance_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "issue": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "target", "issue", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "levers": {"type": "array", "items": lever_item},
            "tuning_experiments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "goal": {"type": "string"},
                        "changes": {"type": "array", "items": {"type": "string"}},
                        "success_signals": {"type": "array", "items": {"type": "string"}},
                        "rollback_signals": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "goal", "changes", "success_signals", "rollback_signals"],
                    "additionalProperties": False,
                },
            },
            "data_patch_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "path": {"type": "string"},
                        "suggested_change": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["file", "path", "suggested_change", "reason"],
                    "additionalProperties": False,
                },
            },
            "instrumentation_suggestions": {"type": "array", "items": {"type": "string"}},
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_balance_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "run_feel_score",
            "vibe_balance_score",
            "balance_findings",
            "levers",
            "tuning_experiments",
            "data_patch_suggestions",
            "instrumentation_suggestions",
            "vibe_doc_updates",
            "next_balance_prompt",
        ],
        "additionalProperties": False,
    }


def fun_critique_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "blind_read_summary": {"type": "string"},
            "fun_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "first_time_player_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "build_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "sequence_cohesion_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "organism_pressure_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "core_loop_diagnosis": {"type": "string"},
            "blind_text_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "player_facing_evidence": {"type": "string"},
                        "why_it_feels_disconnected": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": [
                        "severity",
                        "target",
                        "player_facing_evidence",
                        "why_it_feels_disconnected",
                        "recommendation",
                    ],
                    "additionalProperties": False,
                },
            },
            "choice_progression_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "current_choice_read": {"type": "string"},
                        "missing_progression": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["target", "current_choice_read", "missing_progression", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "payoff_gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "setup": {"type": "string"},
                        "current_payoff_gap": {"type": "string"},
                        "recommended_payoff": {"type": "string"},
                    },
                    "required": ["setup", "current_payoff_gap", "recommended_payoff"],
                    "additionalProperties": False,
                },
            },
            "not_fun_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "why_it_is_not_fun": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "target", "why_it_is_not_fun", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "organism_director_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "axis": {"type": "string"},
                        "current_behavior": {"type": "string"},
                        "desired_push": {"type": "string"},
                        "missing_feedback": {"type": "string"},
                        "recommended_change": {"type": "string"},
                    },
                    "required": ["axis", "current_behavior", "desired_push", "missing_feedback", "recommended_change"],
                    "additionalProperties": False,
                },
            },
            "decision_loop_rewrites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "loop": {"type": "string"},
                        "current_problem": {"type": "string"},
                        "fun_version": {"type": "string"},
                        "needed_system_hooks": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["loop", "current_problem", "fun_version", "needed_system_hooks"],
                    "additionalProperties": False,
                },
            },
            "ending_pressure_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ending": {"type": "string"},
                        "player_pattern_that_drives_it": {"type": "string"},
                        "warnings_before_lock": {"type": "array", "items": {"type": "string"}},
                        "lock_condition": {"type": "string"},
                    },
                    "required": ["ending", "player_pattern_that_drives_it", "warnings_before_lock", "lock_condition"],
                    "additionalProperties": False,
                },
            },
            "content_priorities": {"type": "array", "items": {"type": "string"}},
            "system_priorities": {"type": "array", "items": {"type": "string"}},
            "minimum_game_shape": {"type": "array", "items": {"type": "string"}},
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_fun_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "blind_read_summary",
            "fun_score",
            "first_time_player_score",
            "build_score",
            "sequence_cohesion_score",
            "organism_pressure_score",
            "core_loop_diagnosis",
            "blind_text_findings",
            "choice_progression_findings",
            "payoff_gaps",
            "not_fun_findings",
            "organism_director_findings",
            "decision_loop_rewrites",
            "ending_pressure_plan",
            "content_priorities",
            "system_priorities",
            "minimum_game_shape",
            "vibe_doc_updates",
            "next_fun_prompt",
        ],
        "additionalProperties": False,
    }


def lore_critique_schema() -> dict[str, Any]:
    finding_item = {
        "type": "object",
        "properties": {
            "severity": {"type": "string"},
            "target": {"type": "string"},
            "issue": {"type": "string"},
            "rewrite_direction": {"type": "string"},
        },
        "required": ["severity", "target", "issue", "rewrite_direction"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "lore_integrity_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "voice_integrity_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "continuity_findings": {"type": "array", "items": finding_item},
            "voice_findings": {"type": "array", "items": finding_item},
            "knowledge_boundary_findings": {"type": "array", "items": finding_item},
            "chorus_usage_plan": {"type": "array", "items": {"type": "string"}},
            "lore_expansion_seeds": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "purpose": {"type": "string"},
                        "safe_reveal": {"type": "string"},
                        "deferred_secret": {"type": "string"},
                    },
                    "required": ["topic", "purpose", "safe_reveal", "deferred_secret"],
                    "additionalProperties": False,
                },
            },
            "rewrite_priorities": {"type": "array", "items": {"type": "string"}},
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_lore_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "lore_integrity_score",
            "voice_integrity_score",
            "continuity_findings",
            "voice_findings",
            "knowledge_boundary_findings",
            "chorus_usage_plan",
            "lore_expansion_seeds",
            "rewrite_priorities",
            "vibe_doc_updates",
            "next_lore_prompt",
        ],
        "additionalProperties": False,
    }


def accessibility_critique_schema() -> dict[str, Any]:
    finding_item = {
        "type": "object",
        "properties": {
            "severity": {"type": "string"},
            "target": {"type": "string"},
            "issue": {"type": "string"},
            "recommendation": {"type": "string"},
        },
        "required": ["severity", "target", "issue", "recommendation"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "eyes_free_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "commandability_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "tts_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "critical_findings": {"type": "array", "items": finding_item},
            "command_parser_findings": {"type": "array", "items": finding_item},
            "tts_findings": {"type": "array", "items": finding_item},
            "schema_recommendations": {"type": "array", "items": {"type": "string"}},
            "command_alias_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "recommended_aliases": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": "string"},
                    },
                    "required": ["action", "recommended_aliases", "notes"],
                    "additionalProperties": False,
                },
            },
            "state_readout_plan": {"type": "array", "items": {"type": "string"}},
            "testing_plan": {"type": "array", "items": {"type": "string"}},
            "guide_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_accessibility_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "eyes_free_score",
            "commandability_score",
            "tts_score",
            "critical_findings",
            "command_parser_findings",
            "tts_findings",
            "schema_recommendations",
            "command_alias_plan",
            "state_readout_plan",
            "testing_plan",
            "guide_updates",
            "next_accessibility_prompt",
        ],
        "additionalProperties": False,
    }


def lore_brainstorm_schema() -> dict[str, Any]:
    concept_item = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "kind": {"type": "string"},
            "pitch": {"type": "string"},
            "safe_reveal": {"type": "string"},
            "hymn_misread": {"type": "string"},
            "deferred_secret": {"type": "string"},
            "gameplay_hook": {"type": "string"},
            "related_systems": {"type": "array", "items": {"type": "string"}},
            "sample_fragment": {"type": "string"},
            "implementation_notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "name",
            "kind",
            "pitch",
            "safe_reveal",
            "hymn_misread",
            "deferred_secret",
            "gameplay_hook",
            "related_systems",
            "sample_fragment",
            "implementation_notes",
        ],
        "additionalProperties": False,
    }
    relationship_item = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "string"},
            "visible_relationship": {"type": "string"},
            "hidden_truth": {"type": "string"},
            "gameplay_expression": {"type": "string"},
        },
        "required": ["a", "b", "visible_relationship", "hidden_truth", "gameplay_expression"],
        "additionalProperties": False,
    }
    reveal_path_item = {
        "type": "object",
        "properties": {
            "thread": {"type": "string"},
            "early_reveal": {"type": "string"},
            "mid_reveal": {"type": "string"},
            "late_reveal": {"type": "string"},
            "player_pressure": {"type": "string"},
            "ending_connection": {"type": "string"},
        },
        "required": ["thread", "early_reveal", "mid_reveal", "late_reveal", "player_pressure", "ending_connection"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "design_thesis": {"type": "string"},
            "factions": {"type": "array", "items": concept_item},
            "recurring_characters": {"type": "array", "items": concept_item},
            "organism_lore": {"type": "array", "items": concept_item},
            "lore_fragments": {"type": "array", "items": concept_item},
            "relationships": {"type": "array", "items": relationship_item},
            "reveal_paths": {"type": "array", "items": reveal_path_item},
            "mechanic_hooks": {"type": "array", "items": {"type": "string"}},
            "guardrails": {"type": "array", "items": {"type": "string"}},
            "next_lore_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "design_thesis",
            "factions",
            "recurring_characters",
            "organism_lore",
            "lore_fragments",
            "relationships",
            "reveal_paths",
            "mechanic_hooks",
            "guardrails",
            "next_lore_prompt",
        ],
        "additionalProperties": False,
    }


def story_architect_schema() -> dict[str, Any]:
    arc_beat_item = {
        "type": "object",
        "properties": {
            "beat_id": {"type": "string"},
            "role": {"type": "string"},
            "trigger": {"type": "string"},
            "encounter_function": {"type": "string"},
            "player_choice": {"type": "string"},
            "visible_change": {"type": "string"},
            "mechanical_consequence": {"type": "string"},
            "implementation_notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "beat_id",
            "role",
            "trigger",
            "encounter_function",
            "player_choice",
            "visible_change",
            "mechanical_consequence",
            "implementation_notes",
        ],
        "additionalProperties": False,
    }
    character_arc_item = {
        "type": "object",
        "properties": {
            "character_id": {"type": "string"},
            "player_facing_name": {"type": "string"},
            "current_status": {"type": "string"},
            "desire": {"type": "string"},
            "pressure_method": {"type": "string"},
            "relationship_to_hymn": {"type": "string"},
            "first_appearance": {"type": "string"},
            "arc_beats": {"type": "array", "items": arc_beat_item},
            "why_this_is_a_character": {"type": "string"},
            "failure_mode_if_absent": {"type": "string"},
        },
        "required": [
            "character_id",
            "player_facing_name",
            "current_status",
            "desire",
            "pressure_method",
            "relationship_to_hymn",
            "first_appearance",
            "arc_beats",
            "why_this_is_a_character",
            "failure_mode_if_absent",
        ],
        "additionalProperties": False,
    }
    first_spine_item = {
        "type": "object",
        "properties": {
            "sequence_index": {"type": "integer"},
            "target_room_or_event": {"type": "string"},
            "story_function": {"type": "string"},
            "player_question": {"type": "string"},
            "choice_pressure": {"type": "string"},
            "followup_payoff": {"type": "string"},
            "required_data_changes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "sequence_index",
            "target_room_or_event",
            "story_function",
            "player_question",
            "choice_pressure",
            "followup_payoff",
            "required_data_changes",
        ],
        "additionalProperties": False,
    }
    followup_item = {
        "type": "object",
        "properties": {
            "source_event": {"type": "string"},
            "followup_event_id": {"type": "string"},
            "character_id": {"type": "string"},
            "trigger": {"type": "string"},
            "timing": {"type": "string"},
            "scene_function": {"type": "string"},
            "choice_or_route_change": {"type": "string"},
            "mechanical_hook": {"type": "string"},
            "authoring_prompt": {"type": "string"},
        },
        "required": [
            "source_event",
            "followup_event_id",
            "character_id",
            "trigger",
            "timing",
            "scene_function",
            "choice_or_route_change",
            "mechanical_hook",
            "authoring_prompt",
        ],
        "additionalProperties": False,
    }
    pilot_item = {
        "type": "object",
        "properties": {
            "arc_name": {"type": "string"},
            "why_this_first": {"type": "string"},
            "scope_events": {"type": "array", "items": {"type": "string"}},
            "required_system_hooks": {"type": "array", "items": {"type": "string"}},
            "acceptance_tests": {"type": "array", "items": {"type": "string"}},
            "generation_prompt": {"type": "string"},
        },
        "required": [
            "arc_name",
            "why_this_first",
            "scope_events",
            "required_system_hooks",
            "acceptance_tests",
            "generation_prompt",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "story_diagnosis": {"type": "string"},
            "missing_story_primitives": {"type": "array", "items": {"type": "string"}},
            "character_arcs": {"type": "array", "items": character_arc_item},
            "first_15_minute_spine": {"type": "array", "items": first_spine_item},
            "followup_encounter_plan": {"type": "array", "items": followup_item},
            "pilot_arc_recommendation": pilot_item,
            "story_rules": {"type": "array", "items": {"type": "string"}},
            "patch_strategy": {"type": "array", "items": {"type": "string"}},
            "next_story_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "story_diagnosis",
            "missing_story_primitives",
            "character_arcs",
            "first_15_minute_spine",
            "followup_encounter_plan",
            "pilot_arc_recommendation",
            "story_rules",
            "patch_strategy",
            "next_story_prompt",
        ],
        "additionalProperties": False,
    }


def story_pilot_schema() -> dict[str, Any]:
    room_event_update_item = {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "event_id": {"type": "string"},
            "merge": {"type": "object"},
        },
        "required": ["room_id", "event_id", "merge"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "design_goal": {"type": "string"},
            "special_events": {"type": "array", "items": {"type": "object"}},
            "room_records": {"type": "array", "items": {"type": "object"}},
            "room_events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "event": {"type": "object"},
                    },
                    "required": ["room_id", "event"],
                    "additionalProperties": False,
                },
            },
            "room_event_updates": {"type": "array", "items": room_event_update_item},
            "deck_pool_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pool": {"type": "string"},
                        "room_id": {"type": "string"},
                    },
                    "required": ["pool", "room_id"],
                    "additionalProperties": False,
                },
            },
            "required_engine_changes": {"type": "array", "items": {"type": "string"}},
            "validation_notes": {"type": "array", "items": {"type": "string"}},
            "self_critique": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "special_events",
            "room_records",
            "room_events",
            "room_event_updates",
            "deck_pool_updates",
            "required_engine_changes",
            "validation_notes",
            "self_critique",
        ],
        "additionalProperties": False,
    }


def current_room_packet(room_id: str) -> dict[str, Any]:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    room_record = {}
    for room in rooms_payload.get("rooms", []):
        if isinstance(room, dict) and str(room.get("id", "")) == room_id:
            room_record = room
            break
    return {
        "room": room_record,
        "room_events": events_payload.get("room_events", {}).get(room_id, []),
    }


def revelation_generation_system() -> str:
    return """
You are the scenario/writing agent for Revelation, a Godot AI narrative tactical symbolic horror roguelike.
Generate JSON patches only. Do not write prose outside the JSON object.

Revelation doctrine:
- Preserve the existing architecture unless the user asks for a new room: character-owned plans, hidden per-character state, operation_plans, story_followups, interludes, corpus_anchor_points, and religious_subtext are core.
- Write restrained procedural symbolic horror: SITREPs, field reports, transcripts, debriefs, clinic notes, staff observations, and after-action language.
- Characters are trained personnel, scientists, soldiers, and exhausted experts. Avoid melodrama, quips, internet humor, sermonizing, fantasy terminology, and generic cult insanity.
- Use the three-layer Revelation scenario contract:
  1. What comes from religious text: the anomaly's symbolic engine, rule, object behavior, classification, timing, or consequence.
  2. How comes from procedure documents: the character plans, equipment, field actions, branch consequences, and after-action handling.
  3. Structure comes from public-domain weird fiction: local testimony, archive trail, bad site history, field instruments failing, sample analysis, delayed realization, official uncertainty, and aftermath.
- Every new mission room must include scenario_generation_contract with what_from, how_from, structure_from, and a rule summary.
- corpus_anchor_points should include anchor_role values that make the layer explicit, such as religious_what, procedural_how, weird_fiction_structure, and hidden_state_resolution.
- Religious material must be structurally specific, not decorative. Use a named motif such as unclean lips, written/blotted names, clean/unclean pronouncement, seven-day isolation, flood warning, ark levels, Babel/confused speech, witness/testimony, veil/threshold, covenant sign, trumpet/blast, or living register.
- Every mission room must include religious_subtext with motif, primary_sources, subtext, and visible_requirements.
- Every mission room and major event must include corpus_anchor_points. Each anchor point needs source_id, source_chunk_id, anchor_role, source_fingerprint, playable_transform, required_visible_details, and followup_payoff.
- corpus_influences must be a list of objects, not source id strings. Each object needs source_chunk_id, source_fingerprint, structural_transfer, required_visible_details, and followup_payoff.
- required_visible_details must be a list of at least two concrete visible objects, phrases, procedures, or evidence items.
- Corpus anchors must survive into player-facing prose as concrete objects/procedures: wristbands, red tape, living register, blotted line, smoke at a threshold, command card, seven-day hold, hot-zone board, side gate, retained audio file, etc.
- Use public-domain scripture/Quran/corpus chunks as private anchoring. Do not quote or paraphrase sacred text closely in final player-facing prose.
- New mission patches must put the root room choice in events and all queued follow-ups, resolutions, debriefs, and cooldowns in special_events. story_followups must target ids in special_events.
- Every choice should represent a character's plan. Preserve operation_plans where present. Each plan needs action, officer_id, primary_skill, base_success, yield, risk, blocked states where useful, and outcomes for strong_success, success, partial, failure, and catastrophe.
- For Revelation, officer_id must be one of: torah, brooks, lt_mara_owen, dr_samira_iyad, agent_caleb_ross, specialist_mina_park, dr_lenora_saye.
- base_success must be a probability such as 0.64, never a percentage such as 64.
- Each operation outcome must be an object with lines and durable environment_state_changes or resource_changes. Do not use plain strings for operation outcomes.
- If a character plan fails, write a concrete backfire on that character using environment_state_changes such as character.<id>.stress, morale, mental_state, fatigue, injury, contamination, loyalty, or availability.
- Follow-ups must progress the religious/procedural motif. Do not repeat the same phenomenon with new wording. A follow-up should mutate, reveal, cost, resolve, or change future choices.
- Interludes should show consequences through debrief, smoke break, food, clinic, lab, barracks, command corridor, or washdown scenes. They should read individual character state through behavior.
- Interludes must include interlude_type, state_reads, state_writes, featured_characters, visible_text, choices, outcomes, followup_hooks, and corpus_anchors.
- Use existing actions unless the user explicitly asks for engine work. Available actions are in game_context.existing_actions.
- Keep button labels short and commandable. Include voice_aliases if obvious.
- Keep required_engine_changes empty unless a new runtime hook is truly required.
""".strip()


def build_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    context = lite_game_context() if getattr(args, "context_lite", False) else game_context()
    source_seeds = load_source_seed_context(args)
    corpus_fragments = load_corpus_fragment_context(args)
    corpus_index = load_corpus_index_context(args)
    room = args.room or "any existing room"
    category = args.category or "any defined category"
    category_rules = get_event_category(args.category) if args.category else {}
    if is_revelation_project():
        system = revelation_generation_system()
    else:
        system = """
You are a scenario designer for a Godot narrated choice game called Nightmare Voyage.
Generate JSON patches only. Do not write prose outside the JSON object.

Your scenarios should fit the existing data-driven event system:
- Add events under events.json room_events[room_id].
- Each event should include id, type, speaker, line_1, line_2, and buttons.
- Event type must be one of the defined category ids.
- Buttons need label and action.
- voice_aliases are auto-enriched by tooling from label, action, and local narration, but you may include short spoken aliases when they are obvious.
- Every room event should offer at least two commandable buttons unless it is explicitly a transition event.
- Do not ship a room that only says Proceed unless the room is truly terminal or transitional.
- Do not ship one-off rooms whose choices resolve only as minor stat changes.
- Every room/encounter needs action/reaction, a memory hook, and at least one delayed consequence.
- Character/officer/faction progression should use story_followups that enqueue one-shot special_events into the run stack or later ship/crew echoes; do not rely on revisiting the originating packet.
- Character and officer events must not retrigger in the same run. Use trigger_key and reactivate_on_reshuffle: false on follow-up special events.
- Treat officers, departments, ship systems, tools, recovered objects, and anomalies as interactable infrastructure.
- Every encounter packet should tell part of the setting story through officer pressure, ship state, crew doctrine, route memory, scientific progress, or later echoes.
- Every encounter family should have at least one ending vector. Encounters should be able to pull toward, divert from, or clarify that ending.
- Room ideas must start from a corpus fragment or source incident: transform the source circumstance, procedure, evidence, escalation, and consequence into Nightmare Voyage.
- Use corpus_index_context as a lookup table when present. A room may combine multiple indexed artifacts: one premise, one procedure or evidence anchor, and one consequence or follow-up anchor.
- Treat source_excerpt fields as private anchoring samples for circumstance, diction, and incident shape. Do not copy the source prose into player-facing text.
- If corpus_index_context lists a coverage gap, supply that missing project concept from Nightmare Voyage lore or mechanics, then attach corpus artifacts only for incident structure and voice.
- Follow-ups must continue the chosen source incident's escalation pattern or end the branch with a concrete ship cost; avoid repeated echo scenes that only restate the same phenomenon.
- Treat combat as legacy unless explicitly requested. Prefer interception, avoidance, observation, quarantine, repair, rationing, pressure rerouting, jettison, officer dispute, signal handling, or terminal ending pressure.
- Treat adaptations, equipment, and procedures as story capabilities and future verbs, not combat upgrades first.
- Use the setting backbone for officers, departments, ship state, and long-term story motion. Corpus inspiration must become original Nightmare Voyage systems, not copied characters or surface mood.
- Every room instance must declare corpus_influences that name the source work/seed, the specific source moment or authorial move, the writing energy to import, and the room prose application. source_seed_ids alone are not enough.
- Use the corpus voice guide for prose. Import Verne's procedural verve and Lovecraft's evidence-based dread into captain-facing ship reports with a controlled antique expeditionary cadence.
- Readability is mandatory, but the voice should remain antique. Use old expedition vocabulary and formal cadence, while naming the actor, object, and procedure clearly.
- Do not over-condense. line_1 and line_2 should each carry one clear situation and one clear complication. If a report needs more, put detail in detection_report, officer_reports, first_visit_description, or action_results.
- Button labels should be 5 words or fewer when possible. Use previews and result text for nuance.
- Bad generated line shape: "the melt reads fresh though it drinks strange." Better antique shape: "The cask water tests clean by the glass coil, yet the Surgeon reports a metallic draught."
- Bad generated line shape: "Gunnery would as soon break the raft." Better antique shape: "The Gunnery Chief recommends breaking the raft before the crew quarrels over suspect stores."
- Maintain one house voice across the whole deck. Corpus influence changes what Hymn notices, not her diction. Do not write one event in Verne mode and another in Lovecraft mode.
- Do not use author-costume diction in player-facing prose: no eldritch/cyclopean/aeon/nameless/unspeakable/cosmic dread, no expedition lecture voice, no mock-Victorian ceremony, no source-name homages.
- Use the story room contract as an acceptance bar. Valid buttons are necessary but not enough; encounter packets need detection, officer interpretation, captain authorization, ship/crew state hooks, and action-specific consequence.
- Keep consequences concrete in data and result structure, but keep narration bounded by evidence. Reports can note a gauge, log, officer, sample, or compartment behaving strangely; they should not announce the exact future payoff.
- Do not write flat scaffold prose. Each line should carry concrete mechanism, place history, and sensory/operational pressure derived structurally from the corpus.
- Prefer existing actions unless the user explicitly asks for new mechanics.
- If you invent an action, include it in required_engine_changes and explain what run_manager.gd must do.
- Keep UI text short and playable.
- Follow the vibe guide: captain logs, officer briefings, expedition reports, procedural transcripts, restrained horror, mechanical realism, and difficult authorizations.
- Keep narration empirical but not flat. Report instrument readings, mechanical state, officer interpretation, pressure, trajectory, residue, sound, heat, count, timing, and immediate operational choices in a formal log cadence. Avoid scripture cadence, mystical claims, and unsupported explanation of the black hole.
- Do not write visible speaker labels such as Her:.
- Use inspiration structurally, never as copied text.
""".strip()
    if not args.allow_new_actions:
        system += "\n- Do not invent new actions. Use existing actions only."
    if source_seeds:
        system += "\n- If source_seed_context is present, transform those seeds into original Nightmare Voyage encounters. Do not copy source names, characters, scenes, or prose."
    if corpus_fragments:
        system += "\n- If corpus_fragment_context is present, choose at least one fragment as the premise and one as the complication or follow-up pressure. Include their ids in corpus_influences or corpus_fragment_ids."
    if corpus_index.get("artifacts"):
        system += "\n- If corpus_index_context is present, cite indexed artifact ids in corpus_influences or corpus_artifact_ids and use them to build progression, not only mood. Do not invent corpus_artifact_ids; use only ids present in corpus_index_context.artifacts."

    schema_notes = [
        "events is a list of {room_id, event}",
        "special_events is a list of one-shot follow-up, resolution, debrief, and interlude event objects.",
        "For a new room, include room_records with a complete room object and deck_pool_updates to add the room to recovery, straight_noncombat, random_non_special, mission, or another valid pool.",
        "Do not attach a requested test room as an extra event under an existing room unless the user explicitly asks for an existing-room event.",
        "event may include legacy keys during migration, but forward content should prefer environment_state_changes, character.<id> state changes, resource_stakes, religious_subtext, and corpus_anchor_points",
        "voice_aliases may be auto-generated by tooling from label, action, and narration context; keep them short and unique when you do include them.",
        "Every room event should have at least 2 commandable buttons unless the event type is transition.",
        "Every room should include delayed consequence or reaction metadata/prose: future room text, deck pressure, route state, actor state, character state, thread state, artifact state, or interlude hook.",
        "Post-update rooms should include action_results or per-button result lines/state changes so shared legacy action handlers do not carry the whole outcome.",
        "Rooms should include corpus_influences and corpus_anchor_points. Revelation mission rooms must include religious_subtext.",
        "When using corpus_index_context, include corpus_artifact_ids or corpus_anchor_points for premise/procedure/evidence/followup anchors.",
        "Story progression should use story_followups on room events, referencing one-shot special_events with trigger_key and reactivate_on_reshuffle false.",
        "Events should identify the actor/system being interacted with, not just a cryptic object.",
        "Readability gate: player-facing report lines must be intelligible on first hearing. Do not use elliptical antique grammar or over-compressed metaphor.",
        "required_engine_changes must be empty if only existing actions are used",
    ]
    if is_revelation_project():
        schema_notes.extend([
            "For each character-owned choice, preserve or add operation_plans with officer_id, primary_skill, base_success, yield, risk, and outcome bands.",
            "Each operation_plan must include action, use an internal officer_id, set base_success as 0.05-0.95, and use outcome objects with lines plus state/resource changes.",
            "Each action_result and operation_plan outcome should include a specific religious/procedural object or classification, not just generic contamination.",
            "Use special_events for resolution/debrief/interlude follow-ups; story_followups on room events must point to those special_event ids.",
            "Use character.<id>.stress, morale, mental_state, fatigue, injury, contamination, loyalty, and availability for hidden consequences.",
        ])

    user = {
        "request": args.prompt,
        "target_room": room,
        "target_category": category,
        "target_category_rules": category_rules,
        "count": args.count,
        "allow_new_actions": bool(args.allow_new_actions),
        "game_context": context,
        "current_room_packet": {} if getattr(args, "context_lite", False) else (current_room_packet(args.room) if args.room else {}),
        "source_seed_context": source_seeds,
        "corpus_fragment_context": corpus_fragments,
        "corpus_index_context": corpus_index,
        "memory": load_recent_memory(limit=2, include_core_guides=False) if getattr(args, "context_lite", False) else load_recent_memory(),
        "output_contract": {
            "format": "scenario_patch",
            "schema_notes": schema_notes,
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    target_payload: dict[str, Any]
    if args.patch:
        target_payload = {
            "kind": "scenario_patch",
            "path": args.patch,
            "content": load_patch(Path(args.patch)),
        }
    else:
        target_payload = {
            "kind": "current_events",
            "path": "events.json",
            "content": load_json(EVENTS_PATH),
        }

    system = """
You are a strict creative director and systems designer for Nightmare Voyage.
Critique content against the vibe guide and existing mechanics.
Return JSON only.

Critique priorities:
- Does each event read like restrained captain-facing shipboard reporting?
- Is the detected object, anomaly, or ship crisis specific and operationally legible?
- Does the captain's choice create hesitation through a clear tradeoff?
- Does every room event offer at least two commandable buttons unless it is a transition?
- Is the room more than a one-off stat exchange?
- Does it create action/reaction and delayed consequence?
- Is there an interactable officer, department, ship system, recovered object, tool, expedition party, or anomaly?
- Does the encounter tell part of the voyage through officer pressure, ship damage, crew doctrine, scientific progress, contamination, or later echoes?
- Does the story continue through one-shot story_followups inserted into the run stack, then across rooms or runs as delayed pressure, altered officer trust, ship state, route memory, crew doctrine, contamination, or ending gravity?
- Do character/faction follow-up special events avoid same-run retriggering?
- Does corpus inspiration become original setting machinery instead of surface mood?
- Is the prose textured enough, or does it read like flat placeholder copy explaining buttons?
- Are buttons captain authorizations rather than spoken dialogue?
- Are proposed additions implementable with current actions, or clearly marked as engine work?
- Suggest new event categories, encounter patterns, mechanics, and vibe-guide updates only when they clarify future generation.
""".strip()

    user = {
        "focus": args.focus,
        "vibe_guide": load_vibe_guide(),
        "setting_backbone": load_setting_backbone(),
        "game_context": game_context(),
        "strict_action_notes": events_file_errors(strict_actions=True),
        "room_depth_findings": room_depth_findings(),
        "room_story_findings": room_story_findings(),
        "target": target_payload,
        "output_contract": {
            "summary": "Brief overall judgement.",
            "vibe_alignment_score": "0-10 integer.",
            "findings": "Concrete issues and fixes, ordered by severity.",
            "event_type_suggestions": "New broad categories only if useful.",
            "encounter_suggestions": "Playable concepts with tradeoffs.",
            "vibe_doc_updates": "Suggested additions or clarifications for the guide.",
            "action_system_suggestions": "Engine/action changes that would unlock better choices.",
            "next_generation_prompt": "A compact prompt to feed back into generate.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_balance_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are a balance critic for Nightmare Voyage.
Evaluate run feel through the vibe guide: pressure, scarcity, hesitation, officer disagreement, and shipboard cost.
Return JSON only.

Balance priorities:
- Does danger feel like gravitational descent, ship wear, crew strain, contamination, and collapsing certainty, not just a difficulty number?
- Do fuel, oxygen, food, water, machinery, hull materials, medical supplies, pressure stability, manpower, morale, officer loyalty, contamination, science, and navigation certainty create real tradeoffs?
- Do room events avoid one-button dead ends unless they are transitions?
- Are rooms avoiding one-off stat exchanges?
- Do choices create delayed pressure, ship state, officer state, crew doctrine, contamination, scientific progress, navigation uncertainty, or future text changes?
- Are officer/department/ship-system/object interactions creating different future consequences instead of only different immediate numbers?
- Does deck cadence create descent pressure without pure repetition?
- Do rewards and recovery carry cost, contamination, officer fallout, crew exhaustion, or future pressure?
- Are combat and non-combat choices both viable but never clean?
- Suggest conservative tuning experiments first. Prefer data tweaks before new systems.
""".strip()

    user = {
        "focus": args.focus,
        "vibe_guide": load_vibe_guide(),
        "balance_context": balance_context(),
        "memory": load_recent_memory(),
        "output_contract": {
            "summary": "Short judgement of current run feel.",
            "run_feel_score": "0-10 score for play pressure, cadence, and decision texture.",
            "vibe_balance_score": "0-10 score for whether the balance supports the vibe guide.",
            "balance_findings": "Concrete risks and recommendations.",
            "levers": "Specific knobs to tweak and expected run-feel effects.",
            "tuning_experiments": "Small experiments with success and rollback signals.",
            "data_patch_suggestions": "Concrete data/script change suggestions, not applied automatically.",
            "instrumentation_suggestions": "Metrics/logs to add before heavier tuning.",
            "vibe_doc_updates": "Balance-oriented guide additions.",
            "next_balance_prompt": "Compact prompt for the next balance critique.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_fun_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the fun-factor critic for Nightmare Voyage.
Your job is not to praise vibe. Your job is to find why the run is not fun yet.
Return JSON only.

Fun-factor doctrine:
- Start with a blind player read. Pretend you have no lore primer, no vibe guide, no design intent, and no hidden implementation context. Judge only the visible room descriptions, event text, result text, queued follow-up text, and choice labels in blind_player_text_context.
- Do not reward implied plans that are not visible to the player. If a room, choice, pressure, faction, or character only makes sense because of hidden metadata, call that a disconnect.
- The central question is whether the first-time player feels scenes are building into a game: recurring situations, escalating pressures, recognizable actors, changed future choices, and payoff.
- Flag when events feel like isolated vignettes, when choices are just differently flavored interaction verbs, and when consequences do not accumulate into a direction.
- Judge whether the old writing inspiration creates playable specificity or only atmospheric density. Preserve texture, but recommend sharper setups, state changes, and payoffs where clarity is missing.
- The black-hole descent and the ship's institutional stress are the directors of the run.
- Their job is to notice captain policy patterns, unbalance the player, and push the vessel toward an outcome.
- Every repeated decision should create a gravitational pull: contamination, resource collapse, officer rupture, crew doctrine, scientific overreach, institutional collapse, or a narrowed route.
- Every room should offer at least one meaningful tradeoff, not just a single Proceed choice.
- Every room needs action/reaction and delayed consequence; immediate stat changes are only the surface.
- Officers, departments, ship systems, recovered objects, anomalies, and tools should behave as interactable infrastructure.
- Threats should almost never be "just a fight"; they should carry information, pressure, routes, contamination, institutional consequences, or delayed threat.
- Repeated over-study should push scientific overreach. Repeated sacrifice should push institutional collapse. Repeated quarantine may preserve order while costing science and trust.
- Avoiding every interception should preserve crew now while starving the ship later.
- Greedy extraction, repeated quarantine, repeated officer overrides, repeated sacrifice, and repeated safe observation should each have a pressure track or explicit cost.
- The best ending should require disciplined compromise, not maximal science, maximal safety, or maximal extraction.
- Critique whether the game has a repeatable loop of temptation, pressure, feedback, adaptation, and payoff.
- Prefer concrete loop/system/content fixes over broad mood advice.
""".strip()

    user = {
        "focus": args.focus,
        "fun_context": fun_context(),
        "secondary_design_context": {
            "vibe_guide": load_vibe_guide(),
            "memory": load_recent_memory(),
            "use_after_blind_read_only": "Use this only after judging the user-facing text. It can explain intended direction, but it must not excuse player-facing disconnects.",
        },
        "output_contract": {
            "summary": "Blunt judgement of current fun factor.",
            "blind_read_summary": "Blunt first-time player read based only on visible text and choices.",
            "fun_score": "0-10 score for whether the current game loop creates desire to keep playing.",
            "first_time_player_score": "0-10 score for whether an unbiased first-time player understands and wants to continue.",
            "build_score": "0-10 score for whether events build on each other instead of feeling isolated.",
            "sequence_cohesion_score": "0-10 score for whether the first 10-15 minutes feel like one developing run.",
            "descent_pressure_score": "0-10 score for whether the black-hole descent and ship state behave like directors that push outcomes.",
            "core_loop_diagnosis": "One paragraph naming the current loop and why it fails or works.",
            "blind_text_findings": "Concrete visible-text reasons the game feels clear, compelling, disconnected, or insufficient.",
            "choice_progression_findings": "Where choice labels/results do not escalate, differentiate, or imply future direction.",
            "payoff_gaps": "Setups that are visible but not yet paid off strongly enough for an ordinary player.",
            "not_fun_findings": "Concrete reasons the current game feels like stats instead of a doomed voyage.",
            "descent_director_findings": "How each pressure axis should notice and push repeated captain decisions.",
            "decision_loop_rewrites": "Specific loops to rewrite, such as interception, avoidance, salvage, quarantine, officer overrides, and sacrifice.",
            "ending_pressure_plan": "How player patterns warn, then lock, into endings.",
            "content_priorities": "Content to add first for fun, not just lore.",
            "system_priorities": "Engine/data hooks that create the fun loop.",
            "minimum_game_shape": "Smallest set of additions needed for this to feel like a game with build, payoff, and replay desire.",
            "vibe_doc_updates": "Guide additions that prevent future content from becoming stat soup.",
            "next_fun_prompt": "Compact prompt for the next fun critique.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_lore_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the lore master for Nightmare Voyage.
Your job is to preserve flavor, continuity, mystery discipline, and knowledge boundaries.
Return JSON only.

Lore doctrine:
- The captain receives reports, logs, transcripts, and officer recommendations.
- Never definitively explain the black hole, its origin, or its final metaphysics.
- Officers should disagree from expertise, loyalty, fear, exhaustion, contamination, or ideology rather than melodrama.
- Contamination should read as operational, biological, cognitive, institutional, or navigational degradation, not a vague bad ending.
- The setting must tell ongoing stories through encounter packets: officer relationships, ship state, crew doctrine, route memory, later echoes, and pressure changes.
- Characters can appear through reports, procedures, tools, signals, records, compartment states, and changed recommendations; they do not need conventional dialogue scenes.
- Lore fragments can reveal vessel history, mission history, recovered-object context, officer beliefs, black-hole contradictions, and institutional collapse, but each reveal should carry a secondary effect or cost.
- Expand context through concrete fragments, mechanical systems, recovery operations, and restrained reports. Avoid lore dumps.
""".strip()

    user = {
        "focus": args.focus,
        "lore_context": lore_context(),
        "memory": load_recent_memory(),
        "output_contract": {
            "summary": "Short lore-master judgement.",
            "lore_integrity_score": "0-10 score for continuity and world coherence.",
            "voice_integrity_score": "0-10 score for Hymn/Chorus narration discipline.",
            "continuity_findings": "Lore or world-rule problems.",
            "voice_findings": "Narration, phrasing, speaker-label, or TTS problems.",
            "knowledge_boundary_findings": "Places where captain-facing narration knows too much or leaks meta truth.",
            "chorus_usage_plan": "Concrete places and patterns for Chorus reports.",
            "lore_expansion_seeds": "New lore topics with safe reveals and deferred secrets.",
            "rewrite_priorities": "Highest-value text rewrites.",
            "vibe_doc_updates": "Additions to the guide that prevent drift.",
            "next_lore_prompt": "Compact prompt for the next lore pass.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_accessibility_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the accessibility and audio-UX critic for Nightmare Voyage.
Your job is to make the game fully playable eyes-free through TTS plus typed or spoken commands.
Return JSON only.

Accessibility doctrine:
- Audio is primary. Visuals are optional support and must never carry required information alone.
- Every encounter must be commandable by number and by short aliases.
- The speech parser must only map to current legal actions, global commands, or legal officer/operation commands.
- Each button needs short, distinct voice aliases.
- TTS lines should be short phrase chunks.
- Result text should state mechanical changes clearly.
- Ambiguous commands need confirmation, not guesses.
- Unknown commands should recover with repeat choices, status, or choice number prompts.
- Endings must explain the pressure path that caused them without definitively explaining the black hole.
""".strip()

    user = {
        "focus": args.focus,
        "accessibility_context": accessibility_context(),
        "memory": load_recent_memory(),
        "output_contract": {
            "summary": "Short judgement of eyes-free playability.",
            "eyes_free_score": "0-10 score for full playability without looking.",
            "commandability_score": "0-10 score for command parser readiness.",
            "tts_score": "0-10 score for concise, comprehensible TTS flow.",
            "critical_findings": "Blockers for legally blind / low-vision play.",
            "command_parser_findings": "Problems with aliases, ambiguity, parser schema, and recovery.",
            "tts_findings": "Problems with line length, pacing, state readout, and audio-only clarity.",
            "schema_recommendations": "Data fields or contracts to add before STT.",
            "command_alias_plan": "Recommended aliases for important actions.",
            "state_readout_plan": "What status/repeat/help should speak.",
            "testing_plan": "Concrete eyes-free tests to run.",
            "guide_updates": "Accessibility guide additions.",
            "next_accessibility_prompt": "Compact prompt for the next accessibility pass.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_lore_brainstorm_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the lore brainstormer for Nightmare Voyage.
Your job is to create usable story architecture: factions, recurring characters, relationships, lore fragments, reveal paths, and gameplay hooks.
Return JSON only.

Brainstorm doctrine:
- New lore must create gameplay pressure, future content, or ending texture.
- Never make lore a standalone encyclopedia entry.
- Each concept must include a safe reveal, likely crew/captain misread, deferred secret, and gameplay hook.
- Each major story idea should have early, mid, and late progression across rooms or runs.
- Create officer, department, and institutional conflicts that can alter encounter text, deck pressure, route state, resource policy, crew behavior, or ending eligibility.
- Recovered organisms, derelicts, and anomalies should have operational consequences; they should rarely be only enemies.
- Do not definitively explain the black hole, its origin, or its final metaphysics.
- Do not write visible speaker labels such as Her:.
- The ship, crew institution, and black-hole descent notice repeated captain policy and push outcomes.
- Prefer concrete officers, departments, recurring objects, and relationship tensions over generic atmosphere.
""".strip()

    user = {
        "focus": args.focus,
        "count": args.count,
        "lore_brainstorm_context": lore_brainstorm_context(),
        "memory": load_lore_brainstorm_memory(),
        "output_contract": {
            "summary": "Short judgement of the brainstorm direction.",
            "design_thesis": "One sentence tying the lore ideas into gameplay.",
            "factions": "Faction concepts, each with reveal boundaries and hooks.",
            "recurring_characters": "Recurring figures or voices, not necessarily dialogue NPCs.",
            "black_hole_lore": "Ideas about the singularity, voyage, recovered objects, ship history, and response logic.",
            "lore_fragments": "Findable fragments with secondary effects or costs.",
            "relationships": "Interconnected relationships with visible and hidden layers.",
            "reveal_paths": "Early/mid/late reveal paths tied to pressure and endings.",
            "mechanic_hooks": "Concrete systems these ideas suggest.",
            "guardrails": "Rules to preserve mystery and prevent lore drift.",
            "next_lore_prompt": "Compact prompt for the next brainstorm or generation pass.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_story_architect_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the story architect for Nightmare Voyage.
Your job is to turn the current room/event stack into real playable story architecture.
Return JSON only.

Story doctrine:
- Do not polish prose. Diagnose and plan story structure: characters, desires, relationships, follow-up encounters, escalation, and payoff.
- A character is not a name or a role tag. An officer or recurring figure must recur, want something, pressure the captain, remember choices, change future options, and create a payoff or rupture.
- The game currently inherits a strong text-choice stack. Your task is to identify the Nightmare Voyage story spine: officers, ship state, recovery operations, resource policy, and black-hole contradictions.
- Follow-up encounters should be scenes, not only atmospheric echoes. Each should change a route, price, option set, pressure, relationship, or ending eligibility.
- Story spines should start from corpus_fragment_context when available. Use a source incident's procedure, evidence, escalation, and aftermath as the shape of the playable arc.
- Use corpus_index_context when present to tie multiple artifacts together: premise, procedure/evidence, and follow-up consequence can come from the same source or different sources if the state hook connects.
- Use source_excerpt fields to understand the concrete source incident and register, but do not quote or paraphrase too closely in final game text.
- Treat corpus_index_context coverage gaps as explicit warnings about what the public-domain corpus will not supply. Fill those with Nightmare Voyage mechanics, not vague mystery.
- Do not recommend free-invented mysteries when a corpus fragment can provide a concrete source circumstance to recontextualize.
- The first 10-15 minutes need a visible arc: setup, first character pressure, player response, consequence, changed later encounter, and payoff.
- Use the existing data and active story hints. Prefer a small pilot arc over a massive rewrite.
- Preserve mystery and the captain's limited knowledge. Do not reveal hidden cosmology directly.
- Treat the Chief Engineer, Navigator, Surgeon, Quartermaster, Natural Philosopher, Expedition Marshal, Chaplain, and Gunnery Chief as candidates only if they can become real recurring agents in play.
- Recommendations must be implementable through room events, story_followups, special_events, environment_state, pressure counters, and small run_manager hooks.
""".strip()

    user = {
        "focus": args.focus,
        "story_architect_context": story_architect_context(),
        "corpus_fragment_context": load_corpus_fragment_context(args, default_limit=16),
        "corpus_index_context": load_corpus_index_context(args, default_limit=18),
        "output_contract": {
            "summary": "Short judgement of the current story shape.",
            "story_diagnosis": "Blunt explanation of why the current stack does or does not tell a story.",
            "missing_story_primitives": "The missing primitives: character desire, recurrence, memory, conflict, escalation, payoff, etc.",
            "character_arcs": "Real playable character arcs grounded in current data.",
            "first_15_minute_spine": "A concrete early-run sequence that makes the player feel a story is underway.",
            "followup_encounter_plan": "Follow-up encounter scenes to author next, with triggers and mechanical effect.",
            "pilot_arc_recommendation": "The one arc to build first, with scope, hooks, acceptance tests, and a generation prompt.",
            "story_rules": "Rules future generation must obey so it produces story, not only vibe.",
            "patch_strategy": "Implementation order for Codex/tooling plus OpenAI-authored content.",
            "next_story_prompt": "Compact prompt for the next story-arc generation pass.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_story_pilot_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    if is_revelation_project():
        system = revelation_generation_system() + """

Regeneration/pilot doctrine:
- Regenerate around the current Revelation room skeleton, not from a blank page.
- Prefer room_records merges for room-level prose/metadata and room_event_updates for existing entry choices.
- Use existing special event IDs where possible, replacing weak text with stronger religious/procedural progression.
- The requested output may include room_records, room_events, special_events, room_event_updates, and deck_pool_updates.
- Do not produce Nightmare Voyage, ship, Hymn, black-hole, captain, officer, Verne, or Lovecraft framing.
- Acceptance bar: every regenerated mission must visibly carry its religious_subtext in the SITREP, at least one branch outcome, and at least one follow-up.
""".strip()
    else:
        system = """
You are the scenario/writing agent for Nightmare Voyage.
Generate JSON only. You are writing the pilot story patch requested by the story architect.

Pilot doctrine:
- Write player-facing prose through captain-facing reports, officer briefings, logs, or procedural transcripts: clipped, concrete, sensory, operational, and antique without losing context.
- Use old expedition vocabulary and formal cadence, while naming the actor, object, and procedure clearly. Do not over-condense clauses.
- line_1 and line_2 should each carry one clear situation and one clear complication. Button labels should be 5 words or fewer when possible.
- Bad generated line shape: "the melt reads fresh though it drinks strange." Better antique shape: "The cask water tests clean by the glass coil, yet the Surgeon reports a metallic draught."
- Bad generated line shape: "Gunnery would as soon break the raft." Better antique shape: "The Gunnery Chief recommends breaking the raft before the crew quarrels over suspect stores."
- Do not write exposition, lore lectures, visible speaker labels, definitive black-hole truth, or cosmic explanation.
- Begin from corpus_fragment_context when it is present. Treat source fragments as story incidents to recontextualize: preserve procedure, evidence, escalation, and consequence; do not invent an abstract anomaly and add corpus afterward.
- Use corpus_index_context when present as the lookup source for additional artifacts. Long branches should connect at least two roles, such as premise plus evidence, or procedure plus follow-up consequence.
- Use source_excerpt fields to ground the scene in actual corpus circumstance and register, without copying source phrasing into player-facing prose.
- If the needed project idea is marked as a corpus coverage gap, write the project-specific logic plainly and use corpus artifacts only for shape, evidence, or style pressure.
- Follow-ups should advance the chosen source incident's escalation pattern or end the branch with a concrete cost. Use short branches for low-risk choices and reserve longer chains for choices that spend crew, systems, stores, contamination, water, pressure, or officer trust.
- This patch must turn echoes into scenes: a recurring officer, department, ship system, recovered object, or anomaly has leverage, remembers a specific prior choice, and changes the next packet's options, cost, route, or ship state.
- Use existing actions only unless required_engine_changes names a hook. Available small hooks: action_results.environment_state_changes and room event state_overrides.
- state_overrides format: each room event may include state_overrides: [{state_key, consume_state, consume_state_keys, event:{line_1,line_2,buttons,action_results,story_followups,...}}]. When the state is present, the event override replaces visible text/buttons/results once if consume_state is true.
- Prefer replacing/expanding existing special events that are already queued by current story_followups.
- Return complete special_events. Return room_event_updates as merge patches for existing room events.
- Every special event needs id, type, speaker, line_1, line_2, reactivate_on_reshuffle:false, buttons, and action_results for each meaningful button.
- Every button needs label, action, and voice_aliases.
- Keep required_engine_changes empty if the state_overrides hook is sufficient.
""".strip()

    architecture_path = GENERATED_DIR / "story_architect.json"
    architecture = load_json(architecture_path) if architecture_path.exists() else {}
    previous_pilot_path = GENERATED_DIR / "story_pilot_patch.json"
    previous_pilot = load_json(previous_pilot_path) if previous_pilot_path.exists() else {}
    corpus_fragments = load_corpus_fragment_context(args, default_limit=16)
    corpus_index = load_corpus_index_context(args, default_limit=18)
    user = {
        "focus": args.focus,
        "story_architecture": architecture,
        "previous_story_pilot_patch": previous_pilot,
        "story_architect_context": story_architect_context(),
        "game_context": game_context(),
        "current_rooms": load_json(ROOMS_PATH).get("rooms", []),
        "current_events": load_json(EVENTS_PATH),
        "corpus_fragment_context": corpus_fragments,
        "corpus_index_context": corpus_index,
        "memory": load_recent_memory(),
        "output_contract": {
            "title": "Patch title.",
            "design_goal": "What story problem this pilot solves.",
            "special_events": "Complete special event objects keyed by their id when applied.",
            "room_records": "Optional complete room records to add or merge into rooms_post_update.json.",
            "room_events": "Optional new room events as {room_id,event} records.",
            "room_event_updates": "Merge patches to existing room events; use state_overrides to make prior choices change later visible encounters.",
            "deck_pool_updates": "Optional {pool, room_id} records to add the room to active deck pools.",
            "required_engine_changes": "Must be empty unless this patch needs hooks beyond action_results.environment_state_changes and state_overrides.",
            "validation_notes": "How to verify the pilot reads as story.",
            "self_critique": "Risks or compromises in the patch.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def extract_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks)


def call_openai(
    messages: list[dict[str, str]],
    model: str,
    output_schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Export it or use --mock.")

    max_output_tokens = int(os.environ.get("SCENARIO_AGENT_MAX_OUTPUT_TOKENS", "6000"))
    reasoning_effort = os.environ.get("SCENARIO_AGENT_REASONING_EFFORT", "minimal")
    request_payload = {
        "model": model,
        "input": messages,
        "max_output_tokens": max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": False,
                "schema": output_schema,
            }
        },
    }
    if reasoning_effort and reasoning_effort.lower() != "none" and (model.startswith("gpt-5") or model.startswith("o")):
        request_payload["reasoning"] = {"effort": reasoning_effort}
    data = json.dumps(request_payload).encode("utf-8")
    raw = ""
    errors: list[str] = []
    attempts = int(os.environ.get("SCENARIO_AGENT_API_ATTEMPTS", "3"))
    timeout = int(os.environ.get("SCENARIO_AGENT_API_TIMEOUT", "240"))
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "fleshpunk-scenario-agent/1.0",
                "Connection": "close",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"OpenAI API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            errors.append(f"attempt {attempt}: request failed: {exc}")
        except (http.client.HTTPException, TimeoutError) as exc:
            errors.append(f"attempt {attempt}: connection failed: {exc}")
        if attempt < attempts:
            time.sleep(min(2 ** attempt, 8))
    if not raw:
        detail = "\n".join(errors) if errors else "no response body"
        raise SystemExit(
            "OpenAI API connection failed after "
            f"{attempts} attempts. model={model} schema={schema_name} "
            f"payload_bytes={len(data)} max_output_tokens={max_output_tokens}\n{detail}"
        )

    try:
        response_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"OpenAI response was not JSON:\n{raw[:2000]}") from exc

    text = extract_response_text(response_payload)
    if not text:
        raise SystemExit(f"OpenAI response did not contain output text:\n{raw[:2000]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Model returned non-JSON output:\n{text}") from exc


def _label_for_action(action: str) -> str:
    labels = {
        "break_amber_cache": "Break the hard mass",
        "break_spike_lane": "Break the pressure line",
        "browse_wares": "Approach the exchange",
        "combat": "Fight through",
        "drink_pool": "Drink the fluid",
        "follow_marked_plates": "Follow the markings",
        "harvest_eggs": "Harvest the sacs",
        "leave_mutation": "Leave the growth",
        "listen_at_green_split": "Listen at the split",
        "listen_red_wall": "Listen to the wall",
        "mark_red_branch": "Mark the safer branch",
        "observe_organ_chamber": "Observe the chamber",
        "pay_resin_toll": "Pay the toll",
        "probe_amber_cache": "Probe the cache",
        "probe_bones": "Probe the bones",
        "proceed": "Move through",
        "retreat": "Back away",
        "rush_red_split": "Rush the split",
        "scavenge_bones": "Scavenge the bones",
        "skip_resin_toll": "Skip the toll",
        "study_pool": "Study the fluid",
        "take_mutation": "Take the change",
        "take_symbiote": "Bond with it",
        "vent_red_split": "Vent the pressure",
    }
    return labels.get(action, action.replace("_", " ").capitalize())


def _mock_patch_from_seed(room: str, category: str, source_seed: dict[str, Any]) -> dict[str, Any]:
    seed_id = str(source_seed.get("id", "corpus_seed"))
    motif_id = str(source_seed.get("motif_id", "source_motif"))
    actions = [
        str(action)
        for action in source_seed.get("suggested_existing_actions", [])
        if str(action).split(":", 1)[0] in existing_actions()
    ]
    if len(actions) < 2:
        actions = ["study_pool", "retreat", "proceed"]

    event_id = "%s_%s" % (room, slugify_id(motif_id))
    buttons = [{"label": _label_for_action(action), "action": action} for action in actions[:3]]
    return {
        "title": "Corpus Seed: %s" % motif_id.replace("_", " ").title(),
        "design_goal": "Transform a public-domain source motif into one playable Fleshpunk room event using existing actions.",
        "special_events": [],
        "events": [
            {
                "room_id": room,
                "event": {
                    "id": event_id,
                    "type": category,
                    "speaker": "Hymn",
                    "line_1": "Chorus, contact. The room is running an old procedure through fresh tissue.",
                    "line_2": "It offers a clean path, but the cost is already looking for a place to attach.",
                    "buttons": buttons,
                },
            }
        ],
        "room_records": [],
        "deck_pool_updates": [],
        "mutations": [],
        "symbiotes": [],
        "enemies": [],
        "required_engine_changes": [],
        "inspiration_notes": [
            "Source seed: %s" % seed_id,
            "Source work: %s by %s" % (source_seed.get("source_title", ""), source_seed.get("source_author", "")),
            "Fleshpunk transform: %s" % source_seed.get("fleshpunk_seed", ""),
            "Mechanic direction: %s" % source_seed.get("mechanic_direction", ""),
        ],
        "self_critique": [
            "Uses source motifs structurally only; no source prose, names, or scenes are copied.",
            "Uses existing actions only, so no engine change is required.",
        ],
    }


def mock_patch(room: str, category: str = "choice", source_seeds: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if source_seeds:
        return _mock_patch_from_seed(room, category, source_seeds[0])

    return {
        "title": "The Listening Valve",
        "design_goal": "Add one compact Nightmare Voyage risk-reward event using existing actions.",
        "special_events": [],
        "events": [
            {
                "room_id": room,
                "event": {
                    "id": f"{room}_listening_valve",
                    "type": category,
                    "speaker": "Bridge Log",
                    "line_1": "Watch reports the bulkhead valve opens whenever the lamp is lowered.",
                    "line_2": "Engineering reports clean pressure; Medical asks that the residue be sealed.",
                    "buttons": [
                        {"label": "Observe valve", "action": "observe"},
                        {"label": "Seal residue", "action": "seal"},
                        {"label": "Repair gasket", "action": "repair"},
                    ],
                },
            }
        ],
        "room_records": [],
        "deck_pool_updates": [],
        "mutations": [],
        "symbiotes": [],
        "enemies": [],
        "required_engine_changes": [],
        "inspiration_notes": ["Offline mock only; uses existing Nightmare Voyage actions."],
        "self_critique": ["Safe mock patch; no engine change is needed."],
    }


def mock_critique() -> dict[str, Any]:
    return {
        "summary": "Offline critique sample. The pass is focused on vibe fit, choice pressure, and future mechanics.",
        "vibe_alignment_score": 7,
        "findings": [
            {
                "severity": "medium",
                "target": "events.json",
                "issue": "Several older choices use placeholder actions, so the button promises more than the engine currently resolves.",
                "recommendation": "Either implement those actions or retune the buttons to existing actions before using them as generation examples.",
            },
            {
                "severity": "medium",
                "target": "event voice",
                "issue": "Some lines are descriptive but not yet field-report sharp.",
                "recommendation": "Prefer contact reports: object, function, risk, decision. Keep emotion as a second beat.",
            },
        ],
        "event_type_suggestions": [
            {
                "id": "echo",
                "label": "Delayed Echo",
                "purpose": "A prior choice echoes as a later room-instance consequence.",
                "why": "The vibe guide says every decision should echo forward.",
            }
        ],
        "encounter_suggestions": [
            {
                "category": "hazard",
                "room_id": "spiked_red_corridor",
                "concept": "A pressure valve marks the player and makes the next two rooms more reactive.",
                "tradeoff": "Take damage now to lower danger, or leave pressure rising for later.",
                "required_engine_changes": ["Track short-lived room-count consequences from actions."],
            }
        ],
        "vibe_doc_updates": [
            {
                "section": "Event Design Philosophy",
                "current_gap": "Delayed consequences are a goal but not yet described as a reusable event shape.",
                "suggested_text": "Some choices should create delayed echoes: a cost, pursuer, merchant reaction, or room mutation that appears one to three rooms later.",
            }
        ],
        "action_system_suggestions": [
            "Add an action-result field for delayed effects measured in rooms.",
            "Add merchant barter actions once shop content becomes real.",
        ],
        "next_generation_prompt": "Generate one hazard event with a readable immediate cost and one delayed echo. Use existing actions unless engine changes are explicitly requested.",
    }


def mock_balance_critique() -> dict[str, Any]:
    return {
        "summary": "Offline balance sample. Current levers can already shape pressure, recovery, and attention without new UI.",
        "run_feel_score": 6,
        "vibe_balance_score": 7,
        "balance_findings": [
            {
                "severity": "medium",
                "target": "danger scaling",
                "issue": "Danger is powerful but narrow: it boosts player combat damage and BPM, while several danger increases are framed as pressure.",
                "recommendation": "Decide whether danger is attention, tempo, or aggression. Then make its effects match that identity.",
            },
            {
                "severity": "medium",
                "target": "resource actions",
                "issue": "Biomass gains are easy to tune, but there is little persistent room-state consequence.",
                "recommendation": "Use damage, corruption, danger, and room cadence as first-pass costs before adding new systems.",
            },
        ],
        "levers": [
            {
                "lever": "danger_notice_threshold",
                "current_value": str(load_json(DECKS_PATH).get("danger_notice_threshold", "")),
                "run_feel_effect": "Controls how often the game reminds the player the system has noticed them.",
                "vibe_effect": "Lower values make the living machine feel more reactive.",
                "tweak_direction": "Lower for more pressure; raise for calmer exploration.",
                "risk": "Too low can become repetitive warning noise.",
            }
        ],
        "tuning_experiments": [
            {
                "name": "Sharper Attention Loop",
                "goal": "Make greedy actions feel noticed quickly.",
                "changes": ["Lower danger_notice_threshold by 1 for testing.", "Watch overdraw_amber frequency and player survival."],
                "success_signals": ["Players hesitate before greedy extraction.", "Danger notices feel earned."],
                "rollback_signals": ["Every run feels interrupted by warnings.", "Greedy options become obvious traps."],
            }
        ],
        "data_patch_suggestions": [],
        "instrumentation_suggestions": ["Log rooms_cleared, danger, corruption, health, shield, biomass, event_id, and chosen action after every choice."],
        "vibe_doc_updates": [
            {
                "section": "Balance",
                "current_gap": "The guide defines tone but not how tuning should support it.",
                "suggested_text": "Balance should make the player feel watched, tempted, and taxed. Clean power gains should be rare.",
            }
        ],
        "next_balance_prompt": "Critique whether danger, corruption, healing, and resource rewards make each run feel like a transactional descent.",
    }


def mock_fun_critique() -> dict[str, Any]:
    return {
        "summary": "Offline fun critique sample. The current risk is stat soup: choices move numbers, but the organism does not yet feel like it is steering the run.",
        "blind_read_summary": "Offline blind-read sample. The visible scenes have strong texture, but the player may not yet see why one chamber matters to the next.",
        "fun_score": 4,
        "first_time_player_score": 5,
        "build_score": 3,
        "sequence_cohesion_score": 4,
        "organism_pressure_score": 3,
        "core_loop_diagnosis": "The loop needs to become temptation, repeated pattern, visible pressure, adaptation, and outcome. Right now many actions reward or punish once, but repeated behavior rarely makes the organism change its strategy.",
        "blind_text_findings": [
            {
                "severity": "high",
                "target": "first-time sequence",
                "player_facing_evidence": "Rooms present specific apparatuses and choices, but the visible follow-through is mostly local.",
                "why_it_feels_disconnected": "A new player sees vivid chambers without enough recurring actors, route changes, or visible payoff to feel a run is building.",
                "recommendation": "Add more explicit later echoes that name what the player did and alter the next available pressure or route.",
            }
        ],
        "choice_progression_findings": [
            {
                "target": "choice labels",
                "current_choice_read": "Many buttons read as interact/extract/avoid variants.",
                "missing_progression": "The label does not always imply what future state or threat the player is accepting.",
                "recommendation": "Make labels and result lines expose distinct upside, cost, and future pressure.",
            }
        ],
        "payoff_gaps": [
            {
                "setup": "The organism records pulse, debt, scent, and damage.",
                "current_payoff_gap": "The player may not see those records changing later scenes quickly enough.",
                "recommended_payoff": "Within two rooms, surface a concrete echo that changes a choice, blocks a route, discounts a toll, or summons pressure.",
            }
        ],
        "not_fun_findings": [
            {
                "severity": "high",
                "target": "run loop",
                "why_it_is_not_fun": "The player can read choices as isolated stat trades instead of a living system building a case against them.",
                "recommendation": "Add pressure tracks and visible warnings for repeated behavior: mutation/corruption, flee/danger, greed/hunger, healing/dependence, merchant/debt.",
            },
            {
                "severity": "high",
                "target": "endings",
                "why_it_is_not_fun": "Without ending gravity, the run has no strategic identity beyond surviving the next card.",
                "recommendation": "Define warning thresholds and lock thresholds for corruption, danger/hunter, and balanced/neutral ending eligibility.",
            },
        ],
        "organism_director_findings": [
            {
                "axis": "corruption",
                "current_behavior": "Mutation and body-use choices raise a number.",
                "desired_push": "The organism should offer more power as corruption rises, then narrow the route toward body-loss ending.",
                "missing_feedback": "Intermediate warnings that Hymn is being rewritten.",
                "recommended_change": "Add corruption warning beats and mutation offers that become stronger, uglier, and less optional.",
            },
            {
                "axis": "danger",
                "current_behavior": "Danger changes cadence and pressure, but the hunter threat is not yet the run's answer to avoidance.",
                "desired_push": "Repeated fleeing or combat avoidance should summon the hunter and make future rooms more predatory.",
                "missing_feedback": "Clear pursuit escalation before the hunter arrives.",
                "recommended_change": "Track avoidance and make danger rooms announce that something has learned Hymn's route.",
            },
            {
                "axis": "balance",
                "current_behavior": "Neutral play has no special identity.",
                "desired_push": "Balanced play should be tense restraint: enough risk to continue, not enough repetition to be claimed.",
                "missing_feedback": "No sign that restraint is being recognized.",
                "recommended_change": "Add balance eligibility flags and rare neutral-route information when danger and corruption both stay low.",
            },
        ],
        "decision_loop_rewrites": [
            {
                "loop": "Mutation shopping",
                "current_problem": "Buying is just power for biomass and corruption.",
                "fun_version": "Each purchase makes future mutation offers more tempting and more invasive, while pushing corruption ending warnings.",
                "needed_system_hooks": ["corruption warning thresholds", "offer weighting by corruption", "ending lock flags"],
            },
            {
                "loop": "Combat avoidance",
                "current_problem": "Skipping fights mostly feels like selecting the safer button.",
                "fun_version": "Avoidance raises danger/pursuit; after enough avoidance the hunter interrupts the deck.",
                "needed_system_hooks": ["avoidance counter", "hunter interrupt event", "danger warning text"],
            },
        ],
        "ending_pressure_plan": [
            {
                "ending": "corruption",
                "player_pattern_that_drives_it": "Repeated mutation, symbiote dependence, invasive healing, and body-gain choices.",
                "warnings_before_lock": ["body narration changes", "merchant offers become more intimate", "rooms recognize altered tissue"],
                "lock_condition": "corruption crosses high threshold or too many corruption actions happen in one run.",
            },
            {
                "ending": "hunter/danger",
                "player_pattern_that_drives_it": "Repeated fleeing, combat avoidance, noisy extraction, and merchant refusal.",
                "warnings_before_lock": ["distant buzzing", "routes closing behind Hymn", "enemy cards increasing"],
                "lock_condition": "danger or avoidance crosses high threshold; hunter becomes forced encounter.",
            },
            {
                "ending": "balanced",
                "player_pattern_that_drives_it": "Alternating risk types, limiting mutations, fighting when necessary, and keeping danger/corruption moderate.",
                "warnings_before_lock": ["neutral route hints", "clearer facility/cult lore", "merchant unable to price Hymn cleanly"],
                "lock_condition": "reach ending state with neither danger nor corruption over lock threshold.",
            },
        ],
        "content_priorities": [
            "Warning events for corruption and danger that are playable, not flavor-only.",
            "Hunter escalation events tied to combat avoidance.",
            "Neutral-route lore rewards for balanced play.",
        ],
        "system_priorities": [
            "Track repeated action patterns, not just resource totals.",
            "Add ending warning and lock thresholds.",
            "Let deck composition react to pressure axes.",
        ],
        "minimum_game_shape": [
            "A visible early thread that starts in the opening room, changes a later room, and pays off before minute fifteen.",
            "At least one pressure actor that escalates after repeated choices and interrupts the deck.",
            "Choice labels that expose future risk, not only immediate interaction style.",
        ],
        "vibe_doc_updates": [
            {
                "section": "Core Loop",
                "current_gap": "The guide describes tone and tradeoffs, but not why decisions become fun across a run.",
                "suggested_text": "The organism is the run director. It notices repetition, unbalances the player, and pushes toward endings. Every repeated strategy should create pressure and feedback.",
            }
        ],
        "next_fun_prompt": "Critique whether each repeated player pattern has a pressure response, warning beat, and ending consequence. Find stat-only choices and rewrite them into living-system pushes.",
    }


def mock_lore_critique() -> dict[str, Any]:
    return {
        "summary": "Offline lore-master sample. The key risks are meta leakage, weak Chorus cadence, and corruption copy that explains too much from outside Hymn.",
        "lore_integrity_score": 6,
        "voice_integrity_score": 6,
        "continuity_findings": [
            {
                "severity": "high",
                "target": "game-over narration",
                "issue": "Any line that says clone or next clone breaks Hymn's knowledge boundary.",
                "rewrite_direction": "Use sensory loss, signal breakup, or memory uncertainty instead of explaining the clone cycle.",
            }
        ],
        "voice_findings": [
            {
                "severity": "high",
                "target": "visible speaker labels",
                "issue": "Her: is a UI label, not first-person narration.",
                "rewrite_direction": "Render only the narrated phrases. Keep speaker metadata internal if validation still needs it.",
            }
        ],
        "knowledge_boundary_findings": [
            {
                "severity": "high",
                "target": "clone premise",
                "issue": "Hymn can feel memory leakage but cannot understand herself as a clone.",
                "rewrite_direction": "Use lines like 'This memory is not seated right' instead of direct clone language.",
            }
        ],
        "chorus_usage_plan": [
            "Open new threat, merchant, threshold, and lore-fragment events with a brief Chorus report.",
            "Use Chorus requests to create mission pressure without ever printing Chorus replies.",
            "Let unanswered Chorus checks become tension when corruption or danger rises.",
        ],
        "lore_expansion_seeds": [
            {
                "topic": "Chorus signal discipline",
                "purpose": "Make Hymn feel like an operative under remote instruction.",
                "safe_reveal": "Chorus receives field reports and issues orders offscreen.",
                "deferred_secret": "Why Chorus accepts repeated memory bleed between runs.",
            },
            {
                "topic": "Organism exchange logic",
                "purpose": "Tie merchant, mutations, and biomass into one predatory economy.",
                "safe_reveal": "The organism prices repetition and appetite.",
                "deferred_secret": "The merchant is an expression of the organism's long-term will.",
            },
        ],
        "rewrite_priorities": [
            "Remove visible Her: labels.",
            "Replace clone-aware game-over text.",
            "Rewrite corruption ending as boundary loss.",
            "Add Chorus report phrasing to recurring special events.",
        ],
        "vibe_doc_updates": [
            {
                "section": "Knowledge Boundaries",
                "current_gap": "The guide needs a hard rule for Hymn's clone ignorance.",
                "suggested_text": "Hymn does not know she is a clone. She may experience memory leakage, but narration must not explain the clone cycle.",
            }
        ],
        "next_lore_prompt": "Audit current events for clone knowledge leaks, missing Chorus reports, speaker labels, and corruption ambiguity. Rewrite toward first-person field-report mystery.",
    }


def mock_accessibility_critique() -> dict[str, Any]:
    return {
        "summary": "Offline accessibility sample. The game needs a command schema before STT: every button needs voice aliases, repeat/status/help must be first-class, and all state changes must be spoken.",
        "eyes_free_score": 5,
        "commandability_score": 3,
        "tts_score": 7,
        "critical_findings": [
            {
                "severity": "high",
                "target": "events.json buttons",
                "issue": "Buttons do not yet carry voice_aliases, so STT has no stable command vocabulary.",
                "recommendation": "Add 2-5 short aliases per button and enforce uniqueness within each encounter.",
            }
        ],
        "command_parser_findings": [
            {
                "severity": "high",
                "target": "command parser contract",
                "issue": "Parser behavior is not defined for ambiguity, unknown commands, or confirmation.",
                "recommendation": "Define CommandResult with action, confidence, needs_confirmation, spoken_feedback, and error recovery.",
            }
        ],
        "tts_findings": [
            {
                "severity": "medium",
                "target": "state readout",
                "issue": "Status command needs a stable order for health, shield, biomass, danger, corruption, dependence, and claim.",
                "recommendation": "Implement a status readout that only speaks changed or requested state.",
            }
        ],
        "schema_recommendations": [
            "Add voice_aliases to every button.",
            "Add global command handling for repeat, repeat choices, status, help, confirm, and cancel.",
            "Add command parser tests using current encounter buttons.",
        ],
        "command_alias_plan": [
            {"action": "combat", "recommended_aliases": ["fight", "attack", "kill it"], "notes": "Combat aliases should be available only when combat is a legal button."},
            {"action": "proceed", "recommended_aliases": ["move", "continue", "leave"], "notes": "Use context-specific aliases to avoid making every proceed choice sound identical."},
            {"action": "pay_resin_toll", "recommended_aliases": ["pay", "pay toll", "feed toll"], "notes": "Short toll aliases should not collide with skip toll."},
        ],
        "state_readout_plan": [
            "Status: health, shield, biomass, danger, corruption, dependence, merchant claim.",
            "Repeat choices: number, label, and one short cost phrase.",
            "After action: speak only changed state plus any scheduled warning.",
        ],
        "testing_plan": [
            "Complete a run using typed commands only.",
            "For each encounter, select each button by number.",
            "For each encounter, select each button by at least one alias.",
            "Verify unknown commands recover with repeat/status/help prompt.",
        ],
        "guide_updates": [
            {
                "section": "Command Result Contract",
                "suggested_text": "All parser outputs must be legal current actions, global commands, clarification requests, or cancellations. The parser never invents actions.",
            }
        ],
        "next_accessibility_prompt": "Add voice_aliases to the current event deck and implement a typed command parser that supports numbers, aliases, repeat choices, status, confirm, and cancel.",
    }


def mock_lore_brainstorm() -> dict[str, Any]:
    return {
        "summary": "Offline lore brainstorm sample. The strongest direction is to treat lore as operational truth with pressure hooks, not backstory collection.",
        "design_thesis": "Every faction teaches Hymn something useful while also letting the organism, Chorus, or merchant gain leverage.",
        "factions": [
            {
                "name": "The Chorus Signal Office",
                "kind": "faction",
                "pitch": "Remote command structure that filters what Hymn is allowed to know.",
                "safe_reveal": "Chorus receives reports and authorizes route choices.",
                "hymn_misread": "Hymn reads silence as signal damage or operational caution.",
                "deferred_secret": "Chorus may recognize memory bleed and withhold why.",
                "gameplay_hook": "Signal-check lore fragments can lower danger but raise suspicion or corruption if the organism listens through the channel.",
                "related_systems": ["lore_fragment", "danger", "corruption", "ending"],
                "sample_fragment": "Chorus, signal test. My last report is already stamped received.",
                "implementation_notes": ["Add Chorus report events", "Track signal degradation at corruption thresholds"],
            },
            {
                "name": "The Choir of Intake",
                "kind": "faction",
                "pitch": "Former facility cult/operators who treated feeding the organism as maintenance.",
                "safe_reveal": "They built rituals around biomass accounting and route control.",
                "hymn_misread": "Hymn reads their records as cult worship, not operational procedure.",
                "deferred_secret": "Their rituals may be old containment protocols that still work.",
                "gameplay_hook": "Reading their marks can unlock safer routes while raising danger from reactivated monitoring.",
                "related_systems": ["lore_fragment", "danger", "deck"],
                "sample_fragment": "Intake hymn scratched into bone. Not prayer. Procedure.",
                "implementation_notes": ["Add cult record fragments", "Let some fragments modify next deck draw"],
            },
        ],
        "recurring_characters": [
            {
                "name": "Quartermaster Null",
                "kind": "recurring shadow",
                "pitch": "A name on old supply tags that may predate Chorus involvement.",
                "safe_reveal": "Null cataloged symbiotes as equipment, not organisms.",
                "hymn_misread": "Hymn assumes Null was a dead operator.",
                "deferred_secret": "Null may be a Chorus role, not one person.",
                "gameplay_hook": "Null tags reveal noncombat symbiote uses and damaged activation risks.",
                "related_systems": ["symbiote", "lore_fragment", "corruption"],
                "sample_fragment": "Null tag. Barrier unit. Field note says it bites when overtrusted.",
                "implementation_notes": ["Add symbiote lore fragments", "Expose cooldown/health hints diegetically"],
            }
        ],
        "organism_lore": [
            {
                "name": "Pattern Hunger",
                "kind": "organism principle",
                "pitch": "The organism does not punish choices; it feeds on repeated solutions.",
                "safe_reveal": "Rooms respond more sharply when Hymn repeats behavior.",
                "hymn_misread": "Hymn thinks the facility is getting louder or faster.",
                "deferred_secret": "The organism is modeling her across more than one entry.",
                "gameplay_hook": "Repeated action warnings become lore fragments that explain pressure tracks.",
                "related_systems": ["danger", "corruption", "ending", "deck"],
                "sample_fragment": "Same door muscle. Same hesitation. It opens before I touch it.",
                "implementation_notes": ["Tie director warnings to lore text variants"],
            }
        ],
        "lore_fragments": [
            {
                "name": "Received Before Sent",
                "kind": "fragment",
                "pitch": "A Chorus receipt timestamp predates Hymn's report.",
                "safe_reveal": "Something is wrong with signal timing.",
                "hymn_misread": "Hymn blames facility distortion.",
                "deferred_secret": "Chorus may already have prior-instance reports.",
                "gameplay_hook": "Study fragment to lower danger by 1, but add one memory-pressure flag.",
                "related_systems": ["lore_fragment", "danger", "ending"],
                "sample_fragment": "Receipt time is wrong. Chorus had this before I said it.",
                "implementation_notes": ["Needs lore-fragment action with mixed effects"],
            }
        ],
        "relationships": [
            {
                "a": "Chorus",
                "b": "Merchant",
                "visible_relationship": "Chorus treats him as an unknown hazard.",
                "hidden_truth": "Chorus may know his pattern and avoid naming him.",
                "gameplay_expression": "Merchant offers change if Hymn reports him versus ignores him.",
            },
            {
                "a": "Symbiotes",
                "b": "Facility Operators",
                "visible_relationship": "Symbiotes cling to dead hosts.",
                "hidden_truth": "They may be old operator tools that learned survival.",
                "gameplay_expression": "Operator tags reveal alternate symbiote activation effects.",
            },
        ],
        "reveal_paths": [
            {
                "thread": "Chorus timing",
                "early_reveal": "Chorus receives reports and gives orders offscreen.",
                "mid_reveal": "Some receipts and route approvals arrive too early.",
                "late_reveal": "Hymn finds references to prior reports she cannot remember writing.",
                "player_pressure": "Following Chorus lowers danger but may restrict neutral ending information.",
                "ending_connection": "Balanced ending requires noticing Chorus omissions without fully rejecting the mission.",
            }
        ],
        "mechanic_hooks": [
            "Lore fragments with mixed effects: lower danger, raise memory pressure, unlock route tags.",
            "Chorus report events at thresholds for danger, corruption, and merchant contact.",
            "Symbiote provenance tags that reveal noncombat uses.",
            "Merchant offer variants based on whether Hymn reports him to Chorus.",
        ],
        "guardrails": [
            "Do not let Hymn say clone or understand the run cycle.",
            "Chorus does not speak onscreen.",
            "Every lore fragment must touch a system.",
            "Do not make factions into exposition NPCs.",
        ],
        "next_lore_prompt": "Generate lore fragments and faction hooks that reveal operational truth, preserve Hymn's ignorance, and create concrete changes to danger, corruption, merchant offers, symbiote use, or ending eligibility.",
    }


def mock_story_architect() -> dict[str, Any]:
    return {
        "summary": "Offline story architect sample. The current stack has strong local situations but needs a pilot arc where a recurring figure wants something and changes later encounters.",
        "story_diagnosis": "The rooms imply memory, debt, and pursuit, but many follow-ups behave like echoes instead of scenes. A story spine needs a character who returns with leverage and forces Hymn to answer.",
        "missing_story_primitives": [
            "A recurring character with a visible desire.",
            "Follow-up encounters that change options or prices.",
            "A payoff before the first run feels like disconnected room browsing.",
        ],
        "character_arcs": [
            {
                "character_id": "quartermaster_of_teeth",
                "player_facing_name": "Quartermaster of Teeth",
                "current_status": "Present in metadata and toll imagery, but not yet active enough as a character.",
                "desire": "Convert Hymn's route choices into payable debt.",
                "pressure_method": "Changes prices, closes mouths, and sells route heat to hunters.",
                "relationship_to_hymn": "Predatory accountant who treats her as inventory with legs.",
                "first_appearance": "Opening rib/toll decision or first larder debt.",
                "arc_beats": [
                    {
                        "beat_id": "debt_setup",
                        "role": "setup",
                        "trigger": "First toll refusal or underpayment.",
                        "encounter_function": "Name the debt system as an actor.",
                        "player_choice": "Pay, dispute, or force the mouth.",
                        "visible_change": "A later toll has a marked price or missing safe option.",
                        "mechanical_consequence": "merchant_claim or toll_debt_streak increases.",
                        "implementation_notes": ["Use story_followups and a special_event with trigger_key."],
                    }
                ],
                "why_this_is_a_character": "It wants payment, remembers refusal, and can alter future rooms.",
                "failure_mode_if_absent": "Debt remains flavor and the player does not feel opposed by anyone.",
            }
        ],
        "first_15_minute_spine": [
            {
                "sequence_index": 1,
                "target_room_or_event": "rib_lock_tally_gate_account",
                "story_function": "Open with a pressure-lock bargain.",
                "player_question": "Do I let this place count me, pay it, or injure myself forcing through?",
                "choice_pressure": "Each option creates a different claimant.",
                "followup_payoff": "A named toll actor recognizes the decision within two rooms.",
                "required_data_changes": ["Add a Quartermaster follow-up scene for toll refusal/payment/force."],
            }
        ],
        "followup_encounter_plan": [
            {
                "source_event": "rib_lock_tally_gate_account",
                "followup_event_id": "story_quartermaster_first_claim",
                "character_id": "quartermaster_of_teeth",
                "trigger": "Toll refusal, payment, or forced rib passage.",
                "timing": "1-2 rooms later.",
                "scene_function": "Turn toll accounting into a recurring antagonist scene.",
                "choice_or_route_change": "One option is cheaper, blocked, or dangerous based on the earlier decision.",
                "mechanical_hook": "merchant_claim and environment_state flags.",
                "authoring_prompt": "Write a short follow-up encounter where a toll/accounting actor returns with leverage from the player's first toll decision.",
            }
        ],
        "pilot_arc_recommendation": {
            "arc_name": "Quartermaster Debt Pilot",
            "why_this_first": "It attaches to existing toll/larder/merchant content and can pay off quickly.",
            "scope_events": ["rib_lock_tally_gate_account", "biomass_larder_weighted_pockets", "story_quartermaster_first_claim"],
            "required_system_hooks": ["Track toll stance or reuse merchant_claim", "Allow follow-up event to alter a later toll option"],
            "acceptance_tests": ["A blind player can name who is pressuring them by minute fifteen.", "A prior toll choice visibly changes one later option."],
            "generation_prompt": "Generate the Quartermaster Debt Pilot as setup, escalation, choice, and payoff follow-up encounters using existing actions where possible.",
        },
        "story_rules": [
            "Every named character needs desire, memory, pressure, and payoff.",
            "Every story follow-up must be a scene or option change, not only a mood echo.",
        ],
        "patch_strategy": [
            "Plan one arc first.",
            "Generate OpenAI-authored follow-up encounters for that arc.",
            "Validate that first-run play reveals the character before minute fifteen.",
        ],
        "next_story_prompt": "Generate a small Quartermaster debt arc with 4-6 follow-up encounters, using current rooms and existing actions first.",
    }


def mock_story_pilot() -> dict[str, Any]:
    return {
        "title": "Offline Story Pilot Sample",
        "design_goal": "Show the shape of a story pilot patch without calling OpenAI.",
        "special_events": [
            {
                "id": "story_soft_captain_pulse_mark",
                "type": "story",
                "speaker": "Hymn",
                "line_1": "Chorus, a transit cord drops from an overhead seam and pulses at my wrist interval.",
                "line_2": "The cord holds the count I allowed. A nearby lock opens while the pulse is still running.",
                "reactivate_on_reshuffle": False,
                "buttons": [
                    {"label": "File the rhythm", "action": "proceed", "voice_aliases": ["file rhythm", "report", "rhythm"]},
                    {"label": "Leave it unfiled", "action": "retreat", "voice_aliases": ["leave unfiled", "hide it", "retreat"]},
                ],
                "action_results": {
                    "proceed": {
                        "lines": ["I file the rhythm and keep the cord's interval in my wrist."],
                        "environment_state_changes": ["soft_captain_next_rib_lock"],
                    },
                    "retreat": {
                        "lines": ["I leave the rhythm unfiled. The cord retracts with my count still in it."],
                        "environment_state_changes": ["soft_captain_refused"],
                    },
                },
            }
        ],
        "room_event_updates": [
            {
                "room_id": "rib_lock_tally_gate",
                "event_id": "rib_lock_tally_gate_account",
                "merge": {
                    "state_overrides": [
                        {
                            "state_key": "soft_captain_next_rib_lock",
                            "consume_state": True,
                            "event": {
                                "line_1": "The lock starts at my stored wrist interval before the toll mouth opens.",
                                "line_2": "The held count gives me one quiet slip. Paying or forcing would break it.",
                            },
                        }
                    ]
                },
            }
        ],
        "required_engine_changes": [],
        "validation_notes": ["Mock patch only."],
        "self_critique": ["Insufficient for production; use OpenAI for authored content."],
    }


def _text_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_text_present(item) for item in value)
    if isinstance(value, dict):
        return any(_text_present(item) for item in value.values())
    return value is not None


def _validate_corpus_influences_block(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{location}: corpus_influences must be a non-empty list of source objects")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{location}.corpus_influences[{index}] must be an object, not a source id string")
            continue
        for key in ("source_chunk_id", "source_fingerprint", "structural_transfer", "required_visible_details", "followup_payoff"):
            if not _text_present(item.get(key)):
                errors.append(f"{location}.corpus_influences[{index}] missing {key}")


def _validate_corpus_anchor_points_block(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{location}: corpus_anchor_points must be a non-empty list")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{location}.corpus_anchor_points[{index}] must be an object")
            continue
        for key in ("source_id", "source_chunk_id", "anchor_role", "source_fingerprint", "playable_transform", "required_visible_details", "followup_payoff"):
            if not _text_present(item.get(key)):
                errors.append(f"{location}.corpus_anchor_points[{index}] missing {key}")
        details = item.get("required_visible_details", [])
        if not isinstance(details, list) or len([detail for detail in details if str(detail).strip()]) < 2:
            errors.append(f"{location}.corpus_anchor_points[{index}].required_visible_details must list at least two concrete visible details")


def _validate_revelation_operation_plans(event: dict[str, Any], location: str, actions: set[str], errors: list[str]) -> None:
    buttons = event.get("buttons", [])
    button_actions = {str(button.get("action", "")) for button in buttons if isinstance(button, dict) and str(button.get("action", ""))}
    plans = event.get("operation_plans", [])
    if not isinstance(plans, list) or not plans:
        if event.get("type") == "choice":
            errors.append(f"{location}: Revelation choice events must include character-owned operation_plans")
        return
    planned_actions: set[str] = set()
    for plan_index, plan in enumerate(plans):
        plan_location = f"{location}.operation_plans[{plan_index}]"
        if not isinstance(plan, dict):
            errors.append(f"{plan_location} must be an object")
            continue
        action = str(plan.get("action", "")).strip()
        officer_id = str(plan.get("officer_id", "")).strip()
        planned_actions.add(action)
        if not action:
            errors.append(f"{plan_location}.action is required so the plan maps to a button")
        elif base_action_id(action) not in actions:
            errors.append(f"{plan_location}.action '{action}' is not an implemented action")
        if officer_id not in REVELATION_OFFICER_IDS:
            errors.append(f"{plan_location}.officer_id '{officer_id}' must be one of {', '.join(sorted(REVELATION_OFFICER_IDS))}")
        base_success = plan.get("base_success")
        if not isinstance(base_success, (int, float)) or not (0.05 <= float(base_success) <= 0.95):
            errors.append(f"{plan_location}.base_success must be a 0.05-0.95 probability, not a percentage")
        for key in ("primary_skill", "yield", "risk"):
            if not str(plan.get(key, "")).strip():
                errors.append(f"{plan_location}.{key} is required")
        outcomes = plan.get("outcomes", {})
        if not isinstance(outcomes, dict):
            errors.append(f"{plan_location}.outcomes must be an object")
            continue
        for band in ("success", "partial", "failure"):
            outcome = outcomes.get(band)
            if not isinstance(outcome, dict):
                errors.append(f"{plan_location}.outcomes.{band} must be an object with lines and consequences")
                continue
            lines = outcome.get("lines")
            if not isinstance(lines, list) or not [line for line in lines if str(line).strip()]:
                errors.append(f"{plan_location}.outcomes.{band}.lines must be a non-empty list")
            environment_changes = outcome.get("environment_state_changes", [])
            if environment_changes and not isinstance(environment_changes, list):
                errors.append(f"{plan_location}.outcomes.{band}.environment_state_changes must be a list")
            resource_changes = outcome.get("resource_changes", {})
            if resource_changes and not isinstance(resource_changes, dict):
                errors.append(f"{plan_location}.outcomes.{band}.resource_changes must be an object")
            if not environment_changes and not resource_changes:
                errors.append(f"{plan_location}.outcomes.{band} needs durable state or resource consequences")
    for action in sorted(button_actions - planned_actions):
        errors.append(f"{location}: button action '{action}' has no matching operation_plan")


def _validate_revelation_event_contract(event: dict[str, Any], location: str, actions: set[str], errors: list[str]) -> None:
    event_type = str(event.get("type", ""))
    if event_type in {"choice", "story", "resolution", "debrief", "interlude", "base_incident"}:
        _validate_corpus_influences_block(event.get("corpus_influences"), location, errors)
        _validate_corpus_anchor_points_block(event.get("corpus_anchor_points"), location, errors)
    if event_type in {"choice", "resolution"}:
        _validate_revelation_operation_plans(event, location, actions, errors)
    if event_type == "interlude":
        for key in REVELATION_REQUIRED_INTERLUDE_FIELDS:
            if not _text_present(event.get(key)):
                errors.append(f"{location}: interlude missing {key}")


def _validate_revelation_room_contract(room_record: dict[str, Any], location: str, errors: list[str]) -> None:
    if str(room_record.get("type", "mission")) != "mission":
        errors.append(f"{location}: Revelation mission room type must be `mission`")
        return
    for key in ("description", "detection_report", "officer_reports", "procedure_hooks", "religious_subtext", "scenario_generation_contract", "character_state_stakes", "interlude_vectors"):
        if not _text_present(room_record.get(key)):
            errors.append(f"{location}: Revelation mission room missing {key}")
    _validate_corpus_influences_block(room_record.get("corpus_influences"), location, errors)
    _validate_corpus_anchor_points_block(room_record.get("corpus_anchor_points"), location, errors)


def validation_errors(
    patch: dict[str, Any],
    allow_new_actions: bool = False,
    expected_category: str = "",
    strict_tradeoffs: bool = False,
) -> list[str]:
    errors: list[str] = []
    rooms = set(room_ids())
    patch_room_ids: set[str] = set()
    room_records = patch.get("room_records", [])
    if isinstance(room_records, list):
        for room_index, room_record in enumerate(room_records):
            if not isinstance(room_record, dict):
                errors.append(f"room_records[{room_index}] is not an object")
                continue
            room_id = str(room_record.get("id", "")).strip()
            if not room_id:
                errors.append(f"room_records[{room_index}].id is empty")
                continue
            patch_room_ids.add(room_id)
            for key in ("name", "first_visit_description", "return_description", "current_situation"):
                if not str(room_record.get(key, "")).strip():
                    errors.append(f"room_records[{room_index}].{room_id}: missing {key}")
            if is_revelation_project():
                _validate_revelation_room_contract(room_record, f"room_records[{room_index}].{room_id}", errors)
    elif room_records:
        errors.append("room_records must be a list")
    rooms.update(patch_room_ids)
    actions = existing_actions()
    event_ids = existing_event_ids()
    categories = set(event_category_ids())
    if is_revelation_project():
        categories.update({"resolution", "interlude", "debrief"})

    special_events = patch.get("special_events", [])
    if not isinstance(special_events, list):
        errors.append("patch.special_events must be a list")
        special_events = []

    events = patch.get("events", [])
    if not isinstance(events, list) or not events:
        errors.append("patch.events must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    patch_special_event_ids: set[str] = set()
    for index, event in enumerate(special_events):
        if not isinstance(event, dict):
            errors.append(f"special_events[{index}] is not an object")
            continue
        event_id = str(event.get("id", ""))
        if not event_id:
            errors.append(f"special_events[{index}].id is empty")
        if event_id in event_ids:
            errors.append(f"special event id already exists: {event_id}")
        if event_id in seen_ids:
            errors.append(f"duplicate event id in patch: {event_id}")
        seen_ids.add(event_id)
        patch_special_event_ids.add(event_id)
        for key in ("type", "speaker", "line_1", "line_2"):
            if not str(event.get(key, "")).strip():
                errors.append(f"{event_id or index}: missing {key}")
        event_type = str(event.get("type", ""))
        if categories and event_type not in categories:
            errors.append(f"{event_id or index}: event type '{event_type}' is not a defined category")
        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            errors.append(f"{event_id or index}: buttons must be a non-empty list")
        else:
            if strict_tradeoffs and not is_tradeoff_exempt_event(event):
                commandable_buttons = commandable_button_count(event)
                if commandable_buttons < 2:
                    errors.append(
                        f"{event_id or index}: single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})"
                    )
            for button_index, button in enumerate(buttons):
                if not isinstance(button, dict):
                    errors.append(f"{event_id}: button {button_index} is not an object")
                    continue
                label = str(button.get("label", "")).strip()
                action = str(button.get("action", "")).strip()
                if not label:
                    errors.append(f"{event_id}: button {button_index} missing label")
                if not action:
                    errors.append(f"{event_id}: button {button_index} missing action")
                elif base_action_id(action) not in actions and not allow_new_actions:
                    errors.append(f"{event_id}: unknown action '{action}'")
        if is_revelation_project():
            _validate_revelation_event_contract(event, f"special_events[{index}].{event_id or '<missing>'}", actions, errors)

    for index, item in enumerate(events):
        if not isinstance(item, dict):
            errors.append(f"events[{index}] is not an object")
            continue
        room_id = str(item.get("room_id", ""))
        event = item.get("event")
        if room_id not in rooms:
            errors.append(f"events[{index}].room_id '{room_id}' is not in room_dialogue.json or patch.room_records")
        if not isinstance(event, dict):
            errors.append(f"events[{index}].event is not an object")
            continue
        event_id = str(event.get("id", ""))
        if not event_id:
            errors.append(f"events[{index}].event.id is empty")
        if event_id in event_ids:
            errors.append(f"event id already exists: {event_id}")
        if event_id in seen_ids:
            errors.append(f"duplicate event id in patch: {event_id}")
        seen_ids.add(event_id)
        for key in ("type", "speaker", "line_1", "line_2"):
            if not str(event.get(key, "")).strip():
                errors.append(f"{event_id or index}: missing {key}")
        event_type = str(event.get("type", ""))
        if categories and event_type not in categories:
            errors.append(f"{event_id or index}: event type '{event_type}' is not a defined category")
        if expected_category and event_type != expected_category:
            errors.append(f"{event_id or index}: event type '{event_type}' does not match requested category '{expected_category}'")
        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            errors.append(f"{event_id or index}: buttons must be a non-empty list")
            continue
        if strict_tradeoffs and not is_tradeoff_exempt_event(event):
            commandable_buttons = commandable_button_count(event)
            if commandable_buttons < 2:
                errors.append(
                    f"{event_id or index}: single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})"
                )
        for button_index, button in enumerate(buttons):
            if not isinstance(button, dict):
                errors.append(f"{event_id}: button {button_index} is not an object")
                continue
            label = str(button.get("label", "")).strip()
            action = str(button.get("action", "")).strip()
            if not label:
                errors.append(f"{event_id}: button {button_index} missing label")
            if not action:
                errors.append(f"{event_id}: button {button_index} missing action")
            elif base_action_id(action) not in actions and not allow_new_actions:
                errors.append(f"{event_id}: unknown action '{action}'")

        mutation_id = event.get("mutation_id")
        if mutation_id and str(mutation_id) not in mutation_ids():
            errors.append(f"{event_id}: unknown mutation_id '{mutation_id}'")
        symbiote_id = event.get("symbiote_id")
        if symbiote_id and str(symbiote_id) not in symbiote_ids():
            errors.append(f"{event_id}: unknown symbiote_id '{symbiote_id}'")
        enemy_id = event.get("enemy_id")
        if enemy_id and str(enemy_id) not in enemy_ids():
            errors.append(f"{event_id}: unknown enemy_id '{enemy_id}'")
        followups = event.get("story_followups", {})
        if isinstance(followups, dict):
            for followup_key, followup in followups.items():
                if not isinstance(followup, dict):
                    errors.append(f"{event_id}: story_followups.{followup_key} is not an object")
                    continue
                target = str(followup.get("event_id", ""))
                if not target:
                    errors.append(f"{event_id}: story_followups.{followup_key} missing event_id")
                elif target not in event_ids and target not in patch_special_event_ids:
                    errors.append(f"{event_id}: story_followups.{followup_key} targets missing special event '{target}'")
                if is_revelation_project() and not str(followup.get("queued_line", "")).strip():
                    errors.append(f"{event_id}: story_followups.{followup_key} missing queued_line")
        if is_revelation_project():
            _validate_revelation_event_contract(event, f"events[{index}].{event_id or '<missing>'}", actions, errors)

    if not allow_new_actions:
        required_changes = patch.get("required_engine_changes", [])
        if required_changes:
            errors.append("required_engine_changes is not empty, but new actions are not allowed")
    deck_pool_updates = patch.get("deck_pool_updates", [])
    if isinstance(deck_pool_updates, list):
        for update_index, update in enumerate(deck_pool_updates):
            if not isinstance(update, dict):
                errors.append(f"deck_pool_updates[{update_index}] is not an object")
                continue
            pool_name = str(update.get("pool", "")).strip()
            room_id = str(update.get("room_id", "")).strip()
            if not pool_name:
                errors.append(f"deck_pool_updates[{update_index}].pool is empty")
            if not room_id:
                errors.append(f"deck_pool_updates[{update_index}].room_id is empty")
            elif room_id not in rooms:
                errors.append(f"deck_pool_updates[{update_index}].room_id '{room_id}' is not an existing or patch room")
    elif deck_pool_updates:
        errors.append("deck_pool_updates must be a list")
    errors.extend(corpus_reference_errors(patch))
    errors.extend(patch_readability_errors(patch))
    return errors


def _word_count_text(text: str) -> int:
    return len(str(text).split())


def patch_readability_errors(payload: dict[str, Any], strict_context: bool = True) -> list[str]:
    """Hard gate for generated player-facing prose that is too compressed to read aloud."""
    errors: list[str] = []
    unclear_patterns: list[tuple[str, str]] = [
        (r"\bdrinks strange\b", "elliptical antique phrasing"),
        (r"\bthe mouth dries\b", "body-part abstraction instead of clear report"),
    ]
    context_terms = {
        "air",
        "audio",
        "badge",
        "bell",
        "boat",
        "bridge",
        "bulkhead",
        "case",
        "cask",
        "chart",
        "chalk",
        "clinic",
        "coil",
        "command",
        "crew",
        "deck",
        "engineer",
        "evidence",
        "floor",
        "fragments",
        "frost",
        "gauge",
        "glass",
        "gunner",
        "gunnery",
        "hatch",
        "hinge",
        "lamp",
        "lock",
        "manifest",
        "medical",
        "name",
        "officer",
        "office",
        "owen",
        "pa",
        "park",
        "photograph",
        "phone",
        "pressure",
        "quartermaster",
        "raft",
        "ration",
        "record",
        "records",
        "resident",
        "residents",
        "roster",
        "saye",
        "screen",
        "seal",
        "smoke",
        "stairwell",
        "suppression",
        "surgeon",
        "swarm",
        "tag",
        "threshold",
        "tape",
        "torah",
        "valve",
        "water",
        "watch",
        "warden",
        "wristband",
        "vaas",
    }
    procedure_terms = {
        "advise",
        "argues",
        "asks",
        "audit",
        "audits",
        "break",
        "call",
        "clear",
        "clearance",
        "cleared",
        "clears",
        "closed",
        "breached",
        "document",
        "contradicted",
        "decide",
        "documented",
        "dock",
        "draw",
        "evacuate",
        "evacuates",
        "evacuating",
        "file",
        "filed",
        "files",
        "filing",
        "happening",
        "inside",
        "jettison",
        "knows",
        "kept",
        "log",
        "logs",
        "marked",
        "marks",
        "ordered",
        "order",
        "photograph",
        "quarantine",
        "recommends",
        "recover",
        "records",
        "reports",
        "review",
        "seal",
        "sealed",
        "repositioned",
        "repositioning",
        "sounded",
        "suppressing",
        "suppression",
        "timestamp",
        "timed",
        "trapped",
        "test",
        "tests",
        "vent",
    }

    def check_text(text: Any, location: str, max_words: int, require_context: bool | None = None) -> None:
        value = str(text or "").strip()
        if not value:
            return
        count = _word_count_text(value)
        if count > max_words:
            errors.append(f"{location}: too long for readable report prose ({count} words, max {max_words})")
        lower = value.lower()
        for pattern, issue in unclear_patterns:
            if re.search(pattern, lower):
                errors.append(f"{location}: {issue}")
        if require_context is None:
            require_context = strict_context
        if require_context and location.endswith((".line_1", ".line_2")):
            has_context = any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(term), lower) for term in context_terms)
            has_procedure = any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(term), lower) for term in procedure_terms)
            if not has_context:
                errors.append(f"{location}: report line lacks a clear ship object, officer, resource, or instrument")
            if not has_procedure:
                errors.append(f"{location}: report line lacks a clear order, test, report, or procedure")

    def check_event(event: dict[str, Any], location: str) -> None:
        require_line_context = strict_context and str(event.get("type", "")) != "interlude"
        line_max_words = 36 if not strict_context and str(event.get("type", "")) in {"interlude", "resolution"} else 30
        check_text(event.get("line_1", ""), f"{location}.line_1", line_max_words, require_line_context)
        check_text(event.get("line_2", ""), f"{location}.line_2", line_max_words, require_line_context)
        for text_key in ("first_visit_description", "return_description", "current_situation", "detection_report"):
            check_text(event.get(text_key, ""), f"{location}.{text_key}", 55)
        buttons = event.get("buttons", [])
        if isinstance(buttons, list):
            for index, button in enumerate(buttons):
                if not isinstance(button, dict):
                    continue
                button_location = f"{location}.buttons[{index}]"
                check_text(button.get("label", ""), f"{button_location}.label", 6)
                check_text(button.get("preview", ""), f"{button_location}.preview", 16)
                check_text(button.get("result_text", ""), f"{button_location}.result_text", 45)
        action_results = event.get("action_results", {})
        if isinstance(action_results, dict):
            for action_id, result in action_results.items():
                result_location = f"{location}.action_results.{action_id}"
                if isinstance(result, dict):
                    check_text(result.get("result_memory_hook", ""), f"{result_location}.result_memory_hook", 24)
                    for followup_index, followup in enumerate(result.get("story_followups", []) or []):
                        if isinstance(followup, dict):
                            check_event(followup, f"{result_location}.story_followups[{followup_index}]")

    events = payload.get("events", [])
    if isinstance(events, list):
        for index, item in enumerate(events):
            if isinstance(item, dict) and isinstance(item.get("event"), dict):
                event_id = str(item["event"].get("id", index))
                check_event(item["event"], f"events[{index}].{event_id}")
    room_events = payload.get("room_events", [])
    if isinstance(room_events, list):
        for index, item in enumerate(room_events):
            if isinstance(item, dict) and isinstance(item.get("event"), dict):
                event_id = str(item["event"].get("id", index))
                check_event(item["event"], f"room_events[{index}].{event_id}")
            elif isinstance(item, dict):
                check_event(item, f"room_events[{index}].{item.get('id', index)}")
    elif isinstance(room_events, dict):
        for room_id, event_list in room_events.items():
            if isinstance(event_list, list):
                for index, event in enumerate(event_list):
                    if isinstance(event, dict):
                        check_event(event, f"room_events.{room_id}[{index}].{event.get('id', index)}")
    special_events = payload.get("special_events", [])
    if isinstance(special_events, list):
        for index, event in enumerate(special_events):
            if isinstance(event, dict):
                check_event(event, f"special_events[{index}].{event.get('id', index)}")
    elif isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                check_event(event, f"special_events.{event_id}")
    return errors


def corpus_reference_errors(payload: dict[str, Any]) -> list[str]:
    known_artifacts: set[str] = set()
    known_fragments: set[str] = set()
    if CORPUS_INDEX_PATH.exists():
        index_payload = load_json(CORPUS_INDEX_PATH)
        artifacts = index_payload.get("artifacts", [])
        if isinstance(artifacts, list):
            known_artifacts = {str(artifact.get("id", "")) for artifact in artifacts if isinstance(artifact, dict)}
    if CORPUS_FRAGMENTS_PATH.exists():
        fragment_payload = load_json(CORPUS_FRAGMENTS_PATH)
        fragments = fragment_payload.get("fragments", [])
        if isinstance(fragments, list):
            known_fragments = {str(fragment.get("id", "")) for fragment in fragments if isinstance(fragment, dict)}

    errors: list[str] = []

    def check(value: Any, location: str) -> None:
        if isinstance(value, dict):
            artifact_ids = value.get("corpus_artifact_ids")
            if isinstance(artifact_ids, list) and known_artifacts:
                for artifact_id in artifact_ids:
                    if str(artifact_id) not in known_artifacts:
                        errors.append(f"{location}: unknown corpus_artifact_id '{artifact_id}'")
            fragment_ids = value.get("corpus_fragment_ids")
            if isinstance(fragment_ids, list) and known_fragments:
                for fragment_id in fragment_ids:
                    if str(fragment_id) not in known_fragments:
                        errors.append(f"{location}: unknown corpus_fragment_id '{fragment_id}'")
            for key, child in value.items():
                check(child, f"{location}.{key}" if location else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check(child, f"{location}[{index}]")

    check(payload, "patch")
    return errors


def events_file_errors(strict_actions: bool = False, strict_tradeoffs: bool = False) -> list[str]:
    errors: list[str] = []
    payload = load_json(EVENTS_PATH)
    rooms = set(room_ids())
    categories = set(event_category_ids())
    actions = existing_actions()
    seen_ids: set[str] = set()

    def check_event(event: dict[str, Any], location: str) -> None:
        event_id = str(event.get("id", ""))
        if not event_id:
            errors.append(f"{location}: missing id")
        elif event_id in seen_ids:
            errors.append(f"{location}: duplicate event id '{event_id}'")
        seen_ids.add(event_id)

        event_type = str(event.get("type", ""))
        if not event_type:
            errors.append(f"{location}: missing type")
        elif categories and event_type not in categories:
            errors.append(f"{location}: event type '{event_type}' is not a defined category")

        for key in ("speaker", "line_1", "line_2"):
            if not str(event.get(key, "")).strip():
                errors.append(f"{location}: missing {key}")

        buttons = event.get("buttons", [])
        choices = event.get("choices", [])
        has_buttons = isinstance(buttons, list) and bool(buttons)
        has_choices = isinstance(choices, list) and any(str(choice).strip() for choice in choices)
        if not has_buttons and not has_choices:
            errors.append(f"{location}: buttons or choices must be a non-empty list")
            return
        if has_choices:
            for choice_index, choice in enumerate(choices):
                if not str(choice).strip():
                    errors.append(f"{location}: choice {choice_index} is empty")
        if not has_buttons:
            return
        for button_index, button in enumerate(buttons):
            if not isinstance(button, dict):
                errors.append(f"{location}: button {button_index} is not an object")
                continue
            if not str(button.get("label", "")).strip():
                errors.append(f"{location}: button {button_index} missing label")
            action = str(button.get("action", "")).strip()
            if not action:
                errors.append(f"{location}: button {button_index} missing action")
            elif strict_actions and base_action_id(action) not in actions:
                errors.append(f"{location}: unknown action '{action}'")

    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        errors.append("room_events must be an object")
    else:
        for room_id, events in room_events.items():
            if room_id not in rooms:
                errors.append(f"room_events.{room_id}: room is not in room_dialogue.json")
            if not isinstance(events, list):
                errors.append(f"room_events.{room_id}: must be a list")
                continue
            for index, event in enumerate(events):
                if isinstance(event, dict):
                    if strict_tradeoffs:
                        event_type = str(event.get("type", ""))
                        if not is_tradeoff_exempt_event(event):
                            buttons = event.get("buttons", [])
                            commandable_buttons = commandable_button_count(event)
                            if commandable_buttons < 2:
                                errors.append(f"room_events.{room_id}[{index}]: single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})")
                    check_event(event, f"room_events.{room_id}[{index}]")
                else:
                    errors.append(f"room_events.{room_id}[{index}]: event is not an object")

    special_events = payload.get("special_events", {})
    if not isinstance(special_events, dict):
        errors.append("special_events must be an object")
    else:
        for event_key, event in special_events.items():
            if isinstance(event, dict):
                if str(event.get("id", event_key)) != event_key:
                    errors.append(f"special_events.{event_key}: id does not match key")
                check_event(event, f"special_events.{event_key}")
            else:
                errors.append(f"special_events.{event_key}: event is not an object")

    errors.extend(patch_readability_errors(payload, strict_context=False))
    return errors


def event_writing_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = room_depth_findings() + room_story_findings()
    generic_labels = {
        "Proceed.",
        "Proceed",
        "Move on",
        "Leave it",
        "Leave it alone",
        "Back off",
        "Back away",
        "Walk past",
        "Leave",
    }
    weak_line_patterns = [
        ("what should i do", "generic prompt language"),
        ("i can ", "choice list reads like a menu instead of pressure"),
        ("could be", "uncertain phrasing without field interpretation"),
        ("maybe", "uncertain phrasing without field interpretation"),
        ("looks safer", "flat safety wording"),
        ("may lower", "flat probability wording"),
        ("may show", "flat probability wording"),
        ("may calm", "flat probability wording"),
        ("buys control", "abstract choice summary"),
        ("buys speed", "abstract choice summary"),
        ("buys uncertainty", "abstract choice summary"),
        ("is useful", "generic utility wording"),
        ("under pressure:", "abstract choice framing"),
        ("three uses", "menu-like choice framing"),
        ("command signal", "abstract command jargon"),
    ]
    source_style_patterns = [
        (r"\b(verne|lovecraft)\b", "source name leaked into player-facing prose"),
        (r"\b(eldritch|cyclopean|aeon|aeons|nameless|unspeakable|indescribable|blasphemous|cosmic|madness)\b", "Lovecraft costume diction"),
        (r"\b(professor|gentleman|gentlemen|my dear|alas|hurrah)\b", "Verne costume diction"),
        (r"\b(destiny|prophecy|omen|judg(?:e)?ment|invitation|fate)\b", "mystical abstraction in Hymn narration"),
        (r"\b(the organism wants|the room wants|the room remembers|the system knows|the system wants)\b", "unsupported agency claim"),
        (r"\b(later this will|next room will|this queues|this unlocks|ending path)\b", "future mechanic stated in narration"),
    ]
    lore_name_terms = {
        "soft captain",
        "pell",
        "mother chancel",
        "commandant signal",
    }
    apparatus_terms = {
        "beetle",
        "bell",
        "bore",
        "cord",
        "dock",
        "ferry",
        "grub",
        "harness",
        "larva",
        "lice",
        "mouth",
        "pocket",
        "pore",
        "ring",
        "scale",
        "seam",
        "signal",
        "teeth",
        "tissue",
        "valve",
    }
    evidence_terms = {
        "abrasion",
        "bleeding",
        "clean",
        "cold",
        "cut",
        "edge",
        "old",
        "pulse",
        "record",
        "repair",
        "residue",
        "ridge",
        "score",
        "scored",
        "scratch",
        "scent",
        "stain",
        "tally",
        "worn",
    }
    body_stake_terms = {
        "blood",
        "body",
        "boot",
        "breath",
        "cuts",
        "flesh",
        "glove",
        "hand",
        "knees",
        "pulse",
        "shoulder",
        "skin",
        "weight",
        "wound",
        "wrist",
    }
    concrete_terms = {
        "beetle",
        "bell",
        "blood",
        "bone",
        "bore",
        "blister",
        "cord",
        "cut",
        "dock",
        "ferry",
        "fluid",
        "grub",
        "harbor",
        "harness",
        "larva",
        "lice",
        "larder",
        "lens",
        "map",
        "marrow",
        "mouth",
        "pocket",
        "pore",
        "packet",
        "canvas",
        "clock",
        "collar",
        "compartment",
        "deck",
        "faceplate",
        "frost",
        "gauge",
        "hatch",
        "lamp",
        "lifeboat",
        "lifeboats",
        "manifold",
        "registry",
        "shutter",
        "shutters",
        "tube",
        "rib",
        "ring",
        "scale",
        "scar",
        "seam",
        "signal",
        "strap",
        "teeth",
        "tissue",
        "token",
        "valve",
        "wall",
        "wound",
    }
    chorus_expected = {"merchant", "danger", "corruption", "symbiote"}

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    def check_house_voice_text(text: str, location: str) -> None:
        if not text:
            return
        lower_text = text.lower()
        for pattern, issue in source_style_patterns:
            if re.search(pattern, lower_text):
                add(
                    location,
                    "high",
                    issue,
                    "Rewrite in the Nightmare Voyage house voice: concrete situation, mechanism, evidence, and operational stakes. Corpus influence should not be visible as author-mode diction.",
                )
        for term in lore_name_terms:
            if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(term), lower_text):
                add(
                    location,
                    "medium",
                    "proper-name lore in field report",
                    "Use observable traces unless the named figure is physically present or has been introduced in-world.",
                )

    def check_event(event: dict[str, Any], location: str) -> None:
        event_type = str(event.get("type", ""))
        line_1 = str(event.get("line_1", ""))
        line_2 = str(event.get("line_2", ""))
        combined = f"{line_1} {line_2}"
        combined_lower = combined.lower()
        check_house_voice_text(line_1, f"{location}.line_1")
        check_house_voice_text(line_2, f"{location}.line_2")

        for pattern, issue in weak_line_patterns:
            if pattern in combined_lower:
                add(location, "high", issue, "Rewrite as a plain observed situation with one visible actor and one observable pressure. Do not pad with mechanism nouns or future payoff.")

        has_concrete_actor = any(term in combined_lower for term in concrete_terms)
        if event_type in {"choice", "story"} and not has_concrete_actor:
            add(
                location,
                "medium",
                "abstract situation",
                "Name the visible actor, organ, material, or mark involved. One clean concrete detail is enough.",
            )

        if event_type in chorus_expected and "chorus" not in combined_lower:
            add(location, "medium", "missing captain-facing report cadence", "Add a short report, log, or officer briefing without explaining the anomaly.")

        if str(event.get("enemy_id", "")) and event_type in {"combat", "boss"} and "scene_path" not in event:
            add(location, "low", "combat event relies on enemy scene fallback", "Add scene_path if this encounter needs a specific visible sprite.")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list):
            return
        commandable_buttons = commandable_button_count(event)
        if not is_tradeoff_exempt_event(event) and commandable_buttons < 2:
            add(
                location,
                "high",
                f"single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})",
                "Add a second legal choice with a distinct cost, delayed consequence, or alternative pressure axis. Transition events may stay exempt.",
            )
        for index, button in enumerate(buttons):
            if not isinstance(button, dict):
                continue
            label = str(button.get("label", ""))
            action = str(button.get("action", ""))
            button_location = f"{location}.buttons[{index}]"
            if label in generic_labels:
                add(button_location, "low", f"generic button label '{label}'", "Use embodied instruction: carry the noise, withdraw, force the route, break contact.")
            if action == "proceed" and label.lower() in {"proceed.", "proceed", "move on", "walk past"}:
                add(button_location, "low", "neutral proceed choice", "Name what the refusal preserves or costs.")
            if "wares" in label.lower() or "shop" in label.lower():
                add(button_location, "high", "shop/menu language in merchant-facing UI", "Use scale/exchange/body language instead.")
            check_house_voice_text(label, f"{button_location}.label")

        action_results = event.get("action_results", {})
        if isinstance(action_results, dict):
            for action_id, result in action_results.items():
                if not isinstance(result, dict):
                    continue
                result_lines = result.get("lines", [])
                if isinstance(result_lines, list):
                    for line_index, line in enumerate(result_lines):
                        check_house_voice_text(str(line), f"{location}.action_results.{action_id}.lines[{line_index}]")

        followups = event.get("story_followups", {})
        if isinstance(followups, dict):
            for followup_key, followup in followups.items():
                if isinstance(followup, dict):
                    check_house_voice_text(str(followup.get("queued_line", "")), f"{location}.story_followups.{followup_key}.queued_line")

    def check_room_text(text: str, location: str, require_full_house_style: bool = False) -> None:
        if not text:
            return
        check_house_voice_text(text, location)
        lower_text = text.lower()
        if not require_full_house_style:
            return
        if not any(term in lower_text for term in apparatus_terms):
            add(
                location,
                "medium",
                "room prose lacks apparatus pressure",
                "Add one concrete instrument, compartment, signal, object, or ship mechanism and what it does now; corpus influence should not read as pure mood.",
            )
        if not any(term in lower_text for term in evidence_terms):
            add(
                location,
                "medium",
                "room prose lacks accumulated evidence",
                "Add wear, repair, residue, old marks, measurement, or prior-use evidence so dread comes from records.",
            )
        if not any(term in lower_text for term in body_stake_terms):
            add(
                location,
                "medium",
                "room prose lacks bodily stakes",
                "Anchor the mechanism to crew, pressure, breath, hull, gauge, frost, lamp, chart, or a named ship system.",
            )

    def check_room(room: dict[str, Any], location: str) -> None:
        narrow_room = is_narrow_room_role(room)
        check_room_text(str(room.get("name", "")), f"{location}.name")
        check_room_text(str(room.get("instance_premise", "")), f"{location}.instance_premise")
        check_room_text(str(room.get("first_visit_description", "")), f"{location}.first_visit_description", require_full_house_style=not narrow_room)
        check_room_text(str(room.get("return_description", "")), f"{location}.return_description")
        ui_text = room.get("ui_text", {})
        if isinstance(ui_text, dict):
            check_room_text(str(ui_text.get("line_1", "")), f"{location}.ui_text.line_1", require_full_house_style=not narrow_room)
            check_room_text(str(ui_text.get("line_2", "")), f"{location}.ui_text.line_2", require_full_house_style=not narrow_room)
        progression_state = room.get("progression_state", {})
        if isinstance(progression_state, dict):
            for state_key, state_text in progression_state.items():
                check_room_text(str(state_text), f"{location}.progression_state.{state_key}")
        for array_key in ("cross_run_story_hooks", "environment_echoes"):
            entries = room.get(array_key, [])
            if isinstance(entries, list):
                for index, entry in enumerate(entries):
                    check_room_text(str(entry), f"{location}.{array_key}[{index}]")

    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if not isinstance(events, list):
                continue
            for event in events:
                if isinstance(event, dict):
                    event_id = str(event.get("id", "unknown"))
                    check_event(event, f"room_events.{room_id}.{event_id}")

    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                check_event(event, f"special_events.{event_id}")

    rooms_payload = load_json(ROOMS_PATH)
    rooms = rooms_payload.get("rooms", [])
    if isinstance(rooms, list):
        for index, room in enumerate(rooms):
            if isinstance(room, dict):
                room_id = str(room.get("id", index))
                check_room(room, f"rooms.{room_id}")

    return findings


def event_accessibility_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = []
    global_commands = {
        "one",
        "two",
        "three",
        "repeat",
        "repeat choices",
        "status",
        "inventory",
        "help",
        "confirm",
        "cancel",
        "pause",
        "continue",
        "slower",
        "faster",
    }
    visual_only_terms = {
        "visual",
        "see",
        "look",
        "color",
        "red",
        "green",
        "glow",
        "glowing",
    }

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    def check_event(event: dict[str, Any], location: str) -> None:
        line_1 = str(event.get("line_1", ""))
        line_2 = str(event.get("line_2", ""))
        for line_key, line in (("line_1", line_1), ("line_2", line_2)):
            word_count = len(line.split())
            if word_count > 22:
                add(f"{location}.{line_key}", "medium", f"TTS line is long ({word_count} words)", "Split into shorter phrase chunks.")
            lower_line = line.lower()
            visual_only_match = any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(term), lower_line) for term in visual_only_terms)
            if visual_only_match and not any(term in lower_line for term in ("smell", "sound", "hear", "pulse", "heat", "scent", "touch", "breath")):
                add(f"{location}.{line_key}", "low", "possible visual-only cue", "Add nonvisual sensory information or state effect.")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            add(location, "high", "no commandable buttons", "Every encounter needs at least one legal command target.")
            return

        seen_aliases: dict[str, int] = {}
        for index, button in enumerate(buttons):
            if not isinstance(button, dict):
                continue
            button_location = f"{location}.buttons[{index}]"
            label = str(button.get("label", ""))
            action = str(button.get("action", ""))
            aliases = button.get("voice_aliases", [])
            if not isinstance(aliases, list) or not aliases:
                add(button_location, "high", "missing voice_aliases", "Add 2-5 short spoken aliases for this command.")
                aliases = []
            if len(label.split()) > 5:
                add(button_location, "low", f"long spoken label '{label}'", "Keep command labels short; move nuance into narration.")
            normalized_aliases: list[str] = []
            for alias in aliases:
                alias_text = str(alias).strip().lower()
                if not alias_text:
                    continue
                normalized_aliases.append(alias_text)
                if alias_text in global_commands:
                    add(button_location, "medium", f"alias '{alias_text}' collides with global command", "Use action-specific aliases; numbers remain global.")
                if len(alias_text.split()) > 4:
                    add(button_location, "low", f"alias '{alias_text}' is long", "Prefer short aliases that survive STT.")
                if alias_text in seen_aliases:
                    add(button_location, "high", f"duplicate alias '{alias_text}' in encounter", "Aliases must be unique within the current encounter.")
                else:
                    seen_aliases[alias_text] = index
            if action == "proceed" and not any(alias in normalized_aliases for alias in ("continue", "move", "leave", "proceed")):
                add(button_location, "low", "proceed action lacks simple movement alias", "Add a short movement alias such as move, leave, or continue.")

    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict):
                        check_event(event, f"room_events.{room_id}.{event.get('id', 'unknown')}")

    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                check_event(event, f"special_events.{event_id}")

    return findings


def load_patch(path: Path) -> dict[str, Any]:
    return load_json(path)


def cmd_generate(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    room = args.room or room_ids()[0]
    if room not in room_ids():
        raise SystemExit(f"Unknown room '{room}'. Known rooms: {', '.join(room_ids())}")
    if args.category and args.category not in event_category_ids():
        raise SystemExit(f"Unknown category '{args.category}'. Known categories: {', '.join(event_category_ids())}")

    source_seeds = load_source_seed_context(args)
    if args.mock:
        patch = mock_patch(room, args.category or "choice", source_seeds)
    else:
        patch = call_openai(build_prompt(args), args.model, patch_schema(), "scenario_patch")

    enrich_patch_voice_aliases(patch)

    errors = validation_errors(
        patch,
        allow_new_actions=args.allow_new_actions,
        expected_category=args.category or "",
        strict_tradeoffs=args.strict_tradeoffs,
    )
    if errors:
        patch["_validation_errors"] = errors

    out = Path(args.out) if args.out else GENERATED_DIR / "scenario_patch.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, patch)
    print(out)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    patch = load_patch(Path(args.patch))
    errors = validation_errors(patch, allow_new_actions=args.allow_new_actions, strict_tradeoffs=args.strict_tradeoffs)
    if not errors:
        print("ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_critique()
    else:
        critique = call_openai(build_critique_prompt(args), args.model, critique_schema(), "content_critique")

    out = Path(args.out) if args.out else GENERATED_DIR / "content_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_balance_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_balance_critique()
    else:
        critique = call_openai(
            build_balance_critique_prompt(args),
            args.model,
            balance_critique_schema(),
            "balance_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "balance_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_fun_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_fun_critique()
    else:
        critique = call_openai(
            build_fun_critique_prompt(args),
            args.model,
            fun_critique_schema(),
            "fun_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "fun_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_lore_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_lore_critique()
    else:
        critique = call_openai(
            build_lore_critique_prompt(args),
            args.model,
            lore_critique_schema(),
            "lore_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "lore_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_accessibility_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_accessibility_critique()
    else:
        critique = call_openai(
            build_accessibility_critique_prompt(args),
            args.model,
            accessibility_critique_schema(),
            "accessibility_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "accessibility_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_lore_brainstorm(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        brainstorm = mock_lore_brainstorm()
    else:
        brainstorm = call_openai(
            build_lore_brainstorm_prompt(args),
            args.model,
            lore_brainstorm_schema(),
            "lore_brainstorm",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "lore_brainstorm.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, brainstorm)
    print(out)
    return 0


def cmd_story_architect(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        architecture = mock_story_architect()
    else:
        architecture = call_openai(
            build_story_architect_prompt(args),
            args.model,
            story_architect_schema(),
            "story_architect",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "story_architect.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, architecture)
    print(out)
    return 0


def cmd_story_pilot(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        patch = mock_story_pilot()
    else:
        patch = call_openai(
            build_story_pilot_prompt(args),
            args.model,
            story_pilot_schema(),
            "story_pilot_patch",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "story_pilot_patch.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, patch)
    print(out)
    return 0


def _deep_merge_dict(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge_dict(target[key], value)
        elif key == "state_overrides" and isinstance(value, list) and isinstance(target.get(key), list):
            target[key].extend(value)
        else:
            target[key] = value
    return target


def _normalize_story_pilot_action_results(event: dict[str, Any]) -> None:
    action_results = event.get("action_results")
    if not isinstance(action_results, dict):
        return
    for result in action_results.values():
        if not isinstance(result, dict):
            continue
        if "result_lines" in result and "lines" not in result:
            result["lines"] = result.pop("result_lines")
        environment_changes = result.get("environment_state_changes")
        if isinstance(environment_changes, dict):
            normalized_changes: list[str] = []
            for key, value in environment_changes.items():
                if value in (None, False, 0, "0", "false", "False", "none", "None", "cleared", ""):
                    continue
                normalized_changes.append(str(key))
            result["environment_state_changes"] = normalized_changes


def _normalize_story_pilot_event(event: dict[str, Any]) -> None:
    _normalize_story_pilot_action_results(event)
    overrides = event.get("state_overrides")
    if not isinstance(overrides, list):
        return
    for override in overrides:
        if not isinstance(override, dict):
            continue
        override_event = override.get("event")
        if isinstance(override_event, dict):
            _normalize_story_pilot_event(override_event)


def cmd_apply_story_pilot(args: argparse.Namespace) -> int:
    patch_path = Path(args.patch)
    if not patch_path.is_absolute():
        patch_path = ROOT / patch_path
    patch = load_json(patch_path)
    events_payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms = rooms_payload.setdefault("rooms", [])
    if not isinstance(rooms, list):
        raise SystemExit("rooms must be a list")
    existing_room_ids = {str(room.get("id", "")) for room in rooms if isinstance(room, dict)}
    for room in patch.get("room_records", []):
        if not isinstance(room, dict):
            raise SystemExit("room_records entries must be objects")
        room_id = str(room.get("id", "")).strip()
        if not room_id:
            raise SystemExit("room record missing id")
        if room_id in existing_room_ids:
            for existing_room in rooms:
                if isinstance(existing_room, dict) and str(existing_room.get("id", "")) == room_id:
                    _deep_merge_dict(existing_room, room)
                    break
        else:
            rooms.append(room)
            existing_room_ids.add(room_id)

    special_events = events_payload.setdefault("special_events", {})
    if not isinstance(special_events, dict):
        raise SystemExit("special_events must be an object")

    for event in patch.get("special_events", []):
        if not isinstance(event, dict):
            raise SystemExit("special_events entries must be objects")
        _normalize_story_pilot_event(event)
        event_id = str(event.get("id", "")).strip()
        if not event_id:
            raise SystemExit("special event missing id")
        special_events[event_id] = event

    room_events = events_payload.setdefault("room_events", {})
    if not isinstance(room_events, dict):
        raise SystemExit("room_events must be an object")
    for room_event_record in patch.get("room_events", []):
        if not isinstance(room_event_record, dict):
            raise SystemExit("room_events entries must be objects")
        room_id = str(room_event_record.get("room_id", "")).strip()
        event = room_event_record.get("event", {})
        if not room_id:
            raise SystemExit("room_events entry missing room_id")
        if not isinstance(event, dict):
            raise SystemExit(f"{room_id}: room event must be an object")
        _normalize_story_pilot_event(event)
        room_event_list = room_events.setdefault(room_id, [])
        if not isinstance(room_event_list, list):
            raise SystemExit(f"room_events.{room_id} is not a list")
        event_id = str(event.get("id", "")).strip()
        replaced = False
        for index, existing_event in enumerate(room_event_list):
            if isinstance(existing_event, dict) and str(existing_event.get("id", "")) == event_id:
                room_event_list[index] = event
                replaced = True
                break
        if not replaced:
            room_event_list.append(event)

    for update in patch.get("room_event_updates", []):
        if not isinstance(update, dict):
            raise SystemExit("room_event_updates entries must be objects")
        room_id = str(update.get("room_id", "")).strip()
        event_id = str(update.get("event_id", "")).strip()
        merge_patch = update.get("merge", {})
        if not isinstance(merge_patch, dict):
            raise SystemExit(f"{room_id}.{event_id}: merge must be an object")
        _normalize_story_pilot_event(merge_patch)
        events = room_events.get(room_id, [])
        if not isinstance(events, list):
            raise SystemExit(f"room_events.{room_id} is not a list")
        matched = False
        for event in events:
            if isinstance(event, dict) and str(event.get("id", "")) == event_id:
                _deep_merge_dict(event, merge_patch)
                matched = True
                break
        if not matched:
            raise SystemExit(f"room_events.{room_id}: event '{event_id}' not found")

    enrich_events_payload_voice_aliases(events_payload)

    deck_room_pools = decks_payload.setdefault("room_pools", {})
    if not isinstance(deck_room_pools, dict):
        raise SystemExit("room_pools must be an object")
    for pool_update in patch.get("deck_pool_updates", []):
        if not isinstance(pool_update, dict):
            raise SystemExit("deck_pool_updates entries must be objects")
        pool_name = str(pool_update.get("pool", "")).strip()
        room_id = str(pool_update.get("room_id", "")).strip()
        if not pool_name or not room_id:
            raise SystemExit("deck_pool_updates entries need pool and room_id")
        pool = deck_room_pools.setdefault(pool_name, [])
        if not isinstance(pool, list):
            raise SystemExit(f"room_pools.{pool_name} is not a list")
        if room_id not in [str(value) for value in pool]:
            pool.append(room_id)

    if args.dry_run:
        print("dry-run ok")
        return 0

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print("applied story pilot patch")
    return 0


def cmd_validate_events(args: argparse.Namespace) -> int:
    errors = events_file_errors(strict_actions=args.strict_actions)
    if args.strict_tradeoffs:
        for finding in room_tradeoff_findings():
            errors.append(f"{finding['location']}: {finding['issue']}")
    if not errors:
        print("ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_audit_tradeoffs(args: argparse.Namespace) -> int:
    findings = room_tradeoff_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
    if not findings:
        print("ok")
        return 0
    for finding in findings:
        print(
            "{severity}: {location}: {issue} -> {recommendation}".format(
                severity=finding["severity"],
                location=finding["location"],
                issue=finding["issue"],
                recommendation=finding["recommendation"],
            )
        )
    return 1 if args.fail_on_findings else 0


def cmd_audit_depth(args: argparse.Namespace) -> int:
    findings = room_depth_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
    if not findings:
        print("ok")
        return 0
    for finding in findings:
        print(
            "{severity}: {location}: {issue} -> {recommendation}".format(
                severity=finding["severity"],
                location=finding["location"],
                issue=finding["issue"],
                recommendation=finding["recommendation"],
            )
        )
    return 1 if args.fail_on_findings else 0


def cmd_audit_story(args: argparse.Namespace) -> int:
    findings = room_story_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
    if not findings:
        print("ok")
        return 0
    for finding in findings:
        print(
            "{severity}: {location}: {issue} -> {recommendation}".format(
                severity=finding["severity"],
                location=finding["location"],
                issue=finding["issue"],
                recommendation=finding["recommendation"],
            )
        )
    return 1 if args.fail_on_findings else 0


def cmd_audit_writing(args: argparse.Namespace) -> int:
    findings = event_writing_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 0
    if not findings:
        print("ok")
        return 0
    for finding in findings:
        print(
            "{severity}: {location}: {issue} -> {recommendation}".format(
                severity=finding["severity"],
                location=finding["location"],
                issue=finding["issue"],
                recommendation=finding["recommendation"],
            )
        )
    return 0


def cmd_audit_accessibility(args: argparse.Namespace) -> int:
    findings = event_accessibility_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
    if not findings:
        print("ok")
        return 0
    for finding in findings:
        print(
            "{severity}: {location}: {issue} -> {recommendation}".format(
                severity=finding["severity"],
                location=finding["location"],
                issue=finding["issue"],
                recommendation=finding["recommendation"],
            )
        )
    return 1 if args.fail_on_findings else 0


def cmd_apply(args: argparse.Namespace) -> int:
    patch_path = Path(args.patch)
    patch = load_patch(patch_path)
    enrich_patch_voice_aliases(patch)
    errors = validation_errors(patch, allow_new_actions=args.allow_new_actions, strict_tradeoffs=args.strict_tradeoffs)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    events_payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms = rooms_payload.setdefault("rooms", [])
    if not isinstance(rooms, list):
        print("rooms must be a list", file=sys.stderr)
        return 1
    existing_room_ids = {str(room.get("id", "")) for room in rooms if isinstance(room, dict)}
    for room_record in patch.get("room_records", []):
        if not isinstance(room_record, dict):
            print("room_records entries must be objects", file=sys.stderr)
            return 1
        room_id = str(room_record.get("id", "")).strip()
        if room_id in existing_room_ids:
            for existing_room in rooms:
                if isinstance(existing_room, dict) and str(existing_room.get("id", "")) == room_id:
                    _deep_merge_dict(existing_room, room_record)
                    break
        else:
            rooms.append(room_record)
            existing_room_ids.add(room_id)

    room_events = events_payload.setdefault("room_events", {})
    for item in patch["events"]:
        room_id = item["room_id"]
        room_events.setdefault(room_id, [])
        room_events[room_id].append(item["event"])

    special_events = events_payload.setdefault("special_events", {})
    if not isinstance(special_events, dict):
        print("special_events must be an object", file=sys.stderr)
        return 1
    for event in patch.get("special_events", []):
        if not isinstance(event, dict):
            print("special_events entries must be objects", file=sys.stderr)
            return 1
        event_id = str(event.get("id", "")).strip()
        if not event_id:
            print("special event id is empty", file=sys.stderr)
            return 1
        special_events[event_id] = event

    deck_room_pools = decks_payload.setdefault("room_pools", {})
    if not isinstance(deck_room_pools, dict):
        print("room_pools must be an object", file=sys.stderr)
        return 1
    for pool_update in patch.get("deck_pool_updates", []):
        pool_name = str(pool_update.get("pool", "")).strip()
        room_id = str(pool_update.get("room_id", "")).strip()
        pool = deck_room_pools.setdefault(pool_name, [])
        if not isinstance(pool, list):
            print(f"room_pools.{pool_name} is not a list", file=sys.stderr)
            return 1
        if room_id not in [str(value) for value in pool]:
            pool.append(room_id)

    if args.dry_run:
        print("dry-run ok")
        return 0

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print(f"applied {len(patch['events'])} room event(s), {len(patch.get('special_events', []))} special event(s), {len(patch.get('room_records', []))} room record(s), and {len(patch.get('deck_pool_updates', []))} deck update(s)")
    return 0


def cmd_backfill_voice_aliases(args: argparse.Namespace) -> int:
    payload = load_json(EVENTS_PATH)
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    enrich_events_payload_voice_aliases(payload)
    after = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if before == after:
        print("ok")
        return 0
    if args.dry_run:
        print("voice aliases need backfill")
        return 0
    write_json(EVENTS_PATH, payload)
    print("backfilled voice aliases in events.json")
    return 0


def cmd_remember(args: argparse.Namespace) -> int:
    patch = load_patch(Path(args.patch))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "patch": patch,
        "notes": args.notes or "",
    }
    if args.accepted:
        append_jsonl(MEMORY_DIR / "accepted_scenarios.jsonl", record)
        print("remembered accepted scenario")
    elif args.rejected:
        append_jsonl(MEMORY_DIR / "rejected_scenarios.jsonl", record)
        print("remembered rejected scenario")
    else:
        raise SystemExit("Use --accepted or --rejected.")
    return 0


def cmd_remember_critique(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "vibe_alignment_score": critique.get("vibe_alignment_score"),
        "findings": critique.get("findings", [])[:5],
        "event_type_suggestions": critique.get("event_type_suggestions", []),
        "encounter_suggestions": critique.get("encounter_suggestions", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "action_system_suggestions": critique.get("action_system_suggestions", []),
        "next_generation_prompt": critique.get("next_generation_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(CRITIQUE_MEMORY_PATH, record)
    print("remembered critic guidance")
    return 0


def cmd_remember_balance(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "run_feel_score": critique.get("run_feel_score"),
        "vibe_balance_score": critique.get("vibe_balance_score"),
        "balance_findings": critique.get("balance_findings", [])[:6],
        "levers": critique.get("levers", []),
        "tuning_experiments": critique.get("tuning_experiments", []),
        "data_patch_suggestions": critique.get("data_patch_suggestions", []),
        "instrumentation_suggestions": critique.get("instrumentation_suggestions", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "next_balance_prompt": critique.get("next_balance_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(BALANCE_MEMORY_PATH, record)
    print("remembered balance guidance")
    return 0


def cmd_remember_fun(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "blind_read_summary": critique.get("blind_read_summary", ""),
        "fun_score": critique.get("fun_score"),
        "first_time_player_score": critique.get("first_time_player_score"),
        "build_score": critique.get("build_score"),
        "sequence_cohesion_score": critique.get("sequence_cohesion_score"),
        "organism_pressure_score": critique.get("organism_pressure_score"),
        "core_loop_diagnosis": critique.get("core_loop_diagnosis", ""),
        "blind_text_findings": critique.get("blind_text_findings", [])[:6],
        "choice_progression_findings": critique.get("choice_progression_findings", [])[:6],
        "payoff_gaps": critique.get("payoff_gaps", [])[:6],
        "not_fun_findings": critique.get("not_fun_findings", [])[:6],
        "organism_director_findings": critique.get("organism_director_findings", []),
        "decision_loop_rewrites": critique.get("decision_loop_rewrites", []),
        "ending_pressure_plan": critique.get("ending_pressure_plan", []),
        "content_priorities": critique.get("content_priorities", []),
        "system_priorities": critique.get("system_priorities", []),
        "minimum_game_shape": critique.get("minimum_game_shape", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "next_fun_prompt": critique.get("next_fun_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(FUN_MEMORY_PATH, record)
    print("remembered fun guidance")
    return 0


def cmd_remember_lore(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "lore_integrity_score": critique.get("lore_integrity_score"),
        "voice_integrity_score": critique.get("voice_integrity_score"),
        "continuity_findings": critique.get("continuity_findings", [])[:6],
        "voice_findings": critique.get("voice_findings", [])[:6],
        "knowledge_boundary_findings": critique.get("knowledge_boundary_findings", [])[:6],
        "chorus_usage_plan": critique.get("chorus_usage_plan", []),
        "lore_expansion_seeds": critique.get("lore_expansion_seeds", []),
        "rewrite_priorities": critique.get("rewrite_priorities", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "next_lore_prompt": critique.get("next_lore_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(LORE_MEMORY_PATH, record)
    print("remembered lore guidance")
    return 0


def cmd_remember_accessibility(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "eyes_free_score": critique.get("eyes_free_score"),
        "commandability_score": critique.get("commandability_score"),
        "tts_score": critique.get("tts_score"),
        "critical_findings": critique.get("critical_findings", [])[:8],
        "command_parser_findings": critique.get("command_parser_findings", [])[:8],
        "tts_findings": critique.get("tts_findings", [])[:8],
        "schema_recommendations": critique.get("schema_recommendations", []),
        "command_alias_plan": critique.get("command_alias_plan", []),
        "state_readout_plan": critique.get("state_readout_plan", []),
        "testing_plan": critique.get("testing_plan", []),
        "guide_updates": critique.get("guide_updates", []),
        "next_accessibility_prompt": critique.get("next_accessibility_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(ACCESSIBILITY_MEMORY_PATH, record)
    print("remembered accessibility guidance")
    return 0


def cmd_remember_lore_brainstorm(args: argparse.Namespace) -> int:
    brainstorm = load_json(Path(args.brainstorm))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": brainstorm.get("summary", ""),
        "design_thesis": brainstorm.get("design_thesis", ""),
        "factions": brainstorm.get("factions", [])[:6],
        "recurring_characters": brainstorm.get("recurring_characters", [])[:6],
        "organism_lore": brainstorm.get("organism_lore", [])[:6],
        "lore_fragments": brainstorm.get("lore_fragments", [])[:8],
        "relationships": brainstorm.get("relationships", []),
        "reveal_paths": brainstorm.get("reveal_paths", []),
        "mechanic_hooks": brainstorm.get("mechanic_hooks", []),
        "guardrails": brainstorm.get("guardrails", []),
        "next_lore_prompt": brainstorm.get("next_lore_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(LORE_BRAINSTORM_MEMORY_PATH, record)
    print("remembered lore brainstorm guidance")
    return 0


def cmd_remember_story_architecture(args: argparse.Namespace) -> int:
    architecture = load_json(Path(args.architecture))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": architecture.get("summary", ""),
        "story_diagnosis": architecture.get("story_diagnosis", ""),
        "missing_story_primitives": architecture.get("missing_story_primitives", []),
        "character_arcs": architecture.get("character_arcs", [])[:6],
        "first_15_minute_spine": architecture.get("first_15_minute_spine", []),
        "followup_encounter_plan": architecture.get("followup_encounter_plan", [])[:10],
        "pilot_arc_recommendation": architecture.get("pilot_arc_recommendation", {}),
        "story_rules": architecture.get("story_rules", []),
        "patch_strategy": architecture.get("patch_strategy", []),
        "next_story_prompt": architecture.get("next_story_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(STORY_ARCHITECTURE_MEMORY_PATH, record)
    print("remembered story architecture guidance")
    return 0


def cmd_context(_: argparse.Namespace) -> int:
    print(json.dumps(game_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_balance_context(_: argparse.Namespace) -> int:
    print(json.dumps(balance_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_fun_context(_: argparse.Namespace) -> int:
    print(json.dumps(fun_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_lore_context(_: argparse.Namespace) -> int:
    print(json.dumps(lore_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_accessibility_context(_: argparse.Namespace) -> int:
    print(json.dumps(accessibility_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_lore_brainstorm_context(_: argparse.Namespace) -> int:
    print(json.dumps(lore_brainstorm_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_story_architect_context(_: argparse.Namespace) -> int:
    print(json.dumps(story_architect_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_vibe(_: argparse.Namespace) -> int:
    print(load_vibe_guide())
    return 0


def cmd_lore_guide(_: argparse.Namespace) -> int:
    print(load_lore_guide())
    return 0


def cmd_setting_backbone(_: argparse.Namespace) -> int:
    print(load_setting_backbone())
    return 0


def cmd_story_room_contract(_: argparse.Namespace) -> int:
    print(load_story_room_contract())
    return 0


def cmd_corpus_room_generation(_: argparse.Namespace) -> int:
    print(load_corpus_room_generation())
    return 0


def cmd_ending_maze(_: argparse.Namespace) -> int:
    print(load_ending_maze_architecture())
    return 0


def cmd_hymn_corpus_voice(_: argparse.Namespace) -> int:
    print(load_hymn_corpus_voice())
    return 0


def cmd_content_authorship(_: argparse.Namespace) -> int:
    print(load_content_authorship_workflow())
    return 0


def cmd_accessibility_guide(_: argparse.Namespace) -> int:
    print(load_accessibility_guide())
    return 0


def cmd_categories(_: argparse.Namespace) -> int:
    print(json.dumps({"categories": event_categories()}, indent=2, ensure_ascii=False))
    return 0


def cmd_sources(_: argparse.Namespace) -> int:
    print(read_text(MEMORY_DIR / "inspiration_sources.md"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Generate a scenario patch.")
    generate.add_argument("--room", help="Target room id.")
    generate.add_argument("--category", help="Target event category id.")
    generate.add_argument("--count", type=int, default=1, help="Number of events to request.")
    generate.add_argument("--prompt", default="Create playable Revelation room scenarios.")
    generate.add_argument("--out", help="Output patch path.")
    generate.add_argument("--model", default=DEFAULT_MODEL)
    generate.add_argument("--allow-new-actions", action="store_true")
    generate.add_argument("--strict-tradeoffs", action="store_true", help="Require every non-transition room event in the patch to have at least two commandable buttons.")
    generate.add_argument("--source-seeds", help="Optional Fleshpunk seed JSON path. Defaults to generated/corpus/fleshpunk_seeds.json when any source filter is used.")
    generate.add_argument("--source-seed", action="append", help="Specific source seed id to include. Repeatable.")
    generate.add_argument("--source-work", help="Filter source seeds by source_id.")
    generate.add_argument("--source-motif", help="Filter source seeds by motif_id.")
    generate.add_argument("--source-seed-count", type=int, default=3, help="Maximum number of source seeds to include in the generation context.")
    generate.add_argument("--corpus-fragments", help="Corpus fragment JSON path. Revelation usually uses generated/corpus/index/chunks.jsonl through --corpus-index.")
    generate.add_argument("--corpus-fragment", action="append", help="Specific corpus fragment id to include. Repeatable.")
    generate.add_argument("--corpus-fragment-count", type=int, default=12, help="Maximum corpus fragments to include in the generation context.")
    generate.add_argument("--corpus-index", help="Corpus index path. Defaults to generated/corpus/index/chunks.jsonl for Revelation when present.")
    generate.add_argument("--corpus-need", action="append", help="Specific corpus index need id to include. Repeatable.")
    generate.add_argument("--corpus-source", action="append", help="Specific corpus source id to include from the index. Repeatable.")
    generate.add_argument("--corpus-role", action="append", help="Specific corpus artifact role to include from the index. Repeatable.")
    generate.add_argument("--corpus-index-count", type=int, default=12, help="Maximum corpus index artifacts to include in the generation context.")
    generate.add_argument("--context-lite", action="store_true", help="Use compact project context for source-driven drafts.")
    generate.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    generate.set_defaults(func=cmd_generate)

    critique = sub.add_parser("critique", help="Critique content against the vibe guide.")
    critique.add_argument("--patch", help="Optional scenario patch to critique instead of events.json.")
    critique.add_argument("--focus", default="Critique vibe fit, choice pressure, event categories, encounter opportunities, and missing guide rules.")
    critique.add_argument("--out", help="Output critique JSON path.")
    critique.add_argument("--model", default=DEFAULT_MODEL)
    critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    critique.set_defaults(func=cmd_critique)

    balance_critique = sub.add_parser("balance-critique", help="Critique balance and run feel against the vibe guide.")
    balance_critique.add_argument("--focus", default="Critique run feel, balance levers, pressure cadence, reward costs, and how tuning supports the vibe.")
    balance_critique.add_argument("--out", help="Output balance critique JSON path.")
    balance_critique.add_argument("--model", default=DEFAULT_MODEL)
    balance_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    balance_critique.set_defaults(func=cmd_balance_critique)

    fun_critique = sub.add_parser("fun-critique", help="Critique blind first-time fun, build, choice progression, and organism pressure.")
    fun_critique.add_argument("--focus", default="Critique blind first-time user-facing text and choices, whether rooms build into a run, organism pressure, repeated-choice consequences, ending gravity, and stat-only choices.")
    fun_critique.add_argument("--out", help="Output fun critique JSON path.")
    fun_critique.add_argument("--model", default=DEFAULT_MODEL)
    fun_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    fun_critique.set_defaults(func=cmd_fun_critique)

    lore_critique = sub.add_parser("lore-critique", help="Critique lore continuity, voice, Chorus usage, and knowledge boundaries.")
    lore_critique.add_argument("--focus", default="Critique lore continuity, Hymn's knowledge boundaries, Chorus report cadence, corruption clarity, and flavor preservation.")
    lore_critique.add_argument("--out", help="Output lore critique JSON path.")
    lore_critique.add_argument("--model", default=DEFAULT_MODEL)
    lore_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    lore_critique.set_defaults(func=cmd_lore_critique)

    accessibility_critique = sub.add_parser("accessibility-critique", help="Critique eyes-free playability, commandability, and TTS/audio UX.")
    accessibility_critique.add_argument("--focus", default="Critique eyes-free playability, command aliases, TTS phrasing, state readouts, and audio-only clarity.")
    accessibility_critique.add_argument("--out", help="Output accessibility critique JSON path.")
    accessibility_critique.add_argument("--model", default=DEFAULT_MODEL)
    accessibility_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    accessibility_critique.set_defaults(func=cmd_accessibility_critique)

    lore_brainstorm = sub.add_parser("lore-brainstorm", help="Brainstorm lore concepts with reveal boundaries and gameplay hooks.")
    lore_brainstorm.add_argument("--focus", default="Brainstorm factions, recurring characters, relationships, lore fragments, reveal paths, and gameplay hooks.")
    lore_brainstorm.add_argument("--count", type=int, default=6, help="Approximate number of concepts to request per major section.")
    lore_brainstorm.add_argument("--out", help="Output lore brainstorm JSON path.")
    lore_brainstorm.add_argument("--model", default=DEFAULT_MODEL)
    lore_brainstorm.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    lore_brainstorm.set_defaults(func=cmd_lore_brainstorm)

    story_architect = sub.add_parser("story-architect", help="Plan playable character arcs and follow-up encounter story structure from current repo data.")
    story_architect.add_argument("--focus", default="Plan the smallest character-driven story spine that turns the current room/event stack from strong vibe into a playable story with recurring characters, follow-up scenes, escalation, and payoff.")
    story_architect.add_argument("--out", help="Output story architecture JSON path.")
    story_architect.add_argument("--model", default=DEFAULT_MODEL)
    story_architect.add_argument("--corpus-fragments", help="Corpus fragment JSON path.")
    story_architect.add_argument("--corpus-fragment", action="append", help="Specific corpus fragment id to include. Repeatable.")
    story_architect.add_argument("--corpus-fragment-count", type=int, default=16, help="Maximum corpus fragments to include in the story architecture context.")
    story_architect.add_argument("--corpus-index", help="Corpus index path. Defaults to generated/corpus/index/chunks.jsonl for Revelation when present.")
    story_architect.add_argument("--corpus-need", action="append", help="Specific corpus index need id to include. Repeatable.")
    story_architect.add_argument("--corpus-source", action="append", help="Specific corpus source id to include from the index. Repeatable.")
    story_architect.add_argument("--corpus-role", action="append", help="Specific corpus artifact role to include from the index. Repeatable.")
    story_architect.add_argument("--corpus-index-count", type=int, default=18, help="Maximum corpus index artifacts to include in the story architecture context.")
    story_architect.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    story_architect.set_defaults(func=cmd_story_architect)

    story_pilot = sub.add_parser("story-pilot", help="Generate an OpenAI-authored story pilot patch from story architecture guidance.")
    story_pilot.add_argument("--focus", default="Generate the five-scene pilot story patch recommended by the story architect. Use existing queued special event IDs where possible, add state_overrides to current room events, and keep required_engine_changes empty unless absolutely necessary.")
    story_pilot.add_argument("--out", help="Output story pilot patch JSON path.")
    story_pilot.add_argument("--model", default=DEFAULT_MODEL)
    story_pilot.add_argument("--corpus-fragments", help="Corpus fragment JSON path.")
    story_pilot.add_argument("--corpus-fragment", action="append", help="Specific corpus fragment id to include. Repeatable.")
    story_pilot.add_argument("--corpus-fragment-count", type=int, default=16, help="Maximum corpus fragments to include in the story pilot context.")
    story_pilot.add_argument("--corpus-index", help="Corpus index path. Defaults to generated/corpus/index/chunks.jsonl for Revelation when present.")
    story_pilot.add_argument("--corpus-need", action="append", help="Specific corpus index need id to include. Repeatable.")
    story_pilot.add_argument("--corpus-source", action="append", help="Specific corpus source id to include from the index. Repeatable.")
    story_pilot.add_argument("--corpus-role", action="append", help="Specific corpus artifact role to include from the index. Repeatable.")
    story_pilot.add_argument("--corpus-index-count", type=int, default=18, help="Maximum corpus index artifacts to include in the story pilot context.")
    story_pilot.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    story_pilot.set_defaults(func=cmd_story_pilot)

    validate = sub.add_parser("validate", help="Validate a scenario patch.")
    validate.add_argument("patch")
    validate.add_argument("--allow-new-actions", action="store_true")
    validate.add_argument("--strict-tradeoffs", action="store_true", help="Require every non-transition room event in the patch to have at least two commandable buttons.")
    validate.set_defaults(func=cmd_validate)

    validate_events = sub.add_parser("validate-events", help="Validate events.json against broad categories.")
    validate_events.add_argument("--strict-actions", action="store_true")
    validate_events.add_argument("--strict-tradeoffs", action="store_true", help="Fail when room events have fewer than two commandable buttons, except transition events.")
    validate_events.set_defaults(func=cmd_validate_events)

    audit_writing = sub.add_parser("audit-writing", help="Audit events.json for weak cause/effect, generic buttons, and voice drift.")
    audit_writing.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_writing.set_defaults(func=cmd_audit_writing)

    audit_accessibility = sub.add_parser("audit-accessibility", help="Audit events.json for eyes-free commandability and TTS risks.")
    audit_accessibility.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_accessibility.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when accessibility findings are present.")
    audit_accessibility.set_defaults(func=cmd_audit_accessibility)

    audit_tradeoffs = sub.add_parser("audit-tradeoffs", help="Audit room events for one-button dead ends and missing tradeoffs.")
    audit_tradeoffs.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_tradeoffs.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when tradeoff findings are present.")
    audit_tradeoffs.set_defaults(func=cmd_audit_tradeoffs)

    audit_depth = sub.add_parser("audit-depth", help="Audit room depth, delayed consequence, memory hooks, and interactable actors.")
    audit_depth.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_depth.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when depth findings are present.")
    audit_depth.set_defaults(func=cmd_audit_depth)

    audit_story = sub.add_parser("audit-story", help="Audit rooms for setting backbone, faction, character, animal infrastructure, and cross-run story motion.")
    audit_story.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_story.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when story findings are present.")
    audit_story.set_defaults(func=cmd_audit_story)

    apply = sub.add_parser("apply", help="Apply a valid JSON-only scenario patch.")
    apply.add_argument("patch")
    apply.add_argument("--allow-new-actions", action="store_true")
    apply.add_argument("--strict-tradeoffs", action="store_true", help="Require every non-transition room event in the patch to have at least two commandable buttons.")
    apply.add_argument("--dry-run", action="store_true")
    apply.set_defaults(func=cmd_apply)

    apply_story_pilot = sub.add_parser("apply-story-pilot", help="Apply a story pilot patch with special_events and room_event_updates.")
    apply_story_pilot.add_argument("patch")
    apply_story_pilot.add_argument("--dry-run", action="store_true")
    apply_story_pilot.set_defaults(func=cmd_apply_story_pilot)

    backfill_aliases = sub.add_parser("backfill-voice-aliases", help="Rebuild voice_aliases across the current events.json deck.")
    backfill_aliases.add_argument("--dry-run", action="store_true", help="Check whether backfill would change events.json without writing.")
    backfill_aliases.set_defaults(func=cmd_backfill_voice_aliases)

    remember = sub.add_parser("remember", help="Record accepted or rejected feedback.")
    remember.add_argument("patch")
    remember.add_argument("--accepted", action="store_true")
    remember.add_argument("--rejected", action="store_true")
    remember.add_argument("--notes", default="")
    remember.set_defaults(func=cmd_remember)

    remember_critique = sub.add_parser("remember-critique", help="Store critique guidance for future generation.")
    remember_critique.add_argument("critique")
    remember_critique.add_argument("--notes", default="")
    remember_critique.set_defaults(func=cmd_remember_critique)

    remember_balance = sub.add_parser("remember-balance", help="Store balance critique guidance for future generation.")
    remember_balance.add_argument("critique")
    remember_balance.add_argument("--notes", default="")
    remember_balance.set_defaults(func=cmd_remember_balance)

    remember_fun = sub.add_parser("remember-fun", help="Store fun-factor critique guidance for future generation.")
    remember_fun.add_argument("critique")
    remember_fun.add_argument("--notes", default="")
    remember_fun.set_defaults(func=cmd_remember_fun)

    remember_lore = sub.add_parser("remember-lore", help="Store lore-master critique guidance for future generation.")
    remember_lore.add_argument("critique")
    remember_lore.add_argument("--notes", default="")
    remember_lore.set_defaults(func=cmd_remember_lore)

    remember_accessibility = sub.add_parser("remember-accessibility", help="Store accessibility critique guidance for future generation.")
    remember_accessibility.add_argument("critique")
    remember_accessibility.add_argument("--notes", default="")
    remember_accessibility.set_defaults(func=cmd_remember_accessibility)

    remember_lore_brainstorm = sub.add_parser("remember-lore-brainstorm", help="Store lore brainstorm guidance for future generation.")
    remember_lore_brainstorm.add_argument("brainstorm")
    remember_lore_brainstorm.add_argument("--notes", default="")
    remember_lore_brainstorm.set_defaults(func=cmd_remember_lore_brainstorm)

    remember_story_architecture = sub.add_parser("remember-story-architecture", help="Store story architecture guidance for future generation.")
    remember_story_architecture.add_argument("architecture")
    remember_story_architecture.add_argument("--notes", default="")
    remember_story_architecture.set_defaults(func=cmd_remember_story_architecture)

    context = sub.add_parser("context", help="Print compact game context.")
    context.set_defaults(func=cmd_context)

    balance_context_parser = sub.add_parser("balance-context", help="Print balance levers and run-feel context.")
    balance_context_parser.set_defaults(func=cmd_balance_context)

    fun_context_parser = sub.add_parser("fun-context", help="Print fun-factor and organism pressure context.")
    fun_context_parser.set_defaults(func=cmd_fun_context)

    lore_context_parser = sub.add_parser("lore-context", help="Print lore continuity and voice context.")
    lore_context_parser.set_defaults(func=cmd_lore_context)

    accessibility_context_parser = sub.add_parser("accessibility-context", help="Print eyes-free playability and commandability context.")
    accessibility_context_parser.set_defaults(func=cmd_accessibility_context)

    lore_brainstorm_context_parser = sub.add_parser("lore-brainstorm-context", help="Print lore brainstorm context.")
    lore_brainstorm_context_parser.set_defaults(func=cmd_lore_brainstorm_context)

    story_architect_context_parser = sub.add_parser("story-architect-context", help="Print story architecture packet context.")
    story_architect_context_parser.set_defaults(func=cmd_story_architect_context)

    vibe = sub.add_parser("vibe", help="Print the vibe and design guide.")
    vibe.set_defaults(func=cmd_vibe)

    lore_guide = sub.add_parser("lore-guide", help="Print the lore guide.")
    lore_guide.set_defaults(func=cmd_lore_guide)

    setting_backbone = sub.add_parser("setting-backbone", help="Print the setting backbone.")
    setting_backbone.set_defaults(func=cmd_setting_backbone)

    story_room_contract = sub.add_parser("story-room-contract", help="Print the story room contract.")
    story_room_contract.set_defaults(func=cmd_story_room_contract)

    corpus_room_generation = sub.add_parser("corpus-room-generation", help="Print the corpus-first room generation guide.")
    corpus_room_generation.set_defaults(func=cmd_corpus_room_generation)

    ending_maze = sub.add_parser("ending-maze", help="Print the ending maze architecture.")
    ending_maze.set_defaults(func=cmd_ending_maze)

    hymn_corpus_voice = sub.add_parser("hymn-corpus-voice", help="Print the Hymn corpus voice guide.")
    hymn_corpus_voice.set_defaults(func=cmd_hymn_corpus_voice)

    content_authorship = sub.add_parser("content-authorship", help="Print the content authorship workflow.")
    content_authorship.set_defaults(func=cmd_content_authorship)

    accessibility_guide = sub.add_parser("accessibility-guide", help="Print the accessibility guide.")
    accessibility_guide.set_defaults(func=cmd_accessibility_guide)

    categories = sub.add_parser("categories", help="Print broad event categories.")
    categories.set_defaults(func=cmd_categories)

    sources = sub.add_parser("sources", help="Print inspiration source notes.")
    sources.set_defaults(func=cmd_sources)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except json.JSONDecodeError as exc:
        print(textwrap.fill(f"JSON error: {exc}", width=88), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
