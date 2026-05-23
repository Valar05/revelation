#!/usr/bin/env python3
"""Audit Revelation content skeleton contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
MANIFEST_PATH = ROOT / "generated" / "corpus" / "revelation_source_manifest.json"

LEGACY_STATE_ALIASES = {
    "morale": "squad.morale",
    "unrest": "squad.refusal_risk or squad.mutiny_risk",
    "crew.morale": "squad.morale",
    "symbolic_contamination": "squad.contamination, torah.contamination, or site.<id>.symbolic_contamination",
    "institutional_pressure": "institute.political_pressure or institute.command_confidence",
    "squad_stress": "squad.stress",
    "civilian_risk": "site.<id>.civilian_risk",
}

GENERIC_CORPUS_PHRASES = (
    "use the source as procedural or symbolic structure, not quotation",
    "follow the chosen branch into a concrete personnel or containment consequence",
    "use the source as procedural",
    "use the source as symbolic",
)

CANONICAL_PREFIXES = (
    "squad.",
    "torah.",
    "brooks.",
    "character.",
    "resource.",
    "mental.",
    "institute.",
    "artifact.",
    "site.",
    "thread.",
)

MISSION_REQUIRED_ROOM_FIELDS = (
    "id",
    "name",
    "type",
    "room_role",
    "encounter_family",
    "operation_type",
    "description",
    "first_visit_description",
    "detection_report",
    "current_situation",
    "officer_reports",
    "resource_stakes",
    "followup_vectors",
    "progression_state",
    "procedure_hooks",
    "corpus_influences",
)

EVENT_REQUIRED_FIELDS = (
    "id",
    "type",
    "speaker",
    "line_1",
    "line_2",
    "buttons",
    "action_results",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def active_corpus_ids() -> set[str]:
    if not MANIFEST_PATH.exists():
        return set()
    manifest = load_json(MANIFEST_PATH)
    return {str(source.get("id")) for source in manifest.get("sources", []) if source.get("active")}


def event_records(events: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for room_events in events.get("room_events", {}).values():
        if isinstance(room_events, list):
            for record in room_events:
                if isinstance(record, dict) and record.get("id"):
                    records[str(record["id"])] = record
    for record in events.get("special_events", {}).values():
        if isinstance(record, dict) and record.get("id"):
            records[str(record["id"])] = record
    return records


def iter_state_like_values(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        key = value.get("key")
        if isinstance(key, str):
            found.append(key)
        for nested in value.values():
            found.extend(iter_state_like_values(nested))
    elif isinstance(value, list):
        for item in value:
            found.extend(iter_state_like_values(item))
    return found


def _has_text_or_list(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_text_or_list(item) for item in value)
    if isinstance(value, dict):
        return any(_has_text_or_list(item) for item in value.values())
    return value is not None


def weak_corpus_records(records: Any) -> list[str]:
    weak: list[str] = []
    if not isinstance(records, list):
        return ["corpus influence block is not a list"]
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            weak.append(f"anchor #{index + 1} is not an object")
            continue
        for field in ("source_fingerprint", "structural_transfer", "required_visible_details", "followup_payoff"):
            if not _has_text_or_list(record.get(field)):
                weak.append(f"anchor #{index + 1} missing `{field}`")
        joined = " ".join(str(record.get(field, "")) for field in ("writing_influence", "room_application", "followup_application", "interlude_application", "structural_transfer", "followup_payoff")).lower()
        for phrase in GENERIC_CORPUS_PHRASES:
            if phrase in joined:
                weak.append(f"anchor #{index + 1} uses generic phrase `{phrase}`")
    return weak


def weak_anchor_points(records: Any) -> list[str]:
    weak: list[str] = []
    if not isinstance(records, list):
        return ["corpus_anchor_points block is not a list"]
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            weak.append(f"anchor point #{index + 1} is not an object")
            continue
        for field in ("source_id", "source_chunk_id", "anchor_role", "source_fingerprint", "playable_transform", "required_visible_details", "followup_payoff"):
            if not _has_text_or_list(record.get(field)):
                weak.append(f"anchor point #{index + 1} missing `{field}`")
        details = record.get("required_visible_details", [])
        if not isinstance(details, list) or len([item for item in details if str(item).strip()]) < 2:
            weak.append(f"anchor point #{index + 1} needs at least two required_visible_details")
    return weak


def resource_keys(event: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for result in event.get("action_results", {}).values():
        if not isinstance(result, dict):
            continue
        changes = result.get("resource_changes")
        if isinstance(changes, dict):
            keys.extend(str(key) for key in changes)
    return keys


def has_durable_result(result: dict[str, Any]) -> bool:
    for key in ("environment_state_changes", "state_changes", "ship_state_changes", "story_followup", "interlude_hook"):
        value = result.get(key)
        if value:
            return True
    changes = result.get("resource_changes")
    return isinstance(changes, dict) and bool(changes)


def operation_plans(event: dict[str, Any]) -> list[dict[str, Any]]:
    plans = event.get("operation_plans", [])
    if isinstance(plans, list):
        return [plan for plan in plans if isinstance(plan, dict)]
    if isinstance(plans, dict):
        normalized: list[dict[str, Any]] = []
        for action, plan in plans.items():
            if isinstance(plan, dict):
                copy = plan.copy()
                copy.setdefault("action", str(action))
                normalized.append(copy)
        return normalized
    return []


def audit(strict: bool) -> int:
    rooms = load_json(ROOMS_PATH)
    events = load_json(EVENTS_PATH)
    records = event_records(events)
    active_sources = active_corpus_ids()
    findings: list[tuple[str, str]] = []

    def warn(code: str, message: str) -> None:
        findings.append((code, message))

    for room in rooms.get("rooms", []):
        if not isinstance(room, dict):
            continue
        room_id = room.get("id", "<missing>")
        if room.get("type") == "mission":
            if not room.get("character_state_stakes"):
                warn("room.character_state", f"{room_id}: add character_state_stakes so mission pressure targets individual people, not only aggregate resources")
            for field in MISSION_REQUIRED_ROOM_FIELDS:
                if field not in room or room.get(field) in ("", [], {}):
                    warn("room.schema", f"{room_id}: missing or empty mission field `{field}`")
            if not room.get("deployment_manifest") and not strict:
                warn("room.deployment_manifest", f"{room_id}: add deployment_manifest so squad geography and roles are clear")
            if not room.get("interlude_vectors"):
                warn("room.interlude", f"{room_id}: add interlude_vectors so mission consequences can surface between missions")
            if not room.get("religious_subtext"):
                warn("room.religious_subtext", f"{room_id}: add religious_subtext so the anomaly is tied to a specific religious motif, not generic symbolism")
            for issue in weak_corpus_records(room.get("corpus_influences", [])):
                warn("corpus.weak", f"{room_id}: {issue}")
            if not room.get("corpus_anchor_points"):
                warn("corpus.anchor_points", f"{room_id}: add corpus_anchor_points so source material becomes playable details")
            else:
                for issue in weak_anchor_points(room.get("corpus_anchor_points", [])):
                    warn("corpus.anchor_points", f"{room_id}: {issue}")
        for key in room.get("resource_stakes", {}):
            if key in LEGACY_STATE_ALIASES:
                warn("state.alias", f"{room_id}: resource_stakes uses legacy `{key}`; prefer `{LEGACY_STATE_ALIASES[key]}`")

    for event_id, event in records.items():
        is_system_event = str(event_id).startswith("pressure_") or bool(event.get("system_event", False))
        for field in EVENT_REQUIRED_FIELDS:
            if is_system_event and field == "buttons" and event.get("choices"):
                continue
            if is_system_event and field == "action_results" and event.get("choice_effects"):
                continue
            if field not in event or event.get(field) in ("", [], {}):
                warn("event.schema", f"{event_id}: missing or empty event field `{field}`")

        influences = event.get("corpus_influences", [])
        if not is_system_event and event.get("type") in {"choice", "story", "debrief", "interlude", "base_incident"} and not influences:
            warn("corpus.missing", f"{event_id}: missing corpus_influences")
        for seed_id in event.get("corpus_artifact_ids", []):
            if active_sources and seed_id not in active_sources and not str(seed_id).startswith("revelation_seed_"):
                warn("corpus.inactive", f"{event_id}: corpus_artifact_id `{seed_id}` is not an active source id")
        if influences:
            for issue in weak_corpus_records(influences):
                warn("corpus.weak", f"{event_id}: {issue}")
            if event.get("type") in {"choice", "story", "debrief", "base_incident"} and not event.get("corpus_anchor_points"):
                warn("corpus.anchor_points", f"{event_id}: add corpus_anchor_points so anchors show up as prose/evidence/follow-up obligations")
            elif event.get("corpus_anchor_points"):
                for issue in weak_anchor_points(event.get("corpus_anchor_points", [])):
                    warn("corpus.anchor_points", f"{event_id}: {issue}")

        if event.get("type") == "choice":
            plans = operation_plans(event)
            buttons = event.get("buttons", [])
            button_actions = {str(button.get("action", "")) for button in buttons if isinstance(button, dict)}
            planned_actions = {str(plan.get("action", "")) for plan in plans}
            if not plans:
                warn("plan.missing", f"{event_id}: mission choice event should define character-owned operation_plans")
            for action in sorted(button_actions - planned_actions):
                if action:
                    warn("plan.missing", f"{event_id}:{action}: button has no character-owned operation plan")
            for plan in plans:
                action = str(plan.get("action", ""))
                for field in ("action", "officer_id", "primary_skill", "base_success", "yield", "risk", "outcomes"):
                    if field not in plan or plan.get(field) in ("", [], {}):
                        warn("plan.schema", f"{event_id}:{action}: operation plan missing or empty `{field}`")
                outcomes = plan.get("outcomes", {})
                if isinstance(outcomes, dict):
                    for band in ("success", "partial", "failure"):
                        if band not in outcomes:
                            warn("plan.outcome", f"{event_id}:{action}: operation plan lacks `{band}` outcome")

        action_results = event.get("action_results", {})
        if isinstance(action_results, dict):
            for action, result in action_results.items():
                if not isinstance(result, dict):
                    warn("event.result", f"{event_id}:{action}: action result is not an object")
                    continue
                if not has_durable_result(result):
                    warn("branch.consequence", f"{event_id}:{action}: result has no durable state/resource/follow-up/interlude consequence")
                for key in resource_keys({"action_results": {action: result}}):
                    if key in LEGACY_STATE_ALIASES:
                        warn("state.alias", f"{event_id}:{action}: resource_changes uses legacy `{key}`; prefer `{LEGACY_STATE_ALIASES[key]}`")
                for state_key in iter_state_like_values(result):
                    if state_key in LEGACY_STATE_ALIASES:
                        warn("state.alias", f"{event_id}:{action}: state change uses legacy `{state_key}`; prefer `{LEGACY_STATE_ALIASES[state_key]}`")
                    elif "." in state_key and not state_key.startswith(CANONICAL_PREFIXES):
                        warn("state.unknown", f"{event_id}:{action}: state key `{state_key}` is not in a canonical namespace")

        followups = event.get("story_followups", {})
        if isinstance(followups, dict):
            for action, followup in followups.items():
                if not isinstance(followup, dict):
                    warn("followup.schema", f"{event_id}:{action}: follow-up entry is not an object")
                    continue
                target = followup.get("event_id")
                if target not in records:
                    warn("followup.missing", f"{event_id}:{action}: follow-up target `{target}` does not exist")
                if not followup.get("queued_line"):
                    warn("followup.schema", f"{event_id}:{action}: follow-up lacks queued_line")
        elif event.get("type") == "choice":
            warn("followup.missing", f"{event_id}: choice event has no story_followups")

        if event.get("type") == "interlude":
            required_fields = ("interlude_type", "choices", "outcomes") if is_system_event else ("interlude_type", "state_reads", "state_writes", "featured_characters", "visible_text", "choices", "outcomes", "followup_hooks", "corpus_anchors")
            for field in required_fields:
                if field not in event or event.get(field) in ("", [], {}):
                    warn("interlude.schema", f"{event_id}: missing or empty interlude field `{field}`")

    if findings:
        print("REVELATION_CONTENT_AUDIT_FINDINGS")
        for code, message in findings:
            print(f"- [{code}] {message}")
        if strict:
            return 1
        print(f"REVELATION_CONTENT_AUDIT_WARNINGS count={len(findings)}")
        return 0

    print("REVELATION_CONTENT_AUDIT_OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any finding is detected.")
    args = parser.parse_args()
    return audit(args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
