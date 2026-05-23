#!/usr/bin/env python3
"""Serve lightweight linked room/event/design docs for Revelation review."""

from __future__ import annotations

import argparse
import html
import json
import posixpath
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOMS_PATH = ROOT / "room_dialogue.json"
LEGACY_EVENTS_PATH = ROOT / "events.json"
POST_UPDATE_ROOMS_PATH = ROOT / "rooms_post_update.json"
POST_UPDATE_EVENTS_PATH = ROOT / "events_post_update.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
DOCS_DIR = ROOT / ".agent-memory"
DESIGN_DOCS = {
    "project_orientation": ROOT / "PROJECT_ORIENTATION.md",
    "revelation_foundational_systems": DOCS_DIR / "revelation_foundational_systems.md",
    "revelation_style": DOCS_DIR / "revelation_style.md",
    "revelation_corpus_strategy": DOCS_DIR / "revelation_corpus_strategy.md",
    "revelation_scenario_generation_process": DOCS_DIR / "revelation_scenario_generation_process.md",
    "revelation_credit_streamlined_generation": DOCS_DIR / "revelation_credit_streamlined_generation.md",
    "revelation_anomaly_exemplar_plan": DOCS_DIR / "revelation_anomaly_exemplar_plan.md",
    "revelation_interlude_glue_layer": DOCS_DIR / "revelation_interlude_glue_layer.md",
    "revelation_state_vocabulary": DOCS_DIR / "revelation_state_vocabulary.md",
    "revelation_content_schemas": DOCS_DIR / "revelation_content_schemas.md",
    "revelation_progression_rules": DOCS_DIR / "revelation_progression_rules.md",
    "revelation_corpus_retrieval_contract": DOCS_DIR / "revelation_corpus_retrieval_contract.md",
    "revelation_agent_roles": DOCS_DIR / "revelation_agent_roles.md",
    "revelation_brothers_door_generated_draft": DOCS_DIR / "revelation_brothers_door_generated_draft.md",
    "brothers_door_generated_patch_json": ROOT / "generated/brothers_door_scenario_patch.json",
    "brothers_door_selected_fragments_json": ROOT / "generated/corpus/brothers_door_selected_fragments.json",
    "content_authorship_workflow": DOCS_DIR / "content_authorship_workflow.md",
    "story_room_contract": DOCS_DIR / "story_room_contract.md",
    "corpus_room_generation": DOCS_DIR / "corpus_room_generation.md",
    "vibe_guide": DOCS_DIR / "vibe_guide.md",
    "lore_guide": DOCS_DIR / "lore_guide.md",
    "mechanic_backlog": DOCS_DIR / "mechanic_backlog.md",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def active_paths() -> dict[str, Path]:
    return {
        "rooms": POST_UPDATE_ROOMS_PATH if POST_UPDATE_ROOMS_PATH.exists() else LEGACY_ROOMS_PATH,
        "events": POST_UPDATE_EVENTS_PATH if POST_UPDATE_EVENTS_PATH.exists() else LEGACY_EVENTS_PATH,
    }


def room_slug(room_id: str) -> str:
    return quote(room_id, safe="")


def event_slug(event_id: str) -> str:
    return quote(event_id, safe="")


def doc_slug(doc_id: str) -> str:
    return quote(doc_id, safe="")


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def normalize_followups(event: dict[str, Any]) -> list[dict[str, Any]]:
    followups = event.get("story_followups")
    entries: list[dict[str, Any]] = []

    def add_value(key: str, value: Any) -> None:
        if isinstance(value, str) and value:
            entries.append({"action": key, "event_id": value})
        elif isinstance(value, dict):
            entry = value.copy()
            entry.setdefault("action", key)
            entries.append(entry)

    if isinstance(followups, str):
        add_value("default", followups)
    elif isinstance(followups, dict):
        for key, value in followups.items():
            add_value(str(key), value)
    elif isinstance(followups, list):
        for index, value in enumerate(followups):
            add_value(str(index), value)

    return entries


def followup_tree_lines(store: "ContentStore", event: dict[str, Any], depth: int = 0, seen: set[str] | None = None, max_depth: int = 4) -> list[str]:
    if seen is None:
        seen = set()
    if depth >= max_depth:
        return []
    lines: list[str] = []
    for followup in normalize_followups(event):
        followup_id = str(followup.get("event_id", ""))
        if not followup_id:
            continue
        action = str(followup.get("action", "default"))
        delay = followup.get("delay_rooms", "")
        trigger = str(followup.get("trigger_key", ""))
        linked_event = store.events_by_id.get(followup_id, {})
        indent = "  " * depth
        label = f"`{action}` -> [{followup_id}](/events/{event_slug(followup_id)})"
        details: list[str] = []
        if delay != "":
            details.append(f"delay {delay}")
        if trigger:
            details.append(f"trigger `{trigger}`")
        if isinstance(linked_event, dict) and linked_event:
            line_1 = str(linked_event.get("line_1", ""))
            if line_1:
                details.append(line_1)
        if details:
            label += " (" + "; ".join(details) + ")"
        lines.append(f"{indent}- {label}\n")
        if followup_id in seen:
            lines.append(f"{indent}  - cycle already shown\n")
            continue
        if isinstance(linked_event, dict) and linked_event:
            child_seen = set(seen)
            child_seen.add(followup_id)
            lines.extend(followup_tree_lines(store, linked_event, depth + 1, child_seen, max_depth))
    return lines


class ContentStore:
    def __init__(self) -> None:
        paths = active_paths()
        self.rooms_path = paths["rooms"]
        self.events_path = paths["events"]
        self.rooms_payload = load_json(self.rooms_path)
        self.events_payload = load_json(self.events_path)
        symbiotes_payload = load_json(SYMBIOTES_PATH) if SYMBIOTES_PATH.exists() else {}
        symbiotes = symbiotes_payload.get("symbiotes", [])
        self.symbiotes_by_id = {
            str(symbiote.get("id")): symbiote
            for symbiote in symbiotes
            if isinstance(symbiote, dict) and symbiote.get("id")
        }
        self.rooms = [
            room
            for room in self.rooms_payload.get("rooms", [])
            if isinstance(room, dict) and room.get("id")
        ]
        self.rooms_by_id = {str(room.get("id")): room for room in self.rooms}
        room_events = self.events_payload.get("room_events", {})
        self.room_events = room_events if isinstance(room_events, dict) else {}
        special_events = self.events_payload.get("special_events", {})
        self.special_events = special_events if isinstance(special_events, dict) else {}
        self.events_by_id: dict[str, dict[str, Any]] = {}
        self.event_rooms: dict[str, str] = {}
        for room_id, events in self.room_events.items():
            if not isinstance(events, list):
                continue
            for event in events:
                if isinstance(event, dict) and event.get("id"):
                    event_id = str(event.get("id"))
                    self.events_by_id[event_id] = event
                    self.event_rooms[event_id] = str(room_id)
        for event_id, event in self.special_events.items():
            if isinstance(event, dict):
                self.events_by_id[str(event_id)] = event
                self.event_rooms[str(event_id)] = str(event.get("room_id", "special"))

    @property
    def content_track(self) -> str:
        return str(self.rooms_payload.get("content_track", "legacy"))

    def room_events_for(self, room_id: str) -> list[dict[str, Any]]:
        events = self.room_events.get(room_id, [])
        if not isinstance(events, list):
            return []
        return [event for event in events if isinstance(event, dict)]


def md_heading(level: int, text: str) -> str:
    return f"{'#' * level} {text}\n\n"


def format_list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "_none_\n"
    return "".join(f"- {value}\n" for value in values) + "\n"


def event_action_result(event: dict[str, Any], action: str) -> dict[str, Any]:
    results = event.get("action_results", {})
    if isinstance(results, dict):
        base_action = action.split(":", 1)[0]
        result = results.get(action, results.get(base_action, {}))
        if isinstance(result, dict):
            return result
    return {}


def operation_plans_for_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    plans = event.get("operation_plans", [])
    if isinstance(plans, list):
        return [plan for plan in plans if isinstance(plan, dict)]
    if isinstance(plans, dict):
        normalized: list[dict[str, Any]] = []
        for action, plan in plans.items():
            if isinstance(plan, dict):
                plan_copy = plan.copy()
                plan_copy.setdefault("action", str(action))
                normalized.append(plan_copy)
        return normalized
    return []


def operation_plan_for_action(event: dict[str, Any], action: str) -> dict[str, Any]:
    for plan in operation_plans_for_event(event):
        if str(plan.get("action", "")) == action:
            return plan
    return {}


def compact_mapping(value: Any) -> str:
    if isinstance(value, dict) and value:
        return ", ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, str) and value:
        return value
    return ""


def operation_outcome_summary(plan: dict[str, Any]) -> list[str]:
    outcomes = plan.get("outcomes", {})
    if not isinstance(outcomes, dict):
        return []
    rows: list[str] = []
    for band in ("strong_success", "success", "partial", "failure", "catastrophe"):
        outcome = outcomes.get(band)
        if not isinstance(outcome, dict):
            continue
        lines = outcome.get("lines", [])
        text = ""
        if isinstance(lines, list) and lines:
            text = " ".join(str(line) for line in lines)
        elif outcome.get("line"):
            text = str(outcome.get("line"))
        if text:
            rows.append(f"  - **{band.replace('_', ' ').title()}:** {text}\n")
    return rows


def action_result_for_action(event: dict[str, Any], action: str) -> dict[str, Any]:
    action_results = event.get("action_results", {})
    if not isinstance(action_results, dict):
        return {}
    for key in (action, "default"):
        result = action_results.get(key)
        if isinstance(result, dict):
            return result
    return {}


def display_buttons_for_event(store: ContentStore, event: dict[str, Any]) -> list[dict[str, Any]]:
    buttons: list[dict[str, Any]] = []
    symbiote_choices = event.get("symbiote_choices", [])
    explicit_choice_count = 0
    if isinstance(symbiote_choices, list):
        for symbiote_id_variant in symbiote_choices:
            symbiote_id = str(symbiote_id_variant)
            if not symbiote_id:
                continue
            explicit_choice_count += 1
            symbiote = store.symbiotes_by_id.get(symbiote_id, {})
            label = str(symbiote.get("name", symbiote_id.replace("_", " ").title()))
            buttons.append({
                "label": f"Bond: {label}",
                "action": f"take_symbiote:{symbiote_id}",
                "voice_aliases": ["bond", "take symbiote", label.lower()],
            })
    if explicit_choice_count == 0 and event.get("symbiote_choice_count") is not None:
        choice_count = int(event.get("symbiote_choice_count", 0))
        for symbiote_id, symbiote in list(store.symbiotes_by_id.items())[:choice_count]:
            label = str(symbiote.get("name", symbiote_id.replace("_", " ").title()))
            buttons.append({
                "label": f"Random bond option: {label}",
                "action": f"take_symbiote:{symbiote_id}",
                "voice_aliases": ["bond", "take symbiote", label.lower()],
            })
    raw_buttons = event.get("buttons", [])
    if isinstance(raw_buttons, list):
        buttons.extend(button for button in raw_buttons if isinstance(button, dict))
    return buttons


def preview_markdown(store: ContentStore, room_id: str) -> str:
    room = store.rooms_by_id.get(room_id)
    if not room:
        return f"# Missing Room\n\nNo room found for `{room_id}`.\n"

    title = str(room.get("name", room_id))
    events = store.room_events_for(room_id)
    lines: list[str] = []
    lines.append(md_heading(1, title))
    lines.append(str(room.get("first_visit_description", "")))
    lines.append("\n\n")

    if not events:
        lines.append("_No playable events yet._\n")
        return "".join(lines)

    corpus_influences = room.get("corpus_influences", room.get("corpus_anchors", []))
    if isinstance(corpus_influences, list) and corpus_influences:
        lines.append(md_heading(2, "Writing Influence"))
        for influence in corpus_influences:
            if not isinstance(influence, dict):
                continue
            source = str(influence.get("source_title", influence.get("seed_id", "source")))
            source_moment = str(influence.get("source_moment", influence.get("source_bit", "")))
            writing_influence = str(influence.get("writing_influence", ""))
            application = str(influence.get("room_application", influence.get("room_reflection", "")))
            lines.append(f"- **{source}:** {source_moment}\n")
            if writing_influence:
                lines.append(f"  - Energy: {writing_influence}\n")
            if application:
                lines.append(f"  - Room use: {application}\n")
        lines.append("\n")

    for event in events:
        event_id = str(event.get("id", "missing_id"))
        lines.append(md_heading(2, str(event.get("title", event_id)).replace("_", " ").title()))
        if event.get("line_1"):
            lines.append(str(event.get("line_1", "")))
            lines.append("\n\n")
        if event.get("line_2"):
            lines.append(str(event.get("line_2", "")))
            lines.append("\n\n")
        buttons = display_buttons_for_event(store, event)
        if buttons:
            lines.append(md_heading(3, "Choices"))
            for button in buttons:
                if not isinstance(button, dict):
                    continue
                label = str(button.get("label", ""))
                action = str(button.get("action", ""))
                lines.append(f"- **{label}**\n")
                result = event_action_result(event, action)
                preview = result.get("preview", "")
                if preview:
                    lines.append(f"  - {preview}\n")
                plan = operation_plan_for_action(event, action)
                if plan:
                    base_success = plan.get("base_success", "")
                    if isinstance(base_success, (int, float)):
                        lines.append(f"  - Estimate seed: {int(round(float(base_success) * 100))}% before hidden state modifiers.\n")
                    yield_text = compact_mapping(plan.get("yield", ""))
                    risk_text = compact_mapping(plan.get("risk", ""))
                    if yield_text:
                        lines.append(f"  - Yield: {yield_text}\n")
                    if risk_text:
                        lines.append(f"  - Risk: {risk_text}\n")
                result_lines = result.get("lines", [])
                if isinstance(result_lines, list) and result_lines:
                    lines.append(f"  - Result: {' '.join(str(line) for line in result_lines)}\n")
                if plan:
                    lines.extend(operation_outcome_summary(plan))
            lines.append("\n")
        followups = normalize_followups(event)
        if followups:
            lines.append(md_heading(3, "Later Pressure"))
            lines.extend(followup_tree_lines(store, event))
            lines.append("\n")

        story_thread = event.get("story_thread", {})
        if isinstance(story_thread, dict) and story_thread:
            lines.append(md_heading(3, "Story Thread"))
            lines.append(f"- **{story_thread.get('id', 'thread')}:** {story_thread.get('role', '')}\n\n")

    ending_vectors = room.get("ending_vectors", [])
    if isinstance(ending_vectors, list) and ending_vectors:
        lines.append(md_heading(2, "Possible Ending"))
        for ending in ending_vectors:
            if not isinstance(ending, dict):
                continue
            label = str(ending.get("label", ending.get("id", "ending")))
            ending_id = str(ending.get("id", ""))
            if ending_id and ending_id in store.events_by_id:
                lines.append(f"- [{label}](/events/{event_slug(ending_id)})")
            else:
                lines.append(f"- **{label}**")
            pulls = ending.get("pulls_toward", [])
            if isinstance(pulls, list) and pulls:
                lines.append(": pulls from " + ", ".join(str(item) for item in pulls))
            lines.append("\n")
        lines.append("\n")

    mutation_hooks = room.get("mutation_hooks", [])
    if isinstance(mutation_hooks, list) and mutation_hooks:
        lines.append(md_heading(2, "Mutation Openings"))
        for hook in mutation_hooks:
            if isinstance(hook, dict):
                lines.append(f"- **{hook.get('capability', '')}:** {hook.get('effect', '')}\n")
        lines.append("\n")

    return "".join(lines)


def room_markdown(store: ContentStore, room_id: str) -> str:
    room = store.rooms_by_id.get(room_id)
    if not room:
        return f"# Missing Room\n\nNo room found for `{room_id}`.\n"

    lines: list[str] = []
    title = str(room.get("name", room_id))
    lines.append(md_heading(1, title))
    lines.append(f"`{room_id}`\n\n")
    lines.append(md_heading(2, "Descriptions"))
    lines.append(f"**First visit:** {room.get('first_visit_description', '')}\n\n")
    lines.append(f"**Return:** {room.get('return_description', '')}\n\n")

    for state_key in ("return_description_variants", "stateful_return_descriptions", "return_states", "room_memory_states"):
        state_data = room.get(state_key)
        if state_data:
            lines.append(md_heading(3, state_key))
            lines.append("```json\n")
            lines.append(json.dumps(state_data, indent=2, ensure_ascii=False))
            lines.append("\n```\n\n")

    lines.append(md_heading(2, "Story Anchors"))
    for label, key in (
        ("Tags", "tags"),
        ("Factions", "faction_ids"),
        ("Storylines", "storyline_ids"),
        ("Recurring characters", "recurring_character_ids"),
        ("Source seeds", "source_seed_ids"),
    ):
        lines.append(f"**{label}:**\n")
        lines.append(format_list(room.get(key, [])))

    infrastructure = room.get("animal_infrastructure", [])
    if isinstance(infrastructure, list) and infrastructure:
        lines.append(md_heading(2, "Animal Infrastructure"))
        for actor in infrastructure:
            if not isinstance(actor, dict):
                continue
            lines.append(md_heading(3, str(actor.get("id", "unnamed_actor"))))
            lines.append(f"{actor.get('function', '')}\n\n")
            lines.append("**Possible interactions:**\n")
            lines.append(format_list(actor.get("possible_interactions", [])))

    hooks = room.get("cross_run_story_hooks", [])
    if isinstance(hooks, list) and hooks:
        lines.append(md_heading(2, "Cross-Run Hooks"))
        lines.append(format_list(hooks))

    progression = room.get("progression_state", {})
    if isinstance(progression, dict) and progression:
        lines.append(md_heading(2, "Progression State"))
        for key, value in progression.items():
            lines.append(f"- **{key}:** {value}\n")
        lines.append("\n")

    ending_vectors = room.get("ending_vectors", [])
    if isinstance(ending_vectors, list) and ending_vectors:
        lines.append(md_heading(2, "Ending Vectors"))
        for ending in ending_vectors:
            if not isinstance(ending, dict):
                continue
            lines.append(md_heading(3, str(ending.get("label", ending.get("id", "ending")))))
            if ending.get("id"):
                lines.append(f"`{ending.get('id')}`\n\n")
            pulls = ending.get("pulls_toward", [])
            if pulls:
                lines.append("**Pulls toward:**\n")
                lines.append(format_list(pulls))
            diverts = ending.get("diverts_to", [])
            if diverts:
                lines.append("**Diverts to:**\n")
                lines.append(format_list(diverts))

    mutation_hooks = room.get("mutation_hooks", [])
    if isinstance(mutation_hooks, list) and mutation_hooks:
        lines.append(md_heading(2, "Mutation Hooks"))
        for hook in mutation_hooks:
            if isinstance(hook, dict):
                lines.append(f"- **{hook.get('capability', '')}:** {hook.get('effect', '')}\n")
        lines.append("\n")

    events = store.room_events_for(room_id)
    lines.append(md_heading(2, f"Room Events ({len(events)})"))
    if not events:
        lines.append("_No events._\n")
    for event in events:
        event_id = str(event.get("id", "missing_id"))
        lines.append(f"- [{event_id}](/events/{event_slug(event_id)}) - `{event.get('type', '')}`\n")
    lines.append("\n")
    return "".join(lines)


def event_markdown(store: ContentStore, event_id: str) -> str:
    event = store.events_by_id.get(event_id)
    if not event:
        return f"# Missing Event\n\nNo event found for `{event_id}`.\n"

    room_id = store.event_rooms.get(event_id, "")
    lines: list[str] = []
    lines.append(md_heading(1, event_id))
    lines.append(f"Type: `{event.get('type', '')}`\n\n")
    if room_id and room_id != "special":
        lines.append(f"Room: [{room_id}](/rooms/{room_slug(room_id)})\n\n")
    elif event.get("room_id"):
        special_room_id = str(event.get("room_id"))
        lines.append(f"Linked room: [{special_room_id}](/rooms/{room_slug(special_room_id)})\n\n")
    lines.append(md_heading(2, "Narration"))
    lines.append(f"**Speaker:** {event.get('speaker', '')}\n\n")
    lines.append(f"{event.get('line_1', '')}\n\n")
    lines.append(f"{event.get('line_2', '')}\n\n")

    buttons = display_buttons_for_event(store, event)
    lines.append(md_heading(2, "Choices"))
    if buttons:
        for button in buttons:
            if not isinstance(button, dict):
                continue
            action = str(button.get("action", ""))
            lines.append(f"- **{button.get('label', '')}** -> `{action}`\n")
            aliases = button.get("voice_aliases", [])
            if isinstance(aliases, list) and aliases:
                lines.append(f"  - voice: {', '.join(str(alias) for alias in aliases)}\n")
            action_result = action_result_for_action(event, action)
            resource_changes = compact_mapping(action_result.get("resource_changes", {}))
            if resource_changes:
                lines.append(f"  - resources: {resource_changes}\n")
            environment_changes = action_result.get("environment_state_changes", [])
            if isinstance(environment_changes, list) and environment_changes:
                preview = ", ".join(str(change) for change in environment_changes[:4])
                if len(environment_changes) > 4:
                    preview += ", ..."
                lines.append(f"  - state: {preview}\n")
    else:
        lines.append("_No choices._\n")
    lines.append("\n")

    followups = normalize_followups(event)
    if followups:
        lines.append(md_heading(2, "Story Follow-Ups"))
        lines.extend(followup_tree_lines(store, event))
        lines.append("\n")

    plans = operation_plans_for_event(event)
    if plans:
        lines.append(md_heading(2, "Operation Plans"))
        for plan in plans:
            label = str(plan.get("plan_id", plan.get("action", "operation")))
            lines.append(md_heading(3, label))
            lines.append(f"- Action: `{plan.get('action', '')}`\n")
            if plan.get("officer_id"):
                lines.append(f"- Officer: `{plan.get('officer_id')}`\n")
            if plan.get("primary_skill"):
                lines.append(f"- Skill: `{plan.get('primary_skill')}`\n")
            base_success = plan.get("base_success", "")
            if isinstance(base_success, (int, float)):
                lines.append(f"- Base estimate: {int(round(float(base_success) * 100))}% before hidden state modifiers.\n")
            yield_text = compact_mapping(plan.get("yield", ""))
            risk_text = compact_mapping(plan.get("risk", ""))
            if yield_text:
                lines.append(f"- Yield: {yield_text}\n")
            if risk_text:
                lines.append(f"- Risk: {risk_text}\n")
            outcome_rows = operation_outcome_summary(plan)
            if outcome_rows:
                lines.append("**Outcome bands:**\n")
                lines.extend(outcome_rows)
            lines.append("\n")

    story_thread = event.get("story_thread", {})
    if isinstance(story_thread, dict) and story_thread:
        lines.append(md_heading(2, "Story Thread"))
        lines.append(f"- **{story_thread.get('id', 'thread')}:** {story_thread.get('role', '')}\n\n")

    hidden_keys = {"id", "type", "speaker", "line_1", "line_2", "buttons", "story_followups", "operation_plans", "story_thread"}
    extra = {key: value for key, value in event.items() if key not in hidden_keys}
    if extra:
        lines.append(md_heading(2, "Event Data"))
        lines.append("```json\n")
        lines.append(json.dumps(extra, indent=2, ensure_ascii=False))
        lines.append("\n```\n\n")
    return "".join(lines)


def markdown_to_html(markdown: str) -> str:
    html_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []
    in_list = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                html_lines.append("<pre><code>%s</code></pre>" % escape("\n".join(code_lines)))
                code_lines = []
                in_code = False
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("#"):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            level = min(len(line) - len(line.lstrip("#")), 4)
            text = line[level:].strip()
            html_lines.append(f"<h{level}>{inline_markdown(text)}</h{level}>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_markdown(line[2:])}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{inline_markdown(line)}</p>")
    if in_code:
        html_lines.append("<pre><code>%s</code></pre>" % escape("\n".join(code_lines)))
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def inline_markdown(text: str) -> str:
    escaped = escape(text)
    escaped = escaped.replace("`", "")
    escaped = replace_links(escaped)
    while "**" in escaped:
        first = escaped.find("**")
        second = escaped.find("**", first + 2)
        if second == -1:
            break
        escaped = escaped[:first] + "<strong>" + escaped[first + 2:second] + "</strong>" + escaped[second + 2:]
    return escaped


def replace_links(text: str) -> str:
    result = ""
    cursor = 0
    while True:
        start = text.find("[", cursor)
        if start == -1:
            result += text[cursor:]
            break
        mid = text.find("](", start)
        end = text.find(")", mid)
        if mid == -1 or end == -1:
            result += text[cursor:]
            break
        result += text[cursor:start]
        label = text[start + 1:mid]
        href = text[mid + 2:end]
        result += f'<a href="{href}">{label}</a>'
        cursor = end + 1
    return result


def page(title: str, body: str, store: ContentStore, md_href: str = "") -> bytes:
    md_link = f'<a href="{md_href}">Markdown</a>' if md_href else ""
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #111514;
      --panel: #18201e;
      --text: #e8ede7;
      --muted: #aeb9b1;
      --line: #334039;
      --accent: #d9b46a;
      --danger: #db6d64;
      --link: #87c7b0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 1;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(17, 21, 20, 0.96);
    }}
    nav {{ display: flex; flex-wrap: wrap; gap: 10px; font-size: 14px; }}
    main {{
      width: min(980px, 100%);
      margin: 0 auto;
      padding: 18px 16px 56px;
    }}
    h1, h2, h3, h4 {{ line-height: 1.18; margin: 1.25em 0 0.45em; }}
    h1 {{ font-size: 30px; margin-top: 0.25em; }}
    h2 {{ font-size: 22px; color: var(--accent); }}
    h3 {{ font-size: 18px; color: var(--muted); }}
    a {{ color: var(--link); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    p, li {{ font-size: 16px; }}
    ul {{ padding-left: 22px; }}
    code, pre {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }}
    pre {{
      overflow-x: auto;
      padding: 12px;
      border: 1px solid var(--line);
      background: var(--panel);
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .room-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .room-card {{
      display: block;
      min-height: 84px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      text-decoration: none;
    }}
    .room-card strong {{ display: block; color: var(--text); margin-bottom: 4px; }}
    .room-card span {{ color: var(--muted); font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <nav>
      <a href="/rooms">Rooms</a>
      <a href="/events">Events</a>
      <a href="/docs">Docs</a>
      {md_link}
    </nav>
    <div class="meta">{escape(store.content_track)} / {escape(store.rooms_path.name)} / {escape(store.events_path.name)}</div>
  </header>
  <main>{body}</main>
</body>
</html>
"""
    return html_doc.encode("utf-8")


def rooms_index(store: ContentStore) -> bytes:
    cards = []
    for room in store.rooms:
        room_id = str(room.get("id", ""))
        event_count = len(store.room_events_for(room_id))
        cards.append(
            '<a class="room-card" href="/preview/%s"><strong>%s</strong><span>%s events / preview</span></a>'
            % (room_slug(room_id), escape(room.get("name", room_id)), event_count)
        )
    body = "<h1>Room Docs</h1><p>Linked preview of active room and event data.</p><div class=\"room-grid\">%s</div>" % "".join(cards)
    return page("Room Docs", body, store)


def events_index(store: ContentStore) -> bytes:
    items = []
    for event_id in sorted(store.events_by_id.keys()):
        event = store.events_by_id[event_id]
        room_id = store.event_rooms.get(event_id, "special")
        items.append(
            '<li><a href="/events/%s">%s</a> <span class="meta">%s / %s</span></li>'
            % (event_slug(event_id), escape(event_id), escape(room_id), escape(event.get("type", "")))
        )
    body = "<h1>Events</h1><ul>%s</ul>" % "".join(items)
    return page("Events", body, store)


def docs_index(store: ContentStore) -> bytes:
    items = []
    for doc_id, path in DESIGN_DOCS.items():
        if not path.exists():
            continue
        title = doc_id.replace("_", " ").title()
        items.append(
            '<li><a href="/docs/%s">%s</a> <span class="meta">%s</span></li>'
            % (doc_slug(doc_id), escape(title), escape(path.relative_to(ROOT)))
        )
    body = "<h1>Design Docs</h1><p>Project guidance, mechanics, room structure, style, and lore references.</p><ul>%s</ul>" % "".join(items)
    return page("Design Docs", body, store)


def doc_markdown(doc_id: str) -> str:
    path = DESIGN_DOCS.get(doc_id)
    if path is None or not path.exists():
        return f"# Missing Document\n\nNo design document found for `{doc_id}`.\n"
    return path.read_text(encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "NightmareVoyageDocs/0.2"

    def do_GET(self) -> None:
        store = ContentStore()
        parsed = urlparse(self.path)
        path = posixpath.normpath(unquote(parsed.path))
        if path == ".":
            path = "/"

        try:
            if path in {"/", "/rooms"}:
                self.send_bytes(rooms_index(store), "text/html; charset=utf-8")
                return
            if path == "/events":
                self.send_bytes(events_index(store), "text/html; charset=utf-8")
                return
            if path == "/docs":
                self.send_bytes(docs_index(store), "text/html; charset=utf-8")
                return
            if path.startswith("/docs/"):
                doc_id = path.removeprefix("/docs/")
                markdown = False
                if doc_id.endswith(".md"):
                    doc_id = doc_id[:-3]
                    markdown = True
                if doc_id not in DESIGN_DOCS or not DESIGN_DOCS[doc_id].exists():
                    self.send_error(HTTPStatus.NOT_FOUND, "document not found")
                    return
                md = doc_markdown(doc_id)
                if markdown:
                    self.send_bytes(md.encode("utf-8"), "text/markdown; charset=utf-8")
                else:
                    body = markdown_to_html(md)
                    self.send_bytes(page(doc_id.replace("_", " ").title(), body, store, f"/docs/{doc_slug(doc_id)}.md"), "text/html; charset=utf-8")
                return
            if path.startswith("/preview/"):
                room_id = path.removeprefix("/preview/")
                markdown = False
                if room_id.endswith(".md"):
                    room_id = room_id[:-3]
                    markdown = True
                if room_id not in store.rooms_by_id:
                    self.send_error(HTTPStatus.NOT_FOUND, "room not found")
                    return
                md = preview_markdown(store, room_id)
                if markdown:
                    self.send_bytes(md.encode("utf-8"), "text/markdown; charset=utf-8")
                else:
                    body = markdown_to_html(md)
                    self.send_bytes(page(f"{room_id} preview", body, store, f"/preview/{room_slug(room_id)}.md"), "text/html; charset=utf-8")
                return
            if path.startswith("/rooms/"):
                room_id = path.removeprefix("/rooms/")
                markdown = False
                if room_id.endswith(".md"):
                    room_id = room_id[:-3]
                    markdown = True
                if room_id not in store.rooms_by_id:
                    self.send_error(HTTPStatus.NOT_FOUND, "room not found")
                    return
                md = room_markdown(store, room_id)
                if markdown:
                    self.send_bytes(md.encode("utf-8"), "text/markdown; charset=utf-8")
                else:
                    body = markdown_to_html(md)
                    self.send_bytes(page(room_id, body, store, f"/rooms/{room_slug(room_id)}.md"), "text/html; charset=utf-8")
                return
            if path.startswith("/events/"):
                event_id = path.removeprefix("/events/")
                markdown = False
                if event_id.endswith(".md"):
                    event_id = event_id[:-3]
                    markdown = True
                if event_id not in store.events_by_id:
                    self.send_error(HTTPStatus.NOT_FOUND, "event not found")
                    return
                md = event_markdown(store, event_id)
                if markdown:
                    self.send_bytes(md.encode("utf-8"), "text/markdown; charset=utf-8")
                else:
                    body = markdown_to_html(md)
                    self.send_bytes(page(event_id, body, store, f"/events/{event_slug(event_id)}.md"), "text/html; charset=utf-8")
                return
            self.send_error(HTTPStatus.NOT_FOUND, "not found")
        except Exception as exc:  # pragma: no cover - intentionally visible in local tool
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_bytes(self, payload: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving Revelation docs at http://{args.host}:{args.port}/docs")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping room docs server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
