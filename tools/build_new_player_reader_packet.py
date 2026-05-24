#!/usr/bin/env python3
"""Build a minimal-context new-player reader packet for scenario review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
DECK_PATH = ROOT / "encounter_decks_post_update.json"
DEFAULT_OUTPUT = ROOT / "generated" / "reviews" / "new_player_reader_packet.md"
OUTCOME_BANDS = {"success", "strong_success", "weak_success", "partial", "failure"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def one_line(value: Any) -> str:
    return str(value or "").replace("\n", " ").strip()


def md_escape(value: Any) -> str:
    return one_line(value).replace("|", "\\|")


def action_base(action: str) -> str:
    return action.split(":", 1)[0]


def room_by_id(rooms_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rooms = rooms_payload.get("rooms", [])
    if not isinstance(rooms, list):
        return {}
    return {
        str(room.get("id")): room
        for room in rooms
        if isinstance(room, dict) and room.get("id")
    }


def room_sequence(deck_payload: dict[str, Any], rooms: dict[str, dict[str, Any]]) -> list[str]:
    sequence: list[str] = []
    opening = one_line(deck_payload.get("opening_room_id"))
    first = one_line(deck_payload.get("first_room_after_opening"))
    if opening:
        sequence.append(opening)
    if first and first not in sequence:
        sequence.append(first)
    pools = deck_payload.get("room_pools", {})
    mission_pool = pools.get("mission", []) if isinstance(pools, dict) else []
    if isinstance(mission_pool, list):
        for room_id in mission_pool:
            room_id = one_line(room_id)
            if room_id and room_id not in sequence:
                sequence.append(room_id)
    for room_id in rooms.keys():
        if room_id not in sequence:
            sequence.append(room_id)
    return sequence


def event_lines(event: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for index in range(1, 10):
        key = f"line_{index}"
        line = one_line(event.get(key))
        if line:
            lines.append(line)
    return lines


def result_for_action(event: dict[str, Any], action: str) -> dict[str, Any]:
    for plan in plans_for_action(event, action):
        outcomes = plan.get("outcomes", {})
        if not isinstance(outcomes, dict):
            continue
        for band in ("success", "strong_success", "partial", "failure"):
            outcome = outcomes.get(band)
            if isinstance(outcome, dict) and outcome.get("lines"):
                return outcome

    results = event.get("action_results", {})
    if not isinstance(results, dict):
        return {}
    exact = results.get(action)
    if isinstance(exact, dict):
        return exact
    base = results.get(action_base(action))
    return base if isinstance(base, dict) else {}


def plans_for_action(event: dict[str, Any], action: str) -> list[dict[str, Any]]:
    plans = event.get("operation_plans", [])
    if not isinstance(plans, list):
        return []
    base = action_base(action)
    matches: list[dict[str, Any]] = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        plan_action = one_line(plan.get("action"))
        if plan_action == action or plan_action == base:
            matches.append(plan)
    return matches


def followups_for_action(event: dict[str, Any], action: str) -> list[tuple[str, dict[str, Any]]]:
    followups = event.get("story_followups", {})
    if not isinstance(followups, dict):
        return []
    base = action_base(action)
    action_band_matches: list[tuple[str, dict[str, Any]]] = []
    direct_matches: list[tuple[str, dict[str, Any]]] = []
    base_matches: list[tuple[str, dict[str, Any]]] = []
    for key, value in followups.items():
        if not isinstance(value, dict):
            continue
        key = str(key)
        if key == action:
            direct_matches.append((key, value))
            continue
        if key.startswith(f"{action}:"):
            suffix = key[len(action) + 1 :]
            first_segment = suffix.split(":", 1)[0]
            if action != base or first_segment in OUTCOME_BANDS:
                action_band_matches.append((key, value))
            continue
        if key == base:
            base_matches.append((key, value))
            continue
        if key.startswith(f"{base}:"):
            suffix = key[len(base) + 1 :]
            first_segment = suffix.split(":", 1)[0]
            if first_segment in OUTCOME_BANDS:
                base_matches.append((key, value))
    if action_band_matches:
        return action_band_matches
    if direct_matches:
        return direct_matches
    return base_matches


def special_event(events_payload: dict[str, Any], event_id: str) -> dict[str, Any]:
    special_events = events_payload.get("special_events", {})
    if not isinstance(special_events, dict):
        return {}
    event = special_events.get(event_id, {})
    return event if isinstance(event, dict) else {}


def all_events_by_id(events_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    room_events = events_payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_event_list in room_events.values():
            if not isinstance(room_event_list, list):
                continue
            for event in room_event_list:
                if isinstance(event, dict) and event.get("id"):
                    events[str(event["id"])] = event
    special_events = events_payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                events[str(event_id)] = event
    return events


def collect_branch_warnings(events_payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    room_events = events_payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return warnings
    for room_id, event_list in room_events.items():
        if not isinstance(event_list, list):
            continue
        for event in event_list:
            if not isinstance(event, dict):
                continue
            event_id = one_line(event.get("id"))
            buttons = event.get("buttons", [])
            if not isinstance(buttons, list):
                continue
            result_texts: dict[str, str] = {}
            for button in buttons:
                if not isinstance(button, dict):
                    continue
                action = one_line(button.get("action"))
                if not action:
                    continue
                result = result_for_action(event, action)
                lines = result.get("lines", [])
                result_text = " ".join(one_line(line) for line in lines) if isinstance(lines, list) else ""
                result_texts[action] = result_text
                if not result_text:
                    warnings.append(f"{room_id}/{event_id}: `{action}` has no immediate action result text.")
                if not followups_for_action(event, action):
                    warnings.append(f"{room_id}/{event_id}: `{action}` has no matching story follow-up.")
            unique_results = {text for text in result_texts.values() if text}
            if len(result_texts) > 1 and len(unique_results) <= 1:
                warnings.append(f"{room_id}/{event_id}: choices appear to resolve to identical immediate text.")
    return warnings


def write_prompt(lines: list[str]) -> None:
    lines.append("# New Player Reader Packet\n\n")
    lines.append("## Role\n\n")
    lines.append(
        "You are a first-time player reading these playable scenario beats with minimal context. "
        "Do not assume design notes, source texts, or hidden lore. Judge only what the game text gives you.\n\n"
    )
    lines.append("## Minimal Context\n\n")
    lines.append(
        "- You are reading a text-first symbolic horror roguelike called Revelation.\n"
        "- The player issues commands for Torah, an Institute field lead, and a small containment squad.\n"
        "- Each mission presents a concrete anomaly, a tactical choice, and a consequence.\n"
        "- The game should feel procedural, readable, and tense without needing external scripture/source knowledge.\n\n"
    )
    lines.append("## Review Questions\n\n")
    lines.append(
        "For each mission, answer briefly:\n"
        "1. What is happening right now?\n"
        "2. What is the immediate danger or clock?\n"
        "3. Who is present, who is remote, and what does each named person appear able to do?\n"
        "4. What are the choices asking you to decide?\n"
        "5. Do the choice outcomes branch in a meaningful way, or do they feel like the same resolution with different names?\n"
        "6. Are any events, causes, or resolutions presented out of chronological order?\n"
        "7. What information did you need but did not get?\n\n"
    )
    lines.append("## Output Format\n\n")
    lines.append(
        "Return:\n"
        "- A one-paragraph overall comprehension verdict.\n"
        "- A table with one row per mission: `mission`, `clear?`, `chronology`, `branching`, `missing context`, `most confusing line`.\n"
        "- A short list of the three highest-impact fixes.\n\n"
    )


def append_opening(lines: list[str], deck_payload: dict[str, Any], events_payload: dict[str, Any]) -> None:
    opening_event_id = one_line(deck_payload.get("opening_event_id"))
    if not opening_event_id:
        return
    event = special_event(events_payload, opening_event_id)
    if not event:
        return
    lines.append("## Opening Beat\n\n")
    lines.append(f"Event: `{opening_event_id}`\n\n")
    for text in event_lines(event):
        lines.append(f"- {text}\n")
    buttons = event.get("buttons", [])
    if isinstance(buttons, list):
        for button in buttons:
            if not isinstance(button, dict):
                continue
            action = one_line(button.get("action"))
            result = result_for_action(event, action)
            result_lines = result.get("lines", [])
            lines.append(f"\nChoice: **{one_line(button.get('label'))}** (`{action}`)\n\n")
            if isinstance(result_lines, list):
                for result_line in result_lines:
                    lines.append(f"- Result: {one_line(result_line)}\n")
    lines.append("\n")


def build_audit_summary(deck_payload: dict[str, Any], warnings: list[str]) -> str:
    lines: list[str] = []
    lines.append("# New Player Reader Audit Hints\n\n")
    lines.append(
        "Use this only after the clean reader pass. These hints are generated from the JSON before "
        "any human/model reading. They are not a verdict, but they point toward likely structural issues.\n\n"
    )
    lines.append("## Mechanical Audit Hints\n\n")
    lines.append(f"- Opening room: `{one_line(deck_payload.get('opening_room_id'))}`\n")
    lines.append(f"- First room after opening: `{one_line(deck_payload.get('first_room_after_opening'))}`\n")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}\n")
    else:
        lines.append("- No missing immediate result/follow-up or identical immediate-result warnings detected.\n")
    lines.append("\n")
    return "".join(lines)


def append_mission(
    lines: list[str],
    room: dict[str, Any],
    event_list: list[dict[str, Any]],
    events_by_id: dict[str, dict[str, Any]],
) -> None:
    room_id = one_line(room.get("id"))
    title = one_line(room.get("title")) or room_id
    lines.append(f"## Mission: {title}\n\n")
    lines.append(f"Room id: `{room_id}`\n\n")
    description = one_line(room.get("first_visit_description") or room.get("description"))
    if description:
        lines.append(f"Setup: {description}\n\n")
    detection = one_line(room.get("detection_report"))
    if detection:
        lines.append(f"DETECTION: {detection}\n\n")
    current = one_line(room.get("current_situation"))
    if current:
        lines.append(f"CURRENT: {current}\n\n")
    if not event_list:
        lines.append("_No playable events are attached to this room._\n\n")
        return

    for event in event_list:
        event_id = one_line(event.get("id"))
        lines.append(f"### Event: `{event_id}`\n\n")
        for text in event_lines(event):
            lines.append(f"- {text}\n")
        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            lines.append("\n_No player choices on this event._\n\n")
            continue
        lines.append("\n| Choice | Preview | Immediate Result | Planned Outcome Branches | Follow-up Hooks |\n")
        lines.append("| --- | --- | --- | --- | --- |\n")
        for button in buttons:
            if not isinstance(button, dict):
                continue
            label = one_line(button.get("label"))
            action = one_line(button.get("action"))
            result = result_for_action(event, action)
            result_lines = result.get("lines", [])
            immediate = " ".join(one_line(line) for line in result_lines) if isinstance(result_lines, list) else ""
            plans = plans_for_action(event, action)
            branch_parts: list[str] = []
            for plan in plans:
                outcomes = plan.get("outcomes", {})
                if isinstance(outcomes, dict):
                    branch_parts.append(", ".join(outcomes.keys()))
            branches = "; ".join(branch_parts)
            followup_parts: list[str] = []
            for key, followup in followups_for_action(event, action):
                followup_id = one_line(followup.get("event_id"))
                followup_event = events_by_id.get(followup_id, {})
                followup_text = " ".join(event_lines(followup_event))
                followup_parts.append(f"{key} -> {followup_id}: {followup_text}")
            lines.append(
                f"| {md_escape(label)} (`{md_escape(action)}`) "
                f"| {md_escape(button.get('preview'))} "
                f"| {md_escape(immediate)} "
                f"| {md_escape(branches)} "
                f"| {md_escape('; '.join(followup_parts))} |\n"
            )
        lines.append("\n")


def build_packet(output: Path) -> None:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    deck_payload = load_json(DECK_PATH)
    rooms = room_by_id(rooms_payload)
    sequence = room_sequence(deck_payload, rooms)
    room_events = events_payload.get("room_events", {})
    if not isinstance(room_events, dict):
        room_events = {}
    events_by_id = all_events_by_id(events_payload)

    lines: list[str] = []
    write_prompt(lines)
    append_opening(lines, deck_payload, events_payload)
    lines.append("## Mission Sequence Presented To Reader\n\n")
    for index, room_id in enumerate(sequence, 1):
        lines.append(f"{index}. `{room_id}`\n")
    lines.append("\n")
    for room_id in sequence:
        room = rooms.get(room_id)
        if room is None:
            continue
        event_list = room_events.get(room_id, [])
        if not isinstance(event_list, list):
            event_list = []
        append_mission(lines, room, [event for event in event_list if isinstance(event, dict)], events_by_id)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(lines), encoding="utf-8")
    audit_output = output.with_name("new_player_reader_audit_hints.md")
    audit_output.write_text(build_audit_summary(deck_payload, collect_branch_warnings(events_payload)), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_packet(args.output)
    print(args.output)
    print(args.output.with_name("new_player_reader_audit_hints.md"))


if __name__ == "__main__":
    main()
