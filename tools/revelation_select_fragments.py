#!/usr/bin/env python3
"""Build compact Revelation source packets from indexed corpus chunk ids."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "generated" / "corpus" / "index" / "chunks.jsonl"


def compact(text: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def load_chunks(path: Path) -> dict[str, dict[str, Any]]:
    chunks: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            chunk = json.loads(line)
            chunk_id = str(chunk.get("chunk_id", "")).strip()
            if chunk_id:
                chunks[chunk_id] = chunk
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--chunk", action="append", required=True, help="source chunk id")
    parser.add_argument("--excerpt-chars", type=int, default=850)
    args = parser.parse_args()

    chunks = load_chunks(CHUNKS_PATH)
    fragments: list[dict[str, Any]] = []
    missing: list[str] = []
    for index, chunk_id in enumerate(args.chunk, start=1):
        chunk = chunks.get(chunk_id)
        if not chunk:
            missing.append(chunk_id)
            continue
        fragments.append(
            {
                "id": f"selected_{index:02d}",
                "source_id": chunk.get("source_id", ""),
                "source_title": chunk.get("title", ""),
                "source_chunk_id": chunk_id,
                "source_circumstance": compact(str(chunk.get("text", "")), 320),
                "source_excerpt": compact(str(chunk.get("text", "")), args.excerpt_chars),
                "nightmare_room_seed": "Transform this source action into a contemporary Revelation mission with a concrete moral cause, active symbolic manifestation, tactical pressure, and local closure.",
                "escalation_thread": "Escalate from evidence to contact to consequence; do not repeat the same phenomenon with new wording.",
                "suggested_actions": ["intercept", "seal", "recover", "torah_speaks", "clinic", "full_disclosure"],
                "generation_rules": [
                    "The source must survive visibly as objects, sounds, documents, bodies, timings, or procedures in player-facing prose.",
                    "Each choice must be a character's plan, written as direct speaker dialogue without a Plan: prefix.",
                    "The room must identify the sin or moral failure and provide a path to close the local phenomenon.",
                    "Do not show numeric rewards, morale labels, odds, or hidden stat names in player-facing prose.",
                ],
            }
        )

    if missing:
        raise SystemExit(f"Missing chunks: {', '.join(missing)}")
    payload = {"name": args.name, "purpose": args.purpose, "fragments": fragments}
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Wrote {out} with {len(fragments)} fragments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
