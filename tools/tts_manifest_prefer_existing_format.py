#!/usr/bin/env python3
"""Repoint generated TTS manifest entries to existing files of a preferred format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "audio" / "tts_manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def resource_to_path(resource_path: str) -> Path:
    if not resource_path.startswith("res://"):
        raise ValueError(f"Unsupported non-resource path: {resource_path}")
    return ROOT / resource_path.removeprefix("res://")


def path_to_resource(path: Path) -> str:
    return "res://" + str(path.relative_to(ROOT))


def prefer_format(manifest: dict[str, Any], extension: str) -> int:
    generated_file_by_key: dict[str, str] = {}
    changed = 0

    generated = manifest.get("generated", [])
    if not isinstance(generated, list):
        return 0

    for entry in generated:
        if not isinstance(entry, dict):
            continue
        generation_key = str(entry.get("generation_key", "")).strip()
        clip_file = str(entry.get("file", "")).strip()
        if not generation_key or not clip_file:
            continue
        current_path = resource_to_path(clip_file)
        preferred_path = current_path.with_suffix(extension)
        if preferred_path.exists() and current_path != preferred_path:
            entry["file"] = path_to_resource(preferred_path)
            changed += 1
        generated_file_by_key[generation_key] = str(entry.get("file", ""))

    clips = manifest.get("clips", [])
    if isinstance(clips, list):
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            generation_key = str(clip.get("generation_key", "")).strip()
            preferred_file = generated_file_by_key.get(generation_key, "")
            if preferred_file and clip.get("file") != preferred_file:
                clip["file"] = preferred_file

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--format", default="mp3", choices=["mp3", "wav", "opus", "aac", "flac"])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    manifest = load_json(manifest_path)
    changed = prefer_format(manifest, "." + args.format.lstrip("."))
    if not args.check:
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(f"TTS_MANIFEST_PREFER_FORMAT format={args.format} changed={changed} check={args.check}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
