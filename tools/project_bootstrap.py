#!/usr/bin/env python3
"""Print project orientation and validate common Revelation data wiring."""

from __future__ import annotations

import argparse
import configparser
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EVENTS_PATH = ROOT / "events.json"
ROOMS_PATH = ROOT / "room_dialogue.json"
DECKS_PATH = ROOT / "encounter_decks.json"
POST_UPDATE_EVENTS_PATH = ROOT / "events_post_update.json"
POST_UPDATE_ROOMS_PATH = ROOT / "rooms_post_update.json"
POST_UPDATE_DECKS_PATH = ROOT / "encounter_decks_post_update.json"
ENEMIES_PATH = ROOT / "enemies.json"
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
PROJECT_PATH = ROOT / "project.godot"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"
CONTENT_AUTHORSHIP_WORKFLOW_PATH = ROOT / ".agent-memory" / "content_authorship_workflow.md"

ACTION_CASE_RE_TEMPLATE = r'^{indent}"([^"]+)":\s*$'
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
    "dry_name_protocol",
    "extend_eval",
    "full_disclosure",
    "hold_iyad",
    "quarantine_forms",
    "report_word_gap",
    "return_ross",
    "support_owen",
    "torah_exception",
    "torah_speaks",
    "watch_quietly",
}
STORY_ENGINE_CONTENT_TRACK = "revelation_packets_v1"
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
    "symbiote_offer",
    "shipboard_dispute",
    "signal_anomaly",
}
ENVIRONMENT_GROUP_KEYS = {
    "encounter_family",
    "environment_id",
    "environment",
    "environment_family",
    "object_class",
    "operation_type",
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
    "route_state_changes",
    "officer_state_changes",
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_project_config() -> dict[str, Any]:
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str
    parser.read_string("[root]\n" + read_text(PROJECT_PATH))
    return {
        "name": parser.get("application", "config/name", fallback="unknown").strip('"'),
        "main_scene": parser.get("application", "run/main_scene", fallback="unknown").strip('"'),
        "features": parser.get("application", "config/features", fallback="unknown"),
        "autoloads": list(parser["autoload"].keys()) if parser.has_section("autoload") else [],
        "viewport": "%sx%s" % (
            parser.get("display", "window/size/viewport_width", fallback="?"),
            parser.get("display", "window/size/viewport_height", fallback="?"),
        ),
    }


def get_git_status() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ["git unavailable"]
    if result.returncode != 0:
        return [line for line in result.stderr.splitlines() if line.strip()] or ["git status failed"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def ids_from_array_file(path: Path, key: str) -> set[str]:
    payload = load_json(path)
    records = payload.get(key, [])
    if not isinstance(records, list):
        return set()
    return {str(record.get("id", "")) for record in records if isinstance(record, dict) and record.get("id")}


def active_data_paths() -> dict[str, Path]:
    return {
        "rooms": POST_UPDATE_ROOMS_PATH if POST_UPDATE_ROOMS_PATH.exists() else ROOMS_PATH,
        "events": POST_UPDATE_EVENTS_PATH if POST_UPDATE_EVENTS_PATH.exists() else EVENTS_PATH,
        "decks": POST_UPDATE_DECKS_PATH if POST_UPDATE_DECKS_PATH.exists() else DECKS_PATH,
    }


def implemented_actions() -> set[str]:
    source = read_text(RUN_MANAGER_PATH)
    match_start = source.find("match action_id:")
    if match_start == -1:
        actions: set[str] = set()
    else:
        action_tail = source[match_start:]
        match_line = re.search(r'^([ \t]*)match action_id:\s*$', action_tail, re.MULTILINE)
        first_case = re.search(r'^([ \t]*)"[^"]+":\s*$', action_tail, re.MULTILINE)
        case_indent = first_case.group(1) if first_case else (match_line.group(1) + "\t") if match_line else "\t\t"
        default_re = re.compile(rf'^{re.escape(case_indent)}_:\s*$', re.MULTILINE)
        default_match = default_re.search(action_tail)
        if default_match:
            action_block = action_tail[:default_match.start()]
        else:
            action_block = action_tail
        action_re = re.compile(ACTION_CASE_RE_TEMPLATE.format(indent=re.escape(case_indent)), re.MULTILINE)
        actions = set(action_re.findall(action_block))
    actions.update({"proceed", "restart_run"})
    return actions.intersection(FORWARD_ACTIONS)


def iter_events(events_payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    room_events = events_payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, room_event_list in room_events.items():
            if not isinstance(room_event_list, list):
                continue
            for event in room_event_list:
                if isinstance(event, dict):
                    events.append((f"{room_id}/{event.get('id', '<missing-id>')}", event))

    special_events = events_payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                events.append((f"special/{event_id}", event))
    return events


def has_delayed_consequence(event: dict[str, Any]) -> bool:
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
    text = f"{event.get('line_1', '')} {event.get('line_2', '')}".lower()
    return any(term in text for term in ("later", "again", "return", "remembers", "learns", "claim", "debt", "scent", "future", "next"))


def has_environment_group(room_record: dict[str, Any]) -> bool:
    return any(room_record.get(key) for key in ENVIRONMENT_GROUP_KEYS)


def has_environment_echo_plan(room_record: dict[str, Any]) -> bool:
    return any(room_record.get(key) for key in ENVIRONMENT_ECHO_KEYS)


def environment_id_for_room(room_id: str, room_record: dict[str, Any]) -> str:
    for key in ENVIRONMENT_GROUP_KEYS:
        value = str(room_record.get(key, "")).strip()
        if value:
            return value
    return room_id


def corpus_influence_records(room_record: dict[str, Any]) -> list[dict[str, Any]]:
    for key in CORPUS_INFLUENCE_KEYS:
        if key not in room_record:
            continue
        records = room_record.get(key, [])
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
    return []


def has_specific_corpus_influence(room_record: dict[str, Any]) -> bool:
    for record in corpus_influence_records(room_record):
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


def has_ending_vector(room_record: dict[str, Any]) -> bool:
    vectors = room_record.get("ending_vectors", [])
    return isinstance(vectors, list) and any(isinstance(vector, dict) and vector.get("id") for vector in vectors)


def has_mutation_hooks(room_record: dict[str, Any]) -> bool:
    hooks = room_record.get("mutation_hooks", [])
    if isinstance(hooks, list) and any(isinstance(hook, dict) and hook.get("capability") for hook in hooks):
        return True
    adaptation_hooks = room_record.get("adaptation_hooks", [])
    equipment_hooks = room_record.get("equipment_hooks", [])
    procedure_hooks = room_record.get("procedure_hooks", [])
    return any(
        isinstance(hooks_value, list)
        and any(isinstance(hook, dict) and (hook.get("capability") or hook.get("procedure") or hook.get("equipment")) for hook in hooks_value)
        for hooks_value in (adaptation_hooks, equipment_hooks, procedure_hooks)
    )


def is_narrow_room_role(room_record: dict[str, Any]) -> bool:
    room_role = str(room_record.get("room_role", "")).strip()
    if room_role in NARROW_ROOM_ROLES:
        return True
    tags = room_record.get("tags", [])
    return isinstance(tags, list) and any(str(tag) in NARROW_ROOM_ROLES for tag in tags)


def has_room_memory_change(event: dict[str, Any]) -> bool:
    return any(event.get(key) for key in ROOM_MEMORY_KEYS)


def has_action_specific_result(event: dict[str, Any]) -> bool:
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


def has_default_only_followups(event: dict[str, Any]) -> bool:
    followups = event.get("story_followups")
    if not isinstance(followups, dict):
        return False
    return bool(followups) and set(str(key) for key in followups.keys()) == {"default"}


def creative_room_findings(rooms_payload: dict[str, Any], events_payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    if not isinstance(special_events, dict):
        special_events = {}
    if not isinstance(room_events, dict):
        return ["room_events is not an object; creative room critique cannot run"]

    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and room.get("id")
    }
    required_story_keys = (
        "officer_reports",
        "crew_state_hooks",
        "ship_state_hooks",
        "resource_stakes",
        "black_hole_anomaly",
        "followup_vectors",
        "progression_state",
    )
    story_engine_track = str(rooms_payload.get("content_track", "")) == STORY_ENGINE_CONTENT_TRACK
    environment_event_counts: dict[str, int] = {}
    if story_engine_track:
        for room_id, events in room_events.items():
            room_record = rooms_by_id.get(str(room_id), {})
            environment_id = environment_id_for_room(str(room_id), room_record)
            event_count = len(events) if isinstance(events, list) else 0
            environment_event_counts[environment_id] = environment_event_counts.get(environment_id, 0) + event_count

    for room_id, events in sorted(room_events.items()):
        if not isinstance(events, list):
            findings.append(f"{room_id}: room events are not a list")
            continue
        room_record = rooms_by_id.get(str(room_id), {})
        narrow_room = is_narrow_room_role(room_record)
        environment_id = environment_id_for_room(str(room_id), room_record)
        family_event_count = environment_event_counts.get(environment_id, len(events)) if story_engine_track else len(events)
        if family_event_count < 3 and not narrow_room:
            findings.append(f"{room_id}: thin environment family with only {family_event_count} event{'s' if family_event_count != 1 else ''}")
        if not narrow_room and not any(isinstance(event, dict) and has_delayed_consequence(event) for event in events):
            findings.append(f"{room_id}: no explicit delayed consequence or memory hook")
        if story_engine_track and not has_environment_group(room_record):
            findings.append(f"{room_id}: no explicit environment grouping")
        if story_engine_track and not narrow_room and not has_environment_echo_plan(room_record):
            findings.append(f"{room_id}: no later-instance/environment echo plan")
        if story_engine_track and not has_specific_corpus_influence(room_record):
            findings.append(f"{room_id}: no specific corpus writing influence")
        if story_engine_track and not narrow_room and not has_ending_vector(room_record):
            findings.append(f"{room_id}: no ending vector")
        if story_engine_track and not narrow_room and not has_mutation_hooks(room_record):
            findings.append(f"{room_id}: no adaptation/equipment/procedure openings")
        scoped_story_keys = required_story_keys
        if narrow_room:
            scoped_story_keys = (
                "officer_reports",
                "crew_state_hooks",
                "ship_state_hooks",
                "resource_stakes",
                "progression_state",
            )
        missing_story_keys = [key for key in scoped_story_keys if not room_record.get(key)]
        if missing_story_keys:
            findings.append(f"{room_id}: missing story backbone keys ({', '.join(missing_story_keys)})")
        if story_engine_track and not any(isinstance(event, dict) and has_room_memory_change(event) for event in events):
            findings.append(f"{room_id}: no explicit environment memory/state changes")
        for event in events:
            if not isinstance(event, dict):
                continue
            if story_engine_track and not has_action_specific_result(event):
                findings.append(f"{room_id}/{event.get('id', '<missing-id>')}: relies on generic legacy action results")
            buttons = event.get("buttons", [])
            commandable_buttons = sum(1 for button in buttons if isinstance(button, dict)) if isinstance(buttons, list) else 0
            if story_engine_track and commandable_buttons > 1 and has_default_only_followups(event):
                findings.append(f"{room_id}/{event.get('id', '<missing-id>')}: all choices enqueue the same default follow-up")
            for followup in story_followup_entries(event):
                if int(followup.get("delay_rooms", 0)) < 1 and not bool(followup.get("immediate", False)):
                    findings.append(f"{room_id}: story follow-up on {event.get('id', '<missing-id>')} has no delay_rooms >= 1 or immediate flag")
                followup_id = str(followup.get("event_id", ""))
                followup = special_events.get(followup_id, {})
                if not isinstance(followup, dict):
                    findings.append(f"{room_id}: story_followups references missing special event {followup_id}")
                elif bool(followup.get("reactivate_on_reshuffle", True)):
                    findings.append(f"{room_id}: story follow-up {followup_id} can retrigger in the same run")
    return findings


def story_followup_ids(event: dict[str, Any]) -> list[str]:
    return sorted(set(str(followup.get("event_id", "")) for followup in story_followup_entries(event) if str(followup.get("event_id", ""))))


def story_followup_entries(event: dict[str, Any]) -> list[dict[str, Any]]:
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


def event_handles_action(event: dict[str, Any], action: str) -> bool:
    if not action:
        return False
    base_action = action.split(":", 1)[0]
    for key in ACTION_RESULT_KEYS:
        values = event.get(key, {})
        if isinstance(values, dict) and (action in values or base_action in values):
            return True
    return False


def collect_event_facts() -> dict[str, Any]:
    data_paths = active_data_paths()
    events_payload = load_json(data_paths["events"])
    rooms_payload = load_json(data_paths["rooms"])
    decks_payload = load_json(data_paths["decks"])
    content_track = str(rooms_payload.get("content_track", "legacy"))

    rooms = rooms_payload.get("rooms", [])
    room_ids = {str(room.get("id", "")) for room in rooms if isinstance(room, dict) and room.get("id")}
    enemies = ids_from_array_file(ENEMIES_PATH, "enemies")
    mutations = ids_from_array_file(MUTATIONS_PATH, "mutations")
    symbiotes = ids_from_array_file(SYMBIOTES_PATH, "symbiotes")
    actions = implemented_actions()

    unhandled_actions: dict[str, list[str]] = {}
    missing_refs: list[str] = []
    grail_warnings: list[str] = []
    duplicate_event_ids: list[str] = []
    event_ids: set[str] = set()

    for location, event in iter_events(events_payload):
        event_id = str(event.get("id", ""))
        if event_id:
            if event_id in event_ids:
                duplicate_event_ids.append(event_id)
            event_ids.add(event_id)

        for key, known_ids in (
            ("enemy_id", enemies),
            ("mutation_id", mutations),
            ("symbiote_id", symbiotes),
        ):
            ref = str(event.get(key, ""))
            if ref and ref not in known_ids:
                missing_refs.append(f"{location}: unknown {key} '{ref}'")

        if str(event.get("speaker", "")) == "Merchant":
            grail_warnings.append(f"{location}: direct Merchant speaker is legacy; new text should be Hymn narration")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list):
            continue
        for button in buttons:
            if not isinstance(button, dict):
                continue
            action = str(button.get("action", ""))
            if action and action not in actions and not event_handles_action(event, action):
                unhandled_actions.setdefault(action, []).append(location)
            if action == "take_mutation" and content_track not in {"post_update_text_only", STORY_ENGINE_CONTENT_TRACK} and not location.startswith("special/merchant"):
                grail_warnings.append(f"{location}: room-level take_mutation is legacy; new mutations should come through shop/merchant flow")

    return {
        "rooms": sorted(room_ids),
        "event_count": len(iter_events(events_payload)),
        "implemented_actions": sorted(actions),
        "unhandled_actions": unhandled_actions,
        "missing_refs": missing_refs,
        "grail_warnings": grail_warnings,
        "creative_findings": creative_room_findings(rooms_payload, events_payload),
        "duplicate_event_ids": sorted(duplicate_event_ids),
        "opening_room": str(decks_payload.get("opening_room_id", "")),
        "opening_event": str(decks_payload.get("opening_event_id", "")),
        "content_track": content_track,
        "active_rooms_file": data_paths["rooms"].name,
        "active_events_file": data_paths["events"].name,
        "active_decks_file": data_paths["decks"].name,
    }


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def print_bootstrap() -> int:
    config = read_project_config()
    facts = collect_event_facts()
    status = get_git_status()

    print("Revelation bootstrap")

    print_section("Project")
    print(f"Root: {ROOT}")
    print(f"Name: {config['name']}")
    print(f"Main scene: {config['main_scene']}")
    print(f"Autoloads: {', '.join(config['autoloads']) or 'none'}")
    print(f"Viewport: {config['viewport']}")
    print(f"Content track: {facts['content_track']}")
    print(f"Opening: {facts['opening_room']} / {facts['opening_event']}")
    print(f"Active data: {facts['active_rooms_file']}, {facts['active_events_file']}, {facts['active_decks_file']}")

    print_section("Core Files")
    for path in (
        "world.gd",
        "run_manager.gd",
        "ship_dashboard.gd",
        "combat_system.gd",
        "heart_manager.gd",
        "events.json",
        "room_dialogue.json",
        "encounter_decks.json",
        "rooms_post_update.json",
        "events_post_update.json",
        "encounter_decks_post_update.json",
    ):
        print(f"- {path}")

    print_section("Data Summary")
    print(f"Rooms: {len(facts['rooms'])} ({', '.join(facts['rooms'])})")
    print(f"Events: {facts['event_count']}")
    print(f"Implemented actions: {len(facts['implemented_actions'])}")

    print_section("Current Gaps")
    gap_count = 0
    if facts["duplicate_event_ids"]:
        gap_count += len(facts["duplicate_event_ids"])
        print("Duplicate event ids:")
        for event_id in facts["duplicate_event_ids"]:
            print(f"- {event_id}")
    if facts["missing_refs"]:
        gap_count += len(facts["missing_refs"])
        print("Missing references:")
        for issue in facts["missing_refs"]:
            print(f"- {issue}")
    if facts["unhandled_actions"]:
        gap_count += len(facts["unhandled_actions"])
        print("Unhandled button actions:")
        for action, locations in sorted(facts["unhandled_actions"].items()):
            sample = locations[0]
            extra = "" if len(locations) == 1 else f" (+{len(locations) - 1} more)"
            print(f"- {action}: {sample}{extra}")
    if gap_count == 0:
        print("No duplicate ids, missing refs, or unhandled button actions found.")

    print_section("Grail Warnings")
    if facts["grail_warnings"]:
        for warning in facts["grail_warnings"]:
            print(f"- {warning}")
    else:
        print("No vibe/current-state conflicts found.")

    print_section("Creative Critique")
    if facts["creative_findings"]:
        for finding in facts["creative_findings"][:12]:
            print(f"- {finding}")
        if len(facts["creative_findings"]) > 12:
            print(f"- ... +{len(facts['creative_findings']) - 12} more")
    else:
        print("No room depth/story critique findings found.")

    print_section("Content Authorship")
    if CONTENT_AUTHORSHIP_WORKFLOW_PATH.exists():
        print("Codex integrates and verifies; scenario/writing agents author player-facing prose.")
        print("Workflow: .agent-memory/content_authorship_workflow.md")
        print("Do not hand-author final room/event prose unless the user supplies exact text or the change is non-literary glue.")
    else:
        print("Missing .agent-memory/content_authorship_workflow.md.")
        print("Until restored, do not make substantial player-facing prose changes.")

    print_section("Worktree")
    if status:
        for line in status:
            print(f"- {line}")
    else:
        print("Clean")

    print_section("Useful Commands")
    print("source ~/.bashrc")
    print("python tools/project_bootstrap.py --strict")
    print("python tools/revelation_content_auditor.py")
    print("python tools/revelation_content_auditor.py --strict")
    print("python tools/scenario_agent.py context")
    print("python tools/scenario_agent.py content-authorship")
    print("python tools/room_doc_browser.py --host 127.0.0.1 --port 3000")
    print("# Corpus generator port is pending: use .agent-memory/revelation_corpus_strategy.md")
    print("python tools/scenario_agent.py audit-story --json")
    print("python tools/scenario_agent.py audit-writing")
    print("python tools/scenario_agent.py audit-depth --json")
    print("python tools/scenario_agent.py validate generated/scenario_patch.json")
    print("godot --headless --quit --path .")
    print(f"godot --headless --path {ROOT} --script {ROOT / 'tools' / 'text_only_ui_smoke.gd'}")
    print(f"godot --headless --path {ROOT} --script {ROOT / 'tools' / 'story_followup_smoke.gd'}")
    print(f"godot --headless --path {ROOT} --script {ROOT / 'tools' / 'post_update_room_smoke.gd'}")

    return 1 if gap_count else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when gaps are found.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = print_bootstrap()
    return result if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
