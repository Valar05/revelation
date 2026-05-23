#!/usr/bin/env python3
"""Generate compact Revelation room blueprints with strict cost guards."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import revelation_blueprint_compiler as compiler


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"
MEMORY_DIR = ROOT / ".agent-memory"
DEFAULT_MODEL = os.environ.get("REVELATION_BLUEPRINT_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_INPUT_TOKENS = int(os.environ.get("REVELATION_BLUEPRINT_MAX_INPUT_TOKENS", "7000"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.environ.get("REVELATION_BLUEPRINT_MAX_OUTPUT_TOKENS", "4500"))


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def compact_lines(text: str, max_chars: int) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "..."


def env_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    home = Path.home()
    for path in (home / ".secrets" / "anthropic.env", home / ".bashrc", home / ".profile"):
        text = read_text(path)
        if not text:
            continue
        match = re.search(rf"^\s*(?:export\s+)?{re.escape(name)}=(['\"]?)(.*?)\1\s*$", text, re.MULTILINE)
        if match:
            return match.group(2).strip()
    return ""


def compact_revelation_context() -> dict[str, Any]:
    style = read_text(MEMORY_DIR / "revelation_style.md")
    systems = read_text(MEMORY_DIR / "revelation_foundational_systems.md")
    state = read_text(MEMORY_DIR / "revelation_state_vocabulary.md")
    process = read_text(MEMORY_DIR / "revelation_scenario_generation_process.md")
    return {
        "project": "Revelation",
        "voice_rules": [
            "Restrained symbolic horror in operational prose.",
            "Characters are trained personnel; fear shows as hesitation, fatigue, fixation, silence, or procedural breakdown.",
            "Describe anomalies observationally first, emotionally second, interpretively last.",
            "Do not quote scripture in player-facing prose; transform it into field evidence, hazard rules, moral cause, and consequence.",
            "No melodrama, internet humor, generic cult chanting, or pseudo-Lovecraft adjective spam.",
        ],
        "scenario_rules": [
            "The what comes from religious corpus anchors.",
            "The how comes from procedure, evidence custody, tactical movement, quarantine, triage, or field command.",
            "The structure comes from weird-fiction escalation: ordinary report, contradiction, field evidence, failed explanation, partial closure, remainder.",
            "Each mission must have a root sin or moral failure that explains why the anomaly is happening.",
            "Each mission must orient the squad: who deployed, where each person is, what each person's operational role is, and who is remote or absent.",
            "Resolution should close the phenomenon locally through accountability, recovery, confession, restitution, destruction, evacuation, or containment with an explicit unresolved remainder.",
            "Do not reuse foundational examples as default source shapes; avoid locust-swarm scenarios unless the user explicitly asks for locusts.",
            "Each choice is a named character's plan; if that character is unavailable, the runtime can hide the option.",
            "Each character plan has success, partial, and failure/backfire outcomes that alter individual stress, morale, mental_state, fatigue, injury, contamination, loyalty, or availability.",
            "Do not expose numeric odds in player text.",
            "Corpus anchors must survive into visible prose as objects, procedures, timings, phrases, sounds, documents, or bodily effects; hidden anchor metadata is not enough.",
            "Character stakes must survive into visible prose as behavior, hesitation, silence, professional conflict, fatigue, fixation, or relationship pressure; hidden state metadata is not enough.",
        ],
        "known_characters": sorted(compiler.OFFICER_IDS),
        "implemented_actions": sorted(compiler.implemented_actions()),
        "state_vocab_excerpt": compact_lines(state, 650),
        "process_excerpt": compact_lines(process, 850),
        "style_excerpt": compact_lines(style, 750),
        "systems_excerpt": compact_lines(systems, 650),
    }


def compact_fragment(fragment: dict[str, Any], max_excerpt_chars: int) -> dict[str, Any]:
    keys = [
        "id",
        "source_id",
        "source_title",
        "source_chunk_id",
        "source_circumstance",
        "nightmare_room_seed",
        "escalation_thread",
        "ship_state_hooks",
        "suggested_actions",
        "generation_rules",
    ]
    compact = {key: fragment.get(key) for key in keys if key in fragment}
    if fragment.get("source_excerpt"):
        compact["source_excerpt"] = compact_lines(str(fragment["source_excerpt"]), max_excerpt_chars)
    return compact


def load_corpus_packet(path_arg: str | None, limit: int, max_excerpt_chars: int) -> list[dict[str, Any]]:
    if not path_arg:
        return []
    path = Path(path_arg)
    if not path.is_absolute():
        path = ROOT / path
    payload = load_json(path)
    fragments = payload.get("fragments", [])
    if not isinstance(fragments, list):
        raise SystemExit(f"{path}: fragments must be a list")
    return [
        compact_fragment(fragment, max_excerpt_chars)
        for fragment in fragments[:limit]
        if isinstance(fragment, dict)
    ]


def blueprint_contract() -> dict[str, Any]:
    plan_contract = {
        "label": "button text, 5 words or fewer",
        "action": "implemented action id",
        "officer_id": "internal officer id",
        "primary_skill": "short hidden-skill phrase",
        "tactical_step": "for action_horror: concrete procedure such as suppress/fix, bound, breach, clear, evac, break contact, or symbolic close",
        "base_success": 0.65,
        "intent": "what the character is trying to do",
        "yield": "what success gains",
        "risk": "what backfires",
        "success_line": "Claude-authored player-facing result prose",
        "partial_line": "Claude-authored player-facing result prose",
        "failure_line": "Claude-authored player-facing result prose",
    }
    return {
        "title": "room title",
        "design_goal": "one sentence",
        "source_mechanism": {
            "source_chunk_id": "religious source chunk id",
            "source_action": "what happens in the source as an action or sequence",
            "sin_or_transgression": "the human failure that causes the symbolic pressure",
            "witness_or_judgment": "how the source exposes or answers the failure",
            "required_scene_elements": ["source-derived element that must appear visibly"],
        },
        "symbolic_rule": {
            "rule": "if/then manifestation rule derived from source_mechanism",
            "active_manifestation": "what impossible thing is happening now, before the squad arrives",
            "escalation": "how it gets worse if the squad fails",
            "closure_condition": "what resolves the manifestation",
        },
        "room": {
            "id": "new_room_id",
            "name": "player-visible room name",
            "type": "mission",
            "mission_mode": "investigation, action_horror, containment, or base_fallout",
            "description": "short list text",
            "first_visit_description": "operational setup",
            "return_description": "changed return text",
            "detection_report": "instrument/civilian/evidence report",
            "current_situation": "what Torah's squad sees now",
            "action_profile": {
                "physical_threat": "for action_horror: what can injure or kill people now",
                "contact_state": "for action_horror: how the squad is under contact or about to be hit",
                "field_manual_drill": "for action_horror: procedure basis such as react to contact, bounding overwatch, suppress/fix, clear, evacuate, or break contact",
                "tactical_objective": "for action_horror: what the squad must accomplish under pressure",
                "symbolic_close": "for action_horror: what source-derived rule must be addressed beyond force",
                "violent_resolution": "for violent action_horror: what object, anomaly, structure, beast, or threat can be hit, broken, burned, breached, or destroyed",
                "not_monster_of_week": "for action_horror: why the fight is biblical/symbolic and not a generic creature encounter",
            },
            "deployment_manifest": [
                {
                    "officer_id": "internal officer id",
                    "name": "display name",
                    "mission_role": "command lead, tactical point, technical specialist, symbolic asset, remote consult, etc.",
                    "physical_position": "where they are at mission start",
                    "assigned_reason": "why this person is on this mission",
                    "visible_state": "what the player can infer from behavior",
                }
            ],
            "root_sin": "moral failure that caused the anomaly",
            "modern_incident_logic": "how the anomaly appears in a contemporary site without contrivance",
            "closure_test": "what must be learned or done to resolve it",
            "religious_pattern": "religious source structure",
            "anomaly_rule": "how it behaves as an anomaly",
            "forbidden_flat_read": "what not to literalize",
            "officer_reports": ["named observations"],
            "procedure_hooks": ["field procedure or evidence hook"],
            "character_state_stakes": {"officer_id": "what stress/failure changes"},
            "interlude_vectors": ["debrief/smoke break/cooldown consequence"],
        },
        "anchors": [
            {
                "source_id": "source id",
                "source_chunk_id": "exact fragment id",
                "role": "premise/procedure/evidence/escalation/closure",
                "fingerprint": "specific source move",
                "transfer": "how the source becomes playable",
                "visible_details": ["detail 1", "detail 2"],
                "payoff": "later consequence",
            }
        ],
        "root": {
            "id": "stable_event_id",
            "speaker": "SITREP or character name",
            "line_1": "max 30 words, concrete actor/object/procedure",
            "line_2": "max 30 words, clear complication",
            "queued_line": "one sentence that queues the resolution",
            "plans": [plan_contract, plan_contract],
        },
        "resolution": {
            "id": "stable_event_id",
            "speaker": "SITREP or character name",
            "line_1": "max 30 words, concrete actor/object/procedure",
            "line_2": "max 30 words, clear complication",
            "queued_line": "one sentence that queues cooldown",
            "plans": [plan_contract, plan_contract],
        },
        "cooldown": {
            "id": "stable_event_id",
            "speaker": "character name",
            "line_1": "max 30 words, aftermath prose",
            "line_2": "max 30 words, character fallout or future pressure",
            "interlude_type": "debrief, smoke_break, meal, clinic, evidence_review, or command_review",
            "state_reads": ["character or thread state read"],
            "state_writes": ["character or thread state write"],
            "featured_characters": ["officer_id"],
            "visible_text": ["short interlude line"],
            "choices": ["short concession/reflection choice"],
            "outcomes": ["short emotional fallout"],
            "followup_hooks": ["future hook"],
            "corpus_anchors": ["source_chunk_id"],
        },
        "deck_pools": ["mission", "branch", "straight_noncombat", "recovery", "random_non_special"],
        "required_engine_changes": [],
        "inspiration_notes": ["short note"],
        "self_critique": ["one risk in the draft"],
    }


def build_prompt(args: argparse.Namespace) -> tuple[str, str]:
    context = compact_revelation_context()
    corpus_packet = load_corpus_packet(args.corpus_fragments, args.corpus_limit, args.max_excerpt_chars)
    system = "\n".join(
        [
            "You are a senior narrative systems writer for Revelation.",
            "Return exactly one JSON object. No markdown. No commentary.",
            "Keep the JSON compact enough to fit 6000 output tokens.",
            "Optimize for first-pass acceptance: clear modern incident logic, religious specificity, procedural plausibility, and runtime-ready lean blueprint structure.",
            "Spend words on player-facing setup, root cause, concrete evidence, and character-owned plans. Do not spend words on abstract mood.",
            "Use only implemented action ids and internal officer ids from the provided context.",
            "Start from source_mechanism, then symbolic_rule, then modern mission setup. Do not invent a modern incident first and decorate it with corpus afterward.",
            "The religious source must be load-bearing: if source_mechanism were removed, the mission premise, active manifestation, and closure condition would no longer make sense.",
            "The room must begin with an active symbolic manifestation already in progress. The Institute deploys because symbolic energy is manifesting from sin, not because the squad is auditing a cold case.",
            "If the request or corpus implies plague, beasts, war, pursuit, or violent judgment, use mission_mode action_horror and include room.action_profile.",
            "In action_horror, the squad must make physical contact with the threat in the root event; do not reduce the scene to readings, interviews, paper custody, or interval measurement.",
            "In action_horror, at least one root plan or resolution plan must visibly use field manual procedure: react to contact, establish security, suppress/fix, bound, breach, clear, evacuate, break contact, cordon, or contain.",
            "In action_horror, include a combat/containment threat that can injure personnel now, plus a symbolic close condition that force alone cannot satisfy.",
            "If the user asks for violence, at least one plan must be a real force option against an anomaly, object, structure, beast, or active threat. The force option can succeed, backfire, or only partially close the case, but it must be playable and consequential.",
            "In action_horror, write the fear of God through scale, judgment, pressure, awe, bodily risk, and disciplined personnel under contact. Avoid sermon prose and avoid generic monster-of-the-week structure.",
            "If the premise cannot explain why the anomaly occurs in the modern site, change the incident until it can.",
            "Use exactly two root plans and exactly two resolution plans.",
            "Claude writes all player-facing prose: room text, event lines, success_line, partial_line, failure_line, resolution text, and cooldown text.",
            "Do not write buttons, operation_plans, nested outcome objects, corpus_influences, or corpus_anchor_points; the local compiler expands those from your prose fields.",
            "For every anchor, put at least one visible_details item directly into room/event/outcome/cooldown prose.",
            "For every named plan owner, show a concrete character tell in at least one success/partial/failure line.",
            "The first_visit_description or current_situation must visibly establish the deployment manifest: who is physically present, who is remote, and why the plan owners are responsible for their tasks.",
            "The cooldown must be a character scene that reflects changed morale or mental state, not a neutral report summary.",
            "Use at least three recurring character names across the mission, plans, outcomes, and cooldown.",
            "Keep line_1 and line_2 readable on first hearing, no more than 30 words each.",
        ]
    )
    user = {
        "request": args.prompt,
        "cost_guardrail": {
            "task": "Write a compact blueprint only. A deterministic compiler will create the final Godot patch.",
            "avoid": [
                "full final patch boilerplate",
                "repeating instructions",
                "generic religious mood",
                "unexplained modern setup",
                "critique sections beyond self_critique",
            ],
        },
        "context": context,
        "corpus_packet": corpus_packet,
        "blueprint_contract": blueprint_contract(),
    }
    return system, json.dumps(user, indent=2, ensure_ascii=False)


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise SystemExit(f"Model did not return a JSON object:\n{text[:1200]}")
    try:
        payload = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        candidate = stripped[start : end + 1]
        repair_variants = []
        repaired = candidate
        for section in ("resolution", "cooldown", "deck_pools", "required_engine_changes", "inspiration_notes", "self_critique"):
            repaired = repaired.replace('}}]},"' + section + '"', '}]},"' + section + '"')
            repaired = repaired.replace(']}]},"' + section + '"', '}]},"' + section + '"')
        repaired = repaired.replace(']}},\"anchors\"', ']},\"anchors\"', 1)
        repair_variants.append(repaired)
        # Claude sometimes closes room.action_profile and room before continuing
        # with fields that belong inside room, leaving the top-level object closed
        # before anchors. Remove that one premature room close when present.
        repaired_room = candidate.replace('}},"deployment_manifest"', '},"deployment_manifest"', 1)
        if repaired_room != candidate:
            repair_variants.append(repaired_room)
            repaired_room_sections = repaired_room
            for section in ("resolution", "cooldown", "deck_pools", "required_engine_changes", "inspiration_notes", "self_critique"):
                repaired_room_sections = repaired_room_sections.replace('}}]},"' + section + '"', '}]},"' + section + '"')
                repaired_room_sections = repaired_room_sections.replace(']}]},"' + section + '"', '}]},"' + section + '"')
            repaired_room_sections = repaired_room_sections.replace(']}},\"anchors\"', ']},\"anchors\"', 1)
            if repaired_room_sections != repaired_room:
                repair_variants.append(repaired_room_sections)
        for repaired in repair_variants:
            if repaired == candidate:
                continue
            try:
                payload = json.loads(repaired)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                return payload
        debug_path = GENERATED_DIR / "last_invalid_blueprint_response.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(text, encoding="utf-8")
        raise SystemExit(f"Model returned invalid JSON:\n{stripped[:1600]}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Model JSON root must be an object")
    return payload


def _decode_anthropic_response(raw: str) -> dict[str, Any]:
    response_payload = json.loads(raw)
    text_parts = [
        str(part.get("text", ""))
        for part in response_payload.get("content", [])
        if isinstance(part, dict) and part.get("type") == "text"
    ]
    return extract_json("\n".join(text_parts))


def _decode_anthropic_stream(response: Any) -> dict[str, Any]:
    text_parts: list[str] = []
    stop_reason = ""
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            break
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "error":
            raise SystemExit(f"Anthropic stream error: {json.dumps(event.get('error', event), ensure_ascii=False)}")
        if event.get("type") == "message_delta":
            delta = event.get("delta", {})
            if isinstance(delta, dict):
                stop_reason = str(delta.get("stop_reason", "") or stop_reason)
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if isinstance(delta, dict) and delta.get("type") == "text_delta":
                text_parts.append(str(delta.get("text", "")))
    text = "".join(text_parts)
    if stop_reason == "max_tokens":
        debug_path = GENERATED_DIR / "last_invalid_blueprint_response.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(text, encoding="utf-8")
        raise SystemExit(
            f"Anthropic stopped at max_tokens before completing JSON. "
            f"Raw partial saved to {debug_path}"
        )
    return extract_json(text)


def call_anthropic(system: str, user: str, model: str, max_output_tokens: int) -> dict[str, Any]:
    api_key = env_value("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set.")
    payload = {
        "model": model,
        "max_tokens": max_output_tokens,
        "temperature": 0.2,
        "stream": True,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "revelation-blueprint-agent/1.0",
            "Connection": "close",
        },
        method="POST",
    )
    attempts = int(os.environ.get("REVELATION_BLUEPRINT_API_ATTEMPTS", "2"))
    timeout = int(os.environ.get("REVELATION_BLUEPRINT_API_TIMEOUT", "180"))
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if payload.get("stream"):
                    return _decode_anthropic_stream(response)
                raw = response.read().decode("utf-8")
            return _decode_anthropic_response(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Anthropic API error {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, http.client.HTTPException) as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 6))
    raise SystemExit("Anthropic API connection failed:\n" + "\n".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="Specific room/scenario request.")
    parser.add_argument("--corpus-fragments", help="Compact selected corpus fragment JSON.")
    parser.add_argument("--corpus-limit", type=int, default=6)
    parser.add_argument("--max-excerpt-chars", type=int, default=420)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-input-tokens", type=int, default=DEFAULT_MAX_INPUT_TOKENS)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--out", default="generated/revelation_room_blueprint.json")
    parser.add_argument("--compile-out", help="Optional compiled scenario patch output path.")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt budget only; do not call the API.")
    parser.add_argument("--print-prompt", action="store_true", help="Print the assembled prompt JSON.")
    args = parser.parse_args()

    system, user = build_prompt(args)
    prompt_text = system + "\n" + user
    prompt_tokens = estimate_tokens(prompt_text)
    print(
        json.dumps(
            {
                "model": args.model,
                "estimated_input_tokens": prompt_tokens,
                "input_bytes": len(prompt_text.encode("utf-8")),
                "max_input_tokens": args.max_input_tokens,
                "max_output_tokens": args.max_output_tokens,
            },
            indent=2,
        )
    )
    if args.print_prompt:
        print(user)
    if prompt_tokens > args.max_input_tokens:
        raise SystemExit(
            f"prompt budget exceeded: estimated {prompt_tokens} tokens > {args.max_input_tokens}. "
            "Reduce corpus limit, excerpt chars, or prompt size."
        )
    if args.dry_run:
        return 0

    blueprint = call_anthropic(system, user, args.model, args.max_output_tokens)
    errors = compiler.validate_blueprint(blueprint)
    if errors:
        blueprint["_validation_errors"] = errors

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, blueprint)
    print(out)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2

    if args.compile_out:
        compiled = compiler.compile_patch(blueprint)
        compile_out = Path(args.compile_out)
        if not compile_out.is_absolute():
            compile_out = ROOT / compile_out
        write_json(compile_out, compiled)
        print(compile_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
