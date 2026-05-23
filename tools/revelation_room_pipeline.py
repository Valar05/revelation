#!/usr/bin/env python3
"""Run the Revelation room generation/apply/verification pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
GENERATED = ROOT / "generated"

ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
DECKS_PATH = ROOT / "encounter_decks_post_update.json"
BLUEPRINT_AGENT = TOOLS / "revelation_blueprint_agent.py"
BLUEPRINT_COMPILER = TOOLS / "revelation_blueprint_compiler.py"
SCENARIO_AGENT = TOOLS / "scenario_agent.py"
PROJECT_BOOTSTRAP = TOOLS / "project_bootstrap.py"
CONTENT_AUDITOR = TOOLS / "revelation_content_auditor.py"
POST_UPDATE_SMOKE = TOOLS / "post_update_room_smoke.gd"
STORY_FOLLOWUP_SMOKE = TOOLS / "story_followup_smoke.gd"

OPENING_ROOM_ID = "institute_initial_briefing"
OPENING_EVENT_ID = "captain_initial_report"


def resolve_path(path_arg: str | None, default: Path | None = None) -> Path | None:
    if not path_arg:
        return default
    path = Path(path_arg)
    if not path.is_absolute():
        path = ROOT / path
    return path


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def run(cmd: list[str], label: str, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"\n== {label}")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def patch_room_ids(patch: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for room in patch.get("room_records", []) or []:
        if isinstance(room, dict) and str(room.get("id", "")).strip():
            room_id = str(room["id"]).strip()
            if room_id not in ids:
                ids.append(room_id)
    for item in patch.get("events", []) or []:
        if isinstance(item, dict) and str(item.get("room_id", "")).strip():
            room_id = str(item["room_id"]).strip()
            if room_id not in ids:
                ids.append(room_id)
    return ids


def patch_event_ids(patch: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in patch.get("events", []) or []:
        if isinstance(item, dict) and isinstance(item.get("event"), dict):
            event_id = str(item["event"].get("id", "")).strip()
            if event_id:
                ids.add(event_id)
    for event in patch.get("special_events", []) or []:
        if isinstance(event, dict):
            event_id = str(event.get("id", "")).strip()
            if event_id:
                ids.add(event_id)
    return ids


def patch_special_event_ids(patch: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for event in patch.get("special_events", []) or []:
        if isinstance(event, dict) and str(event.get("id", "")).strip():
            ids.append(str(event["id"]).strip())
    return ids


def existing_event_ids() -> set[str]:
    events_payload = load_json(EVENTS_PATH)
    ids: set[str] = set()
    for events in (events_payload.get("room_events", {}) or {}).values():
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict) and str(event.get("id", "")).strip():
                    ids.add(str(event["id"]).strip())
    for event_id in (events_payload.get("special_events", {}) or {}).keys():
        ids.add(str(event_id))
    return ids


def snapshot_active_data() -> dict[Path, dict[str, Any]]:
    return {
        ROOMS_PATH: load_json(ROOMS_PATH),
        EVENTS_PATH: load_json(EVENTS_PATH),
        DECKS_PATH: load_json(DECKS_PATH),
    }


def restore_active_data(snapshot: dict[Path, dict[str, Any]]) -> None:
    for path, payload in snapshot.items():
        write_json(path, payload)


def preprune_patch_conflicts(patch: dict[str, Any]) -> dict[Path, dict[str, Any]] | None:
    room_ids = set(patch_room_ids(patch))
    event_ids = patch_event_ids(patch)
    if not room_ids and not event_ids:
        return None
    if not event_ids.intersection(existing_event_ids()):
        return None

    snapshot = snapshot_active_data()
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms_payload["rooms"] = [
        room
        for room in rooms_payload.get("rooms", []) or []
        if not (isinstance(room, dict) and str(room.get("id", "")) in room_ids)
    ]

    room_events = events_payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id in room_ids:
            room_events.pop(room_id, None)
        for events in room_events.values():
            if isinstance(events, list):
                events[:] = [
                    event
                    for event in events
                    if not (isinstance(event, dict) and str(event.get("id", "")) in event_ids)
                ]

    special_events = events_payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id in event_ids:
            special_events.pop(event_id, None)

    room_pools = decks_payload.get("room_pools", {})
    if isinstance(room_pools, dict):
        for pool in room_pools.values():
            if isinstance(pool, list):
                pool[:] = [room_id for room_id in pool if str(room_id) not in room_ids]
    starter_rooms = decks_payload.get("starter_rooms", [])
    if isinstance(starter_rooms, list):
        decks_payload["starter_rooms"] = [room_id for room_id in starter_rooms if str(room_id) not in room_ids]
    if str(decks_payload.get("first_room_after_opening", "")) in room_ids:
        decks_payload["first_room_after_opening"] = ""

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print(f"Pre-pruned existing active content for {', '.join(sorted(room_ids))} to avoid duplicate ids.")
    return snapshot


def slice_active_to_room(room_id: str, patch: dict[str, Any]) -> None:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms_payload["rooms"] = [
        room
        for room in rooms_payload.get("rooms", []) or []
        if isinstance(room, dict) and str(room.get("id", "")) in {OPENING_ROOM_ID, room_id}
    ]

    room_events = events_payload.get("room_events", {})
    if isinstance(room_events, dict):
        events_payload["room_events"] = {room_id: room_events.get(room_id, [])}
    else:
        events_payload["room_events"] = {room_id: []}

    keep_special = {OPENING_EVENT_ID, *patch_special_event_ids(patch)}
    special_events = events_payload.get("special_events", {})
    if isinstance(special_events, dict):
        events_payload["special_events"] = {
            event_id: event
            for event_id, event in special_events.items()
            if str(event_id) in keep_special
        }
        update_opening_event(events_payload["special_events"].get(OPENING_EVENT_ID), room_id)

    decks_payload["first_room_after_opening"] = room_id
    decks_payload["starter_rooms"] = [room_id]
    decks_payload["draw_rules"] = [{"pool": "mission", "count": 1}]
    room_pools = decks_payload.setdefault("room_pools", {})
    if isinstance(room_pools, dict):
        for pool_name in list(room_pools.keys()):
            if pool_name == "enemy":
                room_pools[pool_name] = []
            elif pool_name in {
                "mission",
                "branch",
                "straight_noncombat",
                "recovery",
                "random_non_special",
                "action_horror",
            }:
                room_pools[pool_name] = [room_id]
            else:
                room_pools[pool_name] = []

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print(f"Active deck sliced to only playable room `{room_id}`.")


def update_opening_event(opening: Any, room_id: str) -> None:
    if not isinstance(opening, dict):
        return
    rooms_payload = load_json(ROOMS_PATH)
    room = next(
        (
            record
            for record in rooms_payload.get("rooms", []) or []
            if isinstance(record, dict) and str(record.get("id", "")) == room_id
        ),
        {},
    )
    room_name = str(room.get("name", room_id))
    description = str(room.get("description", "A Revelation field packet is ready."))
    opening["line_1"] = "Symbolic incidents are no longer isolated. The first playable packet is ready for field deployment."
    opening["line_2"] = f"Torah deploys with the assigned squad. Current packet: {room_name}."
    result = opening.get("action_results", {}).get("intercept")
    if isinstance(result, dict):
        result["lines"] = [f"The first packet opens: {room_name}. {description}"]
        result["environment_state_changes"] = [f"{room_id}_packet_opened"]


def set_followups_immediate(patch: dict[str, Any]) -> None:
    for item in patch.get("events", []) or []:
        if isinstance(item, dict) and isinstance(item.get("event"), dict):
            normalize_followups(item["event"])
    for event in patch.get("special_events", []) or []:
        if isinstance(event, dict):
            normalize_followups(event)


def normalize_followups(event: dict[str, Any]) -> None:
    followups = event.get("story_followups")
    if not isinstance(followups, dict):
        return
    for value in followups.values():
        if isinstance(value, dict):
            value["delay_rooms"] = 0
            value["immediate"] = True
            value["reactivate_on_reshuffle"] = False


def validate_doc_browser(room_id: str, host: str, port: int) -> None:
    base_url = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(base_url + "/", timeout=5) as response:
            index = response.read().decode("utf-8", errors="replace")
        with urllib.request.urlopen(base_url + f"/rooms/{room_id}", timeout=5) as response:
            room_page = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(f"Doc browser check failed at {base_url}: {exc}") from exc
    if room_id not in index or room_id not in room_page:
        raise SystemExit(f"Doc browser is reachable but `{room_id}` is not visible.")
    print(f"Doc browser shows `{room_id}` at {base_url}/rooms/{room_id}")


def build_blueprint(args: argparse.Namespace, blueprint_path: Path, patch_path: Path) -> None:
    if args.prompt is None:
        raise SystemExit("--prompt is required unless --blueprint or --patch is supplied")
    cmd = [
        sys.executable,
        str(BLUEPRINT_AGENT),
        "--prompt",
        args.prompt,
        "--corpus-limit",
        str(args.corpus_limit),
        "--max-excerpt-chars",
        str(args.max_excerpt_chars),
        "--max-input-tokens",
        str(args.max_input_tokens),
        "--max-output-tokens",
        str(args.max_output_tokens),
        "--model",
        args.model,
        "--out",
        str(blueprint_path),
        "--compile-out",
        str(patch_path),
    ]
    if args.corpus_fragments:
        cmd.extend(["--corpus-fragments", args.corpus_fragments])
    if args.print_prompt:
        cmd.append("--print-prompt")
    if args.dry_run:
        cmd.append("--dry-run")
    run(cmd, "Blueprint generation")


def compile_blueprint(blueprint_path: Path, patch_path: Path) -> None:
    run(
        [
            sys.executable,
            str(BLUEPRINT_COMPILER),
            str(blueprint_path),
            "--out",
            str(patch_path),
        ],
        "Blueprint compile",
    )


def validate_patch(patch_path: Path, allow_new_actions: bool = False) -> None:
    cmd = [
        sys.executable,
        str(SCENARIO_AGENT),
        "validate",
        str(patch_path),
        "--strict-tradeoffs",
    ]
    if allow_new_actions:
        cmd.append("--allow-new-actions")
    run(cmd, "Scenario patch validation")


def apply_patch_file(patch_path: Path, allow_new_actions: bool = False) -> None:
    cmd = [
        sys.executable,
        str(SCENARIO_AGENT),
        "apply",
        str(patch_path),
        "--strict-tradeoffs",
    ]
    if allow_new_actions:
        cmd.append("--allow-new-actions")
    run(cmd, "Scenario patch apply")


def run_verification(args: argparse.Namespace, room_id: str) -> None:
    run([sys.executable, str(PROJECT_BOOTSTRAP), "--strict"], "Project bootstrap")
    run([sys.executable, str(CONTENT_AUDITOR), "--strict"], "Revelation content auditor")
    if not args.skip_doc_check:
        validate_doc_browser(room_id, args.doc_host, args.doc_port)
    if not args.skip_smoke:
        run(
            [
                "godot",
                "--headless",
                "--path",
                str(ROOT),
                "--script",
                str(POST_UPDATE_SMOKE),
            ],
            "Godot room smoke",
        )
        run(
            [
                "godot",
                "--headless",
                "--path",
                str(ROOT),
                "--script",
                str(STORY_FOLLOWUP_SMOKE),
            ],
            "Godot story follow-up smoke",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", help="Generation prompt for a new room.")
    parser.add_argument("--corpus-fragments", help="Selected corpus packet JSON.")
    parser.add_argument("--corpus-limit", type=int, default=4)
    parser.add_argument("--max-excerpt-chars", type=int, default=170)
    parser.add_argument("--max-input-tokens", type=int, default=7000)
    parser.add_argument("--max-output-tokens", type=int, default=12000)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--blueprint", help="Use an existing blueprint JSON instead of making a paid generation call.")
    parser.add_argument("--patch", help="Use an existing compiled patch JSON instead of generating or compiling.")
    parser.add_argument("--out-prefix", default="generated/revelation_room_pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Only run the blueprint agent budget check.")
    parser.add_argument("--print-prompt", action="store_true")
    parser.add_argument("--no-apply", action="store_true", help="Generate/compile/validate only.")
    parser.add_argument("--replace-active", action="store_true", help="After apply, make the new room the only playable room.")
    parser.add_argument("--allow-new-actions", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--skip-doc-check", action="store_true")
    parser.add_argument("--doc-host", default="127.0.0.1")
    parser.add_argument("--doc-port", type=int, default=3003)
    args = parser.parse_args()

    out_prefix = resolve_path(args.out_prefix)
    assert out_prefix is not None
    blueprint_path = resolve_path(args.blueprint, out_prefix.with_name(out_prefix.name + "_blueprint.json"))
    patch_path = resolve_path(args.patch, out_prefix.with_name(out_prefix.name + "_compiled_patch.json"))
    assert blueprint_path is not None
    assert patch_path is not None

    if args.patch:
        print(f"Using compiled patch {patch_path}")
    elif args.blueprint:
        compile_blueprint(blueprint_path, patch_path)
    else:
        build_blueprint(args, blueprint_path, patch_path)
        if args.dry_run:
            return 0

    patch = load_json(patch_path)
    set_followups_immediate(patch)
    write_json(patch_path, patch)

    room_ids = patch_room_ids(patch)
    if len(room_ids) != 1:
        raise SystemExit(f"Expected exactly one room in patch; found {room_ids}")
    room_id = room_ids[0]

    preprune_snapshot = preprune_patch_conflicts(patch) if args.replace_active else None
    try:
        validate_patch(patch_path, allow_new_actions=args.allow_new_actions)
        if args.no_apply:
            print(f"Validated `{room_id}` without applying.")
            return 0
        apply_patch_file(patch_path, allow_new_actions=args.allow_new_actions)
        if args.replace_active:
            slice_active_to_room(room_id, patch)
        run_verification(args, room_id)
    except BaseException:
        if preprune_snapshot is not None:
            restore_active_data(preprune_snapshot)
            print("Restored active data after pipeline failure.", file=sys.stderr)
        raise

    print(f"\nPIPELINE_OK room={room_id} patch={patch_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
