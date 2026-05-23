#!/usr/bin/env python3
"""Run the Revelation doc browser and restart it when local docs change."""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "room_doc_browser.py"
WATCH_PATHS = [
    ROOT / "tools" / "room_doc_browser.py",
    ROOT / "rooms_post_update.json",
    ROOT / "events_post_update.json",
    ROOT / "encounter_decks_post_update.json",
    ROOT / ".agent-memory",
    ROOT / "generated",
]
IGNORED_DIRS = {"__pycache__", ".git"}


def iter_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path]
    files: list[Path] = []
    for child in path.rglob("*"):
        if any(part in IGNORED_DIRS for part in child.parts):
            continue
        if child.is_file():
            files.append(child)
    return files


def snapshot(paths: list[Path]) -> dict[str, int]:
    state: dict[str, int] = {}
    for path in paths:
        for file_path in iter_files(path):
            try:
                state[str(file_path)] = file_path.stat().st_mtime_ns
            except OSError:
                continue
    return state


def start_server(host: str, port: int) -> subprocess.Popen[bytes]:
    cmd = [
        sys.executable,
        str(SERVER),
        "--host",
        host,
        "--port",
        str(port),
    ]
    print("Starting doc browser:", " ".join(cmd), flush=True)
    return subprocess.Popen(cmd, cwd=str(ROOT))


def stop_server(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3003)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    running = True

    def handle_stop(signum: int, frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    state = snapshot(WATCH_PATHS)
    process = start_server(args.host, args.port)
    try:
        while running:
            time.sleep(max(args.interval, 0.2))
            if process.poll() is not None:
                print("Doc browser exited; restarting.", flush=True)
                process = start_server(args.host, args.port)
                state = snapshot(WATCH_PATHS)
                continue
            next_state = snapshot(WATCH_PATHS)
            if next_state != state:
                print("Doc files changed; restarting doc browser.", flush=True)
                stop_server(process)
                process = start_server(args.host, args.port)
                state = next_state
    finally:
        stop_server(process)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
