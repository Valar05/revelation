#!/usr/bin/env python3
"""Compile a writer-authored Revelation room blueprint into a deployable patch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_MANAGER_PATH = ROOT / "run_manager.gd"
DEFAULT_POOLS = ["mission", "branch", "straight_noncombat", "recovery", "random_non_special"]
OFFICER_IDS = {
    "torah",
    "brooks",
    "lt_mara_owen",
    "dr_samira_iyad",
    "agent_caleb_ross",
    "specialist_mina_park",
    "dr_lenora_saye",
}
OFFICER_DISPLAY_NAMES = {
    "torah": "Torah",
    "brooks": "Brooks",
    "lt_mara_owen": "Owen",
    "dr_samira_iyad": "Iyad",
    "agent_caleb_ross": "Ross",
    "specialist_mina_park": "Park",
    "dr_lenora_saye": "Saye",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def implemented_actions() -> set[str]:
    text = RUN_MANAGER_PATH.read_text(encoding="utf-8")
    actions = {
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
        "quarantine_forms",
        "report_word_gap",
        "return_ross",
        "support_owen",
        "torah_exception",
        "torah_speaks",
        "watch_quietly",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('"') and stripped.endswith('":'):
            actions.add(stripped.strip('":'))
    return actions


ACTION_ALIASES = {
    "combat": "intercept",
    "fight": "intercept",
    "restrain": "intercept",
}


def normalize_action_id(action: Any) -> str:
    value = first_text(action, "proceed")
    return ACTION_ALIASES.get(value, value)


def require_text(payload: dict[str, Any], key: str, location: str, errors: list[str]) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        errors.append(f"{location}.{key} is required")
    return value


def require_list(payload: dict[str, Any], key: str, location: str, errors: list[str]) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{location}.{key} must be a non-empty list")
        return []
    return value


def source_id_from_chunk(chunk_id: str) -> str:
    if ":" in chunk_id:
        return chunk_id.split(":", 1)[0]
    return chunk_id


def listify(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}, []):
        return []
    return [value]


def first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def clip_words(text: str, max_words: int) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "..."


def normalized_text(value: Any) -> str:
    return str(value or "").lower()


def prose_blob(blueprint: dict[str, Any]) -> str:
    parts: list[str] = []
    room = blueprint.get("room", {})
    if isinstance(room, dict):
        for key in ("description", "first_visit_description", "return_description", "detection_report", "current_situation"):
            parts.append(str(room.get(key, "")))
    for event_key in ("root_event", "resolution_event", "cooldown_interlude"):
        event = blueprint.get(event_key, {})
        if not isinstance(event, dict):
            continue
        for key in ("line_1", "line_2"):
            parts.append(str(event.get(key, "")))
        for plan in event.get("operation_plans", []) or []:
            if not isinstance(plan, dict):
                continue
            outcomes = plan.get("outcomes", {})
            if isinstance(outcomes, dict):
                for outcome in outcomes.values():
                    if isinstance(outcome, dict):
                        parts.extend(str(line) for line in outcome.get("lines", []) or [])
        parts.extend(str(line) for line in listify(event.get("visible_text")))
        parts.extend(str(line) for line in listify(event.get("outcomes")))
    return "\n".join(parts).lower()


def visible_detail_hit(detail: str, blob: str) -> bool:
    detail = normalized_text(detail)
    words = [word for word in re_words(detail) if len(word) >= 4]
    if not words:
        return False
    return sum(1 for word in words if word in blob) >= min(2, len(words))


def re_words(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", text.lower())


def validate_visible_survival(blueprint: dict[str, Any], errors: list[str]) -> None:
    blob = prose_blob(blueprint)
    anchors = blueprint.get("corpus_anchor_points", [])
    if isinstance(anchors, list):
        for index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict):
                continue
            details = [str(detail) for detail in anchor.get("required_visible_details", []) if str(detail).strip()]
            if details and not any(visible_detail_hit(detail, blob) for detail in details):
                chunk_id = anchor.get("source_chunk_id", index)
                errors.append(f"corpus_anchor_points[{index}].{chunk_id}: no required_visible_details appear in player-facing prose")

    plan_owner_ids: set[str] = set()
    for event_key in ("root_event", "resolution_event"):
        event = blueprint.get(event_key, {})
        if not isinstance(event, dict):
            continue
        for plan in event.get("operation_plans", []) or []:
            if isinstance(plan, dict) and str(plan.get("officer_id", "")).strip():
                plan_owner_ids.add(str(plan["officer_id"]))
    for officer_id in sorted(plan_owner_ids):
        display = OFFICER_DISPLAY_NAMES.get(officer_id, officer_id)
        if display.lower() not in blob:
            errors.append(f"character.{officer_id}: plan owner is not named in player-facing prose")
    if len([name for name in OFFICER_DISPLAY_NAMES.values() if name.lower() in blob]) < 3:
        errors.append("character.visible_cast: fewer than three recurring character names appear in player-facing prose")


def validate_deployment_manifest(room: dict[str, Any], errors: list[str]) -> None:
    manifest = room.get("deployment_manifest")
    if not isinstance(manifest, list) or not manifest:
        errors.append("room.deployment_manifest must list deployed/remote squad members")
        return
    required = ("officer_id", "name", "mission_role", "physical_position", "assigned_reason", "visible_state")
    for index, member in enumerate(manifest):
        if not isinstance(member, dict):
            errors.append(f"room.deployment_manifest[{index}] must be an object")
            continue
        for key in required:
            if not first_text(member.get(key)):
                errors.append(f"room.deployment_manifest[{index}].{key} is required")


def validate_action_profile(room: dict[str, Any], errors: list[str]) -> None:
    mode = first_text(room.get("mission_mode"), room.get("operation_type")).lower()
    if mode != "action_horror":
        return
    profile = room.get("action_profile")
    if not isinstance(profile, dict) or not profile:
        errors.append("room.action_profile is required for mission_mode action_horror")
        return
    for key in (
        "physical_threat",
        "contact_state",
        "field_manual_drill",
        "tactical_objective",
        "symbolic_close",
        "not_monster_of_week",
    ):
        if not first_text(profile.get(key)):
            errors.append(f"room.action_profile.{key} is required for action_horror")
    blob = normalized_text(" ".join(str(value) for value in profile.values()))
    tactical_terms = (
        "react",
        "contact",
        "security",
        "suppress",
        "fix",
        "bound",
        "breach",
        "clear",
        "evac",
        "casevac",
        "break contact",
        "cordon",
        "contain",
        "movement",
        "fire",
    )
    if not any(term in blob for term in tactical_terms):
        errors.append("room.action_profile.field_manual_drill must include a concrete tactical procedure")


def normalize_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    chunk_id = first_text(anchor.get("source_chunk_id"), anchor.get("chunk_id"), anchor.get("id"))
    role = first_text(anchor.get("anchor_role"), anchor.get("role"), "premise")
    fingerprint = first_text(anchor.get("source_fingerprint"), anchor.get("fingerprint"), anchor.get("source_moment"))
    transfer = first_text(anchor.get("playable_transform"), anchor.get("structural_transfer"), anchor.get("transfer"))
    details = listify(anchor.get("required_visible_details") or anchor.get("visible_details"))
    payoff = first_text(anchor.get("followup_payoff"), anchor.get("payoff"))
    return {
        "source_id": first_text(anchor.get("source_id"), source_id_from_chunk(chunk_id)),
        "source_chunk_id": chunk_id,
        "anchor_role": role,
        "source_fingerprint": fingerprint,
        "playable_transform": transfer,
        "required_visible_details": [str(detail) for detail in details if str(detail).strip()],
        "followup_payoff": payoff,
    }


def normalize_influence(anchor: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_anchor(anchor)
    source_id = normalized["source_id"]
    return {
        "source_id": source_id,
        "source_title": first_text(anchor.get("source_title"), source_id.replace("_", " ").title()),
        "source_chunk_id": normalized["source_chunk_id"],
        "source_moment": normalized["source_fingerprint"],
        "source_fingerprint": normalized["source_fingerprint"],
        "room_application": normalized["playable_transform"],
        "structural_transfer": normalized["playable_transform"],
        "required_visible_details": normalized["required_visible_details"],
        "followup_payoff": normalized["followup_payoff"],
    }


def default_state_change(event_id: str, action: str, band: str) -> str:
    return f"{event_id}.{action}.{band}"


def default_resource_changes(officer_id: str, band: str) -> dict[str, str]:
    if not officer_id:
        return {}
    if band == "success":
        return {f"character.{officer_id}.morale": "+1"}
    if band == "partial":
        return {f"character.{officer_id}.stress": "+1"}
    return {
        f"character.{officer_id}.stress": "+2",
        f"character.{officer_id}.fatigue": "+1",
    }


def normalize_outcome(plan: dict[str, Any], event_id: str, band: str) -> dict[str, Any]:
    explicit = plan.get("outcomes", {}).get(band) if isinstance(plan.get("outcomes"), dict) else None
    if isinstance(explicit, dict):
        lines = listify(explicit.get("lines"))
        changes = listify(explicit.get("environment_state_changes"))
        resources = explicit.get("resource_changes", {})
        return {
            "lines": [str(line) for line in lines if str(line).strip()],
            "environment_state_changes": [str(change) for change in changes if str(change).strip()],
            "resource_changes": resources if isinstance(resources, dict) else {},
        }

    line = first_text(
        plan.get(f"{band}_line"),
        plan.get(f"{band}_result"),
        plan.get(band),
    )
    action = first_text(plan.get("action"), "proceed")
    officer_id = first_text(plan.get("officer_id"))
    changes = listify(plan.get(f"{band}_changes") or plan.get(f"{band}_state_changes"))
    resources = plan.get(f"{band}_resource_changes", {})
    if not isinstance(resources, dict):
        resources = {}
    if not changes and not resources:
        changes = [default_state_change(event_id, action, band)]
        resources = default_resource_changes(officer_id, band)
    return {
        "lines": [line] if line else [f"{band.title()} result pending field report."],
        "environment_state_changes": [str(change) for change in changes if str(change).strip()],
        "resource_changes": resources,
    }


def normalize_plan(plan: dict[str, Any], event_id: str) -> dict[str, Any]:
    action = normalize_action_id(plan.get("action"))
    officer_id = first_text(plan.get("officer_id"), plan.get("character"), plan.get("character_id"))
    normalized = {
        "label": first_text(plan.get("label"), plan.get("button"), action.replace("_", " ").title()),
        "action": action,
        "officer_id": officer_id,
        "primary_skill": first_text(plan.get("primary_skill"), plan.get("skill"), "field judgment"),
        "tactical_step": first_text(plan.get("tactical_step"), plan.get("procedure_step")),
        "intent": first_text(plan.get("intent"), plan.get("plan"), plan.get("proposal"), plan.get("tactical_step")),
        "base_success": plan.get("base_success", 0.65),
        "yield": first_text(plan.get("yield"), plan.get("intent"), plan.get("success_goal")),
        "risk": first_text(plan.get("risk"), plan.get("failure_risk"), plan.get("backfire")),
        "outcomes": {
            "success": normalize_outcome(plan, event_id, "success"),
            "partial": normalize_outcome(plan, event_id, "partial"),
            "failure": normalize_outcome(plan, event_id, "failure"),
        },
    }
    return normalized


def normalize_event(event: dict[str, Any], event_type: str, followup_id: str = "") -> dict[str, Any]:
    event_id = first_text(event.get("id"), f"{event_type}_event")
    plans = [
        normalize_plan(plan, event_id)
        for plan in listify(event.get("plans") or event.get("operation_plans"))
        if isinstance(plan, dict)
    ]
    buttons = [
        {
            "label": plan["label"],
            "action": plan["action"],
            "preview": clip_words(first_text(plan.get("intent"), plan.get("yield"), plan.get("risk")), 16),
        }
        for plan in plans
    ]
    normalized = {
        "id": event_id,
        "type": event_type,
        "speaker": first_text(event.get("speaker"), "SITREP"),
        "line_1": clip_words(first_text(event.get("line_1")), 30),
        "line_2": clip_words(first_text(event.get("line_2")), 30),
        "buttons": buttons,
        "operation_plans": plans,
        "action_results": {
            plan["action"]: {
                "lines": plan["outcomes"]["success"]["lines"],
                "environment_state_changes": plan["outcomes"]["success"]["environment_state_changes"],
                "resource_changes": plan["outcomes"]["success"]["resource_changes"],
            }
            for plan in plans
        },
    }
    if followup_id:
        normalized["story_followups"] = {
            plan["action"]: {
                "event_id": followup_id,
                "queued_line": first_text(event.get("queued_line"), event.get("followup_line"), "The case file remains open."),
                "trigger_key": followup_id,
                "delay_rooms": 0,
                "immediate": True,
                "reactivate_on_reshuffle": False,
            }
            for plan in plans
        }
    return normalized


def normalize_cooldown(event: dict[str, Any], corpus_anchors: list[dict[str, Any]]) -> dict[str, Any]:
    buttons = event.get("buttons")
    if not isinstance(buttons, list) or not buttons:
        buttons = [
            {"label": "Concede", "action": "proceed"},
            {"label": "Hold Line", "action": "proceed"},
        ]
    return {
        "id": first_text(event.get("id"), "mission_cooldown_interlude"),
        "type": "interlude",
        "speaker": first_text(event.get("speaker"), "Debrief"),
        "line_1": clip_words(first_text(event.get("line_1")), 30),
        "line_2": clip_words(first_text(event.get("line_2")), 30),
        "buttons": buttons,
        "action_results": {
            "proceed": {
                "lines": listify(event.get("visible_text")) or [first_text(event.get("line_1"))],
                "environment_state_changes": listify(event.get("state_writes")) or ["mission.cooldown_seen"],
                "resource_changes": {},
            }
        },
        "interlude_type": first_text(event.get("interlude_type"), "debrief"),
        "state_reads": listify(event.get("state_reads")) or ["mission.thread_state"],
        "state_writes": listify(event.get("state_writes")) or ["mission.cooldown_seen"],
        "featured_characters": listify(event.get("featured_characters")) or ["brooks"],
        "visible_text": listify(event.get("visible_text")) or [first_text(event.get("line_1"))],
        "choices": listify(event.get("choices")) or ["Let the squad speak plainly.", "Keep the report narrow."],
        "outcomes": listify(event.get("outcomes")) or [first_text(event.get("line_2"))],
        "followup_hooks": listify(event.get("followup_hooks")) or ["future command pressure"],
        "corpus_anchors": listify(event.get("corpus_anchors")) or [anchor["source_chunk_id"] for anchor in corpus_anchors[:2]],
    }


def normalize_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    if "root_event" in blueprint and "resolution_event" in blueprint:
        return blueprint

    room = dict(blueprint.get("room", {}))
    room["type"] = "mission"
    contract = dict(room.get("scenario_generation_contract", {}))
    contract.setdefault("root_sin", first_text(room.get("root_sin"), blueprint.get("root_sin")))
    contract.setdefault("modern_incident_logic", first_text(room.get("modern_incident_logic"), blueprint.get("modern_incident_logic")))
    contract.setdefault("closure_test", first_text(room.get("closure_test"), blueprint.get("closure_test")))
    room["scenario_generation_contract"] = contract

    subtext = dict(room.get("religious_subtext", {}))
    subtext.setdefault("source_pattern", first_text(room.get("religious_pattern"), blueprint.get("religious_pattern")))
    subtext.setdefault("transformed_rule", first_text(room.get("anomaly_rule"), blueprint.get("anomaly_rule")))
    subtext.setdefault("forbidden_flat_read", first_text(room.get("forbidden_flat_read"), "Do not literalize the source as a sermon or apparition."))
    room["religious_subtext"] = subtext
    if "deployment_manifest" not in room:
        room["deployment_manifest"] = []
    room.setdefault("mission_mode", first_text(blueprint.get("mission_mode"), room.get("mission_mode"), "investigation"))
    room.setdefault(
        "resource_stakes",
        {
            "squad.stress": "mission pressure rises if evidence is lost",
            "institute.political_pressure": "public accountability may increase command scrutiny",
        },
    )
    room.setdefault(
        "followup_vectors",
        listify(room.get("interlude_vectors"))
        or ["debrief fallout", "command review", "future threshold unease"],
    )
    room.setdefault(
        "progression_state",
        {
            "early": "The anomaly is treated as a falsified record with symbolic residue.",
            "mid": "Accountability choices affect squad trust and Institute pressure.",
            "late": "Unresolved names can return through later evidence reviews.",
        },
    )

    anchors = [
        normalize_anchor(anchor)
        for anchor in listify(blueprint.get("anchors") or blueprint.get("corpus_anchor_points"))
        if isinstance(anchor, dict)
    ]
    influences = [
        normalize_influence(anchor)
        for anchor in listify(blueprint.get("anchors") or blueprint.get("corpus_influences") or blueprint.get("corpus_anchor_points"))
        if isinstance(anchor, dict)
    ]

    root_source = dict(blueprint.get("root") or blueprint.get("root_event") or {})
    resolution_source = dict(blueprint.get("resolution") or blueprint.get("resolution_event") or {})
    cooldown_source = dict(blueprint.get("cooldown") or blueprint.get("cooldown_interlude") or {})
    resolution_id = first_text(resolution_source.get("id"), f"{first_text(room.get('id'), 'mission')}_resolution")
    cooldown_id = first_text(cooldown_source.get("id"), f"{first_text(room.get('id'), 'mission')}_cooldown")
    resolution_source["id"] = resolution_id
    cooldown_source["id"] = cooldown_id

    normalized = {
        "title": first_text(blueprint.get("title"), room.get("name")),
        "design_goal": first_text(blueprint.get("design_goal"), room.get("description")),
        "source_mechanism": blueprint.get("source_mechanism", {}),
        "symbolic_rule": blueprint.get("symbolic_rule", {}),
        "room": room,
        "corpus_influences": influences,
        "corpus_anchor_points": anchors,
        "root_event": normalize_event(root_source, "choice", resolution_id),
        "resolution_event": normalize_event(resolution_source, "resolution", cooldown_id),
        "cooldown_interlude": normalize_cooldown(cooldown_source, anchors),
        "deck_pools": blueprint.get("deck_pools", DEFAULT_POOLS),
        "required_engine_changes": blueprint.get("required_engine_changes", []),
        "inspiration_notes": blueprint.get("inspiration_notes", []),
        "self_critique": blueprint.get("self_critique", []),
    }
    return normalized


def validate_source_first_contract(blueprint: dict[str, Any], errors: list[str]) -> None:
    source = blueprint.get("source_mechanism")
    if not isinstance(source, dict) or not source:
        errors.append("source_mechanism is required; start with religious source action before modern setup")
    else:
        for key in ("source_chunk_id", "source_action", "sin_or_transgression", "witness_or_judgment", "required_scene_elements"):
            if source.get(key) in ("", [], {}, None):
                errors.append(f"source_mechanism.{key} is required")
    rule = blueprint.get("symbolic_rule")
    if not isinstance(rule, dict) or not rule:
        errors.append("symbolic_rule is required; define the active manifestation as an if/then rule")
    else:
        for key in ("rule", "active_manifestation", "escalation", "closure_condition"):
            if rule.get(key) in ("", [], {}, None):
                errors.append(f"symbolic_rule.{key} is required")
        active = normalized_text(rule.get("active_manifestation"))
        active_terms = (
            "now",
            "currently",
            "active",
            "manifest",
            "happening",
            "before the squad",
            "already",
            "has been",
            "have been",
            "presented",
            "report",
            "refusing",
            "is cycling",
            "are trapped",
            "is trapped",
            "slams",
            "appears",
            "rising",
            "weeping",
            "will not",
        )
        if not any(term in active for term in active_terms):
            errors.append("symbolic_rule.active_manifestation must state what is actively happening before the squad arrives")


def validate_corpus_block(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{location} must be a non-empty list")
        return
    for index, item in enumerate(value):
        item_location = f"{location}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_location} must be an object")
            continue
        for key in ("source_chunk_id", "source_fingerprint", "structural_transfer", "required_visible_details", "followup_payoff"):
            if key not in item or item[key] in ("", [], {}):
                errors.append(f"{item_location}.{key} is required")
        details = item.get("required_visible_details", [])
        if not isinstance(details, list) or len([detail for detail in details if str(detail).strip()]) < 2:
            errors.append(f"{item_location}.required_visible_details needs at least two items")


def validate_anchor_block(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{location} must be a non-empty list")
        return
    for index, item in enumerate(value):
        item_location = f"{location}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_location} must be an object")
            continue
        for key in ("source_id", "source_chunk_id", "anchor_role", "source_fingerprint", "playable_transform", "required_visible_details", "followup_payoff"):
            if key not in item or item[key] in ("", [], {}):
                errors.append(f"{item_location}.{key} is required")
        details = item.get("required_visible_details", [])
        if not isinstance(details, list) or len([detail for detail in details if str(detail).strip()]) < 2:
            errors.append(f"{item_location}.required_visible_details needs at least two items")


def validate_plan(plan: dict[str, Any], location: str, actions: set[str], errors: list[str]) -> None:
    action = normalize_action_id(require_text(plan, "action", location, errors))
    if action and action not in actions:
        errors.append(f"{location}.action `{action}` is not implemented")
    officer_id = require_text(plan, "officer_id", location, errors)
    if officer_id and officer_id not in OFFICER_IDS:
        errors.append(f"{location}.officer_id `{officer_id}` is not an internal Revelation officer id")
    base_success = plan.get("base_success")
    if not isinstance(base_success, (int, float)) or not (0.05 <= float(base_success) <= 0.95):
        errors.append(f"{location}.base_success must be 0.05-0.95")
    for key in ("primary_skill", "yield", "risk"):
        require_text(plan, key, location, errors)
    outcomes = plan.get("outcomes")
    if not isinstance(outcomes, dict):
        errors.append(f"{location}.outcomes must be an object")
        return
    for band in ("success", "partial", "failure"):
        outcome = outcomes.get(band)
        outcome_location = f"{location}.outcomes.{band}"
        if not isinstance(outcome, dict):
            errors.append(f"{outcome_location} must be an object")
            continue
        lines = outcome.get("lines")
        if not isinstance(lines, list) or not [line for line in lines if str(line).strip()]:
            errors.append(f"{outcome_location}.lines must be a non-empty list")
        changes = outcome.get("environment_state_changes", [])
        if changes and not isinstance(changes, list):
            errors.append(f"{outcome_location}.environment_state_changes must be a list")
        resource_changes = outcome.get("resource_changes", {})
        if resource_changes and not isinstance(resource_changes, dict):
            errors.append(f"{outcome_location}.resource_changes must be an object")
        if not changes and not resource_changes:
            errors.append(f"{outcome_location} needs durable state/resource changes")


def validate_event_blueprint(event: dict[str, Any], location: str, actions: set[str], errors: list[str]) -> None:
    for key in ("id", "type", "speaker", "line_1", "line_2"):
        require_text(event, key, location, errors)
    buttons = require_list(event, "buttons", location, errors)
    button_actions: set[str] = set()
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            errors.append(f"{location}.buttons[{index}] must be an object")
            continue
        action = require_text(button, "action", f"{location}.buttons[{index}]", errors)
        require_text(button, "label", f"{location}.buttons[{index}]", errors)
        if action:
            button_actions.add(action)
            if action not in actions:
                errors.append(f"{location}.buttons[{index}].action `{action}` is not implemented")
    plans = event.get("operation_plans", [])
    if event.get("type") in {"choice", "resolution"}:
        if not isinstance(plans, list) or not plans:
            errors.append(f"{location}.operation_plans required")
        planned_actions = set()
        for index, plan in enumerate(plans if isinstance(plans, list) else []):
            if not isinstance(plan, dict):
                errors.append(f"{location}.operation_plans[{index}] must be an object")
                continue
            planned_actions.add(str(plan.get("action", "")))
            validate_plan(plan, f"{location}.operation_plans[{index}]", actions, errors)
        for action in sorted(button_actions - planned_actions):
            errors.append(f"{location}: button action `{action}` has no matching operation_plan")


def validate_action_horror_events(blueprint: dict[str, Any], errors: list[str]) -> None:
    room = blueprint.get("room", {})
    if not isinstance(room, dict) or first_text(room.get("mission_mode")).lower() != "action_horror":
        return
    blob = prose_blob(blueprint)
    contact_terms = (
        "swarm",
        "locust",
        "strike",
        "hit",
        "contact",
        "stings",
        "teeth",
        "wings",
        "breach",
        "fire",
        "evac",
        "bound",
        "suppress",
        "cordon",
        "injur",
        "blood",
        "armor",
        "rifle",
    )
    if not any(term in blob for term in contact_terms):
        errors.append("action_horror.visible_contact: player-facing prose must show squad contact, physical threat, or tactical movement")

    tactical_terms = (
        "suppress",
        "fix",
        "bound",
        "breach",
        "clear",
        "evac",
        "casevac",
        "break contact",
        "cordon",
        "contain",
        "security",
        "react to contact",
        "movement",
    )
    plan_steps: list[str] = []
    for event_key in ("root_event", "resolution_event"):
        event = blueprint.get(event_key, {})
        if not isinstance(event, dict):
            continue
        for plan in event.get("operation_plans", []) or []:
            if not isinstance(plan, dict):
                continue
            step = first_text(plan.get("tactical_step"), plan.get("primary_skill"), plan.get("yield"), plan.get("risk")).lower()
            plan_steps.append(step)
    if not any(any(term in step for term in tactical_terms) for step in plan_steps):
        errors.append("action_horror.operation_plans: at least one plan must name a concrete field-manual tactical step")


def validate_blueprint(blueprint: dict[str, Any]) -> list[str]:
    blueprint = normalize_blueprint(blueprint)
    errors: list[str] = []
    validate_source_first_contract(blueprint, errors)
    actions = implemented_actions()
    room = blueprint.get("room")
    if not isinstance(room, dict):
        errors.append("room must be an object")
    else:
        for key in ("id", "name", "description", "first_visit_description", "return_description", "detection_report", "current_situation"):
            require_text(room, key, "room", errors)
        if room.get("type", "mission") != "mission":
            errors.append("room.type must be mission")
        for key in ("scenario_generation_contract", "religious_subtext", "character_state_stakes"):
            if not isinstance(room.get(key), dict) or not room.get(key):
                errors.append(f"room.{key} must be a non-empty object")
        validate_deployment_manifest(room, errors)
        validate_action_profile(room, errors)
        for key in ("officer_reports", "procedure_hooks", "interlude_vectors"):
            require_list(room, key, "room", errors)

    validate_corpus_block(blueprint.get("corpus_influences"), "corpus_influences", errors)
    validate_anchor_block(blueprint.get("corpus_anchor_points"), "corpus_anchor_points", errors)
    for key in ("root_event", "resolution_event", "cooldown_interlude"):
        event = blueprint.get(key)
        if not isinstance(event, dict):
            errors.append(f"{key} must be an object")
            continue
        validate_event_blueprint(event, key, actions, errors)
    cooldown = blueprint.get("cooldown_interlude", {})
    if isinstance(cooldown, dict):
        for key in ("interlude_type", "state_reads", "state_writes", "featured_characters", "visible_text", "choices", "outcomes", "followup_hooks", "corpus_anchors"):
            if key not in cooldown or cooldown[key] in ("", [], {}):
                errors.append(f"cooldown_interlude.{key} is required")
    validate_action_horror_events(blueprint, errors)
    validate_visible_survival(blueprint, errors)
    return errors


def with_common_anchors(event: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    compiled = event.copy()
    compiled.setdefault("corpus_influences", blueprint["corpus_influences"])
    compiled.setdefault("corpus_anchor_points", blueprint["corpus_anchor_points"])
    return compiled


def compile_patch(blueprint: dict[str, Any]) -> dict[str, Any]:
    blueprint = normalize_blueprint(blueprint)
    room = blueprint["room"].copy()
    room["type"] = "mission"
    room.setdefault("room_role", "action_investigation")
    room.setdefault("encounter_family", room["id"])
    room.setdefault("operation_type", "symbolic_field_mission")
    room.setdefault("captaincy_role", "authorize_character_plan")
    room.setdefault("scene_path", "")
    room["corpus_influences"] = blueprint["corpus_influences"]
    room["corpus_anchor_points"] = blueprint["corpus_anchor_points"]
    room.setdefault("active", True)

    root_event = with_common_anchors(blueprint["root_event"], blueprint)
    resolution_event = with_common_anchors(blueprint["resolution_event"], blueprint)
    cooldown_event = with_common_anchors(blueprint["cooldown_interlude"], blueprint)

    pools = blueprint.get("deck_pools", DEFAULT_POOLS)
    return {
        "title": blueprint.get("title", room["name"]),
        "design_goal": blueprint.get("design_goal", room["description"]),
        "events": [{"room_id": room["id"], "event": root_event}],
        "special_events": [resolution_event, cooldown_event],
        "room_records": [room],
        "deck_pool_updates": [{"pool": str(pool), "room_id": room["id"]} for pool in pools],
        "mutations": [],
        "symbiotes": [],
        "enemies": [],
        "required_engine_changes": blueprint.get("required_engine_changes", []),
        "inspiration_notes": blueprint.get("inspiration_notes", []),
        "self_critique": blueprint.get("self_critique", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blueprint")
    parser.add_argument("--out", default="generated/revelation_compiled_patch.json")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    blueprint_path = Path(args.blueprint)
    if not blueprint_path.is_absolute():
        blueprint_path = ROOT / blueprint_path
    blueprint = load_json(blueprint_path)
    errors = validate_blueprint(blueprint)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.validate_only:
        print("ok")
        return 0
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, compile_patch(blueprint))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
